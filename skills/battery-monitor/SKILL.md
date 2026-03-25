---
name: battery-monitor
description: Use when the user wants to run the BatteryAI lithium monitor, inspect signal evolution, or check whether a push notification should fire.
metadata:
  openclaw:
    requires:
      bins: ["python3"]
---

# Battery Monitor

Use this skill when the user asks to run the lithium market monitor, inspect signal evolution, or check whether a push notification should fire.

## Workflow

1. Run the monitor cycle:

```bash
python3 scripts/run_battery_monitor.py
```

2. Read the JSON result.
3. If `should_push` is `true`, summarize the `report` and the `evolution` block.
4. If `reason` is `outside_trading_hours`, tell the user the next check is deferred to the next trading session.

## Notes

- The bundled script finds the BatteryAI project root from `--project-root`, `BATTERY_MONITOR_PROJECT_ROOT`, `BATTERY_PROJECT_ROOT`, or the current workspace.
- If the project root cannot be found, ask the user to open the `battery_cost_monitor` repo as the workspace or provide `--project-root`.
- API data comes from `GET /api/latest`.
- State is stored in `data/agent_state/battery_signals.json` inside this skill package unless overridden.
- Use `--force` only when the user explicitly asks to run outside trading hours.
