# Implementation Plan: Milestone 1 — 分析快照层 + API 端点 + 安全基线

> 来源：PLAN_OPENCLAW_INTEGRATION.md v2（Codex 复审通过，overall 8.0/10）
>
> 范围：Milestone 1A + 1B（分析快照服务层 + API 端点 + 安全基线）
>
> 不含：M2 部署、M3 感知代理、M4 决策代理

---

## Phase 1A: 分析快照服务层

### Step 1: 创建 data_adapter.py

**文件**: `src/services/data_adapter.py`（新建）

**职责**: 统一调用 `gamma_shock_BYTE.py` 的数据获取和信号检测函数，避免重复取数

**关键接口**:
- `MarketDataAdapter.fetch_all(symbol)` → 返回 `{futures_data, daily_data, current_price}`
- `MarketDataAdapter.extract_signal(futures_data, daily_data, symbol)` → 返回标准化信号 dict

**依赖的现有函数**（均来自 `gamma_shock_BYTE.py`，只 import 不修改）:
- `get_futures_minute_data()` (line 382)
- `get_futures_daily_data()` (line 461)
- `calculate_technical_indicators()` (line 525 附近)
- `calculate_daily_technical_indicators()` (line 590 附近)
- `detect_futures_signals()` (line 660)

**验证命令**:
```bash
cd /path/to/battery_cost_monitor
python3 -c "
import sys; sys.path.insert(0, '.'); sys.path.insert(0, 'src/services')
from data_adapter import MarketDataAdapter
adapter = MarketDataAdapter()
raw = adapter.fetch_all('LC0')
print(f'price: {raw[\"current_price\"]}')
signal = adapter.extract_signal(raw['futures_data'], raw['daily_data'])
print(f'signal: {signal[\"direction\"]} strength={signal[\"strength\"]}')
"
```

---

### Step 2: 创建 snapshot.py

**文件**: `src/services/snapshot.py`（新建）

**职责**: 聚合一次完整分析，缓存结果供 API 反复读取

**关键接口**:
- `AnalysisSnapshot.get_snapshot(force_refresh=False)` → 返回完整快照 dict
- 内部调用 `MarketDataAdapter` 获取数据
- 内部调用 `BatteryCostCalculator` 计算成本（传入价格，不让它自己取数）
- 内部调用 `PricePredictor` 获取预测（传入数据，不让它自己取数）

**缓存策略**:
- TTL = `os.getenv("SNAPSHOT_CACHE_TTL", 300)` 秒
- `force_refresh=True` 时跳过缓存
- 底层数据失败时返回旧缓存 + `"stale": true`

**输出 schema**: 与 PLAN 文档第四节「GET /api/latest」一致

**注意**: snapshot 需要处理 `cost_calculator` 和 `price_predictor` 目前各自内部取数的问题。两种策略任选：
- **策略 A（推荐）**: snapshot 取数后，直接用价格计算成本（绕过 cost_calculator 的 `_get_current_prices_from_futures`），只调用其 `_calculate_material_cost` 纯计算方法
- **策略 B**: 接受阶段性重复取数（底层有缓存兜底），先跑通再优化

**验证命令**:
```bash
python3 -c "
import sys; sys.path.insert(0, '.'); sys.path.insert(0, 'src/services')
from snapshot import AnalysisSnapshot
snap = AnalysisSnapshot()
result = snap.get_snapshot()
print(f'timestamp: {result[\"timestamp\"]}')
print(f'price: {result[\"price\"]}')
print(f'signal direction: {result[\"signal\"][\"direction\"]}')
print(f'cost total: {result[\"cost\"][\"total_per_pack\"]}')
# 第二次应该命中缓存
import time; time.sleep(1)
result2 = snap.get_snapshot()
print(f'cached_at same: {result[\"snapshot_cached_at\"] == result2[\"snapshot_cached_at\"]}')
"
```

---

### Step 3: 创建 __init__.py

**文件**: `src/services/__init__.py`（新建）

**内容**: 空文件或简单导出

---

## Phase 1B: API 端点 + 安全基线

### Step 4: 更新 config.py

**文件**: `config.py`（修改）

**新增配置项**（全部走环境变量，config.py 只放读取逻辑和默认值）:
```python
# API 配置
API_CONFIG = {
    'api_key': os.getenv('API_KEY', ''),
    'snapshot_cache_ttl': int(os.getenv('SNAPSHOT_CACHE_TTL', '300')),
    'cors_origins': os.getenv('CORS_ORIGINS', 'http://localhost:5001').split(','),
}
```

**验证**: import 后打印配置确认环境变量生效

---

### Step 5: 更新 web_server.py — API Key 中间件

**文件**: `web_server.py`（修改）

**新增**:
1. `@app.before_request` 中间件：检查 `/api/latest` 和 `/api/refresh` 的 `X-API-Key` header
2. `/api/status` 免鉴权（供容器探活）
3. 统一错误处理：404、401、500 均返回 `{"error": true, "code": "...", "message": "..."}`

---

### Step 6: 更新 web_server.py — 新增 /api/latest

**文件**: `web_server.py`（修改）

**新增路由**: `GET /api/latest`
- 初始化全局 `AnalysisSnapshot` 实例
- 调用 `snapshot.get_snapshot()` 返回 JSON

---

### Step 7: 更新 web_server.py — 修改 /api/refresh

**文件**: `web_server.py`（修改）

**修改**: `POST /api/refresh` 改为调用 `snapshot.get_snapshot(force_refresh=True)` 并返回快照 JSON

---

### Step 8: 更新 web_server.py — CORS 限制

**文件**: `web_server.py`（修改）

**修改**: `CORS(app)` 改为 `CORS(app, origins=API_CONFIG['cors_origins'])`

---

### Step 9: 更新 .env 和 env_example.txt

**文件**: `.env`, `env_example.txt`（修改）

**新增**:
```
# API 鉴权
API_KEY=your_api_key_here

# 快照缓存（秒）
SNAPSHOT_CACHE_TTL=300

# CORS 允许来源（逗号分隔）
CORS_ORIGINS=http://localhost:5001
```

---

### Step 10: 运行 4 个最小测试用例

| # | 测试 | 命令 | 期望 |
|---|------|------|------|
| T1 | latest 成功 | `curl -H "X-API-Key: $KEY" localhost:5001/api/latest` | 200 + JSON |
| T2 | 鉴权失败 | `curl localhost:5001/api/latest` | 401 |
| T3 | 缓存命中 | 连续两次 latest，对比 `snapshot_cached_at` | 相同 |
| T4 | refresh 强制刷新 | `curl -X POST -H "X-API-Key: $KEY" localhost:5001/api/refresh` | 200 + 新 `snapshot_cached_at` |

---

## 文件变更清单

| 文件 | 操作 | 步骤 |
|------|------|------|
| `src/services/__init__.py` | 新建 | Step 3 |
| `src/services/data_adapter.py` | 新建 | Step 1 |
| `src/services/snapshot.py` | 新建 | Step 2 |
| `config.py` | 修改 | Step 4 |
| `web_server.py` | 修改 | Step 5-8 |
| `.env` | 修改 | Step 9 |
| `env_example.txt` | 修改 | Step 9 |

---

## 执行顺序

```
Step 1 → Step 2 → Step 3     # Phase 1A: 快照服务层（可独立验证）
    ↓
Step 4 → Step 5 → Step 6 → Step 7 → Step 8 → Step 9   # Phase 1B: API + 安全
    ↓
Step 10                        # 验证
```

---

## 不做的事（scope guard）

- 不修改 `gamma_shock_BYTE.py` 内部逻辑
- 不修改 `cost_calculator.py` 内部逻辑
- 不新增 `/api/signal`、`/api/cost`、`/api/prediction` 独立端点
- 不做自适应频率
- 不做回溯学习
- 不改 Docker 配置（M2 再做）
- 不改 nginx 配置（M2 再做）
