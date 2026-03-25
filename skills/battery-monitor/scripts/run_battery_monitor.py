#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MEMORY_PATH = SKILL_ROOT / "data/agent_state/battery_signals.json"
PROJECT_MARKERS = (
    "gamma_shock_BYTE.py",
    "src/agents/battery_monitor.py",
    "scripts/run_battery_monitor.py",
)


def iter_candidate_roots(explicit: str | None) -> list[Path]:
    raw_candidates: list[Path] = []
    for raw in (
        explicit,
        os.getenv("BATTERY_MONITOR_PROJECT_ROOT"),
        os.getenv("BATTERY_PROJECT_ROOT"),
        str(Path.cwd()),
        str(SKILL_ROOT),
    ):
        if not raw:
            continue
        raw_candidates.append(Path(raw).expanduser())

    seen: set[Path] = set()
    candidates: list[Path] = []
    for raw in raw_candidates:
        try:
            resolved = raw.resolve()
        except FileNotFoundError:
            continue
        for candidate in (resolved, *resolved.parents):
            if candidate in seen:
                continue
            seen.add(candidate)
            candidates.append(candidate)
    return candidates


def find_project_root(explicit: str | None) -> Path:
    for candidate in iter_candidate_roots(explicit):
        if all((candidate / marker).exists() for marker in PROJECT_MARKERS):
            return candidate
    raise SystemExit(
        "BatteryAI project root not found. Open OpenClaw in the battery_cost_monitor workspace, "
        "pass --project-root, or set BATTERY_MONITOR_PROJECT_ROOT."
    )


def resolve_path(raw_path: str | None, default_path: Path, project_root: Path) -> Path:
    if not raw_path:
        return default_path
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path
    return (project_root / path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one battery monitor cycle.")
    parser.add_argument("--project-root", help="Path to the BatteryAI project root.")
    parser.add_argument("--api-base-url")
    parser.add_argument("--api-key")
    parser.add_argument("--memory-path")
    parser.add_argument("--force", action="store_true", help="Run even outside trading hours.")
    args = parser.parse_args()

    project_root = find_project_root(args.project_root)
    load_dotenv(project_root / ".env", override=False)
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from gamma_shock_BYTE import is_futures_trading_hours
    from src.agents.battery_monitor import BatteryMonitor
    from src.agents.common import call_json_api, load_json_file, save_json_file

    api_base_url = args.api_base_url or os.getenv("BATTERY_API_BASE_URL", "http://127.0.0.1:5001")
    api_key = args.api_key or os.getenv("API_KEY", "")
    memory_path = resolve_path(args.memory_path or os.getenv("BATTERY_MONITOR_MEMORY_PATH"), DEFAULT_MEMORY_PATH, project_root)

    now = datetime.now()
    trading_hours = True if args.force else is_futures_trading_hours()
    memory = load_json_file(memory_path, {})
    monitor = BatteryMonitor()

    if trading_hours:
        snapshot = call_json_api(f"{api_base_url.rstrip('/')}/api/latest", api_key=api_key)
    else:
        snapshot = {
            "timestamp": now.isoformat(timespec="seconds"),
            "price": {"current": None},
            "signal": {"direction": "neutral", "strength": 0},
            "cost": {"change_pct": None},
        }

    result = monitor.monitor_cycle(snapshot=snapshot, memory=memory, now=now, trading_hours=trading_hours)
    save_json_file(memory_path, result["memory"])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
