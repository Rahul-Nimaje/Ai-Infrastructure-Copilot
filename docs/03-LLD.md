# AI Infrastructure Copilot — Low-Level Design (LLD)

## 0. Purpose and Cross-Cutting Conventions

This document specifies the low-level design of the 20 product modules that make up AI Infrastructure Copilot. It is intended to let a dev team scope sprints directly from it. Application code does not exist yet; this LLD is the contract between product, architecture, and engineering.

**AI workflow (applies to every module below):**
`User Prompt → Planner → Agent Selection → Tool Calling → Data Collection → Reasoning → Root Cause Analysis → Recommendation → Script Generation → Human Approval → Execution (via WinRM/SSH) → Audit Log`

**Execution safety rule (global, non-negotiable):** every mutating action, regardless of module or agent, must pass through the Human Approval gate before it reaches Execution. Read-only diagnostics and data-collection calls may auto-run without approval. This rule is restated per-module under "Safety notes" and is enforced centrally by the Execution service, not by individual agents.

**AI Agent Registry (15 agents).** This is the canonical list from `docs/README.md` and `06-ai-architecture.md` — modules below reference these agents by exact name when describing which agent calls the module as an LLM tool via MCP. Several modules that have no 1:1 dedicated agent are covered by the nearest domain-general agent (noted per module):

| # | Agent | Scope |
|---|---|---|
| 1 | Infrastructure Agent | Infrastructure inventory and asset discovery across all target types |
| 2 | Windows Agent | Windows-server operations not owned by a more specific agent: Group Policy, Windows Event Log, IIS, and the Windows side of Performance Analyzer |
| 3 | Linux Agent | Linux-server operations: the Linux side of Performance Analyzer, and Bash script generation |
| 4 | Cloud Agent | Azure, AWS, GCP resource operations |
| 5 | Active Directory Agent | AD users, groups, OUs, computer objects |
| 6 | PowerShell Agent | Generates and risk-scores PowerShell scripts |
| 7 | Security Agent | Threat detection across Windows/Linux/network signals |
| 8 | Network Agent | DNS zones/records and DHCP scopes/leases/reservations, replication, diagnostics |
| 9 | VMware Agent | ESXi, vCenter, datastore, cluster, snapshot operations |
| 10 | Hyper-V Agent | Hyper-V host, VM, replication, storage operations |
| 11 | Automation Agent | Defines, schedules, and triggers Automation Workflows jobs |
| 12 | Reporting Agent | Turns findings into human-readable reports and scheduled summaries (Weekly Reports, Monthly Patch Report) |
| 13 | Planner Agent | Decomposes the user prompt, selects downstream agents/tools, drives the LangGraph state machine end to end |
| 14 | Memory Agent | Manages short-term conversation memory and long-term RAG memory (pgvector) shared by all other agents, including the Script Library retrieval bias |
| 15 | Coordinator Agent | Sequences/parallelizes calls to multiple specialist agents and merges their results into a single response |

Modules that are primarily platform/UX surfaces (Authentication, Script Library, Server Health Dashboard, Alert Center, AI Chat) do not own a dedicated agent; they are entered through the **Planner Agent**, which selects and the **Coordinator Agent**, which sequences the specialist agents above as needed.

All FastAPI routes are versioned under `/api/v1/...` and live behind the single FastAPI backend service. All mutating routes create a `Tasks`/`AutomationJobs` record and an `AuditLogs` entry regardless of whether they were invoked from the UI or from an AI agent tool call.

---

## 1. Authentication — Login, SSO, Azure AD, MFA, JWT, RBAC, Session Management

**Responsibilities**
- Local username/password login with salted-hash storage and lockout policy.
- SSO via SAML 2.0 / OIDC, with first-class Azure AD (Entra ID) integration (OIDC + Graph API group sync).
- MFA via TOTP (authenticator apps) and optional WebAuthn/FIDO2; MFA enforcement configurable per Organization.
- JWT issuance (access + refresh token pair), token rotation, revocation.
- RBAC: Roles composed of Permissions, scoped per Organization; permission checks on every FastAPI route via dependency injection.
- Session management: active session listing, remote sign-out, idle/absolute timeout policies, concurrent-session limits.

**Data flow**
- In: credentials/SSO assertions from the browser (Next.js frontend); Azure AD OIDC callback carries ID token + claims; Graph API pulled server-side for group-to-role mapping.
- Out: JWT access/refresh tokens returned to frontend (stored in httpOnly cookies); session state cached in Redis for fast revocation checks; login/MFA/session events written to `AuditLogs` and streamed to the UI via Socket.IO for admin session monitors.
- No AI agent involvement — Authentication is a prerequisite platform service, not an AI tool. All AI Chat and module API calls pass the resolved `Users`/`Roles`/`Permissions` context downstream as request context, not as agent tool input.

**Key interfaces**
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/mfa/enroll`
- `POST /api/v1/auth/mfa/verify`
- `GET /api/v1/auth/sso/azure-ad/login`
- `GET /api/v1/auth/sso/azure-ad/callback`
- `GET /api/v1/auth/sessions`
- `DELETE /api/v1/auth/sessions/{sessionId}`
- `GET /api/v1/rbac/roles`, `POST /api/v1/rbac/roles`, `PUT /api/v1/rbac/roles/{id}`
- `GET /api/v1/rbac/permissions`

**DB tables touched**
- Core: `Organizations`, `Users`, `Roles`, `Permissions`, `AuditLogs`, `Notifications`.
- Module-specific: `Sessions`, `MFADevices`, `SSOConfigurations`, `RefreshTokens`, `LoginAttempts`.

**Safety notes**
- Role/permission changes and forced session revocation are mutating administrative actions; they are gated by RBAC (only Org Admin-level roles) but are **not** part of the infrastructure Human Approval/Execution pipeline since they do not touch managed infrastructure — they follow standard admin-audit controls instead (immediate effect, always logged to `AuditLogs`).
- Failed login/MFA attempts beyond threshold trigger account lockout and an `Alerts` entry (feeds Security Center, module 15).

---

## 2. Infrastructure Inventory — Auto Discovery of Windows Servers, Linux Servers, Domain Controllers, Routers, Firewalls, NAS, Hyper-V, VMware, Cloud Resources

**Responsibilities**
- Scheduled and on-demand discovery sweeps across IP ranges, AD domains, cloud subscriptions/accounts, and hypervisor inventories.
- Classifies discovered assets by type (Windows Server, Linux Server, Domain Controller, Router, Firewall, NAS, Hyper-V host, VMware host, Cloud Resource) and fingerprints OS/version/roles.
- Maintains a live, deduplicated `InfrastructureInventory` with health/reachability status and ownership tagging.
- Detects drift (new/removed/changed assets) between sweeps and raises change events.

**Data flow**
- In: ICMP/ARP/port sweeps and reverse-DNS for network discovery; WinRM/WMI probes for Windows fingerprinting; SSH banner + `uname`/`hostnamectl` for Linux; AD LDAP queries for Domain Controllers and computer objects; vCenter API for VMware; Hyper-V WMI/PowerShell for Hyper-V hosts; Azure/AWS/GCP SDK resource-graph queries for cloud assets.
- Out: normalized asset records written to `InfrastructureInventory` and `Servers`/`Devices`; discovery job status pushed to UI via Socket.IO; new/changed assets emitted as `Events` consumed by the AI layer (Planner Agent) and Alert Center.
- AI tool usage: **Infrastructure Agent** calls this module's read endpoints to ground its answers ("what servers do we have," "is X reachable") and to seed other agents with target lists (e.g., handing Windows Agent/Linux Agent a list of hosts to poll).

**Key interfaces**
- `POST /api/v1/inventory/discovery-jobs`
- `GET /api/v1/inventory/discovery-jobs/{id}`
- `GET /api/v1/inventory/assets`
- `GET /api/v1/inventory/assets/{id}`
- `PATCH /api/v1/inventory/assets/{id}` (ownership/tag edits)
- `GET /api/v1/inventory/changes`
- `POST /api/v1/inventory/credentials-test` (validates `Credentials` against a target without mutating it)

**DB tables touched**
- Core: `InfrastructureInventory`, `Servers`, `Devices`, `Credentials`, `Events`, `Logs`, `AuditLogs`.
- Module-specific: `DiscoveryJobs`, `DiscoveredAssets`, `AssetChangeHistory`.

**Safety notes**
- Discovery itself is read-only (network probes, credentialed read queries) and auto-runs on schedule without approval.
- The only mutating actions are asset metadata edits (tags/ownership) and credential rotation triggers, both of which go through Human Approval before write, and are logged to `AuditLogs`.

---

## 3. Active Directory Management — User Management, Group Management, OU Management, Password Reset, Unlock Users, Disable Users, Group Membership, Computer Objects

**Responsibilities**
- Read and manage AD Users, Groups, Organizational Units, and Computer Objects.
- Operational actions: create/disable/enable user, reset password (with force-change-at-next-logon), unlock locked-out accounts, manage group membership, move/rename OUs, manage computer object lifecycle (including stale-object detection).

**Data flow**
- In: AD queried via LDAP/LDAPS for reads; mutating operations executed via PowerShell remoting (WinRM) invoking the ActiveDirectory PowerShell module on a domain-joined jump host/DC.
- Out: cached/normalized AD object state written to module tables for fast search/reporting; mutation results and before/after state written to `AuditLogs`; UI updated via React Query invalidation + Socket.IO event; AI layer receives structured findings (e.g., "12 users locked out in last hour") for Root Cause Analysis.
- AI tool usage: **Active Directory Agent** calls read endpoints to answer questions ("who is locked out," "is user X in group Y") and proposes mutating calls (unlock, password reset, group add/remove), which are staged as `Tasks` pending Human Approval before the Active Directory Agent's proposed PowerShell is executed.

**Key interfaces**
- `GET /api/v1/ad/users`, `GET /api/v1/ad/users/{id}`
- `POST /api/v1/ad/users/{id}/reset-password`
- `POST /api/v1/ad/users/{id}/unlock`
- `POST /api/v1/ad/users/{id}/disable`
- `POST /api/v1/ad/users/{id}/enable`
- `GET /api/v1/ad/groups`, `POST /api/v1/ad/groups/{id}/members`, `DELETE /api/v1/ad/groups/{id}/members/{userId}`
- `GET /api/v1/ad/ous`, `PATCH /api/v1/ad/ous/{id}`
- `GET /api/v1/ad/computers`, `POST /api/v1/ad/computers/{id}/decommission`

**DB tables touched**
- Core: `Servers` (DC records), `Credentials`, `Tasks`, `Scripts`, `AuditLogs`, `AIConversations`, `AIMessages`.
- Module-specific: `ADUserCache`, `ADGroupCache`, `ADOrganizationalUnitCache`, `ADComputerObjectCache`, `ADMembershipChangeLog`.

**Safety notes**
- All AD mutations (password reset, unlock, disable/enable, group membership changes, OU edits, computer object decommission) are mutating and require explicit Human Approval before the generated PowerShell is executed via WinRM against the DC.
- Read/list/search operations are diagnostic and auto-run.
- Every approved mutation captures pre-state and post-state in `AuditLogs` for compliance (AD changes are high-sensitivity).

---

## 4. Group Policy Management — Analyze Existing GPO, Create GPO, Modify GPO, Link GPO, Backup, Rollback, Conflict Detection

**Responsibilities**
- Inventory and analyze existing GPOs (settings, links, scope, precedence).
- Create new GPOs and modify settings from natural-language intent.
- Link/unlink GPOs to OUs/domains/sites; detect setting conflicts across linked GPOs (e.g., contradictory password policies).
- Backup GPOs before any change and support point-in-time rollback.

**Data flow**
- In: GPO metadata and settings pulled via PowerShell remoting (GroupPolicy module) over WinRM against a DC; SYSVOL read for backing store details.
- Out: parsed GPO structure cached to `GPOs`/`GPOLinks` tables; backups stored as versioned blobs referenced by `GPOBackups`; conflict findings surfaced to UI and to AI reasoning; rollback and change events logged to `AuditLogs`.
- AI tool usage: **Windows Agent** reads GPO state for analysis/conflict detection and drafts create/modify/link/rollback operations, which are queued as `Tasks` for Human Approval before PowerShell is run against the DC.

**Key interfaces**
- `GET /api/v1/gpo` (list/analyze)
- `GET /api/v1/gpo/{id}`
- `GET /api/v1/gpo/{id}/conflicts`
- `POST /api/v1/gpo`
- `PATCH /api/v1/gpo/{id}`
- `POST /api/v1/gpo/{id}/link`
- `DELETE /api/v1/gpo/{id}/link/{ouId}`
- `POST /api/v1/gpo/{id}/backup`
- `POST /api/v1/gpo/{id}/rollback`

**DB tables touched**
- Core: `Policies`, `Servers` (DC records), `Scripts`, `Tasks`, `AuditLogs`.
- Module-specific: `GPOs`, `GPOLinks`, `GPOBackups`, `GPOConflicts`, `GPOChangeHistory`.

**Safety notes**
- Create, modify, link/unlink, and rollback are all mutating and go through Human Approval; a backup is automatically taken and referenced in the approval request before any modify/rollback is executed.
- Analyze/list/conflict-detection are read-only and auto-run.

---

## 5. Windows Event Log Analyzer — Collect Logs, Detect Errors, Detect BSOD, Failed Logins, Windows Update Failures, Service Failures, Security Events

**Responsibilities**
- Continuous and on-demand collection of Application/System/Security event logs.
- Pattern detection: BSOD/stop-error events, failed logon storms (4625), Windows Update failures, service start/stop failures, and general Security-relevant events.
- Correlates event patterns into candidate root causes for the AI reasoning stage.

**Data flow**
- In: events pulled via WinRM (`Get-WinEvent`/PowerShell remoting) or WMI event subscriptions from target Windows Servers/Domain Controllers; large volumes are batched and shipped to OpenSearch for full-text/pattern search.
- Out: raw+parsed events indexed in OpenSearch and referenced by `EventLogEntries` metadata in PostgreSQL; detected patterns emitted as `Events`/`Alerts`; findings passed to AI layer for Root Cause Analysis and Recommendation.
- AI tool usage: **Windows Agent** queries collected/indexed events (via OpenSearch-backed endpoints) as the primary evidence source for diagnosing incidents (e.g., "why did Server X reboot at 2am").

**Key interfaces**
- `POST /api/v1/eventlogs/collection-jobs`
- `GET /api/v1/eventlogs`
- `GET /api/v1/eventlogs/search`
- `GET /api/v1/eventlogs/bsod`
- `GET /api/v1/eventlogs/failed-logins`
- `GET /api/v1/eventlogs/update-failures`
- `GET /api/v1/eventlogs/service-failures`
- `GET /api/v1/eventlogs/security-events`

**DB tables touched**
- Core: `Logs`, `Events`, `Alerts`, `Servers`.
- Module-specific: `EventLogEntries` (OpenSearch document refs), `EventLogCollectionJobs`, `EventPatternMatches`.

**Safety notes**
- Entirely read-only/diagnostic; collection and analysis auto-run without approval.
- Any remediation the AI recommends (e.g., "restart service," "roll back update") is scoped to modules 9/10/11/17 and must go through their respective Human Approval + Execution flow, not this module directly.

---

## 6. IIS Copilot — Website Status, Application Pools, Bindings, SSL, Logs, HTTP Errors, Performance

**Responsibilities**
- Monitors IIS site status, application pool health (running/stopped/crashed, recycle events), bindings, and SSL certificate validity/expiry.
- Parses IIS logs (W3C format) for HTTP error spikes (4xx/5xx) and performance (response time, throughput).
- Supports app pool recycle/start/stop, binding changes, and certificate rebind as remediation actions.

**Data flow**
- In: IIS state and logs collected via WinRM/PowerShell remoting (`WebAdministration` module) and direct log file reads (W3C logs) from IIS servers.
- Out: normalized site/pool/binding state to `IISSites`/`IISAppPools`/`IISBindings`; log-derived metrics indexed in OpenSearch; certificate expiry feeds `Alerts`/Certificate tracking shared with Server Health Dashboard (module 13).
- AI tool usage: **Windows Agent** reads site/pool/log state to diagnose outages ("site 500ing since deploy") and proposes remediation (recycle pool, rebind cert), staged for Human Approval.

**Key interfaces**
- `GET /api/v1/iis/sites`
- `GET /api/v1/iis/sites/{id}/status`
- `GET /api/v1/iis/app-pools`
- `POST /api/v1/iis/app-pools/{id}/recycle`
- `POST /api/v1/iis/app-pools/{id}/stop`
- `POST /api/v1/iis/app-pools/{id}/start`
- `GET /api/v1/iis/bindings`
- `PATCH /api/v1/iis/bindings/{id}`
- `GET /api/v1/iis/ssl-certificates`
- `GET /api/v1/iis/logs/http-errors`
- `GET /api/v1/iis/performance`

**DB tables touched**
- Core: `Servers`, `Logs`, `Alerts`, `AuditLogs`.
- Module-specific: `IISSites`, `IISAppPools`, `IISBindings`, `IISCertificates`, `IISHttpErrorStats`.

**Safety notes**
- Status/log/performance reads are diagnostic and auto-run.
- App pool recycle/start/stop and binding/certificate changes are mutating and require Human Approval before execution via WinRM.

---

## 7. DNS Manager — Zone Health, Replication, Record Management, Reverse Lookup, Diagnostics

**Responsibilities**
- Monitors DNS zone health and AD-integrated zone replication status across DCs.
- Manages records (A/AAAA/CNAME/MX/TXT/PTR), including create/update/delete.
- Provides reverse lookup and general diagnostics (e.g., stale record detection, orphaned PTR records, resolution latency checks).

**Data flow**
- In: zone/record data and replication metadata pulled via WinRM/PowerShell remoting (`DnsServer` module) against DNS servers/DCs; active resolution checks performed via direct DNS queries from the backend.
- Out: zone/record state cached to `DNSZones`/`DNSRecords`; replication and health status feed `Alerts`; diagnostic results returned to UI/AI.
- AI tool usage: **Network Agent** reads zone/record/replication state for diagnostics ("why can't host X resolve Y") and drafts record create/update/delete operations for Human Approval.

**Key interfaces**
- `GET /api/v1/dns/zones`
- `GET /api/v1/dns/zones/{id}/health`
- `GET /api/v1/dns/zones/{id}/replication`
- `GET /api/v1/dns/records`
- `POST /api/v1/dns/records`
- `PATCH /api/v1/dns/records/{id}`
- `DELETE /api/v1/dns/records/{id}`
- `GET /api/v1/dns/reverse-lookup`
- `GET /api/v1/dns/diagnostics`

**DB tables touched**
- Core: `Servers`, `Alerts`, `AuditLogs`.
- Module-specific: `DNSZones`, `DNSRecords`, `DNSReplicationStatus`, `DNSDiagnosticRuns`.

**Safety notes**
- Zone health, replication status, reverse lookup, and diagnostics are read-only and auto-run.
- Record create/update/delete are mutating and require Human Approval before execution via WinRM.

---

## 8. DHCP Manager — Scope Monitoring, Reservations, Lease Usage, Conflicts

**Responsibilities**
- Monitors DHCP scope utilization and lease usage trends.
- Manages reservations (create/update/delete) and detects IP conflicts (duplicate leases, scope exhaustion risk).

**Data flow**
- In: scope/lease/reservation data pulled via WinRM/PowerShell remoting (`DhcpServer` module) against DHCP servers.
- Out: scope/lease state cached to `DHCPScopes`/`DHCPLeases`/`DHCPReservations`; utilization and conflict findings feed `Alerts`.
- AI tool usage: **Network Agent** reads scope/lease/conflict state to diagnose issues ("scope near exhaustion," "duplicate IP") and drafts reservation changes for Human Approval.

**Key interfaces**
- `GET /api/v1/dhcp/scopes`
- `GET /api/v1/dhcp/scopes/{id}/utilization`
- `GET /api/v1/dhcp/leases`
- `GET /api/v1/dhcp/reservations`
- `POST /api/v1/dhcp/reservations`
- `PATCH /api/v1/dhcp/reservations/{id}`
- `DELETE /api/v1/dhcp/reservations/{id}`
- `GET /api/v1/dhcp/conflicts`

**DB tables touched**
- Core: `Servers`, `Alerts`, `AuditLogs`.
- Module-specific: `DHCPScopes`, `DHCPLeases`, `DHCPReservations`, `DHCPConflictLog`.

**Safety notes**
- Scope/lease/conflict monitoring is read-only and auto-runs.
- Reservation create/update/delete is mutating and requires Human Approval before execution via WinRM.

---

## 9. Performance Analyzer — CPU, Memory, Disk, Network, Services, Processes, Storage

**Responsibilities**
- Continuous telemetry collection and on-demand deep-dive analysis of CPU, memory, disk I/O and capacity, network throughput, service state, process-level resource usage, and storage volumes.
- Baselines normal behavior per host and flags anomalies (spikes, leaks, saturation) for Root Cause Analysis.
- Supports remediation actions: kill/restart process, restart service, clear disk space (delegates to Automation Workflows for scripted cleanup).

**Data flow**
- In: Windows targets via WinRM/WMI (`Get-Counter`, CIM classes); Linux targets via SSH (`top`/`vmstat`/`iostat`/`df`/`systemctl`/`journalctl`).
- Out: time-series metrics written to `PerformanceMetrics` (high-cardinality series may be pushed to OpenSearch); baseline deviations raised as `Alerts`; snapshots exposed to Server Health Dashboard (module 13).
- AI tool usage: **Windows Agent** (for Windows targets) and **Linux Agent** (for Linux targets) are the primary tools for CPU/memory/disk/network/process/service questions and root-cause chains ("why is CPU pegged"), and propose remediation staged for Human Approval.

**Key interfaces**
- `GET /api/v1/performance/{targetId}/cpu`
- `GET /api/v1/performance/{targetId}/memory`
- `GET /api/v1/performance/{targetId}/disk`
- `GET /api/v1/performance/{targetId}/network`
- `GET /api/v1/performance/{targetId}/services`
- `POST /api/v1/performance/{targetId}/services/{serviceName}/restart`
- `GET /api/v1/performance/{targetId}/processes`
- `POST /api/v1/performance/{targetId}/processes/{pid}/kill`
- `GET /api/v1/performance/{targetId}/storage`
- `GET /api/v1/performance/{targetId}/baselines`

**DB tables touched**
- Core: `Servers`, `Devices`, `Alerts`, `AuditLogs`.
- Module-specific: `PerformanceMetrics`, `PerformanceBaselines`, `ProcessSnapshots`, `ServiceStateSnapshots`.

**Safety notes**
- Metric collection, baselining, and listing processes/services are read-only and auto-run.
- Process kill and service restart are mutating and require Human Approval before execution via WinRM/SSH.

---

## 10. PowerShell Generator — generates secure PowerShell scripts with Explanation, Risk Analysis, Rollback Plan

**Responsibilities**
- Generates PowerShell scripts from natural-language intent, targeted at Windows/AD/IIS/DNS/DHCP/GPO operations requested elsewhere in the platform.
- Every generated script is accompanied by a plain-language Explanation, a structured Risk Analysis (impact scope, reversibility, blast radius, required privileges), and an explicit Rollback Plan (a paired rollback script or documented manual steps).
- Applies static safety checks (destructive-cmdlet detection, scope guardrails, credential-leak checks) before a script is eligible for approval.

**Data flow**
- In: structured intent from the Planner Agent/specialist agent (e.g., Active Directory Agent requesting an unlock script) plus context pulled from RAG over the script/knowledge corpus (pgvector) and prior successful `Scripts`.
- Out: generated script persisted to `Scripts` with linked `ScriptRiskAssessments`; presented to the user in the UI (diff/preview) for Human Approval; upon approval, handed to the Execution service for WinRM dispatch; execution result and rollback linkage recorded in `AuditLogs`.
- AI tool usage: **PowerShell Agent** is invoked by every Windows-facing specialist agent (Active Directory Agent, Windows Agent, Network Agent, Hyper-V Agent) whenever a remediation requires code rather than a canned API call.

**Key interfaces**
- `POST /api/v1/scripts/powershell/generate`
- `GET /api/v1/scripts/{id}`
- `GET /api/v1/scripts/{id}/risk-analysis`
- `GET /api/v1/scripts/{id}/rollback-plan`
- `POST /api/v1/scripts/{id}/approve`
- `POST /api/v1/scripts/{id}/reject`

**DB tables touched**
- Core: `Scripts`, `Tasks`, `AIConversations`, `AIMessages`, `AuditLogs`.
- Module-specific: `ScriptRiskAssessments`, `ScriptRollbackPlans`.

**Safety notes**
- Generation itself is inert (no target contact) and auto-runs.
- Any script targeting a mutating operation is blocked from Execution until it passes through the Human Approval gate; the Rollback Plan must be present and valid before approval is offered to the approver.

---

## 11. Bash Script Generator — generates Linux automation scripts

**Responsibilities**
- Generates Bash/shell scripts for Linux automation (systemd service management, cron jobs, log cleanup, package/patch operations, filesystem operations) from natural-language intent.
- Same guarantees as the PowerShell Generator: Explanation, Risk Analysis, Rollback Plan, and static safety checks (destructive command detection: `rm -rf`, disk-partitioning commands, etc.).

**Data flow**
- In: structured intent from Planner Agent/specialist agents plus RAG context (pgvector) over prior Linux scripts and runbooks.
- Out: generated script persisted to `Scripts`/`ScriptRiskAssessments`; presented for Human Approval; upon approval, handed to Execution service for SSH dispatch; results logged to `AuditLogs`.
- AI tool usage: **Linux Agent** generates these scripts itself when a Linux remediation requires shell code, and is also invoked by Security Agent and Automation Agent for the same purpose.

**Key interfaces**
- `POST /api/v1/scripts/bash/generate`
- `GET /api/v1/scripts/{id}`
- `GET /api/v1/scripts/{id}/risk-analysis`
- `GET /api/v1/scripts/{id}/rollback-plan`
- `POST /api/v1/scripts/{id}/approve`
- `POST /api/v1/scripts/{id}/reject`

**DB tables touched**
- Core: `Scripts`, `Tasks`, `AIConversations`, `AIMessages`, `AuditLogs`.
- Module-specific: `ScriptRiskAssessments`, `ScriptRollbackPlans` (shared with module 10).

**Safety notes**
- Generation is inert and auto-runs.
- Execution against any Linux target requires Human Approval; rollback plan required before approval is offered.

---

## 12. Script Library — organizes reusable scripts by category

**Responsibilities**
- Central catalog of all generated and hand-curated scripts (PowerShell and Bash), organized by category (AD, GPO, IIS, DNS, DHCP, Performance, VMware, Hyper-V, Cloud, general maintenance), tagging, versioning, and search.
- Tracks script provenance (AI-generated vs. human-authored), usage history, and approval/execution history for reuse in future Automation Workflows.

**Data flow**
- In: newly generated scripts from modules 10/11; manual uploads/edits by admins via UI.
- Out: script metadata and content served to UI for browsing/search; scripts referenced by Automation Workflows (module 17) when scheduling a job; usage stats fed back to AI layer to prefer previously-approved, well-tested scripts over fresh generation (RAG retrieval bias).
- AI tool usage: all specialist agents that call the PowerShell Agent or Linux Agent for script generation first query the Script Library through the **Memory Agent** (via RAG over `Scripts` embeddings in pgvector) to check for an existing approved script before generating a new one.

**Key interfaces**
- `GET /api/v1/script-library`
- `GET /api/v1/script-library/categories`
- `GET /api/v1/script-library/{id}`
- `POST /api/v1/script-library` (manual add)
- `PATCH /api/v1/script-library/{id}` (metadata/tag edits)
- `DELETE /api/v1/script-library/{id}` (retire)
- `GET /api/v1/script-library/{id}/usage-history`

**DB tables touched**
- Core: `Scripts`, `AuditLogs`.
- Module-specific: `ScriptCategories`, `ScriptTags`, `ScriptUsageHistory`, `ScriptEmbeddings` (pgvector).

**Safety notes**
- Browsing/search/usage-history is read-only and auto-runs.
- Adding, editing, or retiring a library entry is an administrative content action, not an infrastructure mutation, but is still logged to `AuditLogs`; the underlying scripts remain subject to Human Approval at the point they are actually executed against a target (modules 10/11/17).

---

## 13. Server Health Dashboard — CPU, RAM, Disk, Network, Services, Certificates, Windows Updates, Linux Updates

**Responsibilities**
- Aggregated, at-a-glance health view per server/device: CPU, RAM, disk, network, service status, TLS certificate expiry, Windows Update compliance, and Linux patch/update status.
- Rolls up module 9 (Performance), module 6 (IIS certs), and patch-management signals into a single per-asset health score and trend.

**Data flow**
- In: pulls aggregated snapshots from `PerformanceMetrics`, `IISCertificates`, and dedicated update-status collection: Windows Update state via WinRM/PowerShell (`Get-WindowsUpdate`/WUA COM), Linux update state via SSH (`apt`/`yum`/`dnf` dry-run checks).
- Out: composite `HealthSnapshots` written per asset per interval; pushed to UI via Socket.IO for live dashboard tiles; feeds Alert Center thresholds.
- AI tool usage: consumed by **Planner Agent** as the first grounding call when a user asks a broad health question in AI Chat ("how's Server X doing"); no dedicated agent since it's a read aggregation of other agents' domains.

**Key interfaces**
- `GET /api/v1/health/overview`
- `GET /api/v1/health/{assetId}`
- `GET /api/v1/health/{assetId}/certificates`
- `GET /api/v1/health/{assetId}/windows-updates`
- `GET /api/v1/health/{assetId}/linux-updates`
- `POST /api/v1/health/{assetId}/windows-updates/install` (delegates to Automation Workflows)
- `POST /api/v1/health/{assetId}/linux-updates/install` (delegates to Automation Workflows)

**DB tables touched**
- Core: `Servers`, `Devices`, `Alerts`, `Reports`.
- Module-specific: `HealthSnapshots`, `Certificates`, `PatchStatus`.

**Safety notes**
- All dashboard reads are read-only and auto-run on a polling/subscription basis.
- Update/patch installation is mutating and is routed through Automation Workflows' Human Approval + Execution pipeline, not executed directly from the dashboard.

---

## 14. Alert Center — Disk Full, CPU High, RAM High, Service Down, Backup Failed, Certificate Expiry

**Responsibilities**
- Central rules engine that evaluates thresholds/conditions across all telemetry-producing modules and raises, deduplicates, escalates, and resolves alerts: disk full, CPU high, RAM high, service down, backup failed, certificate expiry (and extensible custom rules).
- Routes alerts to Notifications (email/Slack/Teams/webhook) and to the AI layer for automatic triage.

**Data flow**
- In: `Events`/metric threshold breaches from modules 5, 6, 9, 13, plus backup-job status feeds from Automation Workflows.
- Out: `Alerts` records created/updated; `Notifications` dispatched; alert stream pushed to UI via Socket.IO; unresolved alerts surfaced to Planner Agent for proactive suggestions in AI Chat.
- AI tool usage: **Planner Agent** reads open alerts as triage input and the **Coordinator Agent** hands relevant alerts to the matching specialist agent (e.g., a disk-full alert is handed to Windows Agent or Linux Agent) for Root Cause Analysis and Recommendation.

**Key interfaces**
- `GET /api/v1/alerts`
- `GET /api/v1/alerts/{id}`
- `POST /api/v1/alerts/{id}/acknowledge`
- `POST /api/v1/alerts/{id}/resolve`
- `GET /api/v1/alerts/rules`
- `POST /api/v1/alerts/rules`
- `PATCH /api/v1/alerts/rules/{id}`

**DB tables touched**
- Core: `Alerts`, `Events`, `Notifications`, `AuditLogs`.
- Module-specific: `AlertRules`, `AlertEscalations`.

**Safety notes**
- Alert evaluation, acknowledgment, and resolution are administrative/state actions on the alert record itself, not on infrastructure, and auto-run (acknowledge/resolve still logged to `AuditLogs`).
- Any remediation triggered from an alert (e.g., "restart the down service") is dispatched to the owning module and must pass that module's Human Approval gate before Execution.

---

## 15. Security Center — detects Brute Force, Malware Indicators, Suspicious PowerShell, Disabled Antivirus, Firewall Changes, USB Usage

**Responsibilities**
- Continuous detection across Windows/Linux/network signal sources: brute-force login attempts, malware indicators (known-bad hashes/process patterns), suspicious PowerShell (obfuscation, encoded commands, known offensive-tooling patterns), disabled/tampered antivirus, unauthorized firewall rule changes, and USB removable-media usage.
- Produces `SecurityFindings` with severity, evidence, and recommended containment actions.

**Data flow**
- In: Windows Security event logs (module 5) via WinRM, Sysmon/AV logs where present, Linux auth logs via SSH (`journalctl`/`/var/log/auth.log`), firewall rule state via WinRM (`NetSecurity` module)/SSH (`iptables`/`nft`), USB device-arrival events via WMI event subscription.
- Out: `SecurityFindings` and `ThreatIndicators` persisted; high-severity findings raised as `Alerts` and pushed via Socket.IO; findings passed to AI layer for Root Cause Analysis and to the PowerShell Agent/Linux Agent for containment scripts (isolate host, disable account, block IP).
- AI tool usage: **Security Agent** is the primary consumer/producer here, correlating findings and requesting containment scripts from modules 10/11.

**Key interfaces**
- `GET /api/v1/security/findings`
- `GET /api/v1/security/findings/{id}`
- `GET /api/v1/security/brute-force`
- `GET /api/v1/security/malware-indicators`
- `GET /api/v1/security/suspicious-powershell`
- `GET /api/v1/security/antivirus-status`
- `GET /api/v1/security/firewall-changes`
- `GET /api/v1/security/usb-activity`
- `POST /api/v1/security/findings/{id}/contain` (drafts containment script/task)

**DB tables touched**
- Core: `Alerts`, `Events`, `Logs`, `Scripts`, `AuditLogs`.
- Module-specific: `SecurityFindings`, `ThreatIndicators`, `USBActivityLog`, `FirewallChangeLog`.

**Safety notes**
- Detection and evidence-gathering are read-only and auto-run continuously.
- Any containment action (disable account, isolate host, revert firewall change, kill process) is mutating and requires Human Approval before Execution, even under active-incident conditions, per the global execution safety rule — expedited approval UI is provided but the gate is never bypassed.

---

## 16. AI Chat — natural language interface for infrastructure operations

**Responsibilities**
- Primary conversational entry point for all natural-language infrastructure operations: free-text prompt in, plan/diagnosis/recommendation/script out, with inline Human Approval actions surfaced directly in the chat thread.
- Maintains multi-turn context per conversation, supports follow-up refinement, and surfaces which agents/tools were invoked ("show your work") for transparency.

**Data flow**
- In: user prompt from Next.js frontend over Socket.IO (streaming) or REST for non-streaming; conversation history loaded from `AIConversations`/`AIMessages`.
- Out: streamed tokens back to UI over Socket.IO; each turn's Planner→Agent Selection→Tool Calling→Data Collection→Reasoning→Root Cause Analysis→Recommendation→Script Generation chain is persisted as structured `AIMessages` metadata (tool calls, evidence, citations from pgvector RAG); any generated script surfaces an Approval card wired to the Human Approval endpoints of the owning module.
- AI tool usage: this module *is* the front door to the **Planner Agent**, which selects the specialist agent(s) needed from prompt intent, and the **Coordinator Agent**, which sequences/parallelizes those agent calls via LangGraph and merges their results; retrieval is grounded via RAG (pgvector) over documentation, past incidents, and the Script Library, managed by the **Memory Agent**, which also owns per-conversation short-term memory.

**Key interfaces**
- `POST /api/v1/chat/conversations`
- `GET /api/v1/chat/conversations`
- `GET /api/v1/chat/conversations/{id}/messages`
- `POST /api/v1/chat/conversations/{id}/messages` (send prompt; streams via Socket.IO channel `chat:{conversationId}`)
- `POST /api/v1/chat/conversations/{id}/messages/{messageId}/regenerate`
- `DELETE /api/v1/chat/conversations/{id}`

**DB tables touched**
- Core: `AIConversations`, `AIMessages`, `Users`, `Tasks`, `Scripts`, `AuditLogs`.
- Module-specific: none beyond core AI entities; relies on pgvector embedding tables owned by the RAG layer (e.g., `ScriptEmbeddings`, `KnowledgeBaseEmbeddings`).

**Safety notes**
- Conversational reasoning, diagnosis, and recommendation text are informational and auto-run.
- Any action the chat surfaces that would mutate infrastructure (script execution, AD change, GPO rollback, etc.) is rendered as an explicit Approval card and is executed only after Human Approval, through the owning module's endpoints, never directly from the chat module.

---

## 17. Automation Workflows — scheduled jobs, e.g. Cleanup Temp, Restart Service, Weekly Reports, Monthly Patch Report

**Responsibilities**
- Defines and schedules recurring or triggered `Workflows` (cron-like schedules or event triggers) composed of one or more `Scripts`/API actions, e.g., temp-file cleanup, service restarts, weekly infrastructure reports, monthly patch-compliance reports.
- Tracks each run as an `AutomationJobs` record with status, logs, and outcome; supports retry and notification-on-failure.

**Data flow**
- In: workflow definitions created via UI/AI Chat; trigger conditions (cron schedule or `Events`/`Alerts` triggers) evaluated by the scheduler; step scripts pulled from the Script Library (module 12).
- Out: each scheduled run dispatches to the Execution service (WinRM for Windows steps, SSH for Linux steps, cloud SDK / vCenter API / Hyper-V WMI for infra-specific steps); run results, logs, and generated reports written to `AutomationJobs`/`Reports`; failures raised as `Alerts`; UI updated via Socket.IO for live job status.
- AI tool usage: **Automation Agent** owns Workflow definition, scheduling, and ad hoc run-triggering (e.g., "schedule weekly temp cleanup on all web servers" from a chat request routed to it by the Planner Agent); recurring report generation (Weekly Reports, Monthly Patch Report) is owned by the **Reporting Agent**, which pulls data from modules 9/13/15 without further approval since report generation is read-only.

**Key interfaces**
- `GET /api/v1/workflows`
- `POST /api/v1/workflows`
- `PATCH /api/v1/workflows/{id}`
- `DELETE /api/v1/workflows/{id}`
- `POST /api/v1/workflows/{id}/run-now`
- `GET /api/v1/workflows/{id}/jobs`
- `GET /api/v1/automation-jobs/{id}`
- `GET /api/v1/reports/weekly`
- `GET /api/v1/reports/monthly-patch`

**DB tables touched**
- Core: `Workflows`, `AutomationJobs`, `Scripts`, `Tasks`, `Reports`, `Alerts`, `AuditLogs`.
- Module-specific: `WorkflowSchedules`, `WorkflowStepRuns`.

**Safety notes**
- Read-only workflow steps (report generation, data collection) auto-run on schedule.
- Any workflow step classified as mutating (cleanup deleting files, restarting a service, applying patches) requires the workflow to have been Human-Approved at creation/edit time for that step, and — depending on Organization policy — may additionally require per-run approval before each scheduled Execution; this policy is configurable per `Workflows` record but defaults to requiring approval for first run of any new mutating workflow.

---

## 18. VMware Management — ESXi, Datastore, Cluster, Snapshots, VM Health

**Responsibilities**
- Monitors ESXi host health, datastore capacity/latency, cluster (DRS/HA) status, VM inventory and health, and snapshot sprawl/age.
- Supports snapshot create/delete/revert, VM power operations, and basic resource reallocation recommendations.

**Data flow**
- In: pulled via vCenter API (vSphere Automation SDK / REST) — host, cluster, datastore, VM, and snapshot objects.
- Out: normalized state to `VMwareHosts`/`Datastores`/`VMwareClusters`/`VirtualMachines`/`VMSnapshots`; capacity/health issues raised as `Alerts`; feeds Server Health Dashboard and Performance Analyzer for guest-level metrics where guest tools report in.
- AI tool usage: **VMware Agent** reads host/cluster/datastore/VM/snapshot state for diagnosis (e.g., "datastore X is 92% full," "snapshot older than 30 days on VM Y") and drafts snapshot/power operations for Human Approval, executed via the vCenter API.

**Key interfaces**
- `GET /api/v1/vmware/hosts`
- `GET /api/v1/vmware/hosts/{id}`
- `GET /api/v1/vmware/datastores`
- `GET /api/v1/vmware/clusters`
- `GET /api/v1/vmware/vms`
- `GET /api/v1/vmware/vms/{id}/health`
- `GET /api/v1/vmware/vms/{id}/snapshots`
- `POST /api/v1/vmware/vms/{id}/snapshots`
- `DELETE /api/v1/vmware/vms/{id}/snapshots/{snapshotId}`
- `POST /api/v1/vmware/vms/{id}/snapshots/{snapshotId}/revert`
- `POST /api/v1/vmware/vms/{id}/power` (on/off/restart)

**DB tables touched**
- Core: `Servers`, `InfrastructureInventory`, `Alerts`, `AuditLogs`.
- Module-specific: `VMwareHosts`, `Datastores`, `VMwareClusters`, `VirtualMachines`, `VMSnapshots`.

**Safety notes**
- Host/cluster/datastore/VM/snapshot inventory and health reads are read-only and auto-run.
- Snapshot create/delete/revert and VM power operations are mutating and require Human Approval before dispatch to the vCenter API.

---

## 19. Hyper-V Management — VM Monitoring, Replication, Storage, Live Migration

**Responsibilities**
- Monitors Hyper-V host and VM health, Hyper-V Replica status/lag, storage (virtual disk capacity, checkpoint sprawl), and supports live migration between hosts.

**Data flow**
- In: pulled via Hyper-V WMI (`Msvm_*` classes) and PowerShell remoting (`Hyper-V` module) over WinRM against Hyper-V hosts.
- Out: normalized state to `HyperVHosts`/`VirtualMachines`/`HyperVReplication`; replication lag and storage capacity issues raised as `Alerts`.
- AI tool usage: **Hyper-V Agent** reads host/VM/replication/storage state for diagnosis ("replication lag on VM Z exceeds SLA") and drafts live-migration or checkpoint-cleanup operations for Human Approval, executed via WinRM/PowerShell.

**Key interfaces**
- `GET /api/v1/hyperv/hosts`
- `GET /api/v1/hyperv/hosts/{id}`
- `GET /api/v1/hyperv/vms`
- `GET /api/v1/hyperv/vms/{id}/health`
- `GET /api/v1/hyperv/vms/{id}/replication`
- `GET /api/v1/hyperv/vms/{id}/storage`
- `POST /api/v1/hyperv/vms/{id}/live-migrate`
- `POST /api/v1/hyperv/vms/{id}/checkpoints`
- `DELETE /api/v1/hyperv/vms/{id}/checkpoints/{checkpointId}`

**DB tables touched**
- Core: `Servers`, `InfrastructureInventory`, `Alerts`, `AuditLogs`.
- Module-specific: `HyperVHosts`, `VirtualMachines` (shared with module 18 where a VM is tracked once and tagged by hypervisor type), `HyperVReplication`.

**Safety notes**
- Host/VM/replication/storage monitoring is read-only and auto-runs.
- Live migration and checkpoint create/delete are mutating and require Human Approval before execution via WinRM/PowerShell.

---

## 20. Cloud Management — Azure, AWS, GCP

**Responsibilities**
- Unified view and control plane across Azure, AWS, and GCP: resource inventory, cost/utilization signals, and common operational actions (VM/instance start-stop-resize, storage account/bucket checks, network security group/firewall rule review, backup/snapshot status).
- Normalizes provider-specific concepts into a common resource model for cross-cloud reporting.

**Data flow**
- In: pulled via each provider's SDK — Azure SDK for Python (Resource Manager, Compute, Monitor), AWS SDK (boto3: EC2, CloudWatch, S3), GCP SDK (Compute Engine, Monitoring) — using per-Organization `Credentials` (service principal / IAM role / service account) vaulted and scoped to least privilege.
- Out: normalized resources into `InfrastructureInventory`/`CloudResources`; cost/utilization metrics stored alongside `PerformanceMetrics` where applicable; anomalies raised as `Alerts`.
- AI tool usage: **Cloud Agent** reads cross-cloud resource/cost/security state for diagnosis ("which VMs are oversized," "is this bucket public") and drafts mutating operations (resize, stop, security-group change) for Human Approval, executed via the respective provider SDK.

**Key interfaces**
- `GET /api/v1/cloud/accounts`
- `GET /api/v1/cloud/resources`
- `GET /api/v1/cloud/resources/{id}`
- `GET /api/v1/cloud/costs`
- `POST /api/v1/cloud/resources/{id}/start`
- `POST /api/v1/cloud/resources/{id}/stop`
- `POST /api/v1/cloud/resources/{id}/resize`
- `GET /api/v1/cloud/security-groups`
- `PATCH /api/v1/cloud/security-groups/{id}`
- `GET /api/v1/cloud/backups`

**DB tables touched**
- Core: `InfrastructureInventory`, `Credentials`, `Alerts`, `AuditLogs`.
- Module-specific: `CloudAccounts`, `CloudResources`, `CloudCostRecords`, `CloudSecurityGroupSnapshots`.

**Safety notes**
- Resource/cost/security inventory reads are read-only and auto-run.
- Start/stop/resize and security-group/firewall changes are mutating and require Human Approval before dispatch to the Azure/AWS/GCP SDK, regardless of which cloud provider is targeted.
