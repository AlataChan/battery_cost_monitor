# BatteryAI x OpenClaw 集成方案 v2

> 目标：将 battery_cost_monitor 从"看盘工具"升级为"自适应感知 + 采购决策"的智能代理系统
>
> 策略：方案二（采购决策助理）为终态，方案一（自适应监控代理）为第一个里程碑
>
> 最终形态：方案一负责感知，方案二负责决策，串联运行
>
> v2 变更：整合 Codex Plan Review 反馈（v1 评分 6.5/10），重点修正 M1 分层、信号源、安全基线、MVP 精简

---

## 一、系统架构总览

```
┌─────────────────────────────────────────────────────────┐
│                    OpenClaw Skill 层                      │
│                                                          │
│  skill: battery-monitor     skill: procurement-advisor   │
│  （感知代理 - 方案一）        （决策代理 - 方案二）         │
│                                                          │
│       ↓ 调用 API                    ↓ 读取感知层输出       │
│       ↓ 读取记忆                    ↓ 结合业务上下文       │
│       ↓ 写入记忆                    ↓ 生成建议（人工确认）  │
└────────────────────┬────────────────┬────────────────────┘
                     │                │
                     ▼                ▼
┌─────────────────────────────────────────────────────────┐
│              BatteryAI API 层（云端 Docker）              │
│                                                          │
│  GET  /api/latest          完整分析快照 JSON              │
│  POST /api/refresh         触发即时分析                   │
│  GET  /api/status          系统健康状态                   │
│                                                          │
│  /api/latest 包含所有子域数据（signal/cost/prediction）   │
│  无需独立端点，Agent 按需提取字段即可                     │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
┌──────────────────┐   ┌──────────────────────────────────┐
│  分析快照服务层   │   │     BatteryAI 核心引擎（现有）    │
│  (新增)          │   │                                   │
│  src/services/   │   │  gamma_shock_BYTE.py  期货+信号   │
│  snapshot.py     │   │  cost_calculator.py   成本换算    │
│                  │──▶│  ai_mentor.py         AI研判      │
│  职责：          │   │  price_predictor.py   综合预测    │
│  - 聚合一次分析  │   │  chart_generator.py   图表生成    │
│  - 缓存快照结果  │   │                                   │
│  - 统一输出格式  │   └──────────────────────────────────┘
└──────────────────┘
```

**v2 关键变更**：
- 新增 `src/services/snapshot.py` 分析快照服务层，聚合一次分析的全部结果并缓存
- API 精简为 3 个端点（`/api/latest`, `/api/refresh`, `/api/status`）
- 信号数据源明确来自 `gamma_shock_BYTE.py`（不从 cost_calculator 反推）
- 安全基线前移到 M1

---

## 二、里程碑拆分

### Milestone 1A：分析快照服务层（Week 1 前半）

**目标**：在核心引擎和 API 之间插入一个聚合层，避免每个端点各自重跑完整分析

#### 新增文件

```
src/services/__init__.py
src/services/snapshot.py      — 分析快照构建器
src/services/data_adapter.py  — 统一数据获取 adapter（避免重复取数）
```

#### snapshot.py 设计

```python
class AnalysisSnapshot:
    """聚合一次完整分析的所有结果，缓存供 API 反复读取"""

    def __init__(self):
        self._cache = None
        self._cache_time = None
        self._cache_ttl = 300  # 5 分钟缓存

    def get_snapshot(self, force_refresh=False) -> dict:
        """获取或刷新分析快照"""
        if not force_refresh and self._cache and not self._is_expired():
            return self._cache

        snapshot = self._build_snapshot()
        self._cache = snapshot
        self._cache_time = datetime.now()
        return snapshot

    def _build_snapshot(self) -> dict:
        """一次性构建完整快照（调用各核心模块）"""
        # 1. 获取期货数据 + 技术指标（来自 gamma_shock_BYTE.py）
        futures_data = get_futures_minute_data("LC0")
        daily_data = get_futures_daily_data("LC0")
        futures_data = calculate_technical_indicators(futures_data)
        daily_data = calculate_daily_technical_indicators(daily_data)

        # 2. 提取信号（来自 gamma_shock_BYTE.py 的信号检测函数）
        signal = extract_signal(futures_data, daily_data)

        # 3. 成本计算（来自 cost_calculator.py）
        cost = calculate_cost(futures_data)

        # 4. 价格预测 + AI分析（来自 price_predictor.py + ai_mentor.py）
        prediction = predict_price(futures_data, daily_data)

        # 5. 组装统一快照
        return {
            "timestamp": datetime.now().isoformat(),
            "price": { ... },
            "signal": signal,
            "cost": cost,
            "prediction": prediction,
            "ai_analysis": prediction.get("ai_analysis"),
            "data_source": "akshare_futures_LC0"
        }
```

**核心原则**：
- `_build_snapshot()` 只调用一次，所有数据复用同一份期货数据
- 信号提取封装自 `gamma_shock_BYTE.py` 的现有信号检测逻辑（约 line 660-740）
- 缓存 5 分钟，`/api/refresh` 强制刷新，`/api/latest` 读缓存

#### 数据共享 adapter 接口（v2 复审补充）

**问题**：当前 `cost_calculator.py:53` 和 `price_predictor.py:30` 各自内部调用 `get_futures_minute_data()`，会造成重复取数。

**解决**：snapshot 层统一取数据后，通过参数注入给下游模块。

```python
# src/services/data_adapter.py — 统一数据获取，供 snapshot 分发

from gamma_shock_BYTE import (
    get_futures_minute_data,
    get_futures_daily_data,
    calculate_technical_indicators,
    calculate_daily_technical_indicators,
    detect_futures_signals
)

class MarketDataAdapter:
    """统一获取行情数据，避免重复请求"""

    def fetch_all(self, symbol: str = "LC0") -> dict:
        """一次获取所有原始数据和技术指标"""
        futures_data = get_futures_minute_data(symbol)
        daily_data = get_futures_daily_data(symbol)

        if futures_data is not None:
            futures_data = calculate_technical_indicators(futures_data)
        if daily_data is not None:
            daily_data = calculate_daily_technical_indicators(daily_data)

        return {
            "futures_data": futures_data,
            "daily_data": daily_data,
            "current_price": futures_data['close'].iloc[-1] if futures_data is not None else None
        }

    def extract_signal(self, futures_data, daily_data, symbol: str = "LC0") -> dict:
        """从已有数据中提取信号（不重新取数）"""
        market_data, signal_detected = detect_futures_signals(futures_data, symbol, daily_data)
        if market_data is None:
            return {"direction": "unknown", "strength": 0, "confidence": 0}

        # 映射信号类型到标准方向
        direction = "neutral"
        if "多头" in market_data.get("signal_type", ""):
            direction = "bullish"
        elif "空头" in market_data.get("signal_type", ""):
            direction = "bearish"

        return {
            "direction": direction,
            "strength": market_data["signal_strength"],
            "confidence": min(market_data["signal_strength"] * 20, 100),
            "signal_type": market_data["signal_type"],
            "description": market_data["signal_type"],
            "indicators": {
                "ema_trend": market_data.get("trend_short"),
                "macd": f"DIF={market_data.get('DIF', 0):.2f}",
                "kdj_status": "oversold" if market_data.get("K_value", 50) < 20 else
                              "overbought" if market_data.get("K_value", 50) > 80 else "normal",
                "bollinger_position": market_data.get("bb_position"),
                "volume_ratio": round(market_data.get("vol_ratio", 0), 2)
            },
            "raw_market_data": market_data  # 保留完整数据供 AI 分析
        }
```

**snapshot.py 使用方式**：
```python
def _build_snapshot(self):
    adapter = MarketDataAdapter()
    raw = adapter.fetch_all("LC0")           # 取一次数据
    signal = adapter.extract_signal(         # 复用同一份数据
        raw["futures_data"], raw["daily_data"]
    )
    cost = self._calculate_cost(raw["current_price"])  # 复用价格
    prediction = self._predict(raw, signal)             # 复用数据+信号
    ...
```

这样 `cost_calculator` 和 `price_predictor` 的现有代码不需要修改内部逻辑，snapshot 层在外部协调数据流。

#### 涉及的现有文件修改

| 文件 | 修改内容 |
|------|----------|
| `gamma_shock_BYTE.py` | 不改内部逻辑，只 import 其公开函数 |
| `cost_calculator.py` | 不改内部逻辑，snapshot 直接用价格计算成本 |
| `config.py` | 新增 `API_KEY` 和 `SNAPSHOT_CACHE_TTL`，以环境变量为准，config.py 只放默认值 |

---

### Milestone 1B：API 端点 + 安全基线（Week 1 后半）

**目标**：暴露 3 个 JSON 端点，同时完成安全加固

#### API 端点（精简为 3 个）

| 端点 | 方法 | 返回内容 |
|------|------|----------|
| `GET /api/latest` | GET | 完整快照 JSON（包含 price/signal/cost/prediction/ai_analysis） |
| `POST /api/refresh` | POST | 触发强制刷新，返回新快照 |
| `GET /api/status` | GET | 系统状态（已有，增加 snapshot 缓存时间） |

`/api/latest` 包含所有子域数据。Agent 不需要 `/api/signal`、`/api/cost` 等独立端点——直接从 latest 的 JSON 中提取对应字段即可。

#### 安全基线（与 API 同步完成）

| 安全项 | 实现方式 | 位置 |
|--------|----------|------|
| API Key 鉴权 | Flask before_request 中间件（主），nginx 为补充 | web_server.py |
| CORS 限制 | `CORS(app, origins=["https://your-domain.com"])`，白名单写入 `.env` 的 `CORS_ORIGINS` | web_server.py |
| /api/status 访问控制 | 免鉴权但限内网/容器探活（nginx `allow 127.0.0.1; deny all;`） | nginx.conf |
| 输出面收敛 | 外网只暴露 `/api/latest` + `/api/refresh`，关闭 `/output/*`、dashboard | nginx.conf |
| 错误格式统一 | 所有错误返回 `{"error": true, "message": "...", "code": "..."}` | web_server.py |
| API Key 配置 | `API_KEY` 以环境变量为准，`config.py` 只放 `os.getenv("API_KEY")` | config.py / .env |
| 配置读取约定 | 所有新增配置项统一走 `os.getenv()` + `.env`，`config.py` 不硬编码新值 | config.py |

#### web_server.py 修改要点

```python
# 新增：API Key 中间件
@app.before_request
def check_api_key():
    if request.path.startswith('/api/') and request.path != '/api/status':
        api_key = request.headers.get('X-API-Key')
        if api_key != os.getenv('API_KEY'):
            return jsonify({"error": True, "message": "Invalid API Key", "code": "AUTH_FAILED"}), 401

# 新增：/api/latest
@app.route('/api/latest')
def api_latest():
    snapshot = analysis_snapshot.get_snapshot()
    return jsonify(snapshot)

# 修改：/api/refresh 返回快照而非 HTML 结果
@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    snapshot = analysis_snapshot.get_snapshot(force_refresh=True)
    return jsonify({"success": True, "snapshot": snapshot})

# 保留：/api/status（增加缓存信息）
```

---

### Milestone 2：云端 Docker 部署（Week 2）

**目标**：云服务器部署，OpenClaw 远程可调用

#### 部署步骤

```bash
git clone <repo>
cp env_example.txt .env
# 编辑 .env：DEEPSEEK_API_KEY, API_KEY
docker-compose up -d
```

#### nginx 安全配置更新

```nginx
# 只允许 /api/* 对外
location /api/ {
    # API Key 验证（双层保障）
    if ($http_x_api_key = "") { return 401; }

    proxy_pass http://battery_app;
    # ... headers
}

# 拒绝其他路径的外网访问
location / {
    allow 127.0.0.1;
    deny all;
}

# rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
location /api/ {
    limit_req zone=api burst=20 nodelay;
    # ...
}
```

#### HTTPS

```bash
# Let's Encrypt 自动证书
apt install certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

#### 验收标准

- [ ] `curl -H "X-API-Key: xxx" https://your-domain.com/api/latest` 返回完整快照
- [ ] 无 Key 请求返回 401
- [ ] `/output/*` 和 `/` 外网不可访问
- [ ] Docker 自动重启正常（`docker-compose restart` 后服务恢复）

---

### Milestone 3：感知代理 Skill（Week 2-3）

**目标**：OpenClaw `battery-monitor` Skill，固定频率 + 信号驱动推送

#### v2 变更：先固定频率，后自适应

v1 方案一上来就做自适应频率，Codex 指出这是过度设计。v2 改为：
- **第一版**：固定 15 分钟巡检（交易时段），复用 `gamma_shock_BYTE.py` 现有的交易时段判断
- **第二版（优化期）**：基于信号强度调整频率

#### Skill 核心逻辑

```python
def monitor_cycle():
    # 1. 交易时段判断（复用 gamma_shock_BYTE.py 的逻辑）
    if not is_trading_hours():
        return schedule_next("next_open")

    # 2. 获取快照
    snapshot = call_api("/api/latest")

    # 3. 读取信号记忆
    memory = read_memory("battery_signals")

    # 4. 信号演化判断
    evolution = {
        "direction_changed": snapshot.signal.direction != memory.last_direction,
        "strength_delta": snapshot.signal.strength - memory.last_strength,
        "consecutive": count_consecutive(memory, snapshot.signal.direction)
    }

    # 5. 保存当前状态到记忆
    save_memory("battery_signals", {
        "timestamp": snapshot.timestamp,
        "price": snapshot.price.current,
        "direction": snapshot.signal.direction,
        "strength": snapshot.signal.strength,
        "cost_change_pct": snapshot.cost.change_pct,
        "evolution": evolution
    })

    # 6. 推送判断（含冷却时间）
    should_push = (
        snapshot.signal.strength >= 4                          # 强信号
        or evolution.direction_changed                         # 方向反转
        or (evolution.consecutive >= 3 and not recently_pushed(memory, hours=2))  # 连续确认
    )

    if should_push:
        report = format_report(snapshot, memory, evolution)
        push_notification(report)

    # 7. 固定 15 分钟后再检查
    schedule_next("15min")
```

#### 记忆结构

```json
{
  "last_check": "2026-03-24 10:30:00",
  "last_direction": "bearish",
  "last_strength": 3,
  "consecutive_count": 3,
  "consecutive_since": "2026-03-22 14:00:00",
  "last_push_time": "2026-03-24 09:15:00",
  "signal_history_24h": [
    {"time": "2026-03-24 10:15:00", "direction": "bearish", "strength": 3, "price": 151440},
    {"time": "2026-03-24 10:00:00", "direction": "bearish", "strength": 2, "price": 151680}
  ]
}
```

#### 推送规则

| 条件 | 推送 | 冷却时间 |
|------|------|----------|
| 信号强度 ≥ 4 | 立即推送完整分析 | 2 小时 |
| 方向反转 | 立即推送 | 无冷却 |
| 连续 3 次同向确认 | 推送摘要 | 2 小时 |
| 信号强度 < 2 | 静默记录 | - |
| 非交易时段 | 收盘后发送日线摘要 | 每日一次 |

---

### Milestone 4：采购决策代理 Skill（Week 3-5）

**目标**：`procurement-advisor` Skill，市场信号 × 业务上下文 = 采购建议

#### v2 关键变更

1. **明确定位**：只生成建议，不自动执行采购。每条建议都需要人工确认
2. **回溯学习延后**：先做决策日志记录，学习闭环放到优化期
3. **置信度阈值**：置信度 < 50% 不出建议，只出"观察"

#### 业务上下文来源

首次使用时，通过对话交互收集：
```
Agent: "请告诉我贵司的月度碳酸锂需求量（吨）？"
User: "200吨"
Agent: "当前库存多少吨？"
User: "50吨"
...
```

后续自动更新：
- 每次采购后更新库存和 runway
- 每月初提醒更新需求量和预算

#### 决策矩阵（3x3 规则版）

```
                好时机               中性时机             差时机
              (技术看涨反转,        (震荡,无明确        (技术看跌,
               布林带下轨)           方向信号)           布林带上轨)
  ┌──────────┬──────────────────┬──────────────────┬──────────────────┐
  │ 高紧迫   │ 建议：立即采购    │ 建议：立即采购    │ 建议：少量采购    │
  │ (<30天)  │ 量：需求量80%    │ 量：需求量60%    │ 量：最低保障量    │
  │          │ 置信度：高        │ 置信度：中        │ 置信度：中        │
  ├──────────┼──────────────────┼──────────────────┼──────────────────┤
  │ 中紧迫   │ 建议：适量采购    │ 建议：观望        │ 建议：观望        │
  │ (30-60天)│ 量：需求量50%    │ 等待更好时机      │ 等待价格回落      │
  │          │ 置信度：高        │ 置信度：-         │ 置信度：-         │
  ├──────────┼──────────────────┼──────────────────┼──────────────────┤
  │ 低紧迫   │ 建议：战略建仓    │ 建议：观望        │ 建议：观望        │
  │ (>60天)  │ 量：需求量30%    │ 无需行动          │ 无需行动          │
  │          │ 置信度：中        │ 置信度：-         │ 置信度：-         │
  └──────────┴──────────────────┴──────────────────┴──────────────────┘
```

#### 建议输出格式

```json
{
  "decision_id": "DEC-20260324-001",
  "timestamp": "2026-03-24 10:30:00",
  "action": "buy",
  "requires_confirmation": true,
  "summary": "建议本周采购 80 吨碳酸锂",
  "quantity_tons": 80,
  "reasoning": {
    "urgency": "medium (库存45天)",
    "timing": "good (技术信号看涨反转，价格在布林带下轨)",
    "matrix_cell": "中紧迫 × 好时机 → 适量采购"
  },
  "price_context": {
    "current_price": 151440,
    "vs_last_purchase": "-1.02%",
    "vs_3month_avg": "-5.3%",
    "prediction_7d": "neutral_to_bearish"
  },
  "cost_impact": {
    "per_pack_cost": 6057.60,
    "total_purchase_cost": 12115200,
    "vs_budget_remaining": "40.38%"
  },
  "risk_note": "若下跌趋势延续，可分 2 批建仓（本周 40 吨 + 下周视情况）",
  "confidence": 72,
  "valid_until": "2026-03-25 15:00:00"
}
```

#### 决策日志

每次建议自动记录，用于事后复盘：

```json
{
  "decision_id": "DEC-20260324-001",
  "timestamp": "2026-03-24 10:30:00",
  "advice_summary": "适量采购 80 吨",
  "market_snapshot": {
    "price": 151440,
    "signal_direction": "bearish_reversal",
    "signal_strength": 3
  },
  "business_snapshot": {
    "inventory_tons": 50,
    "runway_days": 45,
    "urgency": "medium"
  },
  "user_action": null,
  "outcome_7d": null
}
```

`user_action` 和 `outcome_7d` 事后手动或自动填充。**回溯学习闭环放到 Week 5+ 优化期**。

---

## 三、技术栈选择

| 组件 | 技术 | 理由 |
|------|------|------|
| BatteryAI 核心 | Python 3.12 + Flask | 现有代码，保持不变 |
| 分析快照层 | src/services/snapshot.py（新增） | 解耦核心引擎和 API 层 |
| 期货数据 | akshare | 免费稳定，底层缓存已有（gamma_shock_BYTE.py） |
| AI 分析 | DeepSeek API | 性价比高 |
| 容器化 | Docker + docker-compose | 已验证 |
| 反向代理 | nginx + HTTPS + rate limit | 安全基线 |
| 感知代理 | OpenClaw Skill（与 BatteryAI 解耦） | 调用 API，不侵入内核 |
| 决策代理 | OpenClaw Skill（与 BatteryAI 解耦） | 业务上下文 + 决策矩阵 |
| 记忆存储 | OpenClaw Memory / JSON 文件 | 信号历史 + 决策日志 |
| 未来可选 | MCP Server | 接入 Claude 等更多 Agent |

---

## 四、接口契约（API Schema）

### GET /api/latest

一个端点返回所有数据，Agent 按需提取字段。

```json
{
  "timestamp": "2026-03-24T10:30:00",
  "data_source": "akshare_futures_LC0",
  "price": {
    "current": 151440,
    "unit": "元/吨"
  },
  "signal": {
    "direction": "bearish",
    "strength": 3,
    "confidence": 65,
    "description": "多重指标看跌确认，布林带下轨附近",
    "indicators": {
      "ema_trend": "bearish",
      "macd": "bearish_crossover",
      "kdj_status": "oversold",
      "bollinger_position": 0.15,
      "volume_ratio": 1.3
    }
  },
  "cost": {
    "total_per_pack": 6057.60,
    "baseline_per_pack": 3308.00,
    "change": 2749.60,
    "change_pct": 83.12,
    "unit": "元/pack(40kg LC)",
    "materials": {
      "LC": {
        "name": "碳酸锂",
        "price": 151440,
        "usage_kg": 40,
        "cost": 6057.60
      }
    }
  },
  "prediction": {
    "direction": "neutral_to_bearish",
    "price_range_7d": [148000, 154000],
    "confidence": 55,
    "ai_summary": "短期震荡偏弱..."
  },
  "ai_analysis": {
    "trend_judgment": "...",
    "risk_level": "medium",
    "market_sentiment": "bearish",
    "key_factors": ["布林带下轨支撑", "成交量放大", "KDJ超卖"]
  },
  "snapshot_cached_at": "2026-03-24T10:28:00",
  "snapshot_ttl_seconds": 300
}
```

### POST /api/refresh

```json
// Request: POST /api/refresh (Header: X-API-Key: xxx)
// Response:
{
  "success": true,
  "message": "分析刷新完成",
  "snapshot": { /* 同 /api/latest 结构 */ }
}
```

### GET /api/status

```json
{
  "status": "running",
  "last_analysis_time": "2026-03-24T10:28:00",
  "snapshot_cached": true,
  "snapshot_age_seconds": 120,
  "timestamp": "2026-03-24T10:30:00"
}
```

> 注意：`/api/status` 免鉴权，仅供内网/容器探活使用。不做实时 AI API 探测，避免健康检查变重。

### 错误响应格式（所有端点统一）

```json
{
  "error": true,
  "code": "AUTH_FAILED",
  "message": "Invalid or missing API Key",
  "timestamp": "2026-03-24T10:30:00"
}
```

---

## 五、推进节奏

```
Week 1 前半 ┃ Milestone 1A: 分析快照服务层
            ┃   ├── 新增 src/services/snapshot.py
            ┃   ├── 封装信号提取（来自 gamma_shock_BYTE.py）
            ┃   └── 快照缓存机制
            ┃
Week 1 后半 ┃ Milestone 1B: API + 安全基线
            ┃   ├── 3 个 JSON 端点（latest/refresh/status）
            ┃   ├── API Key 鉴权中间件
            ┃   ├── CORS 限制 + 输出面收敛
            ┃   ├── 统一错误格式
            ┃   └── 本地测试通过
            ┃
Week 2      ┃ Milestone 2: 云端部署
            ┃   ├── Docker 部署到云服务器
            ┃   ├── nginx HTTPS + rate limit
            ┃   ├── /api/* 外网可达，其他路径内网
            ┃   └── 远程 API 调通验收
            ┃
Week 2-3    ┃ Milestone 3: 感知代理
            ┃   ├── OpenClaw battery-monitor Skill
            ┃   ├── 固定 15 分钟巡检（交易时段）
            ┃   ├── 信号记忆 + 演化判断
            ┃   ├── 推送规则（强信号/反转/连续确认）
            ┃   └── 推送冷却（2 小时内不重复）
            ┃
Week 3-5    ┃ Milestone 4: 决策代理
            ┃   ├── OpenClaw procurement-advisor Skill
            ┃   ├── 业务上下文收集（对话交互）
            ┃   ├── 3x3 决策矩阵
            ┃   ├── 建议输出（人工确认制）
            ┃   ├── 置信度 < 50% 不出建议
            ┃   └── 决策日志记录
            ┃
Week 5+     ┃ 优化期
            ┃   ├── 自适应检查频率（基于信号强度）
            ┃   ├── 回溯学习闭环（outcome 填充 + 建议质量评估）
            ┃   ├── 接入更多数据源（行业新闻、库存系统）
            ┃   └── 可选：MCP Server 改造
```

---

## 六、风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| akshare 数据中断 | 无法获取实时价格 | 快照层返回缓存 + 标记 `stale: true` |
| DeepSeek API 故障 | AI 分析不可用 | 快照中 ai_analysis 为 null，纯技术指标仍可用 |
| 信号误判 | 错误采购建议 | 决策矩阵兜底 + 人工确认 + 置信度阈值 |
| 云服务器宕机 | 系统不可用 | Docker restart policy + 健康检查告警 |
| 记忆数据膨胀 | 查询变慢 | 只保留 24h 明细 + 90 天日级汇总 |
| 采购建议被误执行 | 经济损失 | 所有建议标记 `requires_confirmation: true` |
| 旧建议误导 | 过期信息被引用 | 每条建议有 `valid_until`，过期自动标记失效 |

---

## 七、阶段验收标准

### M1 完成标准
- [ ] `src/services/snapshot.py` 构建快照，缓存正常
- [ ] `GET /api/latest` 返回完整结构化 JSON（响应 < 3s）
- [ ] 无 API Key 请求返回 401
- [ ] CORS 限制生效
- [ ] 错误响应格式统一

#### M1 最小测试用例（v2 复审补充）

| # | 测试场景 | 输入 | 期望输出 |
|---|----------|------|----------|
| T1 | latest 成功 | `GET /api/latest` + 有效 API Key | 200 + 完整 JSON（含 price/signal/cost/prediction） |
| T2 | 鉴权失败 | `GET /api/latest` 无 Key / 错误 Key | 401 + `{"error": true, "code": "AUTH_FAILED"}` |
| T3 | 缓存命中 | 5 分钟内连续两次 `GET /api/latest` | 第二次 < 100ms，`snapshot_cached_at` 不变 |
| T4 | 底层数据失败 fallback | akshare 不可达（模拟断网） | 200 + 快照数据 + `"stale": true` 标记（返回缓存） |

测试命令示例：
```bash
# T1: 成功
curl -s -H "X-API-Key: $API_KEY" http://localhost:5001/api/latest | python3 -m json.tool

# T2: 鉴权失败
curl -s http://localhost:5001/api/latest  # 无 Key，应返回 401

# T3: 缓存命中（对比两次 snapshot_cached_at）
curl -s -H "X-API-Key: $API_KEY" http://localhost:5001/api/latest | python3 -c "import sys,json; print(json.load(sys.stdin)['snapshot_cached_at'])"
sleep 2
curl -s -H "X-API-Key: $API_KEY" http://localhost:5001/api/latest | python3 -c "import sys,json; print(json.load(sys.stdin)['snapshot_cached_at'])"
# 两次输出应相同

# T4: 强制刷新后验证
curl -s -X POST -H "X-API-Key: $API_KEY" http://localhost:5001/api/refresh | python3 -m json.tool
```

### M2 完成标准
- [ ] 云端 `curl -H "X-API-Key: xxx" https://domain/api/latest` 正常
- [ ] nginx 限制 `/output/*` 外网不可达
- [ ] HTTPS 证书有效
- [ ] Docker 重启后服务自动恢复

### M3 完成标准（启动 M4 的前提）
- [ ] Skill 固定 15 分钟巡检，交易时段内正常运行
- [ ] 信号记忆跨越 3 天，演化判断正确
- [ ] 强信号/反转推送及时（< 1 分钟延迟）
- [ ] 冷却机制生效（2 小时内不重复推送同类信号）

### M4 完成标准
- [ ] 业务上下文可通过对话收集和更新
- [ ] 决策矩阵 9 个格子均有合理输出
- [ ] 所有建议标注 `requires_confirmation: true` 和 `valid_until`
- [ ] 置信度 < 50% 不输出建议
- [ ] 决策日志完整记录
- [ ] 连续运行 2 周，用户满意度 > 70%

---

## 八、与 v1 的差异汇总

| 项目 | v1 | v2 | 变更原因 |
|------|----|----|----------|
| API 端点数 | 5 个独立端点 | 3 个（latest 包含全部） | Codex: MVP 精简，避免重复计算 |
| 服务分层 | 直接在 web_server.py 加路由 | 新增 snapshot.py 聚合层 | Codex: 避免每个端点各自跑完整分析 |
| 信号数据源 | cost_calculator.py | gamma_shock_BYTE.py | Codex: 信号逻辑实际在此文件 |
| 安全基线 | 分散在 M1 和 M2 | 前移到 M1B | Codex: 安全不应是事后加固 |
| M3 调度 | 一步到位自适应频率 | 先固定频率，后优化 | Codex: 自适应是过度设计 |
| M4 定位 | 决策系统（可能被理解为自动执行） | 建议系统 + 人工确认 | Codex: 必须明确只出建议 |
| 回溯学习 | M4 同步做 | 延后到优化期 | Codex: 先打通日志，再做学习 |
| 缓存策略 | API 层重复设计 | 复用底层缓存 + 快照层缓存 | Codex: 底层已有缓存，不重复 |
