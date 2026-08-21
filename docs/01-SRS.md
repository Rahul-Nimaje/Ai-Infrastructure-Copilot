# Software Requirement Specification (SRS)

## 1. Purpose

This document specifies the functional and non-functional requirements for **AI Infrastructure Copilot**, an enterprise SaaS platform that lets Windows, Linux, Cloud, and Virtualization administrators diagnose, troubleshoot, script, and remediate infrastructure issues using natural language, with AI agents performing diagnosis, root-cause analysis, and script generation, and humans retaining explicit approval authority over every mutating action. It is written for engineering, QA, product, security, and executive stakeholders who need a shared, unambiguous statement of what the system must do before design (`02-HLD.md`, `03-LLD.md`) and build begin.

## 2. Scope

AI Infrastructure Copilot is a single web-based platform (Next.js frontend, FastAPI backend, isolated `execution-worker-service`) covering 20 product modules and 15 AI agents (see `docs/README.md` for the canonical lists). In scope:

- Natural-language interaction with infrastructure via **AI Chat**, backed by a multi-agent LangGraph pipeline.
- Discovery and inventory of Windows, Linux, Cloud (Azure/AWS/GCP), and Virtualization (VMware/Hyper-V) assets.
- Diagnosis, root-cause analysis, script generation (PowerShell and Bash), and human-approved execution against those assets.
- Identity/directory administration (Active Directory, Group Policy), network services administration (DNS, DHCP, IIS), monitoring and alerting (Server Health Dashboard, Alert Center, Performance Analyzer), security posture management (Security Center), and workflow automation (Automation Workflows).
- Full audit logging of every AI recommendation, human decision, and executed action.

Out of scope for v1 (see `17-future-enhancements.md`): ChatOps integrations (Slack/Teams), mobile approval app, community script marketplace, per-customer fine-tuned local models, predictive/anomaly-based failure prediction. `user-manual.md` and `admin-manual.md` are intentionally deferred and are not part of this SRS deliverable; they are written once Phase 1 (MVP) ships, against the real UI.

## 3. Target Users and Stakeholders

| User / Stakeholder | Primary use of the system |
|---|---|
| Windows System Administrators | AD/GPO management, Windows Event Log analysis, PowerShell generation, IIS/DNS/DHCP administration |
| Linux Administrators | Bash script generation, systemd/journalctl/cron diagnostics via SSH |
| Infrastructure Engineers | Infrastructure Inventory, Server Health Dashboard, cross-platform automation |
| Cloud Engineers | Cloud Management (Azure/AWS/GCP), cost and resource diagnostics |
| DevOps Engineers | Automation Workflows, Script Library, CI/CD-adjacent remediation scripting |
| IT Support Teams | AI Chat for first-line triage, Alert Center response |
| MSP Companies | Multi-tenant infrastructure management across client organizations |
| Enterprise IT Departments | Security Center, audit/compliance reporting, RBAC governance |
| Approvers (a role, not necessarily a distinct persona) | Reviewing and approving/rejecting AI-recommended mutating actions |
| Security/Compliance Officers | Reviewing audit logs, RBAC policy, data residency configuration |

## 4. Functional Requirements

Functional requirements are grouped by module. Each FR is written so a mutating action is explicitly gated by the Human Approval step, per the fixed execution-safety rule: *every mutating action requires explicit human approval; read-only diagnostics may auto-run.*

### FR-01 — Authentication
- FR-01.1: The system shall authenticate users via email/password and support SSO (SAML/OIDC) and SCIM provisioning for enterprise identity providers.
- FR-01.2: The system shall enforce multi-factor authentication (MFA) for all users, mandatory for any user holding an Approver or Admin role.
- FR-01.3: The system shall support role-based access control (RBAC) with organization-scoped roles and permissions covering every module and the approval action itself.
- FR-01.4: The system shall support session management including token refresh, revocation, and configurable session timeout per organization policy.

### FR-02 — Infrastructure Inventory
- FR-02.1: The system shall discover and catalog Windows, Linux, Cloud, and Virtualization assets (servers, devices, VMs) via agent-based and agentless (WinRM/SSH/cloud SDK/vCenter/Hyper-V) discovery.
- FR-02.2: The system shall maintain a normalized, searchable inventory record per asset (OS, roles, installed software, network config, ownership tags) refreshed on a configurable schedule.
- FR-02.3: The system shall allow manual tagging, grouping, and metadata enrichment of inventory records; read-only discovery may auto-run, but any inventory-driven remediation action routes through Human Approval.

### FR-03 — Active Directory Management
- FR-03: The system shall allow querying, unlocking, disabling, and resetting passwords for Active Directory users, and querying/modifying group memberships and OU structure, subject to RBAC and the Human Approval gate for any mutating action (unlock, disable, password reset, group/OU change).

### FR-04 — Group Policy Management
- FR-04: The system shall allow querying existing Group Policy Objects (GPOs), diagnosing GPO application failures via AI-assisted analysis, and generating GPO changes (new policy, linked OU, setting modification), with every GPO creation, link, or setting change requiring Human Approval before application.

### FR-05 — Windows Event Log Analyzer
- FR-05: The system shall collect, index, and allow natural-language querying of Windows Event Logs (System, Application, Security) across managed servers, and shall allow the AI agents to auto-run read-only log queries and correlate events for root-cause analysis without requiring approval.

### FR-06 — IIS Copilot
- FR-06: The system shall allow diagnosis of IIS site/application pool health (auto-run, read-only) and shall generate and, upon Human Approval, apply configuration changes (bindings, app pool settings, site recycling, SSL certificate updates).

### FR-07 — DNS Manager
- FR-07: The system shall allow querying DNS zones and records (auto-run, read-only) and shall generate and, upon Human Approval, apply record create/update/delete operations across managed DNS servers.

### FR-08 — DHCP Manager
- FR-08: The system shall allow querying DHCP scopes, leases, and reservations (auto-run, read-only) and shall generate and, upon Human Approval, apply scope, reservation, and option changes.

### FR-09 — Performance Analyzer
- FR-09: The system shall collect performance counters/metrics (CPU, memory, disk, network) from Windows and Linux targets, surface AI-assisted diagnosis of performance degradation (auto-run, read-only), and recommend remediation actions that require Human Approval before execution.

### FR-10 — PowerShell Generator
- FR-10: The system shall generate PowerShell scripts from natural-language intent, run generated scripts through static safety analysis (see `14-test-plan.md`) before they become eligible for Human Approval, and require explicit Human Approval before any generated script executes against a target.

### FR-11 — Bash Script Generator
- FR-11: The system shall generate Bash scripts from natural-language intent, run generated scripts through static safety analysis before they become eligible for Human Approval, and require explicit Human Approval before any generated script executes against a target.

### FR-12 — Script Library
- FR-12: The system shall allow saving, versioning, categorizing, and re-running previously generated or manually authored scripts, and shall re-apply the Human Approval gate on every execution of a stored script regardless of prior approval history.

### FR-13 — Server Health Dashboard
- FR-13: The system shall present real-time and historical health status (availability, resource utilization, service state) for all inventoried servers, sourced from auto-run read-only health checks and streamed to the UI over Socket.IO.

### FR-14 — Alert Center
- FR-14: The system shall ingest, deduplicate, prioritize, and route infrastructure alerts, allow AI-assisted triage and suggested remediation (auto-run diagnosis), and require Human Approval before any suggested remediation executes.

### FR-15 — Security Center
- FR-15: The system shall surface security posture findings (patch status, misconfigurations, exposed services, AD/GPO security gaps) via auto-run read-only scans, and shall require Human Approval before any recommended hardening action (e.g., disabling a service, closing a port, revoking access) executes.

### FR-16 — AI Chat
- FR-16: The system shall provide a natural-language chat interface through which any user may invoke the full AI workflow (Planner → Agent Selection → Tool Calling → Data Collection → Reasoning → Root Cause Analysis → Recommendation → Script Generation → Human Approval → Execution → Audit Log), streaming intermediate progress to the UI.

### FR-17 — Automation Workflows
- FR-17: The system shall allow defining multi-step, schedulable, or event-triggered automation workflows composed of diagnostic and remediation steps, and shall require Human Approval on every mutating step within a workflow unless that specific step has been explicitly pre-approved as a standing policy by an Admin, in which case the approval and its scope are themselves recorded immutably in the audit log.

### FR-18 — VMware Management
- FR-18: The system shall allow querying VM/host/cluster inventory and health via vCenter API (auto-run, read-only), and shall generate and, upon Human Approval, execute VM lifecycle operations (power on/off, snapshot, migrate, resize).

### FR-19 — Hyper-V Management
- FR-19: The system shall allow querying VM/host inventory and health via Hyper-V WMI/PowerShell (auto-run, read-only), and shall generate and, upon Human Approval, execute VM lifecycle operations (power on/off, checkpoint, migrate, resize).

### FR-20 — Cloud Management
- FR-20: The system shall allow querying resource inventory, cost, and configuration across Azure, AWS, and GCP via provider SDKs (auto-run, read-only), and shall generate and, upon Human Approval, execute resource changes (scaling, tagging, stop/start, security-group/firewall changes).

### Cross-cutting AI and workflow requirements

- FR-21: The system shall route every user prompt through the Planner Agent, which selects one or more of the 15 AI agents and orchestrates tool calling, data collection, reasoning, root-cause analysis, recommendation, and script generation as defined in the AI workflow.
- FR-22: The system shall never allow a mutating action to reach the execution-worker-service without a corresponding recorded Human Approval decision.
- FR-23: The system shall write an immutable audit log entry for every AI recommendation, every human approval/rejection decision, and every executed action (success or failure), including the initiating user, timestamp, target asset, and full command/script payload.
- FR-24: The system shall support both the OpenAI API and a local LLM (Llama/Qwen/Mistral) behind a provider-agnostic interface, selectable per deployment/organization.

## 5. Non-Functional Requirements

### 5.1 Performance

| Requirement | Target |
|---|---|
| AI Chat first-token latency (cloud LLM) | ≤ 2.5 seconds p95 |
| AI Chat first-token latency (local LLM) | ≤ 4 seconds p95 |
| Read-only diagnostic auto-run completion (single target) | ≤ 10 seconds p95 |
| Dashboard/API list-view response time | ≤ 500 ms p95 |
| Script generation (PowerShell/Bash) end-to-end | ≤ 8 seconds p95 |
| Approval action round trip (click Approve → execution enqueued) | ≤ 1 second p95 |
| WebSocket event delivery latency (task progress to browser) | ≤ 500 ms p95 |
| Concurrent AI orchestration jobs supported per standard deployment | 200 concurrent jobs sustained |

### 5.2 Security

- RBAC enforced at API and data-access layers for every module; permission checks are additive to, not a substitute for, the Human Approval gate.
- MFA mandatory for Approver and Admin roles; configurable mandatory-for-all per organization policy.
- Encryption in transit (TLS 1.2+ everywhere, mTLS between internal services where feasible) and at rest (PostgreSQL, OpenSearch, pgvector, object storage) for all data including audit logs and vaulted credentials.
- Credentials for target infrastructure (WinRM/SSH/cloud/vCenter/Hyper-V) are stored in a secrets vault and resolved only inside the isolated `execution-worker-service`; no other component ever holds secret material, only opaque references.
- All AI-generated scripts pass static safety analysis (dangerous-pattern detection) before becoming eligible for Human Approval; see `14-test-plan.md`.
- Principle of least privilege enforced for service accounts used against AD, WinRM, SSH, and cloud provider APIs.

### 5.3 Availability

- Target availability: **99.9%** monthly uptime for the platform (API, frontend, notification gateway), excluding scheduled maintenance windows communicated at least 72 hours in advance.
- The isolated `execution-worker-service` targets the same 99.9% availability but degrades safely: on unavailability, pending approvals queue rather than execute against stale state, and no mutating action is attempted without a live, freshly-authenticated session to the target.
- See `02-HLD.md` Sections 6–7 for HA replica strategy and DR RPO/RTO targets.

### 5.4 Compliance and Auditability

- Audit logs (`AuditLogs`) are immutable (append-only, no update/delete API surface) and retained per organization policy, minimum 1 year, configurable up to 7 years for regulated customers.
- The platform is designed to support SOC 2 Type II control objectives: logical access control (RBAC/MFA), change management (approval gate as the change-control mechanism), and monitoring (audit logging, alerting).
- Every executed script and its approval chain must be independently reconstructable from the audit log for compliance review, including who approved it, what changed in the script between generation and approval (if anything), and the execution result.

### 5.5 Data Residency

- Organizations may pin their PostgreSQL/OpenSearch/pgvector data and their `ai-orchestrator`/local-LLM inference to a specific region or on-prem deployment to satisfy data-residency requirements.
- When a local LLM (Llama/Qwen/Mistral) is selected for data-residency reasons, no prompt, completion, or embedding derived from that organization's data is sent to the OpenAI API; the provider-agnostic interface enforces this binding per organization, not per request.
- Vaulted credentials and execution-worker network egress are always scoped to the same region/segment as the target infrastructure they operate on.

## 6. Assumptions and Constraints

- Windows targets have WinRM/PowerShell Remoting enabled and reachable from the `execution-worker-service`'s network segment; WMI is available for legacy query paths.
- Linux targets have SSH access enabled and reachable from the `execution-worker-service`'s network segment; the connecting account has sufficient sudo/privilege configuration for the diagnostic and remediation commands it is expected to run.
- The Active Directory service account used by the platform has been granted the minimum permissions required for the AD/GPO operations in scope (read for diagnostics; delegated write for the specific attributes/OUs covered by Human-Approved actions).
- Cloud provider credentials (Azure/AWS/GCP) are provisioned with least-privilege IAM roles scoped to the resources the organization wants managed.
- VMware (vCenter API) and Hyper-V (WMI/PowerShell) management assumes network reachability and valid service-account credentials to the respective management planes, not direct hypervisor host access.
- Customers are responsible for their own network connectivity (VPN/peering/ExpressRoute/Direct Connect) between the `execution-worker-service` and their infrastructure; the platform does not provide network transport.
- The OpenAI API is reachable from the `ai-orchestrator` for organizations that opt into cloud LLM usage; organizations requiring full data isolation must provision local LLM infrastructure (GPU nodes) per `02-HLD.md` Section 5.2.
- This SRS assumes the fixed tech stack defined in the project brief and does not evaluate alternative stacks.

## 7. External Interface Requirements

| Interface | Direction | Protocol / SDK | Used by |
|---|---|---|---|
| WinRM | Outbound from `execution-worker-service` | WinRM (5985/5986), PowerShell Remoting | Windows Agent, PowerShell Agent, Active Directory Agent |
| WMI | Outbound from `execution-worker-service` | DCOM/WMI | Windows Agent (legacy query paths), Hyper-V Agent |
| SSH | Outbound from `execution-worker-service` | SSH (22), Bash | Linux Agent |
| Active Directory / LDAP | Outbound from `execution-worker-service` | LDAP/LDAPS, ADSI | Active Directory Agent |
| vCenter API | Outbound from `execution-worker-service` | vSphere REST/SOAP API | VMware Agent |
| Hyper-V WMI/PowerShell | Outbound from `execution-worker-service` | WMI, PowerShell Remoting | Hyper-V Agent |
| Azure SDK | Outbound from `execution-worker-service` | Azure Resource Manager REST API | Cloud Agent |
| AWS SDK | Outbound from `execution-worker-service` | AWS REST API (boto3-equivalent) | Cloud Agent |
| GCP SDK | Outbound from `execution-worker-service` | GCP REST API | Cloud Agent |
| OpenAI API | Outbound from `ai-orchestrator` | HTTPS REST | Planner Agent and all reasoning/generation steps when cloud LLM is selected |
| Local LLM runtime (vLLM/Ollama) | Outbound from `ai-orchestrator` | HTTP (internal) | Same, when local LLM is selected |
| Identity Provider (SSO/SCIM) | Inbound/Outbound at `api-service` | SAML/OIDC, SCIM | Authentication module |
| Browser | Inbound | HTTPS REST, WebSocket (Socket.IO) | Next.js frontend |

Full protocol-level detail (ports, auth handshake, retry semantics) is specified per module in `03-LLD.md` and per external system in `05-api-design.md`.
