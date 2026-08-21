# AI Infrastructure Copilot — Developed Tasks & Feature Inventory

This document details all **developed and implemented features** in the AI Infrastructure Copilot codebase, mapped to their specific API endpoints, database models, AI agents, background workers, and frontend components.

---

## 1. Authentication & Multi-Factor Auth (MFA / TOTP)
- **Status**: [x] Developed & Verified
- **Backend Service**: `apps/api/app/modules/authentication`
- **Database Models**: `User`, `Organization`, `UserDevice`
- **API Endpoints**:
  - `POST /api/v1/auth/login` — User authentication returning JWT access and refresh tokens
  - `POST /api/v1/auth/refresh` — Refresh access token using valid refresh token
  - `POST /api/v1/auth/mfa/enroll` — Generate TOTP MFA secret key & QR code URI (`pyotp`)
  - `POST /api/v1/auth/mfa/verify` — Validate TOTP token and enable MFA for user account
  - `POST /api/v1/auth/change-password` — Secure password change with session revocation
- **Frontend UI**: `apps/web/src/features/auth`
  - Login page with custom autofill styling override
  - TOTP enrollment modal & verification form
  - Password change form with strength indicators and show/hide toggles
  - Automatic JWT token refresh interceptor in Axios/Fetch wrapper

---

## 2. Role-Based Access Control (RBAC) & User Management
- **Status**: [x] Developed & Verified
- **Backend Service**: `apps/api/app/modules/rbac`, `apps/api/app/modules/users`
- **Database Models**: `Role`, `Permission`, `RolePermission`, `UserRole`, `Department`, `Designation`
- **Alembic Migrations**: `0001_initial_schema.py`, `0002_seed_default_admin.py`, `0004_departments_designations.py`
- **API Endpoints**:
  - `GET /api/v1/roles`, `POST /api/v1/roles` — Role management and permission binding
  - `GET /api/v1/permissions` — System permission definitions enumeration
  - `GET /api/v1/users`, `POST /api/v1/users`, `PATCH /api/v1/users/{id}` — User CRUD & status toggles
  - `GET /api/v1/departments`, `GET /api/v1/designations` — Organizational structure hierarchy
- **Frontend UI**: `apps/web/src/features/roles`, `apps/web/src/features/users`, `apps/web/src/features/departments`
  - Roles management grid with checkbox matrix for granular permissions
  - User administration table with status toggles and device tracking
  - Department and designation setup panels

---

## 3. Infrastructure Inventory & Server Connection Management
- **Status**: [x] Developed & Verified
- **Backend Service**: `apps/api/app/modules/infrastructure_inventory`, `apps/api/app/modules/credentials`
- **Database Models**: `Server`, `InfrastructureInventory`, `Credential`, `CPU`, `MemoryModule`, `Disk`, `NetworkAdapter`
- **Alembic Migrations**: `0003_server_winrm_connection_settings.py`, `3838d8e1c37a_add_hardware_inventory_tables.py`
- **API Endpoints**:
  - `GET /api/v1/infrastructure/servers`, `POST /api/v1/infrastructure/servers` — Server asset management
  - `GET /api/v1/infrastructure/servers/{id}` — Detailed server hardware telemetry (CPU/RAM/Disk)
  - `POST /api/v1/credentials` — Create vaulted credential (local encrypted / HashiCorp Vault)
- **Frontend UI**: `apps/web/src/features/inventory`, `apps/web/src/features/infrastructure`
  - Server Inventory table with OS icons, environment tags (Production/Staging), and health status badges
  - Server inspector modal showing CPU, memory, disk usage bars, IP address, and WinRM status

---

## 4. Network Discovery & Server Fingerprinting
- **Status**: [x] Developed & Verified
- **Backend Service**: `apps/api/app/modules/discovery`
- **Database Models**: `NetworkDiscoveryScan`, `DiscoveredDevice`, `IPRange`, `DeviceFingerprint`
- **Alembic Migrations**: `1c5e519833f1_network_discovery.py`, `db5b184a8231_fingerprint_discovery.py`
- **API Endpoints**:
  - `POST /api/v1/discovery/scans` — Initiate subnet IP range discovery scan
  - `GET /api/v1/discovery/devices` — Fetch discovered IP devices and open ports
  - `POST /api/v1/discovery/fingerprint` — Trigger OS fingerprinting and service detection
- **Frontend UI**: `apps/web/src/features/discovery`
  - Subnet scanner config card (CIDR input, scan speed settings)
  - Live discovery progress bar and discovered device results table
  - OS fingerprinting & port scanning breakdown view

---

## 5. RAG Knowledge Base & Document Processing Pipeline
- **Status**: [x] Developed & Verified
- **Backend Service**: `apps/api/app/modules/knowledge`, `apps/api/app/workers/tasks/document_tasks.py`
- **Database Models**: `KnowledgeDocument`, `KnowledgeChunk` with `pgvector` vector embedding column
- **Alembic Migration**: `0005_knowledge_base.py`
- **API Endpoints & Celery Workers**:
  - `POST /api/v1/knowledge/upload` — Multipart document upload (PDF, Docx, HTML, TXT)
  - `GET /api/v1/knowledge/documents` — Knowledge Base document status tracking
  - `Celery Worker`: Background document parsing (`python-docx`, `pypdf`, `beautifulsoup4`), text chunking, embedding generation (`openai` / `tiktoken` / vLLM), and `pgvector` insertion
- **Frontend UI**: `apps/web/src/features/knowledge-base`
  - Document dropzone uploader
  - Ingested documents list with parsing status badges (Processing, Ready, Failed)
  - Vector chunk inspector modal

---

## 6. Windows Event Log Analyzer & Root Cause Analysis (RCA)
- **Status**: [x] Developed & Verified
- **Backend Service**: `apps/api/app/modules/windows_event_log_analyzer`
- **Database Models**: `EventLogEntry`
- **Data Seeding**: `apps/api/scripts/seed.py` (Seeds realistic System, Application, and EventLog entries for `web-prod-03`)
- **API Endpoints**:
  - `GET /api/v1/windows-event-log/logs` — Query event logs by server, level (Critical, Error, Warning), log channel, or time window
  - `POST /api/v1/windows-event-log/analyze` — Run AI-powered root cause analysis on log clusters
- **Frontend UI**: `apps/web/src/features/event-log`
  - Windows Event Log viewer table with severity filters and live search
  - "Run AI Root Cause Analysis" action button triggering Windows Agent diagnosis

---

## 7. PowerShell Script Generator & Static Safety Analysis
- **Status**: [x] Developed & Verified
- **Backend Service**: `apps/api/app/modules/scripts`
- **Database Models**: `Script`
- **AI Agent**: `apps/ai-orchestrator/app/agents/powershell_agent.py`
- **API Endpoints**:
  - `POST /api/v1/scripts/generate` — Generate safe, commented PowerShell scripts based on natural language prompt
  - `POST /api/v1/scripts/validate-safety` — Run static safety analysis against generated code
- **Frontend UI**: `apps/web/src/features/powershell`
  - Prompt input box with pre-built admin prompt templates
  - Syntax-highlighted code display
  - Static safety check breakdown card (Risk level: Low/Medium/High, flagged commands)
  - "Submit Task for Human Approval" action button

---

## 8. AI Orchestrator Multi-Agent System (LangGraph + MCP)
- **Status**: [x] Developed & Verified
- **Orchestrator Service**: `apps/ai-orchestrator/app`
- **Multi-Agent Graph**: `LangGraph` workflow in `app/graph.py`
- **Implemented Agents**:
  - `PlannerAgent` (`planner_agent.py`): Parses user intent, decomposes request, selects target agent
  - `CoordinatorAgent` (`coordinator_agent.py`): Manages agent routing and context passing
  - `WindowsAgent` (`windows_agent.py`): Performs Windows diagnostics & Event Log reasoning
  - `PowerShellAgent` (`powershell_agent.py`): Generates parameterised PowerShell scripts
  - `RagAgent` (`rag_agent.py`): Queries `pgvector` knowledge base for relevant infrastructure docs
- **MCP Tool Integration**: Model Context Protocol servers in `mcp_windows.py` and `mcp_scripting.py`
- **API Endpoints**:
  - `POST /api/v1/chat/completions` — Streaming / sync multi-agent response generation
  - `GET /api/v1/chat/sessions`, `GET /api/v1/chat/sessions/{id}/messages` — Chat conversation history
- **Frontend UI**: `apps/web/src/features/ai-chat`
  - Interactive AI Chat interface with markdown code block formatting
  - Multi-turn conversation sidebar
  - Embedded script execution approval proposal cards

---

## 9. Human Approval Gate & Deterministic Task Runner
- **Status**: [x] Developed & Verified
- **Backend Services**: `apps/api/app/modules/tasks`, `apps/api/app/execution/runner.py`
- **Database Models**: `Task`, `AuditLog`
- **API Endpoints**:
  - `POST /api/v1/tasks` — Queue generated script for approval (`status=pending_approval`)
  - `GET /api/v1/tasks/pending` — List pending approval queue for organization
  - `POST /api/v1/tasks/{id}/approve` — Approve task execution; invokes `runner.py`
  - `POST /api/v1/tasks/{id}/reject` — Reject task execution with reason
- **Execution Safety Engine**: `app/execution/runner.py`
  - Validates `status == 'approved'` before execution
  - Respects `EXECUTION_ENABLED` feature flag
  - Executes WinRM PowerShell via `winrm_client.py` using vaulted credentials
  - Writes structured audit trail entry to `AuditLogs`
- **Frontend UI**: `apps/web/src/features/dashboard/components/RecentAutomationRuns.tsx`
  - Pending approval task card with script diff preview, target server hostname, and safety analysis
  - One-click "Approve & Execute" and "Reject" buttons

---

## 10. Process Management & Environment Setup
- **Status**: [x] Developed & Verified
- **PM2 Ecosystem**: `ecosystem.config.js` running 4 concurrent processes:
  - `api`: FastAPI backend service on port 8000
  - `ai-orchestrator`: LangGraph AI service on port 8001
  - `celery-worker`: Document parsing background worker on `documents` queue
  - `web`: Next.js frontend application on port 3000
- **Dev Setup Script**: `scripts/dev-setup.sh` initializing Python virtual environments and editable packages (`py-shared`)
- **Data Seeding**: `apps/api/scripts/seed.py` seeding default org, admin user (`admin@acmecorp.io`), target server (`web-prod-03`), and realistic Windows Event Logs.
