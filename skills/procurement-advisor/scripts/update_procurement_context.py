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
DEFAULT_CONTEXT_PATH = SKILL_ROOT / "data/agent_state/procurement_context.json"
PROJECT_MARKERS = (
    "gamma_shock_BYTE.py",
    "src/agents/procurement_advisor.py",
    "scripts/update_procurement_context.py",
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
    parser = argparse.ArgumentParser(description="Create or update procurement advisor context.")
    parser.add_argument("--project-root", help="Path to the BatteryAI project root.")
    parser.add_argument("--context-path")
    parser.add_argument("--monthly-demand-tons", type=float, required=True)
    parser.add_argument("--inventory-tons", type=float, required=True)
    parser.add_argument("--budget-remaining", type=float, required=True)
    parser.add_argument("--last-purchase-price", type=float)
    parser.add_argument("--avg-3m-price", type=float)
    args = parser.parse_args()

    project_root = find_project_root(args.project_root)
    load_dotenv(project_root / ".env", override=False)
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from src.agents.procurement_advisor import ProcurementAdvisor

    context_path = resolve_path(args.context_path or os.getenv("PROCUREMENT_CONTEXT_PATH"), DEFAULT_CONTEXT_PATH, project_root)

    advisor = ProcurementAdvisor()
    context = advisor.load_context(context_path)
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
    advisor.save_context(context_path, context)
    print(json.dumps(context, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
