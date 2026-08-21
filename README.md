# AI Infrastructure Copilot

Phase 1 MVP implementation. Full architecture blueprint lives in [`docs/`](docs/README.md);
the Phase 1 scope and the deliberate simplifications made to build it are recorded in
the implementation plan this was built from (Authentication, Infrastructure Inventory,
AI Chat, PowerShell Generator, and Windows Event Log Analyzer only — see
[`docs/15-roadmap.md`](docs/15-roadmap.md) Section 3).

## Prerequisites

- Docker + Docker Compose (Postgres with pgvector, Redis)
- Python 3.10+ with `venv` and `pip` available (`sudo apt install python3-pip python3.10-venv` on Debian/Ubuntu if missing)
- Node.js 20+ and npm

## First-time setup

```bash
# 1. Start Postgres + Redis
docker compose -f infra/docker/docker-compose.local.yml up -d

# 2. Set up Python services (creates a venv per service, installs py-shared as editable)
./scripts/dev-setup.sh

# 3. Configure env files
cp apps/api/.env.example apps/api/.env
cp apps/ai-orchestrator/.env.example apps/ai-orchestrator/.env
cp apps/web/.env.local.example apps/web/.env.local
# Edit apps/ai-orchestrator/.env and set OPENAI_API_KEY

# 4. Run migrations
cd apps/api && .venv/bin/alembic upgrade head && cd ../..

# 5. Seed demo data (one org, one admin user, one server, realistic event logs)
cd apps/api && .venv/bin/python -m scripts.seed && cd ../..

# 6. Install frontend deps
npm install
```

## Running

Run each in its own terminal:

```bash
# API (port 8000)
cd apps/api && .venv/bin/uvicorn app.main:app --reload --port 8000

# AI Orchestrator (port 8001)
cd apps/ai-orchestrator && .venv/bin/uvicorn app.main:app --reload --port 8001

# Web (port 3000)
npm run dev:web
```

Then open http://localhost:3000, log in with the admin credentials printed by
`scripts/seed.py` (`admin@acmecorp.io` / `ChangeMe123!`), complete the MFA enrollment card
shown on first login (add the manual-entry key to any TOTP app — Google Authenticator,
Authy, etc.), and try AI Chat: *"why is web-prod-03 running slow?"*

`EXECUTION_ENABLED=false` by default (`apps/api/.env`), so approving a generated script's
task will show status `execution_skipped_flagged_off` instead of actually running
anything — see the plan's MVP simplifications for why, and `docs/15-roadmap.md`'s Phase 1
exit criteria for what "done" means without real execution wired up yet.
