# Roadmap: MVP to GA

## 1. Purpose

This document defines the phased delivery plan for AI Infrastructure Copilot, sequencing the 20 product modules and 15 AI agents (canonical lists in `docs/README.md`) into five phases. Each phase names a smallest-provable-value goal, the modules/agents it delivers, and the exit criteria required before the next phase starts. This is the artifact sprint planning and stakeholder go/no-go decisions should be derived from.

## 2. Sequencing Principles

- **Prove the core loop early.** The single riskiest and most valuable thing this product does is: take a natural-language question, diagnose it with AI, generate a script, and get a human to approve execution. Phase 1 exists to prove that loop end-to-end on the narrowest useful platform (Windows) before expanding breadth.
- **Add platform breadth before feature depth.** Phases 1–2 establish Windows and Linux; cloud and virtualization platforms are deliberately deferred to Phase 5 because they carry the most external-API integration risk and are lower-frequency admin tasks than day-to-day Windows/Linux/AD work for most target users.
- **Security and automation depth comes after the core loop is trustworthy.** Security Center and Automation Workflows (Phase 4) are sequenced after admins have already built trust in individual AI-assisted actions (Phases 1–3); automating multi-step mutating workflows before that trust exists is a change-management risk, not just an engineering one.
- **Every phase ships agents alongside the modules that need them**, never modules without their supporting agents, so no phase ships a UI that promises AI assistance it cannot yet deliver.

## 3. Phase 1 — MVP: Prove the Core Loop

**Goal:** Prove "ask a question, get a diagnosis and a script" on the smallest viable slice: a Windows admin can log in, see their inventory, ask AI Chat a question about a Windows server, get a root-cause diagnosis backed by Event Log data, and receive a PowerShell script that requires explicit approval before it would run.

**Modules delivered:** Authentication, Infrastructure Inventory, AI Chat, PowerShell Generator, Windows Event Log Analyzer.

**Agents delivered:** Planner Agent, Coordinator Agent, Windows Agent, PowerShell Agent.

**What is explicitly NOT in this phase:** real execution against production infrastructure is optional/flagged-off at launch if the execution-worker-service hardening isn't ready; it is acceptable to ship Phase 1 with approval-and-script-generation fully working and execution gated behind a feature flag enabled only for design-partner customers with a signed-off `execution-worker-service` security review.

**Exit criteria to move to Phase 2:**
- A user can authenticate (with MFA), see a populated Infrastructure Inventory for at least Windows targets, and complete an AI Chat conversation that produces a root-cause diagnosis grounded in real Event Log data.
- PowerShell Generator output passes the static safety analysis gate (`14-test-plan.md` Section 6.3) in CI with zero critical-severity findings escaping to the approval queue in the golden/adversarial test suite.
- The Human Approval gate is demonstrated end-to-end in a design-partner or staging environment: a generated script cannot execute without an explicit approval action, and that action is recorded in `AuditLogs`.
- Golden-set evaluation baselines are established for Planner, Coordinator, Windows, and PowerShell agents (not just "it works once" — a repeatable rubric score to regress against).
- At least one design-partner customer has used AI Chat against real (not just seeded) Windows infrastructure in a staging/pilot capacity.

## 4. Phase 2 — Identity and Linux Breadth

**Goal:** Extend the proven core loop across the two remaining foundational admin surfaces most teams need daily: Active Directory/Group Policy administration and Linux/Bash scripting, plus give admins a place to keep and reuse what the AI generates.

**Modules delivered:** Active Directory Management, Group Policy Management, Bash Script Generator, Script Library.

**Agents delivered:** Active Directory Agent, Linux Agent.

**Exit criteria to move to Phase 3:**
- AD query/unlock/disable/password-reset flows and GPO diagnosis flows are live behind the same approval gate proven in Phase 1, with their own golden-set baselines established.
- Bash Script Generator passes the same static safety analysis bar as PowerShell Generator (shellcheck + custom dangerous-pattern rules), verified against the adversarial suite.
- Script Library supports save/version/re-run, and re-running a stored script re-triggers Human Approval rather than reusing a stale approval decision.
- Integration test suite for `execution-worker-service` against a disposable Windows test VM (AD/GPO operations) and a containerized SSH target (Bash execution) is green and part of CI, not just a manual pre-release check.
- At least one design-partner customer has exercised an AD or GPO remediation through full approval-to-execution.

## 5. Phase 3 — Operational Visibility and Network Services

**Goal:** Give admins the day-to-day visibility surfaces (health, alerts, performance) and the network-services modules (IIS, DNS, DHCP) that turn the platform from "a chat tool for one-off questions" into an operational dashboard teams check throughout the day.

**Modules delivered:** IIS Copilot, DNS Manager, DHCP Manager, Performance Analyzer, Server Health Dashboard, Alert Center.

**Agents delivered:** Network Agent, Reporting Agent.

**Exit criteria to move to Phase 4:**
- Server Health Dashboard shows real-time status (via Socket.IO) for all inventoried Windows and Linux assets from Phases 1–2, with alerting thresholds configurable per organization.
- Alert Center ingests and deduplicates alerts, and AI-suggested remediation for at least one alert category (e.g. a failed IIS app pool, a DNS resolution failure) flows through diagnosis (auto-run) → recommendation → approval → execution end-to-end.
- Performance Analyzer surfaces resource-utilization diagnosis for both Windows and Linux targets using the same RCA pipeline proven in earlier phases.
- Load/latency testing (`14-test-plan.md` Section 6.4) has been run at least once against a staging environment approximating the target concurrency (200 concurrent AI jobs) and results are within SLO or have a documented remediation plan.
- Reporting Agent produces at least one scheduled report type (e.g. weekly health summary) consumed by a design-partner customer.

## 6. Phase 4 — Security and Automation Depth

**Goal:** Move from "AI assists one action at a time" to "AI assists a security posture program and multi-step automated workflows," which requires the trust built in Phases 1–3 plus a memory layer so the AI's recommendations account for organizational history, not just point-in-time state.

**Modules delivered:** Security Center, Automation Workflows.

**Agents delivered:** Security Agent, Automation Agent, Memory Agent.

**Exit criteria to move to Phase 5:**
- Security Center surfaces posture findings across the modules already shipped (AD, GPO, Windows, Linux, IIS/DNS/DHCP configuration) with auto-run read-only scanning and approval-gated hardening actions.
- Automation Workflows supports multi-step, schedulable workflows with per-step approval, including the "pre-approved standing policy" path, and every execution of such a workflow is independently reconstructable from `AuditLogs` per the SOC 2-oriented compliance requirement in `01-SRS.md`.
- Memory Agent demonstrably improves recommendation quality on a repeat scenario in the golden-set evaluation (e.g. a recurring alert type is diagnosed faster or more accurately on the second occurrence than the first, measured against the golden-set rubric).
- Security-focused adversarial test suite (attempts to get the platform to recommend disabling audit logging, firewalls, or MFA) is green with zero bypasses, reviewed by the security/compliance stakeholder, not just engineering.
- A design-partner customer has run at least one multi-step Automation Workflow with a mutating step in production or a production-equivalent environment.

## 7. Phase 5 — GA Hardening and Scale-Out: Cloud and Virtualization

**Goal:** Complete platform breadth with Cloud (Azure/AWS/GCP) and Virtualization (VMware/Hyper-V) management, and harden the platform for General Availability: multi-region deployment, DR drills, and load/scale validation at the full 20-module, 15-agent surface area.

**Modules delivered:** VMware Management, Hyper-V Management, Cloud Management.

**Agents delivered:** VMware Agent, Hyper-V Agent, Cloud Agent.

**Exit criteria for GA:**
- All 20 modules and all 15 agents are live with established golden-set evaluation baselines (Section 6.1 of `14-test-plan.md`) and no open critical-severity safety-suite findings.
- VMware/Hyper-V/Cloud integration tests are green against vCenter simulator/sandbox accounts (or nightly live-account suites) per `14-test-plan.md` Section 5.2.
- DR failover runbook (`02-HLD.md` Section 7) has been executed as a live drill at least once, with RPO/RTO targets met and results logged.
- Multi-region deployment topology (`02-HLD.md` Section 5.2) is validated for at least one data-residency-constrained design-partner customer.
- 99.9% availability target (per `01-SRS.md` Section 5.3) has been sustained for a minimum 60-day pre-GA observation window.
- Security review (SOC 2-oriented control mapping) is complete and signed off by the compliance stakeholder.
- `user-manual.md` and `admin-manual.md` (deferred per `17-future-enhancements.md`) are drafted against the real, shipped Phase 1–5 UI and published alongside the GA release.

## 8. Roadmap Summary Table

| Phase | Modules | Agents | Core exit criterion |
|---|---|---|---|
| 1 — MVP | Authentication, Infrastructure Inventory, AI Chat, PowerShell Generator, Windows Event Log Analyzer | Planner, Coordinator, Windows, PowerShell | Core loop (ask → diagnose → script → approve) proven end-to-end |
| 2 — Identity + Linux | Active Directory Management, Group Policy Management, Bash Script Generator, Script Library | Active Directory, Linux | AD/GPO and Linux scripting proven under the same approval gate |
| 3 — Visibility + Network | IIS Copilot, DNS Manager, DHCP Manager, Performance Analyzer, Server Health Dashboard, Alert Center | Network, Reporting | Dashboard + alert-to-remediation loop live; load testing baseline established |
| 4 — Security + Automation | Security Center, Automation Workflows | Security, Automation, Memory | Multi-step automation and posture management trusted and audit-provable |
| 5 — GA Hardening | VMware Management, Hyper-V Management, Cloud Management | VMware, Hyper-V, Cloud | Full 20/15 surface area live, DR drilled, availability target sustained |

Cross-references: architecture supporting each phase in `02-HLD.md`; per-module design in `03-LLD.md`; evaluation methodology gating each phase's agents in `14-test-plan.md`; post-GA scope in `17-future-enhancements.md`.
