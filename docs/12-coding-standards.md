# 12 — Coding Standards

This document defines the conventions engineers must follow when building AI Infrastructure
Copilot. It covers the frontend (`apps/web`), backend (`apps/api`, `apps/execution-worker`,
`apps/ai-orchestrator`), database migrations, git workflow, and API design conventions. The goal is
consistency across a monorepo with mixed TypeScript/Python codebases and a component
(`execution-worker`) whose defects carry real-world blast radius, so several rules below exist
specifically to reduce risk around it and around the Human Approval gate.

---

## 1. TypeScript / React / Next.js (`apps/web`)

### 1.1 Folder conventions

Next.js App Router, feature-oriented structure under `src/`:

```
apps/web/
  src/
    app/                       # route segments only — thin: layout, page, loading, error
      (dashboard)/
        servers/
          page.tsx
          [serverId]/page.tsx
        api/                   # route handlers only when a BFF endpoint is truly needed
    components/
      ui/                      # shadcn/ui primitives (generated, minimally modified)
      servers/                 # feature-scoped composite components
      conversations/
      shared/                  # cross-feature building blocks (data tables, empty states)
    features/                  # feature modules: hooks, queries, types, colocated with UI logic
      servers/
        hooks.ts
        queries.ts             # React Query query/mutation definitions
        types.ts
      conversations/
    lib/                       # framework-agnostic utilities (formatting, api client, socket client)
    hooks/                     # cross-feature hooks (useDebounce, useMediaQuery)
    styles/
  public/
```

### 1.2 File naming

- Components: `PascalCase.tsx` (e.g., `ServerTable.tsx`), one primary exported component per file.
- Hooks: `camelCase.ts` prefixed with `use` (e.g., `useServerStatus.ts`).
- Route segment files use Next.js reserved names as-is (`page.tsx`, `layout.tsx`, `loading.tsx`,
  `error.tsx`, `route.ts`) — never renamed.
- Non-component modules (utils, query definitions, types): `kebab-case.ts` or `camelCase.ts`,
  consistent within a folder — `kebab-case.ts` is the default for new folders.
- Test files: colocated as `ComponentName.test.tsx` / `module.test.ts`.
- One component = one file. Avoid barrel files (`index.ts` re-exports) except at the top of a
  `features/<name>/` module boundary, to keep import traces greppable.

### 1.3 Component structure

- Functional components only, typed with explicit `Props` interfaces (`interface ServerTableProps`),
  never `React.FC` (it adds implicit `children` typing that's rarely correct).
- Server Components by default; add `"use client"` only when the component needs interactivity,
  browser APIs, or hooks — push client boundaries as far down the tree as possible.
- Co-locate a component's Storybook story (if used) and test in the same directory, not in a mirrored
  `__tests__` tree.
- Presentational components receive data via props; data-fetching components use the hooks defined
  in `features/<name>/queries.ts` — never call `fetch`/the API client directly inside a leaf UI
  component.
- Prefer composition (`children`, slot props) over prop-drilled boolean flags that branch rendering
  internally.

### 1.4 State management

- **Server state** (anything that originates from the API: servers, tasks, alerts, AI
  conversations) is owned by **React Query**, never duplicated into local component state or a
  global client store.
  - Query keys are structured, typed arrays defined once per feature in `queries.ts`, e.g.
    `['servers', 'list', filters]`, `['servers', 'detail', serverId]` — never inline ad hoc string
    keys scattered across components.
  - Mutations always invalidate/update the precise affected query keys (prefer
    `queryClient.setQueryData` for optimistic updates over blanket `invalidateQueries` when the
    shape is known), and mutations that trigger a mutating infrastructure action must reflect the
    Human Approval state machine (`pending_approval → approved/rejected → executing → completed`)
    in their returned data, not be assumed to complete synchronously.
  - Shared `staleTime`/`gcTime` defaults are set once in `lib/query-client.ts`; individual queries
    override only when justified (e.g., short `staleTime` for live alert counts).
- **Real-time updates** (Socket.IO events for task/job status, new AI messages, alerts) update the
  React Query cache directly via `queryClient.setQueryData` from a small set of socket-event
  handlers registered once near the app root — components never manage sockets themselves.
- **Local/UI state** (form inputs, modal open/closed, selected tab) uses `useState`/`useReducer`
  colocated in the component; reach for a global client-state library only for truly cross-tree UI
  state (e.g., sidebar collapsed), and prefer React Context over adding a new state library.
- Form state uses `react-hook-form` with a `zod` schema shared, where possible, with the
  corresponding Pydantic model's shape (kept in sync via `packages/shared-types`).

### 1.5 Linting / formatting

- **ESLint**: `eslint-config-next` + `@typescript-eslint/recommended-requiring-type-checking` +
  `eslint-plugin-react-hooks` (`rules-of-hooks` and `exhaustive-deps` as errors, not warnings).
- **Prettier**: single formatting authority for style (semicolons, quotes, trailing commas); ESLint
  style rules that conflict with Prettier are disabled via `eslint-config-prettier`.
- Both run in CI (`npm run lint`, `npm run format:check`) and as a pre-commit hook (`husky` +
  `lint-staged`) so violations never reach a PR.
- `strict: true` in `tsconfig.json` for `apps/web`; `any` is disallowed by lint rule
  (`@typescript-eslint/no-explicit-any: error`) — use `unknown` plus narrowing, or a proper type
  from `packages/shared-types`.
- Imports ordered/grouped automatically (`eslint-plugin-simple-import-sort` or Prettier import
  sort plugin): external packages, then `@/` absolute imports, then relative imports.

---

## 2. Python / FastAPI (`apps/api`, `apps/execution-worker`, `apps/ai-orchestrator`)

### 2.1 Project layout

Each Python service follows a router/module-per-domain layout so the DB entities map predictably to
code locations:

```
apps/api/
  src/
    main.py                 # app factory, middleware, router registration
    core/
      config.py              # Settings (pydantic-settings), loaded once
      security.py             # auth/JWT/session helpers
      dependencies.py         # shared FastAPI Depends() providers
    db/
      session.py              # async session factory
      base.py
    modules/
      servers/
        router.py            # APIRouter, one per resource
        schemas.py           # Pydantic request/response models
        models.py            # SQLAlchemy models (or imported from a shared models package)
        service.py           # business logic, DB access — routers stay thin
        dependencies.py      # module-scoped Depends() providers
      tasks/
      automation_jobs/
      workflows/
      policies/
      alerts/
      ai_conversations/
      audit_logs/
      ...                    # one module per core entity group from the ERD
    tests/
      unit/
      integration/
  alembic/
    versions/
    env.py
```

- Routers contain only request parsing, dependency injection, and calling into `service.py` — no
  business logic, no direct SQL, in the router function body.
- `execution-worker` mirrors the `modules/` pattern for job-type handlers
  (`modules/job_types/<job_type>/handler.py`) instead of HTTP routers, since it consumes from a
  queue rather than serving requests; every handler has a matching `policy.py` declaring whether
  the job type is read-only (auto-runnable) or mutating (approval-required) — this declaration is
  what the CI "policy test" stage from `docs/08-deployment-guide.md` asserts against.
- `ai-orchestrator` mirrors the pattern with `modules/graphs/<graph_name>/` for LangGraph graph
  definitions and `modules/mcp/` for MCP server/client integration code.

### 2.2 Pydantic models and type hints

- Every function signature (including private helpers) has full type hints; `mypy` (or `pyright`)
  runs in CI in strict-ish mode (`disallow_untyped_defs`, `disallow_any_generics`) — untyped `def`
  is a CI failure, not a style nit.
- Pydantic v2 models are the boundary type for every API request/response and every queue
  message; internal service functions accept/return Pydantic models or explicit dataclasses, never
  bare `dict`.
- Naming: `XCreate`, `XUpdate`, `XRead`/`XOut`, `XInDB` suffix convention per resource (e.g.,
  `ServerCreate`, `ServerUpdate`, `ServerRead`) — mirrors the common FastAPI+Pydantic convention so
  it's predictable which model applies where.
- Shared shapes that must match the frontend's TypeScript types are generated into/kept consistent
  with `packages/shared-types` (either hand-synced with a contract test, or generated from the
  OpenAPI schema via `openapi-typescript` — the generation step, once chosen, is documented in
  `apps/web/README` and `apps/api/README`, and CI fails if the checked-in generated types drift
  from the live OpenAPI schema).
- Enum-like fields (job status, approval status, alert severity) are Python `Enum`/`StrEnum`, never
  bare strings, so invalid states are caught at the type level.

### 2.3 Dependency injection patterns

- FastAPI `Depends()` is used for: DB session (`get_db_session`), current authenticated user
  (`get_current_user`), permission checks (`require_permission("servers:write")`), and
  service-layer singletons (`get_server_service`).
- Permission-checking dependencies are composed, not duplicated per router — a single
  `require_permission(...)` dependency factory is reused across every module, so RBAC enforcement
  is centralized and auditable in one place (`core/security.py`).
- Any mutating endpoint that maps to a `Servers`/`Devices`/`Scripts` action which will eventually
  reach `execution-worker` must inject and check an `ApprovalGate` dependency before the
  request is allowed to enqueue a job — this is a structural rule, not a convention left to
  reviewer memory, and is covered by the mandatory review rule in §4.3.
- Long-lived resources (DB engine, Redis client, LLM provider client) are constructed once in the
  app lifespan (`@asynccontextmanager` lifespan handler) and provided via `Depends()`, never
  instantiated inside a request handler.

### 2.4 Formatting / linting

- **ruff** is the single tool for linting *and* import sorting (`ruff check`, replacing
  flake8/isort); **black** is the formatter (`black .`); both run via pre-commit hook and CI
  (`ruff check apps/ --exit-non-zero-on-fix`, `black --check apps/`).
- Line length 100 (matches `black`'s default-adjacent convention already agreed for this repo);
  configured once in `pyproject.toml` at the repo root and inherited by every service.
- Docstrings required (Google style) on public service-layer functions and on every job-type
  handler in `execution-worker`, since those are the functions most likely to be audited later.

---

## 3. Database Migrations (Alembic)

- One Alembic environment per service that owns schema (`apps/api/alembic`); `execution-worker`
  and `ai-orchestrator` do not maintain their own migrations — they read/write through the same
  schema owned by `api`.
- **Naming**: revision files are auto-generated with `alembic revision --autogenerate -m
  "<verb>_<entity>_<short_description>"`, producing filenames like
  `2026_07_13_1200-add_approval_status_to_automationjobs.py`; the `-m` message uses `snake_case`,
  starts with a verb (`add_`, `drop_`, `rename_`, `backfill_`), and names the affected entity/table
  explicitly.
- Every migration is reviewed for a **down-revision path** that actually works
  (`alembic downgrade -1` is run in CI against a throwaway DB as part of the integration test stage)
  — migrations without a working downgrade are rejected unless the destructive step is
  intentionally irreversible, in which case that's called out explicitly in the PR description.
- **Destructive migrations** (`DROP COLUMN`, `DROP TABLE`, `ALTER COLUMN ... NOT NULL` on existing
  data, any migration touching `Credentials`, `AuditLogs`, `Policies`, or `AIConversations`/
  `AIMessages`) require:
  1. A written rollback/backfill plan in the PR description.
  2. Running the migration against a staging snapshot before it is approved for prod.
  3. Sign-off from a second reviewer beyond the PR author, per the mandatory-review rule in §4.3
     (destructive migrations are treated the same as `execution-worker`/Approval-gate changes).
  4. Preference for additive-then-backfill-then-drop as a multi-step migration sequence over a
     single-step destructive change, so a bad migration can be caught before data is lost.
- Autogenerated migrations are always hand-reviewed before commit — `--autogenerate` output is a
  draft, not a final artifact; index/constraint naming is normalized to the project's convention
  (`ix_<table>_<column>`, `fk_<table>_<column>_<ref_table>`, `uq_<table>_<column>`) if Alembic's
  default naming doesn't already match.
- Data backfills that touch large tables (`Logs`, `Events`, `AuditLogs`) are written as batched,
  resumable scripts rather than a single unbounded `UPDATE` inside the migration transaction.

---

## 4. Git Workflow

### 4.1 Branch naming

`<type>/<short-ticket-or-scope>-<kebab-summary>`, e.g.:

- `feat/inf-214-server-inventory-filters`
- `fix/inf-230-approval-gate-race-condition`
- `chore/upgrade-langgraph-0-4`

Types: `feat`, `fix`, `chore`, `refactor`, `docs`, `test`, `perf` — mirrors the Conventional
Commits type list so branch and commit vocabulary stay aligned.

### 4.2 Conventional commits

All commits follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

<optional body>

<optional footer: BREAKING CHANGE:, Refs: INF-xxx>
```

- `<scope>` is the service or area: `web`, `api`, `execution-worker`, `ai-orchestrator`, `infra`,
  `docs`, `shared-types`.
- Example: `feat(execution-worker): add idempotency check to restart-service job handler`
- `fix` commits touching the Human Approval gate or `execution-worker` include `Refs:` the
  incident/ticket for traceability, and never squash away the detail of *what specifically* was
  fixed in the final merge message.
- Squash-merge is the default merge strategy into `main`; the squash commit message is
  hand-edited to a clean Conventional Commit summary of the whole PR, not left as the raw list of
  WIP commits.

### 4.3 PR review requirements

- **Standard PRs**: require at least one approval from a code owner of the touched area (enforced
  via `CODEOWNERS` mapping `apps/web/**`, `apps/api/**`, etc. to the relevant team) before merge.
- **Mandatory two-reviewer rule** — a PR requires approval from **two** reviewers, at least one of
  whom is from the platform/security group, whenever it touches any of:
  - `apps/execution-worker/**` (any file).
  - Any Human Approval gate logic, wherever it lives (`api`'s `ApprovalGate` dependency, approval
    state machine, approval-related DB models/migrations).
  - `infra/k8s/charts/**/execution-worker/**`, especially `networkpolicy.yaml`.
  - Any RBAC/permission definition (`Roles`, `Permissions` modules) or Vault/credential-handling
    code (`Credentials` module, secret-fetching dependencies).
  - Destructive database migrations as defined in §3.
  - This rule is enforced via branch protection rules (required reviewers/groups on the relevant
    `CODEOWNERS` paths) so it cannot be bypassed by habit or oversight.
- PRs must include: what changed and why, test evidence (unit/integration results or a note on
  manual verification), and — for anything in the mandatory-review list — an explicit statement of
  how the change was verified not to weaken the Approval gate or widen `execution-worker`'s network
  exposure.
- CI must be green (lint, unit, integration, container scan) before merge is allowed; no
  "merge with failing checks" override on `main`.

---

## 5. API Design Conventions

- **Resource naming**: plural nouns for collections, matching the ERD entities directly —
  `/servers`, `/devices`, `/scripts`, `/tasks`, `/automation-jobs`, `/workflows`, `/policies`,
  `/alerts`, `/audit-logs`, `/ai-conversations`. Multi-word resources are `kebab-case` in the URL
  even though the underlying entity name is `PascalCase`/`CamelCase` in code
  (`AutomationJobs` → `/automation-jobs`).
- **Nesting**: nest only one level deep for clearly owned sub-resources
  (`/servers/{server_id}/tasks`), otherwise use top-level resources with filter query params
  (`/tasks?server_id=...`) to avoid deep nesting chains.
- **Versioning**: all routes are prefixed `/api/v1/...`; breaking changes ship as `/api/v2/...`
  running alongside `v1` until clients migrate, never an in-place breaking change to `v1`. The
  version prefix is applied once at router-inclusion time in `main.py`, not repeated in every
  router file.
- **HTTP verbs**: standard REST semantics — `GET` (read, safe/idempotent), `POST` (create, or
  trigger an action that isn't a pure CRUD create — e.g., `POST /automation-jobs/{id}/approve`),
  `PATCH` (partial update), `DELETE` (remove/soft-delete). Action-style endpoints that don't fit
  CRUD (approve, reject, cancel, retry) are modeled as `POST /{resource}/{id}/<verb>` rather than
  overloading `PATCH` with implicit side effects.
- **Pagination**: cursor-based pagination (`?cursor=...&limit=...`) for all list endpoints over
  potentially large tables (`Logs`, `Events`, `AuditLogs`, `Tasks`); response envelope includes
  `next_cursor` and `has_more`, not raw offset/limit for those tables (offset pagination is
  acceptable only for small, bounded collections like `Roles`).
- **Response envelope**: consistent shape — `{ "data": ..., "meta": {...} }` for success,
  `{ "error": { "code": "...", "message": "...", "details": {...} } }` for errors, using a fixed
  internal error code vocabulary (not raw exception strings) so the frontend can branch on `code`
  reliably.
- **Filtering/sorting**: query params `?filter[field]=value`, `?sort=-created_at` convention,
  documented per endpoint in the OpenAPI schema rather than invented ad hoc per router.
- **Idempotency**: any endpoint that can enqueue a mutating job to `execution-worker` accepts an
  `Idempotency-Key` header and de-dupes on it, since approval-gated actions must be safe to retry
  from the client without double-executing against real infrastructure.
- **Auth**: all `/api/v1/**` routes (except `/health/*` and auth endpoints themselves) require a
  bearer token validated by the `get_current_user` dependency; every response is scoped to the
  caller's `Organization` — cross-tenant leakage is treated as a security-critical bug subject to
  the mandatory two-reviewer rule for the fix.
- **OpenAPI**: FastAPI's generated OpenAPI schema is the single source of truth for the contract;
  it is published to `docs/` on each release and diffed in CI so unintentional breaking changes to
  `v1` are caught before merge.
