#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.common import call_json_api
from src.agents.procurement_advisor import ProcurementAdvisor


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate procurement advice from the latest BatteryAI snapshot.")
    parser.add_argument("--api-base-url", default=os.getenv("BATTERY_API_BASE_URL", "http://127.0.0.1:5001"))
    parser.add_argument("--api-key", default=os.getenv("API_KEY", ""))
    parser.add_argument(
        "--context-path",
        default=os.getenv("PROCUREMENT_CONTEXT_PATH", "data/agent_state/procurement_context.json"),
    )
    parser.add_argument(
        "--decision-log-path",
        default=os.getenv("PROCUREMENT_DECISION_LOG_PATH", "data/agent_state/procurement_decisions.jsonl"),
    )
    args = parser.parse_args()

    advisor = ProcurementAdvisor()
    context = advisor.load_context(args.context_path)
    if not context:
        raise SystemExit("Procurement context is missing. Run scripts/update_procurement_context.py first.")

    snapshot = call_json_api(f"{args.api_base_url.rstrip('/')}/api/latest", api_key=args.api_key)
    decision = advisor.generate_advice(
        snapshot=snapshot,
        context=context,
        decision_log_path=args.decision_log_path,
    )
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
