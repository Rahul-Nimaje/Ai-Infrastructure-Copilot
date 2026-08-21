# Test Plan

## 1. Purpose and Scope

This document defines the testing strategy for AI Infrastructure Copilot across every layer of the stack: the Next.js frontend, the FastAPI backend, the isolated `execution-worker-service`, and the AI orchestration layer (LangGraph agents, RAG, script generation). It also defines a dedicated AI-agent evaluation strategy, since correctness for this product is not just "does the code run" but "did the agent reach the right diagnosis, and is the generated script safe to even show a human for approval." It assumes the module/agent inventory and execution-safety rule defined in `docs/README.md` and the architecture in `02-HLD.md`.

## 2. Test Levels Overview

| Layer | Test types | Primary tools |
|---|---|---|
| Frontend (Next.js) | Component/unit, integration, e2e | Vitest/Jest + React Testing Library, Playwright |
| Backend (FastAPI) | Unit (per router/service), integration (real Postgres) | pytest, pytest-asyncio, testcontainers-python |
| `execution-worker-service` | Unit, integration against mock/disposable targets | pytest, testcontainers, disposable Windows test VM, containerized SSH server |
| AI orchestration / agents | Golden-set eval, RAG eval, safety/hallucination checks, load/latency | Custom eval harness, pytest, LangSmith or equivalent tracing, locust/k6 |
| Cross-cutting | Security, performance, accessibility | OWASP ZAP, k6/Locust, axe-core |

## 3. Frontend Testing

### 3.1 Component tests
- Every shared component in `components/ui` (shadcn/ui wrappers) and every module-specific component has unit tests covering rendering, prop variants, and interaction states (loading, error, empty).
- React Query hooks are tested with mocked query clients to verify cache keys, invalidation on mutation, and optimistic-update rollback on failure.
- Socket.IO event handlers (task progress, approval.requested, alert.created) are tested with a mocked socket client to verify UI state transitions without a live server.
- Form validation (Zod schemas backing script-execution and approval forms) is unit tested independent of UI rendering.
- Target coverage: 80% line coverage on `components/` and `hooks/`, enforced in CI.

### 3.2 Playwright end-to-end tests (critical flows)

| Flow | Why critical | Key assertions |
|---|---|---|
| **Human Approval gate** | Core safety guarantee of the product | A mutating recommendation cannot execute without an explicit Approve click; Reject cancels the task; approval/rejection appears in the audit trail; UI never exposes an "execute anyway" bypass |
| Login + MFA + RBAC-gated navigation | Security baseline | Users without a module permission cannot reach that module's routes even via direct URL |
| AI Chat end-to-end diagnosis | Primary value proposition | Prompt submission streams Planner → Agent → RCA → Recommendation steps over WebSocket; a generated script renders with a visible "Pending Approval" state before any execution UI is enabled |
| PowerShell/Bash Generator → Script Library save → re-run | Reuse path most admins take | Generated script can be saved, versioned, and re-run; re-run still requires a fresh approval regardless of prior approval history |
| Alert Center triage → AI-suggested remediation → Approval | Alert-to-remediation loop | Auto-run diagnosis appears immediately; remediation step is blocked pending approval |
| Automation Workflow with a mutating step | Standing-policy approval path | Workflow step marked "pre-approved policy" still writes an immutable audit record; a step without pre-approval blocks until approved |
| Cross-module inventory drill-down | Data consistency | Infrastructure Inventory, Server Health Dashboard, and Security Center show consistent state for the same asset |

- Playwright tests run against a fully containerized stack (frontend + backend + Postgres + Redis + a stub `ai-orchestrator`/`execution-worker` that return deterministic canned responses) so e2e runs are fast and independent of live LLM calls or real infrastructure.
- A smaller "live smoke" Playwright suite runs nightly against a staging environment with real (but sandboxed) LLM calls and a disposable test VM, to catch integration drift the stubbed suite cannot.
- Visual regression on shadcn/ui-based dashboards (Server Health Dashboard, Alert Center) via Playwright screenshot comparison, tolerant threshold to avoid noise from live data widgets.

## 4. Backend (FastAPI) Testing

### 4.1 Unit tests per router
- Every router under `apps/api/routers/*` (one per module, 20 total, plus auth/shared routers) has unit tests covering: request validation (Pydantic schema rejection paths), RBAC/permission enforcement (403 for unauthorized roles), and business-logic branches with the DB/cache layer mocked.
- Service-layer functions (the layer between routers and the ORM) are unit tested independent of HTTP, covering edge cases like empty inventories, already-approved tasks, and idempotency-key collisions.
- Target coverage: 85% line coverage on `apps/api/services` and `apps/api/routers`, enforced in CI; coverage gate specifically fails the build if the Human Approval branch of any mutating endpoint is untested.

### 4.2 Integration tests against a real Postgres (testcontainers)
- Every module's full request lifecycle (router → service → repository → real PostgreSQL) is exercised with `testcontainers-python` spinning up an ephemeral Postgres instance per test session, migrations applied via the real migration tool (Alembic).
- Covers: transaction boundaries (approval + audit-log write must commit atomically), unique constraints, cascade behavior on org/user deletion, and pgvector similarity queries against seeded embeddings.
- Redis-backed behavior (rate limiting, session revocation, job enqueue) is integration tested against a real Redis testcontainer, not mocked, since off-by-one TTL and pub/sub timing bugs are common and mocks hide them.
- A dedicated integration suite verifies the **audit-log immutability contract**: no code path in the API exposes an update or delete operation on `AuditLogs`, verified by both a schema-level test (no UPDATE/DELETE grants for the application DB role on that table) and an API-level test (no route accepts `PATCH`/`DELETE` on `/audit-logs/*`).
- Contract tests verify that every mutating endpoint across all 20 modules returns `202 Accepted` with a `PENDING_APPROVAL` task state rather than executing synchronously, closing off any accidental "fast path" that skips the approval gate.

## 5. `execution-worker-service` Testing

The execution-worker is the only service that touches real infrastructure, so its tests run against representative disposable targets rather than mocks wherever protocol fidelity matters.

### 5.1 Unit tests
- Command/script templating, credential-reference resolution (mocked vault), idempotency-key handling, and retry/backoff logic for read-only jobs are unit tested in isolation.
- Verify mutating jobs never auto-retry (per the execution-safety rule) by asserting the retry policy branch explicitly rejects retry attempts for any job flagged mutating.

### 5.2 Integration tests against mock/disposable targets

| Target type | Mechanism | Covers |
|---|---|---|
| Windows | Disposable test VM (ephemeral, provisioned via Terraform/Packer, torn down after suite) with WinRM/PSRemoting enabled | Real PowerShell execution semantics, WinRM auth (Kerberos/NTLM), WMI queries, AD test-domain operations against a throwaway domain controller |
| Linux | Containerized SSH server (e.g. a minimal sshd image) spun up per test run via testcontainers | SSH auth, command execution, output streaming, timeout handling, journalctl/systemd command surface (via a container image with systemd or a stub) |
| Cloud (Azure/AWS/GCP) | Provider SDK against sandbox/free-tier test accounts or provider-supplied local emulators (e.g. LocalStack for AWS) where available; otherwise recorded-response replay (VCR-style cassettes) for CI, with a smaller live-account suite run nightly | Resource query, tagging, start/stop, and failure-path handling (auth expiry, rate limiting) |
| VMware | vCenter simulator (vcsim) where feasible, otherwise a nightly live suite against a sandbox vCenter | VM lifecycle operations, inventory query |
| Hyper-V | Disposable Windows test VM with Hyper-V role enabled, nested virtualization | VM lifecycle operations via WMI/PowerShell |

- Every integration test asserts the **full execution envelope**, not just the command result: credential resolution happens only inside the worker process at call time, the resolved secret never appears in logs or the `Tasks`/`AuditLogs` payload, and a result (success or failure) is always written back even if the connection drops mid-execution.
- Chaos-style tests kill the execution-worker pod mid-job (via testcontainers network partition or pod deletion in a kind/minikube CI cluster) to verify the reconciliation sweep marks the job `UNKNOWN` rather than silently re-executing a mutating action, per the DR runbook in `02-HLD.md` Section 7.

## 6. AI-Agent Evaluation Strategy

Traditional pass/fail unit tests are necessary but not sufficient for the 15 AI agents; correctness here means "reasonable diagnosis" and "safe script," which requires a dedicated evaluation methodology run continuously, not just at release time.

### 6.1 Golden prompt/response test sets per agent

- Each of the 15 agents (Infrastructure, Windows, Linux, Cloud, Active Directory, PowerShell, Security, Network, VMware, Hyper-V, Automation, Reporting, Planner, Memory, Coordinator) has a versioned golden set of 30–100 representative prompts paired with expected agent-selection routing, expected tool calls, and an acceptable-answer rubric (not a single expected string, since LLM output is non-deterministic).
- Example golden-set entries:
  - Windows Agent: "Service X keeps crashing on server Y" → expects Event Log query tool call, expects RCA mentioning a specific event ID pattern from the seeded fixture data, expects a PowerShell remediation suggestion gated behind approval.
  - Planner Agent: ambiguous prompt spanning two domains ("DNS resolution is failing after the GPO push") → expects routing to both Active Directory Agent and Network Agent, not a single-agent dead end.
  - Coordinator Agent: multi-agent conflict ("Security Agent flags a port as risky, Network Agent's diagnosis says it's required for a clustered service") → expects the coordinator to surface the conflict to the human rather than silently picking one recommendation.
- Golden sets are graded by an automated rubric scorer (LLM-as-judge with a fixed grading prompt, cross-checked periodically by a human reviewer sample) on: agent-selection accuracy, tool-call correctness, factual grounding against the seeded fixture data, and whether a mutating recommendation is correctly flagged as requiring approval.
- Golden-set pass rate is a release gate: no agent ships to production with a rubric score regression below its established baseline (tracked over time, not just a fixed threshold, to catch silent drift from a model/prompt change).

### 6.2 RAG retrieval quality evaluation

- A labeled runbook/knowledge set (internal runbooks, vendor documentation excerpts, past resolved incidents) is curated with query-to-relevant-document labels.
- Retrieval quality is measured as **precision@k and recall@k** (k = 3, 5, 10) against this labeled set for the pgvector-backed retrieval step used by Reasoning/Root Cause Analysis.
- Regression thresholds are tracked per agent domain (e.g. Active Directory runbooks vs. Linux runbooks may have different baseline recall due to corpus size); a drop below baseline blocks a RAG-index or embedding-model change from shipping.
- Embedding freshness is tested separately: a scheduled job re-embeds updated `Scripts`/`Reports`/inventory documents, and a test verifies stale embeddings are not silently served (retrieval eval re-run after each re-embedding job).

### 6.3 Hallucination and safety checks for script generation (PowerShell Generator, Bash Script Generator)

This is the highest-risk surface in the product: a generated script that looks plausible but is destructive, and the primary mitigation is that **no generated script is even eligible for Human Approval until it passes static safety analysis.**

- **Static analysis gate (blocking, pre-approval):**
  - PowerShell: `PSScriptAnalyzer` plus a custom rule set flagging dangerous cmdlets/patterns — `Remove-Item -Recurse -Force` on root-level or system paths, `Format-Volume`, `Disable-*Firewall*`/`Set-NetFirewallProfile -Enabled False`, AD object deletion cmdlets (`Remove-ADUser`, `Remove-ADGroup`, `Remove-ADOrganizationalUnit`) without an accompanying rollback/export step, disabling of Windows Defender or audit logging, and credential/secret exfiltration patterns (writing credentials to plaintext files, sending data to non-allowlisted endpoints).
  - Bash: `shellcheck` plus a custom rule set flagging `rm -rf /`, `rm -rf /*`, `dd` to a block device, `chmod -R 777`, disabling `iptables`/`ufw`/`firewalld`, `:(){ :|:& };:`-style fork bombs, piping remote content directly to a shell (`curl ... | sh`), and deletion of `/etc/passwd`, `/etc/shadow`, or systemd unit files without a backup step.
  - A script that trips any **critical**-severity rule is rejected outright and never reaches the approval queue; the agent is asked to regenerate with the flagged pattern explicitly disallowed in the retry prompt.
  - A script that trips a **warning**-severity rule (e.g. a mutating AD action with no explicit rollback plan documented in the script's own comments/description) proceeds to Human Approval but is annotated with the warning inline, so the approver sees it before deciding.
- **Rollback-plan requirement:** any generated script performing a destructive or hard-to-reverse action (AD object deletion, VM deletion, disk partition changes, firewall rule removal) must include an explicit rollback section (e.g. an AD object export prior to deletion, a VM snapshot prior to a risky change); the static analysis gate checks for the presence of this section by pattern and fails scripts that omit it for the flagged action types.
- **Hallucination checks:** golden-set prompts include known-nonexistent cmdlets/flags and fictitious server names to verify the agent does not fabricate a plausible-sounding but incorrect command, and verify it asks a clarifying question or flags uncertainty rather than guessing when the fixture data does not contain enough information to answer confidently.
- **Adversarial prompt set:** a maintained set of prompts that attempt to social-engineer the agent into skipping the approval gate, generating a script that disables audit logging, or embedding a destructive action inside an otherwise benign-looking script (e.g. "clean up temp files" that also deletes a system directory); every entry in this set must be blocked or flagged by the static analysis gate before it reaches the approval stage.
- Results of static analysis and the hallucination/adversarial suite are tracked over time (per model version, per prompt-template version) so a model or prompt change that silently increases the dangerous-pattern rate is caught before rollout, not after an incident.

### 6.4 Load and latency testing for the AI orchestrator

- k6/Locust-driven load tests simulate concurrent AI Chat sessions and background diagnostic triggers (from Alert Center) against a staging `ai-orchestrator` deployment, measuring first-token latency, end-to-end job completion time, and queue depth under load (targets in `01-SRS.md` Section 5.1).
- Load tests run against both the OpenAI API path and the local LLM path (vLLM/Ollama) since their latency/throughput profiles differ; both must independently meet the latency SLOs under the concurrency target (200 concurrent jobs).
- Backpressure behavior is explicitly tested: when queue depth exceeds a threshold, new AI Chat prompts should degrade gracefully (queued with a visible "high load, estimated wait" UI state) rather than timing out silently or dropping requests.
- Soak tests (sustained load over multiple hours) verify no memory/connection leak in the LangGraph checkpointing mechanism and no unbounded growth in `AIConversations`/`AIMessages` query latency as conversation history grows.

## 7. Test Environments

| Environment | Purpose | Data | LLM |
|---|---|---|---|
| Local dev | Developer iteration | Seeded fixtures | Local LLM or mocked responses |
| CI (per PR) | Unit + integration + stubbed e2e | Ephemeral testcontainers | Mocked/stubbed agent responses (deterministic) |
| Staging | Nightly live-smoke e2e, load tests, golden-set eval | Anonymized/synthetic org data, disposable test VM + containerized SSH target | Real OpenAI API (rate-limited) and real local LLM |
| Production | Canary/blue-green rollout monitoring only, no test traffic | N/A | N/A |

## 8. Release Gates

A release is blocked from promotion to the next environment if any of the following fail:

1. Unit + integration coverage thresholds (Section 3.1, 4.1, 4.2) not met.
2. Any critical-flow Playwright e2e test fails, especially the Human Approval gate suite.
3. Any golden-set agent rubric score regresses below its tracked baseline.
4. RAG retrieval precision/recall regresses below baseline.
5. Any script in the adversarial/hallucination safety suite is not blocked or flagged as expected.
6. Load test SLOs (Section 6.4) are not met at target concurrency.
7. Any audit-log immutability contract test fails.

Cross-references: architecture context in `02-HLD.md`; module-level behavior in `03-LLD.md`; multi-agent design in `06-ai-architecture.md`; security control mapping in `07-security-architecture.md`; production-readiness checklist in `16-checklists.md`.
