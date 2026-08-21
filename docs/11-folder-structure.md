# Monorepo Folder Structure

## 1. Why a monorepo

AI Infrastructure Copilot ships four deployable services (`web`, `api`, `ai-orchestrator`, `execution-worker`) plus a `notification-gateway`, all of which share types (API contracts, `Tasks`/`Alerts`/`AIMessages` shapes), all of which are versioned and released together against the same PostgreSQL schema, and all of which are built by the same small team. A monorepo keeps shared TypeScript types and shared Python schemas in one place with atomic cross-service commits (a schema change and its consumers land in one PR), while each app still gets its own Dockerfile, its own dependency manifest, and its own CI job so services build, test, and deploy independently. Polyrepo would be premature given the team size and the tight coupling between the API contract and every consumer of it.

## 2. Top-level layout

```
ai-infra-copilot/
├── apps/
│   ├── web/                     # Next.js 15 frontend
│   ├── api/                     # FastAPI backend (modular monolith)
│   ├── ai-orchestrator/         # LangGraph agent orchestration service
│   ├── execution-worker/        # Isolated WinRM/SSH execution service
│   └── notification-gateway/    # Socket.IO service
├── packages/
│   ├── shared-types/            # Cross-app TypeScript types (API contracts, WS events)
│   ├── ui/                      # Shared shadcn/ui-based component library (optional, if web grows multiple apps)
│   └── py-shared/                # Cross-Python-service package (pydantic schemas, enums, MCP client)
├── infra/
│   ├── terraform/                # Cloud infra as code (per environment)
│   ├── k8s/                      # Kubernetes manifests or Helm charts
│   └── docker/                   # Shared base Dockerfiles / compose for local dev
├── docs/                          # Architecture and design documentation (this file lives here)
├── scripts/                       # Repo-wide dev scripts (bootstrap, seed data, lint-all)
├── .github/
│   └── workflows/                 # CI pipelines, one per app + shared checks
├── package.json                   # Root workspace config (pnpm/turbo/nx)
├── pnpm-workspace.yaml
├── turbo.json                     # Or nx.json, depending on chosen build orchestrator
└── README.md
```

## 3. `apps/web` — Next.js 15 frontend

```
apps/web/
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   └── layout.tsx
│   │   ├── (dashboard)/
│   │   │   ├── layout.tsx            # Shell with nav, socket provider
│   │   │   ├── inventory/page.tsx    # Infrastructure Inventory module
│   │   │   ├── active-directory/page.tsx
│   │   │   ├── group-policy/page.tsx
│   │   │   ├── event-log-analyzer/page.tsx
│   │   │   ├── iis-copilot/page.tsx
│   │   │   ├── dns-manager/page.tsx
│   │   │   ├── dhcp-manager/page.tsx
│   │   │   ├── performance-analyzer/page.tsx
│   │   │   ├── powershell-generator/page.tsx
│   │   │   ├── bash-generator/page.tsx
│   │   │   ├── script-library/page.tsx
│   │   │   ├── server-health/page.tsx
│   │   │   ├── alert-center/page.tsx
│   │   │   ├── security-center/page.tsx
│   │   │   ├── ai-chat/page.tsx
│   │   │   ├── automation-workflows/page.tsx
│   │   │   ├── vmware/page.tsx
│   │   │   ├── hyper-v/page.tsx
│   │   │   └── cloud-management/page.tsx
│   │   └── api/                      # Next.js route handlers (BFF-thin, mostly proxies)
│   ├── components/
│   │   ├── ui/                       # shadcn/ui generated components
│   │   ├── chat/                     # AI Chat widgets, message bubbles, approval cards
│   │   ├── dashboard/                # Charts, health tiles, alert widgets
│   │   └── forms/                    # Shared form primitives (React Hook Form + zod)
│   ├── hooks/
│   │   ├── use-socket.ts             # Socket.IO client hook
│   │   └── use-approval-flow.ts
│   ├── lib/
│   │   ├── api-client.ts             # Typed fetch wrapper using packages/shared-types
│   │   ├── query-client.ts           # React Query setup
│   │   └── auth.ts
│   ├── stores/                       # Client-side state (zustand or React context) for UI-only state
│   └── styles/
│       └── globals.css               # Tailwind entry
├── public/
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── package.json
└── Dockerfile
```

## 4. `apps/api` — FastAPI backend (modular monolith)

Routers map 1:1 to the 20 product modules; each router owns its own request/response schemas and calls into a service layer, keeping the AI-invocation and execution-invocation paths thin (they only enqueue jobs, never call LLMs or WinRM/SSH directly).

```
apps/api/
├── app/
│   ├── main.py                        # FastAPI app factory, middleware, router registration
│   ├── core/
│   │   ├── config.py                  # Settings (pydantic-settings)
│   │   ├── security.py                # JWT, password hashing, RBAC dependency
│   │   ├── db.py                      # SQLAlchemy engine/session, pgvector session
│   │   ├── redis.py                   # Redis client, queue producer helpers
│   │   └── logging.py
│   ├── modules/
│   │   ├── authentication/
│   │   │   ├── router.py
│   │   │   ├── schemas.py
│   │   │   └── service.py
│   │   ├── infrastructure_inventory/
│   │   ├── active_directory_management/
│   │   ├── group_policy_management/
│   │   ├── windows_event_log_analyzer/
│   │   ├── iis_copilot/
│   │   ├── dns_manager/
│   │   ├── dhcp_manager/
│   │   ├── performance_analyzer/
│   │   ├── powershell_generator/
│   │   ├── bash_script_generator/
│   │   ├── script_library/
│   │   ├── server_health_dashboard/
│   │   ├── alert_center/
│   │   ├── security_center/
│   │   ├── ai_chat/                   # Enqueues to ai-jobs queue, reads AIConversations/AIMessages
│   │   ├── automation_workflows/
│   │   ├── vmware_management/
│   │   ├── hyperv_management/
│   │   └── cloud_management/
│   ├── models/                        # SQLAlchemy ORM models, one file per core entity group
│   │   ├── organization.py
│   │   ├── user.py                    # Users, Roles, Permissions
│   │   ├── infrastructure.py          # Servers, Devices, InfrastructureInventory
│   │   ├── credential.py              # Credentials (vaulted references only)
│   │   ├── task.py                    # Tasks, AutomationJobs, Workflows
│   │   ├── policy.py                  # Policies
│   │   ├── alerting.py                # Alerts, Events, Logs
│   │   ├── ai.py                      # AIConversations, AIMessages
│   │   ├── script.py                  # Scripts
│   │   ├── report.py                  # Reports
│   │   ├── audit.py                   # AuditLogs
│   │   └── notification.py            # Notifications
│   ├── repositories/                   # Query layer per entity group
│   ├── queue/
│   │   ├── producer.py                 # Enqueue helpers for ai-jobs / execution-jobs
│   │   └── schemas.py                  # Job payload contracts (mirrors packages/py-shared)
│   ├── dependencies/                   # FastAPI Depends() for auth, pagination, org scoping
│   └── migrations/                     # Alembic migrations
│       └── versions/
├── tests/
│   ├── unit/
│   └── integration/
├── alembic.ini
├── pyproject.toml
└── Dockerfile
```

## 5. `apps/ai-orchestrator` — LangGraph agent orchestration service

```
apps/ai-orchestrator/
├── app/
│   ├── main.py                          # Worker entrypoint (consumes ai-jobs queue)
│   ├── graphs/
│   │   ├── planner_graph.py             # Planner node: prompt -> plan -> agent selection
│   │   ├── diagnosis_graph.py           # Data Collection -> Reasoning -> RCA -> Recommendation
│   │   └── script_generation_graph.py   # Recommendation -> Script Generation -> approval handoff
│   ├── agents/
│   │   ├── infrastructure_agent.py
│   │   ├── windows_agent.py
│   │   ├── linux_agent.py
│   │   ├── cloud_agent.py
│   │   ├── active_directory_agent.py
│   │   ├── powershell_agent.py
│   │   ├── security_agent.py
│   │   ├── network_agent.py
│   │   ├── vmware_agent.py
│   │   ├── hyperv_agent.py
│   │   ├── automation_agent.py
│   │   ├── reporting_agent.py
│   │   ├── planner_agent.py
│   │   ├── memory_agent.py
│   │   └── coordinator_agent.py
│   ├── mcp_servers/
│   │   ├── windows_mcp_server.py        # MCP tool server exposing WinRM/WMI read-only tools
│   │   ├── linux_mcp_server.py
│   │   ├── cloud_mcp_server.py
│   │   └── registry.py                  # MCP server discovery/registration
│   ├── llm/
│   │   ├── provider_interface.py        # Provider-agnostic LLM interface
│   │   ├── openai_provider.py
│   │   └── local_llm_provider.py        # vLLM/Ollama client
│   ├── rag/
│   │   ├── retriever.py                 # pgvector similarity search
│   │   ├── embeddings.py
│   │   └── ingestion.py                 # Document/log ingestion pipeline into pgvector
│   ├── queue/
│   │   ├── consumer.py                  # ai-jobs consumer
│   │   └── producer.py                  # Enqueues execution-jobs (never executes directly)
│   └── checkpointing.py                 # LangGraph state checkpoint persistence
├── tests/
├── pyproject.toml
└── Dockerfile
```

## 6. `apps/execution-worker` — isolated execution service

```
apps/execution-worker/
├── app/
│   ├── main.py                         # Worker entrypoint (consumes execution-jobs queue only)
│   ├── connectors/
│   │   ├── winrm_connector.py          # WinRM/PowerShell remoting
│   │   ├── ssh_connector.py            # SSH/Bash
│   │   ├── cloud_connectors/
│   │   │   ├── azure_connector.py
│   │   │   ├── aws_connector.py
│   │   │   └── gcp_connector.py
│   │   ├── vmware_connector.py
│   │   └── hyperv_connector.py
│   ├── vault/
│   │   └── credential_resolver.py       # Resolves Credentials reference -> secret at call time only
│   ├── execution/
│   │   ├── runner.py                    # Executes approved Tasks/AutomationJobs, streams output
│   │   ├── idempotency.py               # Dedupe key checks before running
│   │   └── result_writer.py             # Writes Tasks/Logs/AuditLogs outcome
│   ├── queue/
│   │   └── consumer.py
│   └── policies/
│       └── approval_guard.py            # Hard check: refuses to run any mutating job without APPROVED status
├── tests/
├── pyproject.toml
└── Dockerfile
```

## 7. `apps/notification-gateway` — Socket.IO service

```
apps/notification-gateway/
├── app/
│   ├── main.py                          # Socket.IO server (python-socketio or Node/Socket.IO server)
│   ├── auth.py                          # WS token validation
│   ├── rooms.py                         # org/user/task/resource room management
│   ├── pubsub_bridge.py                 # Redis pub/sub -> Socket.IO room fan-out
│   └── events/
│       ├── task_events.py
│       ├── alert_events.py
│       └── approval_events.py
├── tests/
├── pyproject.toml (or package.json if Node-based)
└── Dockerfile
```

## 8. `packages/shared-types`

```
packages/shared-types/
├── src/
│   ├── api/                             # Request/response types mirroring FastAPI schemas
│   ├── entities/                        # Organizations, Users, Servers, Tasks, Alerts, etc.
│   ├── ws-events/                       # task.progress, alert.created, approval.requested, ...
│   └── index.ts
├── package.json
└── tsconfig.json
```

## 9. `packages/py-shared`

```
packages/py-shared/
├── py_shared/
│   ├── schemas/                         # Pydantic models shared by api, ai-orchestrator, execution-worker
│   ├── enums/                           # TaskStatus, ApprovalStatus, AgentType, ModuleName
│   ├── job_contracts/                   # ai-job and execution-job payload contracts
│   └── mcp_client/                      # Shared MCP client used by ai-orchestrator
├── pyproject.toml
```

## 10. `infra/`

```
infra/
├── terraform/
│   ├── modules/
│   │   ├── network/                     # VPC, subnets, execution-worker isolated segment
│   │   ├── k8s-cluster/
│   │   ├── postgres/
│   │   ├── redis/
│   │   ├── opensearch/
│   │   └── vault/
│   └── environments/
│       ├── dev/
│       ├── staging/
│       └── prod/
├── k8s/                                  # Or helm/ if templated via Helm
│   ├── base/
│   │   ├── api/
│   │   ├── web/
│   │   ├── ai-orchestrator/
│   │   ├── execution-worker/
│   │   ├── notification-gateway/
│   │   └── network-policies/             # Restrictive NetworkPolicy for execution node pool
│   └── overlays/
│       ├── dev/
│       ├── staging/
│       └── prod/
└── docker/
    ├── docker-compose.local.yml           # Local dev: postgres, redis, opensearch, all apps
    └── base-images/
```

## 11. `docs/`

```
docs/
├── README.md
├── 02-HLD.md
├── 11-folder-structure.md
├── 13-microservice-breakdown.md
└── ... (additional LLD, ERD, API-spec, and module docs)
```

## 12. Notes on build tooling

- Root workspace uses pnpm workspaces for the two Node/TS packages (`apps/web`, `packages/shared-types`, and `apps/notification-gateway` if implemented in Node) plus Turborepo (or Nx) for task graph caching across `build`/`lint`/`test`.
- Python apps (`apps/api`, `apps/ai-orchestrator`, `apps/execution-worker`, `packages/py-shared`) are independent `pyproject.toml` projects; `packages/py-shared` is installed as a local path dependency by the other three so a schema change is picked up by every consumer without publishing to a package index.
- Each app directory owns its own `Dockerfile` so CI builds and deploys each service independently; `infra/docker/docker-compose.local.yml` wires them together for local development against local Postgres/Redis/OpenSearch containers.
