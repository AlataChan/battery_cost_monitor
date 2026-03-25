---
name: procurement-advisor
description: Use when the user wants a lithium procurement recommendation, asks whether to buy now, or needs context-aware purchasing advice.
metadata:
  openclaw:
    requires:
      bins: ["python3"]
---

# Procurement Advisor

Use this skill when the user asks whether to buy lithium now, wants a procurement recommendation, or needs context-aware cost advice.

## Workflow

1. Ensure context exists. If any of these are missing, ask for them one at a time:
- `monthly_demand_tons`
- `inventory_tons`
- `budget_remaining`
- Optional: `last_purchase_price`
- Optional: `avg_3m_price`

2. Save or update the context:

```bash
python3 scripts/update_procurement_context.py \
  --monthly-demand-tons 200 \
  --inventory-tons 50 \
  --budget-remaining 30000000
```

3. Generate advice:

```bash
python3 scripts/run_procurement_advisor.py
```

4. Report the structured decision. Always state that the result is advisory and requires human confirmation.

## Notes

- The bundled scripts find the BatteryAI project root from `--project-root`, `BATTERY_MONITOR_PROJECT_ROOT`, `BATTERY_PROJECT_ROOT`, or the current workspace.
- If the project root cannot be found, ask the user to open the `battery_cost_monitor` repo as the workspace or provide `--project-root`.
- Context is stored in `data/agent_state/procurement_context.json` inside this skill package unless overridden.
- Decision logs append to `data/agent_state/procurement_decisions.jsonl`.
- If the generated `confidence` is below `50`, present it as observation-only guidance.
