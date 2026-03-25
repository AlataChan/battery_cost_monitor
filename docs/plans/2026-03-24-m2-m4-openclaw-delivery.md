# M2-M4 OpenClaw Delivery Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the repo-side work for Milestone 2-4: deployment hardening, OpenClaw-ready battery monitor skill, and procurement advisor skill with tests.

**Architecture:** Keep the existing Flask API as the system of record. Add repo-local skill wrappers under `skills/` for OpenClaw, pure Python agent logic under `src/agents/`, and file-backed JSON state/log storage so the skills can run locally and inside OpenClaw without adding a database.

**Tech Stack:** Python 3.12, Flask, docker-compose, nginx, unittest, JSON file storage.

---

### Task 1: Deployment Security Baseline

**Files:**
- Modify: `docker-compose.yml`
- Modify: `nginx.conf`
- Test: `tests/test_deployment_config.py`

**Step 1: Write the failing tests**
- Assert `docker-compose.yml` exposes `API_KEY`, `SNAPSHOT_CACHE_TTL`, and `CORS_ORIGINS`.
- Assert `nginx.conf` rate-limits `/api/`, requires `X-API-Key`, and blocks `/` and `/output/` from non-local callers.

**Step 2: Run tests to verify they fail**
- Run: `./venv/bin/python -m unittest tests.test_deployment_config -v`

**Step 3: Implement the config changes**
- Add the missing environment variables to `docker-compose.yml`.
- Harden `nginx.conf` to expose `/api/` only, add `limit_req_zone`, protect `/api/status`, and block `/` plus `/output/` for non-local access.

**Step 4: Run tests to verify they pass**
- Run: `./venv/bin/python -m unittest tests.test_deployment_config -v`

### Task 2: Battery Monitor Agent Core

**Files:**
- Create: `src/agents/__init__.py`
- Create: `src/agents/common.py`
- Create: `src/agents/battery_monitor.py`
- Create: `scripts/run_battery_monitor.py`
- Create: `skills/battery-monitor/SKILL.md`
- Test: `tests/test_battery_monitor.py`

**Step 1: Write the failing tests**
- Cover non-trading-hour skip, direction reversal push, cooldown handling, and memory persistence inputs/outputs.

**Step 2: Run tests to verify they fail**
- Run: `./venv/bin/python -m unittest tests.test_battery_monitor -v`

**Step 3: Implement the minimal battery monitor logic**
- Build a pure monitor cycle evaluator using API snapshots plus JSON memory.
- Add a CLI entrypoint that calls the API, loads/stores memory, and prints structured JSON.
- Add an OpenClaw `SKILL.md` that tells the agent when to run the monitor script.

**Step 4: Run tests to verify they pass**
- Run: `./venv/bin/python -m unittest tests.test_battery_monitor -v`

### Task 3: Procurement Advisor Agent Core

**Files:**
- Create: `src/agents/procurement_advisor.py`
- Create: `scripts/update_procurement_context.py`
- Create: `scripts/run_procurement_advisor.py`
- Create: `skills/procurement-advisor/SKILL.md`
- Test: `tests/test_procurement_advisor.py`

**Step 1: Write the failing tests**
- Cover urgency classification, timing classification, good-timing buy advice, low-confidence observe output, and decision log persistence.

**Step 2: Run tests to verify they fail**
- Run: `./venv/bin/python -m unittest tests.test_procurement_advisor -v`

**Step 3: Implement the minimal advisor logic**
- Add file-backed business context load/save.
- Evaluate the 3x3 decision matrix and confidence threshold.
- Emit deterministic structured decisions and append JSONL decision logs.
- Add an OpenClaw `SKILL.md` that guides the agent to collect context and run the advisor script.

**Step 4: Run tests to verify they pass**
- Run: `./venv/bin/python -m unittest tests.test_procurement_advisor -v`

### Task 4: Final Verification

**Files:**
- Modify: `.env`
- Modify: `env_example.txt`
- Modify: `.plans/m1-api-layer/progress.md`

**Step 1: Add agent-related env defaults**
- Add API base URL and JSON state/log paths.

**Step 2: Run full verification**
- Run: `./venv/bin/python -m unittest discover -s tests -v`
- Run targeted local smoke checks for `scripts/run_battery_monitor.py` and `scripts/run_procurement_advisor.py`.

**Step 3: Document remaining external acceptance gaps**
- Note that real cloud HTTPS/domain verification and real OpenClaw runtime validation require external infrastructure.
