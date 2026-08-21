# Future Enhancements (Post-GA)

## 1. Purpose

This document captures ideas explicitly deferred beyond General Availability (Phase 5 in `15-roadmap.md`). None of these are commitments; they are candidates for prioritization once GA usage data, customer feedback, and support-ticket patterns exist to justify the investment. Nothing here should be read into the SRS (`01-SRS.md`) as an implicit requirement.

## 2. Deferred Documentation (explicit note)

`user-manual.md` and `admin-manual.md` are **deferred and NOT written as part of this documentation deliverable.** The reason is deliberate, not an oversight: these two manuals should document the actual shipped UI screens (the real Dashboard, AI Chat, Scripts, Approval, and module screens as they exist in the product), not speculative mockups written before any screen exists. Writing them now, against a design that hasn't been built yet, would produce documentation that is wrong on day one and actively misleading to new customers and support staff.

Plan for these two documents:
- Author `user-manual.md` and `admin-manual.md` once **Phase 1 (MVP)** ships (per `15-roadmap.md` Section 3), against the real Authentication, Infrastructure Inventory, AI Chat, PowerShell Generator, and Windows Event Log Analyzer screens.
- Expand both manuals incrementally at the end of each subsequent phase (Phase 2 through Phase 5) as new modules ship, rather than attempting a single after-the-fact rewrite at GA.
- Version both manuals alongside each release (e.g. `user-manual-v1.0.md` matching the Phase 1 release tag, `user-manual-v2.0.md` matching Phase 2, and so on, or an equivalent versioned-docs-site approach), so a customer running an older release is not sent documentation describing screens they don't have yet.
- Screenshots and walkthroughs in both manuals must be captured from the actual running application (staging or production), never recreated from design mockups, to keep them trustworthy.

## 3. Post-GA Enhancement Candidates

### 3.1 Multi-cloud cost optimization recommendations
Extend Cloud Management and the Cloud Agent to analyze spend across Azure/AWS/GCP and recommend concrete, human-approved cost actions (rightsizing idle VMs, identifying orphaned disks/snapshots, recommending reserved-instance or savings-plan commitments). This reuses the existing diagnosis → recommendation → approval pipeline, so it is a natural extension rather than a new architecture; the main new work is a cost-data ingestion pipeline per provider and a new class of "savings opportunity" recommendation the Reporting Agent can summarize.

### 3.2 Predictive failure detection via anomaly detection
Apply anomaly detection (statistical baselining or a lightweight ML model) to the metrics already collected by Performance Analyzer, so the platform can flag "this disk/CPU/memory trend looks like it will breach a failure threshold in N days" before an alert would otherwise fire. This shifts Alert Center from reactive to predictive and would likely warrant its own evaluation methodology (precision/recall on predicted-vs-actual failures) analogous to the RAG retrieval evaluation already defined for AI agents in `14-test-plan.md`.

### 3.3 ChatOps integration (Slack/Teams)
Let admins interact with AI Chat and approve/reject mutating actions directly from Slack or Microsoft Teams, with the same Human Approval gate enforced identically to the web UI (an approval click in Slack must produce the same immutable audit record as an approval click in the app). This requires careful attention to identity mapping (Slack/Teams identity to platform RBAC role) so the approval gate cannot be weakened by routing around web-app authentication.

### 3.4 Mobile app for on-call approvals
A lightweight mobile app (iOS/Android) focused narrowly on push-notification-driven approval/rejection for on-call staff, not a full port of the web UI. Scope would deliberately stay small: view a pending approval's diagnosis summary and generated script, approve or reject with biometric/MFA confirmation, and view recent audit history. Full module functionality (AD management, dashboards, etc.) would remain web-only unless usage data justifies more.

### 3.5 Marketplace for community-contributed scripts (Script Library)
Allow organizations to optionally publish and consume vetted scripts from a shared community marketplace layered on top of Script Library. This raises new trust and safety questions beyond the existing static-analysis gate (a community-sourced script needs provenance tracking, a review/rating mechanism, and possibly a stricter static-analysis bar than internally-generated scripts) and would need its own security review before consideration, given the platform's execution-safety posture.

### 3.6 Fine-tuned local models per customer
For customers running the local LLM path (Llama/Qwen/Mistral) for data-residency reasons, offer optional fine-tuning on that customer's own runbooks, past incidents, and approved scripts to improve local-model diagnosis quality and reduce reliance on the larger cloud model. This would need its own golden-set evaluation per fine-tuned model (extending the methodology in `14-test-plan.md` Section 6.1) to ensure a fine-tuned model doesn't regress safety behavior (e.g. a fine-tune should never reduce the model's tendency to flag risky actions for approval).

### 3.7 Other candidates worth tracking (not yet scoped)
- Deeper Reporting Agent output: scheduled executive-level compliance/security posture reports suitable for board or audit review, beyond the operational reports shipped in Phase 3.
- Expanded Memory Agent scope: cross-organization pattern learning (with strict tenant isolation) so common failure signatures recognized at one customer can inform faster diagnosis at another, without leaking any customer-specific data.
- Additional virtualization/cloud platform coverage if customer demand emerges (e.g. Proxmox, Nutanix, Oracle Cloud) using the same agent-and-module pattern established for VMware/Hyper-V/Azure/AWS/GCP.
- Deeper Automation Workflows capabilities: conditional branching on live infrastructure state, workflow templates shareable across an organization's teams.

## 4. Prioritization Approach

Post-GA enhancements should be prioritized using the same evidence bar the roadmap phases used pre-GA: real usage data (which modules/agents get used most), support-ticket themes, and design-partner/customer-advisory-board input, rather than speculative build-out. Any enhancement that touches the execution path (i.e., anything that could result in a mutating action reaching infrastructure) must go through the same static-analysis and Human Approval gating already defined in `01-SRS.md` and `14-test-plan.md`; no future enhancement is exempt from that gate.
