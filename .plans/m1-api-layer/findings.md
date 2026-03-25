# Findings: M1 实施前调研

## 现有代码关键发现

### 1. 信号检测函数签名
`gamma_shock_BYTE.py:660` — `detect_futures_signals(data, symbol, daily_data=None)` → `(market_data_dict, signal_detected_bool)`

market_data 包含 40+ 字段，需要在 data_adapter 中精简为 API schema 所需字段。

### 2. 底层缓存已存在
- 分钟线缓存：`gamma_shock_BYTE.py:391-404`，TTL = period * 60 秒
- 日线缓存：`gamma_shock_BYTE.py:471-485`，TTL = 当日有效
- 不需要在 snapshot 层重复做行情缓存，只缓存"分析结果快照"

### 3. cost_calculator 内部取数
`cost_calculator.py:53` `_get_current_prices_from_futures()` 内部调用 `get_futures_minute_data()`。
snapshot 层有两种处理策略：
- 策略 A（推荐）：绕过此方法，直接用 adapter 获取的价格调用 `_calculate_material_cost()`
- 策略 B：接受重复取数（底层有缓存，实际只多一次缓存读取）

### 4. price_predictor 内部取数
`src/core/price_predictor.py:30` 内部也调用 `get_futures_minute_data()` 和 `get_futures_daily_data()`。
同理，可用策略 A 或 B。

### 5. CORS 当前全开
`web_server.py:37` — `CORS(app)` 无限制，需改为白名单。

### 6. 端口已改为 5001
`web_server.py:222` — `app.run(host='0.0.0.0', port=5001)`（之前已修复）

### 7. load_dotenv 已添加
`web_server.py:14-18` — `from dotenv import load_dotenv; load_dotenv()`（之前已修复）

### 8. 空占位文件已处理
- `src/core/price_fetcher.py` — 已加 placeholder 注释
- `src/core/futures_integration.py` — 已加 placeholder 注释
