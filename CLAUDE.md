# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

AI Infrastructure Copilot — an AI assistant that lets Windows/Linux/Cloud admins monitor, troubleshoot,
and automate infrastructure via natural language, with a human-approval gate in front of every mutating
action. This repo is a **Phase 1 MVP** implementation. `docs/` (start at [docs/README.md](docs/README.md))
is the full target-architecture blueprint (20 modules, 15 agents, 5 deployable services); **`TASKS.md`
is the accurate, current inventory of what is actually built** — endpoints, models, agents, and frontend
components that exist today. When the two disagree, trust `TASKS.md` and the code over `docs/`.

Two deliberate MVP simplifications baked into the code (search for "MVP simplification" / "KNOWN DEVIATION"
comments to find the reasoning at each site):
- `EXECUTION_ENABLED=false` by default — approving a task shows `execution_skipped_flagged_off` instead of
  actually running anything against a remote server.
- No separate `execution-worker` or `notification-gateway` services exist yet (unlike `docs/11-folder-structure.md`'s
  blueprint): execution runs inline in `apps/api/app/execution/runner.py`, and Socket.IO is mounted directly
  on the API app (`apps/api/app/socket_app.py`) instead of a standalone gateway.
- `apps/ai-orchestrator/app/graph.py` is a plain async generator with the same node sequence/state shape the
  docs describe for LangGraph, not an actual `langgraph.StateGraph`.

## Repo layout (as it actually exists)

```
apps/
  api/              FastAPI backend — modular monolith, one module per feature under app/modules/
  ai-orchestrator/  FastAPI service that runs the AI agent workflow (consumed by apps/api via HTTP)
  web/              Next.js 15 frontend
packages/
  py-shared/        Pydantic schemas/enums/job_contracts shared between Python services
                     (currently only imported by ai-orchestrator, not by api, though both install it editable)
  shared-types/      TS types (imported in a handful of web hooks/features, not comprehensively adopted)
docs/               Full architecture blueprint (aspirational; see note above)
infra/              A nested git repo (has its own .git) — infra-as-code, kept separate from this repo's history
docker/             The docker-compose file actually used for local dev (see Commands below)
```

Do not confuse `docker/docker-compose.local.yml` (root, current, has the celery `worker` service) with
`infra/docker/docker-compose.local.yml` (older path referenced by `README.md`/`RUNNING.md`, missing the
worker service, different build context). Prefer the root `docker/` one.

## Commands

### First-time setup
```bash
docker compose -f docker/docker-compose.local.yml up -d          # Postgres (pgvector) + Redis
./scripts/dev-setup.sh                                            # creates .venv per Python service, installs py-shared editable
cp apps/api/.env.example apps/api/.env
cp apps/ai-orchestrator/.env.example apps/ai-orchestrator/.env
cp apps/web/.env.local.example apps/web/.env.local
# set OPENAI_API_KEY in apps/ai-orchestrator/.env (and apps/api/.env for the RAG embedding provider)
cd apps/api && .venv/bin/alembic upgrade head && cd ../..
cd apps/api && .venv/bin/python -m scripts.seed && cd ../..       # seeds one org, admin user, one server, event logs
npm install
```
Seeded admin login: `admin@acmecorp.io` / `ChangeMe123!` (MFA enrollment required on first login).

### Running services (each in its own terminal, or via pm2 — see below)
```bash
cd apps/api && .venv/bin/uvicorn app.main:app --reload --port 8000
cd apps/ai-orchestrator && .venv/bin/uvicorn app.main:app --reload --port 8001
cd apps/api && .venv/bin/celery -A app.workers.celery_app worker -Q documents -l info   # doc-ingestion pipeline
npm run dev:web            # or: cd apps/web && npm run dev
```

Or via pm2 (runs all four processes from `ecosystem.config.js`):
```bash
npm run pm2:start
npm run pm2:logs
npm run pm2:restart
npm run pm2:stop
```

### Database migrations (apps/api)
```bash
cd apps/api
.venv/bin/alembic revision --autogenerate -m "description"
.venv/bin/alembic upgrade head
.venv/bin/alembic downgrade -1
```

### Frontend
```bash
npm run lint:web            # eslint (next lint), from repo root
npm run build:web
```
There is no configured test runner for any service yet (no pytest config, no jest/vitest config) — don't
assume `pytest` or `npm test` work; confirm with the user before adding one from scratch.

## Architecture

### apps/api — modular monolith
Each feature lives under `app/modules/<name>/` as a `router.py` + `schemas.py` + `service.py` triplet; routers
stay thin and call into the service layer. `app/main.py` is the single place all routers get registered.

- **Multi-tenancy**: every authenticated request resolves `organization_id` from the JWT (never from a
  client-supplied param — see `app/dependencies.py`). `get_org_db` (in `dependencies.py`) wraps
  `get_scoped_db` (`app/core/db.py`), which calls `SELECT set_config('app.current_org_id', ...)` on the
  session so Postgres RLS backs up the application-layer `organization_id` filtering every repository query
  already does. Endpoints that predate an org (registration) use the plain `get_db` instead.
- **Error envelope**: all errors — `HTTPException` and validation errors alike — are normalized by
  `app/core/errors.py` into `{"error": {"code", "message", "details", "request_id"}}`. Raise
  `HTTPException(status_code=..., detail={"code": "...", "message": "..."})`; never raise a bare string
  detail if you want a stable `code` for clients to branch on.
- **Credentials/secrets**: `app/core/vault.py` does local envelope encryption (`local_vault_master_key`)
  as an MVP stand-in for HashiCorp Vault; `Credential` rows only ever store a vaulted reference.
- **RAG / Knowledge Base** (`app/rag/`, `app/modules/knowledge/`): document upload → Celery task
  (`app/workers/tasks/document_tasks.py`, queue `documents`) parses (docx/pdf/html/txt) → chunks
  (`rag/chunking`) → embeds (`rag/embeddings`, OpenAI by default, `embedding_provider` setting) →
  stores in pgvector (`rag/retrieval/vector_store.py`) alongside keyword search
  (`rag/retrieval/keyword_search.py`). `rag/generation/grounded_generator.py` builds the grounded prompt
  consumed by the orchestrator's RAG agent.
- **Execution safety**: `app/execution/runner.py` only runs a `Task` once its status is `approved`, and
  is a no-op (`execution_skipped_flagged_off`) while `settings.execution_enabled` is `False`. Real execution
  goes over WinRM via `app/core/winrm_client.py` using a resolved vaulted credential, then writes an
  `AuditLog` row (`app/core/audit.py`).
- **Realtime**: `app/socket_app.py` mounts a `python-socketio` ASGI app at `/socket.io` directly on the
  FastAPI app; clients join an `org:{organization_id}` room right after connecting, and `emit_to_org(...)`
  is how any service-layer code pushes events (e.g. task status changes) to the frontend.

### apps/ai-orchestrator — the AI workflow service
A separate FastAPI process, called over HTTP by `apps/api`'s `ai_chat` module (`ai_orchestrator_url`
setting). `POST /run` streams Server-Sent Events as the workflow progresses.

Flow (`app/graph.py`, sequential async generator — see "KNOWN DEVIATION" note in that file for why it
isn't a real LangGraph `StateGraph`):
```
user prompt → planner_agent.plan() → (RAG agent search, if selected)
            → if target_server: coordinator_agent.dispatch() → windows_agent diagnosis
              → root cause + recommendation → (if requires_script) powershell_agent generates script
              → emits a "proposal" event (becomes a Task in apps/api, pending human approval)
            → else: grounded answer straight from RAG context
```
Agents live in `app/agents/`; `app/llm/provider_interface.py` is the provider-agnostic LLM interface with
concrete `openai_provider.py` / `gemini_provider.py` implementations. `app/mcp_windows.py` /
`app/mcp_scripting.py` expose MCP-style tool servers the agents call into. The human-approval boundary is
owned deterministically by `apps/api`'s `tasks` module once a proposal becomes a persisted `Task` row —
the orchestrator itself has nothing to "resume," which is why it doesn't need real LangGraph checkpointing.

### apps/web — Next.js 15 frontend
App Router under `src/app/(dashboard)/<module>/page.tsx`, one route group per module; pages stay thin and
delegate to `src/features/<name>/` (components/hooks/services/types/utils per feature) and shared primitives
in `src/components/common/` (`DataTable`, `AsyncSelect`, `ConfirmationDialog`, `StatusBadge`, etc. — reuse
these instead of one-off implementations). React Query for server state, Zustand/Redux only for global
client-only UI state (see `src/store/`), `zod` + `react-hook-form` for forms.

**Read [apps/web/.claude/rules/FRONTEND_DEVELOPMENT_RULES.md](apps/web/.claude/rules/FRONTEND_DEVELOPMENT_RULES.md)
before making frontend changes** — it's the binding standard for component structure, confirmation dialogs
on destructive actions, pagination/search-select conventions, React Query usage, and state-management split,
and is more detailed than what's summarized here.

### packages/
- `py-shared`: cross-Python-service Pydantic schemas/enums/job contracts, installed editable via
  `scripts/dev-setup.sh`. Currently only `ai-orchestrator` actually imports it (e.g. `RunGraphRequest`);
  `apps/api` has it installed but doesn't import it yet — don't assume a schema change there is
  automatically picked up by `apps/api` without also wiring the import.
- `shared-types`: TS types for API contracts/entities/ws-events; adopted in some `apps/web` hooks/features,
  not repo-wide — check whether the type you need already exists here before hand-rolling an interface.

## Conventions worth knowing before editing

- Domain-specific engineering guidance (RAG/agent patterns, backend API/queue conventions, security,
  infra, network, QA) is available as skills under `.agents/skills/` — invoke the relevant one rather than
  re-deriving these patterns from scratch.
- `docs/` documents are cross-referenced by name throughout the codebase in comments (e.g.
  "docs/05-api-design.md Section 1") — when a comment cites a doc section for *why* something is shaped a
  certain way, read that section before changing the shape.
