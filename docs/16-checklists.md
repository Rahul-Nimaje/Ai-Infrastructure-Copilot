# 16 — Checklists

Two operational checklists for AI Infrastructure Copilot: one to run **every deployment**, and one
to confirm **production readiness** before the platform is allowed to manage real customer
infrastructure at scale. Both are meant to be copied into a PR/release ticket and checked off
item-by-item, not read passively.

---

## A. Deployment Checklist

Use this checklist for every deploy to `staging` or `prod` of `web`, `api`, `execution-worker`, or
`ai-orchestrator`. Skip only the sections that don't apply (e.g., no migration this release), but
do not skip silently, mark as **N/A** explicitly.

### A.1 Pre-deploy

- [ ] All CI stages green on the release commit: lint, unit test, build, container scan (Trivy, no
      unresolved CRITICAL/HIGH findings), integration test.
- [ ] Database migrations (if any) reviewed against the destructive-migration rules in
      `docs/12-coding-standards.md` §3; downgrade path tested; second reviewer signed off if
      destructive or touching `Credentials`/`AuditLogs`/`Policies`/`AIConversations`.
- [ ] Migration dry-run executed against a staging snapshot (not just against an empty test DB) for
      any migration touching a large table (`Logs`, `Events`, `AuditLogs`, `Tasks`).
- [ ] Secrets/credentials rotated if this release requires it (e.g., LLM provider API key rotation,
      Vault policy change); rotation confirmed live in Vault before deploy, not just planned.
- [ ] Feature flags for any partially-shipped functionality set to the correct state for this
      environment (off in `prod` unless explicitly enabling).
- [ ] Release notes / changelog entry drafted, including any change to `execution-worker` job-type
      behavior or the Approval gate, called out explicitly.
- [ ] For `execution-worker` releases specifically: CI "policy test" stage confirmed green (every
      mutating job type still requires a valid approval token — see
      `docs/08-deployment-guide.md` §4.3).
- [ ] On-call engineer identified and available for the deploy window; rollback owner named.
- [ ] Terraform plan (if infra changed) reviewed and approved; no unexpected resource
      destroys/replacements in the plan output.

### A.2 Deploy

**For `web` / `api` / `ai-orchestrator` (blue-green):**

- [ ] `green` deployment created alongside `blue`, scaled to initial low capacity.
- [ ] Traffic shifted to 5%; automated health gate checked (5xx rate, p95/p99 latency, service-
      specific error signals per `docs/08-deployment-guide.md` §5.1) before advancing.
- [ ] Traffic shifted to 25%, then 50%, then 100%, pausing at each stage for the defined soak
      window; health gate re-checked at every stage.
- [ ] Rollback executed immediately if any stage breaches its threshold; incident opened if so.
- [ ] `blue` scaled to zero (not deleted) after a successful soak at 100%, kept available as a fast
      rollback target for the retention window.

**For `execution-worker` (canary by job type):**

- [ ] New version deployed alongside current version, initially restricted to the low-risk job-type
      allow-list.
- [ ] Canary soak window observed in full (minimum duration per environment); job success rate,
      audit-log/approval-record match rate, and idempotency behavior all confirmed clean.
- [ ] Job-type allow-list expanded in stages, each stage explicitly advanced by a human reviewer
      (never auto-promoted).
- [ ] Full cutover to the new version only after every job type has passed its canary stage.
- [ ] Previous version's replicas scaled down (not deleted) after full cutover.

### A.3 Post-deploy

- [ ] Smoke tests run against the deployed environment: login/auth flow, create a test
      diagnostic task (read-only, auto-run), submit a mutating action and confirm it lands in
      `pending_approval` (not auto-executed), approve it and confirm it reaches
      `execution-worker` and completes.
- [ ] Dashboards checked: request rate/error rate/latency for `web`/`api`/`ai-orchestrator`;
      queue depth and job success rate for `execution-worker`; DB/Redis/OpenSearch health.
- [ ] Alerting confirmed live for the new release (no silenced alerts left over from the deploy
      window).
- [ ] Audit log spot-checked: recent approvals/executions from the smoke test appear correctly in
      `AuditLogs` with the right actor, timestamp, and before/after state.
- [ ] Rollback readiness confirmed: previous version's manifests/image tag recorded, rollback
      command tested to work (not just documented) in the last release cycle.
- [ ] Deploy summary posted (image tags, migration applied, canary/blue-green timeline) to the
      team's release channel.
- [ ] Ticket/release closed only after the post-deploy soak period has passed without a triggered
      rollback.

---

## B. Production-Readiness Checklist

Use this checklist before onboarding real customer infrastructure, and re-run it on a recurring
cadence (recommended: quarterly, plus after any material architecture change) — it is not a
one-time gate.

### B.1 Security

- [ ] RBAC enforced end-to-end: every mutating and read endpoint checks a `require_permission(...)`
      dependency (per `docs/12-coding-standards.md` §2.3); a negative test exists proving a
      lower-privileged role is rejected on at least one representative endpoint per resource.
- [ ] Multi-factor authentication is available for all user accounts and enforceable per
      Organization policy; verified against at least one account with MFA required end-to-end
      (not just present as a toggle in the UI).
- [ ] Vault (or equivalent secrets backend) integration is live in the target environment, not
      stubbed: `Credentials` are fetched just-in-time with short-lived leases, never stored
      long-lived in application DB or environment variables.
- [ ] Audit logging verified complete: every approval, execution, credential access, and
      permission change produces an `AuditLogs` entry with actor, timestamp, target entity, and
      before/after state; spot-checked against a real end-to-end action, not just against unit
      tests.
- [ ] `execution-worker`'s NetworkPolicy reviewed and confirmed matching
      `docs/08-deployment-guide.md` §2.5: no ingress from the public internet or from `web`, egress
      limited to queue/DB/Vault/DNS/declared target CIDRs only; verified with an actual network
      policy test (attempted connection from a disallowed pod fails) not just a manifest read.
- [ ] Container images scanned clean (Trivy, no unresolved CRITICAL/HIGH) on the currently deployed
      tag for every service, not just at the time of last release.
- [ ] TLS enforced everywhere in transit (Ingress termination, service-to-service where the mesh
      supports it, DB/Redis/OpenSearch connections); no plaintext internal traffic carrying
      credentials or customer data.
- [ ] Dependency vulnerability scanning (SCA) wired into CI for both `npm`/`pip` dependency trees,
      with a defined SLA for patching CRITICAL findings.
- [ ] Secrets are not present in git history, container images, or logs; a secret-scanning tool
      (e.g., `gitleaks`) runs in CI.

### B.2 Reliability

- [ ] High availability configured: `api`, `web`, `ai-orchestrator`, and `execution-worker` each
      run with `PodDisruptionBudget`s and multi-replica minimums (see
      `docs/08-deployment-guide.md` §2.4); database is multi-AZ with a tested failover.
- [ ] Backups are running on schedule for PostgreSQL (and OpenSearch snapshots) with the retention
      period defined for the environment.
- [ ] A **real restore has been tested** end-to-end (not just "backups exist") — a backup was
      restored to a separate instance, and the platform was verified to boot against the restored
      data within the target RTO; RPO/RTO figures are documented, not assumed.
- [ ] Alerting is wired for the golden signals on every service (error rate, latency, saturation,
      queue depth for `execution-worker`) and for business-critical conditions (approval requests
      stuck pending beyond an SLA, execution job stuck/retrying beyond a threshold, LLM provider
      error rate spike).
- [ ] On-call rotation and escalation path defined and reachable (paging tool wired to alerts, not
      just a dashboard nobody watches).
- [ ] Load testing has been run against `api` and `ai-orchestrator` at expected peak concurrency,
      including a scenario with a burst of simultaneous mutating requests queued to
      `execution-worker`, to confirm HPA scaling and queue backpressure behave as designed.
- [ ] Disaster recovery runbook exists and has been rehearsed at least once (tabletop exercise
      minimum, full DR drill preferred) covering full-region/cluster loss.

### B.3 Compliance

- [ ] Data retention policy is defined and implemented per entity category (e.g., `Logs`/`Events`
      retention window, `AuditLogs` retention which is typically longer/immutable, `AIConversations`
      /`AIMessages` retention and any customer-configurable override) and enforced by an actual
      scheduled job, not just documented intent.
- [ ] Credential access has been reviewed: who/what can read `Credentials` records and Vault paths
      is enumerated, matches least-privilege expectations, and stale/unused access has been
      revoked.
- [ ] Data residency/processing requirements (if applicable to target customers) are reflected in
      the deployed environment's region configuration.
- [ ] A documented process exists for customer data deletion/export requests, and it has been
      exercised at least once against a non-production tenant.
- [ ] Third-party subprocessor list (LLM provider(s), cloud provider, any monitoring/logging SaaS)
      is documented and current.

### B.4 AI-Specific Readiness

- [ ] The Human Approval gate cannot be bypassed by any code path: every mutating job type has a
      passing "must require approval" policy test (per `docs/12-coding-standards.md` §2.3 and
      `docs/08-deployment-guide.md` §4.3), and this has been independently verified by attempting
      to submit a mutating action through every known entry point (API directly, not just through
      the UI) and confirming it lands in `pending_approval`.
- [ ] Read-only diagnostics that are allowed to auto-run are explicitly enumerated and reviewed —
      confirm the auto-run allow-list contains only genuinely side-effect-free operations, with no
      job type that could mutate state misclassified as read-only.
- [ ] `execution-worker`'s network isolation is verified (see B.1) specifically in the context of AI
      autonomy: confirm the AI orchestration layer (`ai-orchestrator`) cannot itself reach
      `execution-worker` or the job queue directly, bypassing `api`'s approval-gating logic — the
      only path from an AI-generated recommendation to an executed action must pass through the
      approval workflow in `api`.
- [ ] Rate limits on LLM calls are in place at both the per-organization and platform-wide level
      (via `ai-orchestrator`), to bound cost and blast radius from a runaway agent loop or prompt
      injection attempt; alerting exists for rate-limit exhaustion.
- [ ] A defined and tested response to prompt injection / malicious tool-call attempts exists for
      the LangGraph/MCP layer — at minimum, generated scripts/commands are never executed directly
      from AI output without passing through the same approval and validation path as
      human-submitted actions.
- [ ] Model provider fallback (OpenAI API to local LLM, or vice versa, per the provider-agnostic
      interface) has been exercised in a failure drill, confirming the platform degrades gracefully
      (e.g., falls back or clearly surfaces unavailability) rather than silently misbehaving.
- [ ] AI-generated scripts/recommendations are logged (`AIConversations`/`AIMessages`) with enough
      detail to reconstruct, for any executed action, exactly what the AI proposed, what a human
      approved, and what `execution-worker` actually ran, including any manual edits made to the
      script between generation and approval.
- [ ] Cost monitoring/alerting is in place for LLM spend per organization, to catch runaway usage
      before it becomes a billing or availability incident.
