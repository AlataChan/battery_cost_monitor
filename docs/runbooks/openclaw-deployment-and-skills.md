# OpenClaw Deployment And Skills Runbook

## Scope

This runbook covers the repo-side operational steps for:

- Milestone 2 deployment hardening
- Milestone 3 `battery-monitor` skill usage
- Milestone 4 `procurement-advisor` skill usage

It does not replace real cloud-domain provisioning or a live OpenClaw workspace.

## 1. Local Prerequisites

- Docker Desktop or Docker Engine with `docker compose`
- Python 3.12 environment
- Valid `.env` with `DEEPSEEK_API_KEY` and `API_KEY`

## 2. Static Validation

Run the automated tests:

```bash
./venv/bin/python -m unittest discover -s tests -v
```

Inspect docker compose resolution:

```bash
docker compose config
```

## 3. Local API Startup

Plain Flask:

```bash
./venv/bin/python -c "from web_server import app; app.run(host='127.0.0.1', port=5001, debug=False, threaded=True)"
```

Docker Compose:

```bash
docker compose up --build
```

## 4. API Smoke Checks

```bash
curl --noproxy '*' -H "X-API-Key: $API_KEY" http://127.0.0.1:5001/api/latest
curl --noproxy '*' http://127.0.0.1:5001/api/latest
curl --noproxy '*' -X POST -H "X-API-Key: $API_KEY" http://127.0.0.1:5001/api/refresh
```

## 5. Battery Monitor Skill

Skill definition:

- `skills/battery-monitor/SKILL.md`

Single-cycle run:

```bash
./venv/bin/python scripts/run_battery_monitor.py --force
```

State file:

- `data/agent_state/battery_signals.json`

Expected behavior:

- Outside trading hours: skip and schedule `next_open`
- Direction reversal: immediate push signal
- Strong signal or 3 consecutive confirmations: push unless cooldown is active

## 6. Procurement Advisor Skill

Skill definition:

- `skills/procurement-advisor/SKILL.md`

Seed business context:

```bash
./venv/bin/python scripts/update_procurement_context.py \
  --monthly-demand-tons 200 \
  --inventory-tons 300 \
  --budget-remaining 30000000 \
  --last-purchase-price 153000 \
  --avg-3m-price 160000
```

Generate advice:

```bash
./venv/bin/python scripts/run_procurement_advisor.py
```

State files:

- `data/agent_state/procurement_context.json`
- `data/agent_state/procurement_decisions.jsonl`

Expected behavior:

- 3x3 decision matrix evaluates urgency × timing
- `confidence < 50` yields `observe`
- all outputs include `requires_confirmation: true` and `valid_until`

## 7. Real Cloud Acceptance

The following must still be validated in the target environment:

- domain and HTTPS certificate provisioning
- public ingress behavior for `/api/*`
- external denial for `/` and `/output/*`
- actual OpenClaw runtime loading `skills/`
