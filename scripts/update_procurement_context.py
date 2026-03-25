#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.procurement_advisor import ProcurementAdvisor


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or update procurement advisor context.")
    parser.add_argument(
        "--context-path",
        default=os.getenv("PROCUREMENT_CONTEXT_PATH", "data/agent_state/procurement_context.json"),
    )
    parser.add_argument("--monthly-demand-tons", type=float, required=True)
    parser.add_argument("--inventory-tons", type=float, required=True)
    parser.add_argument("--budget-remaining", type=float, required=True)
    parser.add_argument("--last-purchase-price", type=float)
    parser.add_argument("--avg-3m-price", type=float)
    args = parser.parse_args()

    advisor = ProcurementAdvisor()
    context = advisor.load_context(args.context_path)
    context.update(
        {
            "monthly_demand_tons": args.monthly_demand_tons,
            "inventory_tons": args.inventory_tons,
            "budget_remaining": args.budget_remaining,
            "last_purchase_price": args.last_purchase_price,
            "avg_3m_price": args.avg_3m_price,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    advisor.save_context(args.context_path, context)
    print(json.dumps(context, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
