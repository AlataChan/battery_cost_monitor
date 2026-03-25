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

from gamma_shock_BYTE import is_futures_trading_hours
from src.agents.battery_monitor import BatteryMonitor
from src.agents.common import call_json_api, load_json_file, save_json_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one battery monitor cycle.")
    parser.add_argument("--api-base-url", default=os.getenv("BATTERY_API_BASE_URL", "http://127.0.0.1:5001"))
    parser.add_argument("--api-key", default=os.getenv("API_KEY", ""))
    parser.add_argument(
        "--memory-path",
        default=os.getenv("BATTERY_MONITOR_MEMORY_PATH", "data/agent_state/battery_signals.json"),
    )
    parser.add_argument("--force", action="store_true", help="Run even outside trading hours.")
    args = parser.parse_args()

    now = datetime.now()
    trading_hours = True if args.force else is_futures_trading_hours()
    memory = load_json_file(args.memory_path, {})
    monitor = BatteryMonitor()

    if trading_hours:
        snapshot = call_json_api(f"{args.api_base_url.rstrip('/')}/api/latest", api_key=args.api_key)
    else:
        snapshot = {
            "timestamp": now.isoformat(timespec="seconds"),
            "price": {"current": None},
            "signal": {"direction": "neutral", "strength": 0},
            "cost": {"change_pct": None},
        }

    result = monitor.monitor_cycle(snapshot=snapshot, memory=memory, now=now, trading_hours=trading_hours)
    save_json_file(args.memory_path, result["memory"])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
