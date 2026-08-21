# 09 - Monitoring & Observability

## 0. Scope and Principles

AI Infrastructure Copilot spans a Next.js frontend, a FastAPI backend, an AI orchestrator (agent/tool-calling layer), and an isolated `execution-worker-service` that talks to real Windows/Linux/Cloud/Virtualization targets, plus PostgreSQL, Redis, and OpenSearch. Observability has three jobs here that matter more than in a typical CRUD app:

1. **Prove what the AI agent did and why**, at the granularity of individual tool calls, since agent behavior is inherently less predictable than hand-written code paths.
2. **Prove what the execution-worker did on a customer's infrastructure**, at the granularity of individual WinRM/SSH commands, since that is the platform's highest-risk surface.
3. **Give operators (both platform SREs and customer OrgAdmins) a live picture of platform health, per-org usage, and job-queue backlog**, so approval-gate bottlenecks and infra failures are caught before they become incidents.

The stack: **Prometheus** (metrics) + **Grafana** (dashboards/alerting UI) + **OpenTelemetry** (traces, and optionally metrics/logs via the same SDK) + **OpenSearch** (already a platform dependency, used here for structured application/business logs) with **Loki** as an optional add-on for high-volume infra/container logs. Alerts from any of these become entries in the **Alert Center** module and/or **Notifications** rows, per Section 5.

---

## 1. Prometheus

### 1.1 What's scraped

Every service exposes a `/metrics` endpoint (Prometheus exposition format) scraped by a Prometheus server (or Prometheus-compatible remote-write target, e.g. Thanos/Mimir/Cortex for multi-cluster/long-term retention) running in-cluster, service discovery via Kubernetes `ServiceMonitor`/`PodMonitor` CRDs (Prometheus Operator).

| Target | Method | Key metrics |
|---|---|---|
| **FastAPI backend** | `/metrics` via `prometheus-fastapi-instrumentator` (or `starlette-exporter`) | `http_requests_total{method,path,status,org_id_bucket}`, `http_request_duration_seconds` (histogram), `http_requests_in_progress`, per-route error rate |
| **execution-worker-service** | `/metrics` (custom exporter) | `worker_jobs_total{status=success\|failed\|rejected}`, `worker_job_duration_seconds`, `worker_active_connections{protocol=winrm\|ssh}`, `worker_queue_depth`, `worker_vault_lease_fetch_seconds`, `worker_credential_fetch_failures_total` |
| **PostgreSQL** | `postgres_exporter` sidecar | connections in use, replication lag, slow query counts, table/index bloat, `pg_stat_activity` waits |
| **Redis** | `redis_exporter` sidecar | memory usage, evictions, connected clients, command latency, keyspace hit ratio (relevant for the JWT deny-list and rate-limit counters, Section 6/9 of `07-security-architecture.md`) |
| **OpenSearch** | built-in `_prometheus` plugin or `opensearch_exporter` | cluster health, indexing/search latency, JVM heap pressure, disk watermark status |
| **Kubernetes/infra layer** | `kube-state-metrics`, `node-exporter`, cAdvisor (via kubelet) | pod restarts, OOMKills, node resource pressure, useful for correlating platform incidents with infra causes |

### 1.2 Custom business metrics

These are the metrics that matter specifically to *this* product's risk model and are emitted directly by the FastAPI backend and AI orchestrator, not derived from generic HTTP metrics:

- `approvals_pending{org_id,risk_tier}` (gauge) - current size of the approval queue, the single most important SLO-adjacent metric for the Human Approval gate; a growing high-risk queue means remediation is stalled.
- `approvals_expired_total{org_id,risk_tier}` (counter) - proposals that timed out unapproved; a leading indicator of understaffed approver rotations.
- `scripts_executed_total{org_id,module,status}` (counter) - "scripts executed today" is a `sum(increase(scripts_executed_total[24h]))` query, sliced by module (PowerShell Generator, Bash Script Generator, Automation Workflows, etc.).
- `ai_agent_tool_calls_total{tool_name,status}` and `ai_agent_tool_call_duration_seconds` (histogram) - per-tool latency/error rate for the AI orchestrator (diagnosis tool vs script-generation tool vs execution-dispatch tool).
- `ai_agent_tokens_total{org_id,model,direction=input|output}` and `ai_agent_cost_usd_total{org_id,model}` (counters) - feeds the AI cost dashboards and the rate-limit/budget enforcement described in `07-security-architecture.md` Section 10.
- `credential_rotation_overdue{org_id,credential_id}` (gauge, 0/1) - surfaces Vault rotation-policy violations (Section 5.4 of the security doc) directly into the metrics pipeline so it can alert the same way infra metrics do.
- `mfa_step_up_failures_total{org_id}` and `login_lockouts_total{org_id}` - security-relevant counters worth graphing alongside operational ones.
- `session_recording_write_failures_total` - because a failed session recording is itself an audit-integrity incident, not just a technical error.

All custom metrics carry `org_id` as a label (cardinality-managed via a bucketing/allow-list for very large customers, or a separate per-org recording rule set, to avoid Prometheus cardinality blowup at scale) so per-tenant dashboards and SLOs are possible without a separate metrics pipeline per tenant.

### 1.3 Retention and scale

Local Prometheus TSDB retention: 15 days (fast local queries for dashboards/alerting). Long-term retention (13+ months, needed for usage-based billing trends and year-over-year capacity planning) is handled via remote-write to Thanos or Mimir backed by object storage, kept separate from the audit-log retention story (which is a compliance requirement, not a metrics one) in `07-security-architecture.md`.

---

## 2. Grafana

Grafana reads from the Prometheus/Thanos data source (and can also query OpenSearch and Loki directly for cross-referencing logs from a dashboard panel). Four dashboard families ship by default:

### 2.1 Platform health dashboard (SRE-facing, cross-org)

- Global request rate, error rate (4xx/5xx), p50/p95/p99 latency per FastAPI route.
- `execution-worker-service` job success/failure rate, active WinRM/SSH connection count, queue depth over time.
- Postgres/Redis/OpenSearch health panels (connections, replication lag, disk watermarks).
- Kubernetes pod health (restarts, OOMKills, node pressure).
- SLO burn-rate panels for the platform's core SLOs (e.g. "API availability", "approval-to-execution latency").

### 2.2 Per-org usage dashboard (customer-facing, filterable by `org_id`, embeddable in Security Center / a future "Usage" module)

- Requests, AI Chat invocations, scripts executed, and approvals (pending/approved/rejected/expired) over the selected time window.
- Module usage breakdown (which of the 20 modules the org actually uses), useful for both the customer and platform CSM/success teams.
- AI token/cost consumption against the org's budget (ties directly to `ai_agent_cost_usd_total` and the rate-limit budget in the security doc).
- Active user count, MFA adoption rate, SSO login share vs local login.

### 2.3 AI agent latency/cost dashboard

- Per-tool p50/p95/p99 latency (`ai_agent_tool_call_duration_seconds`), broken out by tool (diagnosis, root-cause-analysis, script-generation, execution-dispatch).
- Token consumption and $ cost per model, per org, per day, trended, with anomaly highlighting (a sudden per-org spike is both a cost and an abuse signal, cross-referenced with the rate-limit metrics).
- Tool-call error rate and error taxonomy (timeout vs upstream-model-error vs tool-execution-error), since a rising AI tool error rate is often the earliest signal of an upstream model provider incident.
- Approval-queue funnel: proposals generated -> previewed -> approved -> executed -> expired, so the team can see where in the AI-to-execution pipeline proposals are getting stuck.

### 2.4 execution-worker job queue dashboard

- Queue depth over time, per org and globally, with an alert threshold panel.
- Job latency breakdown: time in queue vs Vault credential-fetch time vs actual WinRM/SSH execution time vs session-recording write time, this decomposition is what lets an engineer tell "Vault is slow" apart from "the target host is slow" apart from "we're backlogged."
- Job outcome breakdown (success / target unreachable / auth failure / script error / approval-token invalid), each of which points at a different remediation path.
- Concurrent-connection count against the per-org concurrency cap (Section 10 of the security doc) to see when a customer is being throttled.

All dashboards are provisioned as code (Grafana dashboard JSON checked into the infra repo, loaded via the Grafana Operator/sidecar or Terraform's Grafana provider) rather than hand-built in the UI, so they version alongside the rest of the Terraform/Kubernetes config.

---

## 3. OpenTelemetry (Distributed Tracing)

### 3.1 Trace path

A single user action, e.g. "restart IIS on server X", produces one trace spanning:

```
Next.js frontend (browser span, e.g. via @vercel/otel or manual instrumentation)
  -> API gateway / ingress
    -> FastAPI backend (route handler span)
      -> AI orchestrator (agent reasoning + tool-call spans)
        -> [tool call: diagnostics query] -> Postgres / OpenSearch spans
        -> [tool call: generate script] -> LLM provider call span
        -> [tool call: dispatch execution] -> enqueue span (Redis)
          -> execution-worker-service (job-pickup span)
            -> Vault credential-fetch span
            -> WinRM/SSH command execution span
            -> session-recording write span
```

- **Context propagation**: W3C Trace Context (`traceparent`/`tracestate` headers) end-to-end. The frontend generates or continues a trace on each user-initiated request; FastAPI's OTel middleware extracts/injects context automatically; the AI orchestrator propagates the same `trace_id` into every tool-call span and into the job payload it hands to Redis; `execution-worker-service` extracts trace context from the job payload (since it's a queue hop, not an HTTP call, context travels as job metadata rather than HTTP headers) and continues the same trace.
- The `trace_id` is stored alongside the corresponding `AuditLogs.request_id / trace_id` field (see `07-security-architecture.md` Section 7.1), so an auditor investigating an `AuditLogs` row can pivot directly into the full distributed trace for that action, and conversely an SRE looking at a slow/failed trace can pivot into the audit record to see the human approval context.

### 3.2 Which spans matter most

Not every span is equally important to alert on or dashboard; the ones worth naming explicitly because they map to product risk:

- **AI agent tool-call spans**: each tool invocation (diagnosis, RCA, script-gen, execution-dispatch, approval-check) is its own span with attributes `tool.name`, `tool.status`, `tool.risk_tier`, `org.id`, `model.name`, `tokens.input`, `tokens.output`. This is the primary debugging surface when an agent behaves unexpectedly, letting an engineer replay exactly which tools were called, in what order, with what arguments and results.
- **WinRM/SSH command-execution spans**: span attributes include target host id (not hostname/IP in plain span attributes if that's considered sensitive, prefer an internal target id and join to inventory data under access control), protocol, command/script hash (not full content, to avoid duplicating sensitive script bodies into the tracing backend), duration, exit code, and the `approval_token_id` that authorized it. This span is the technical counterpart to the audit-log row and session recording, three views of the same event for three different audiences (SRE, auditor, reviewer).
- **Vault credential-fetch spans**: duration and outcome (success/deny/error) without ever including the secret value or even the full vault path as a raw attribute (use the `Credentials.id` instead), since traces often have looser access control than the vault/audit path itself.
- **Approval-gate transition spans**: proposed -> previewed -> approved/rejected -> executed, each as a span (or span event) on the parent trace, so the end-to-end "time from proposal to execution" latency, a key product SLO, is directly queryable from trace data instead of being reconstructed from logs after the fact.

### 3.3 Sampling and export

- Head-based sampling at 100% for any trace that touches `execution-worker-service` or an `Approve`-tier action (low volume, high importance, always keep).
- Probabilistic tail sampling (e.g. 10-20%, boosted to 100% on error) for high-volume read-only/diagnostic traces to control cost.
- Export via OTel Collector (deployed as a Kubernetes DaemonSet/sidecar) fanning out to a tracing backend (Grafana Tempo, Jaeger, or a vendor APM) and, for the metrics half of OTel, optionally to the same Prometheus pipeline via the OTel Collector's Prometheus exporter, so traces and metrics stay correlated through shared `org_id`/`trace_id` exemplars in Grafana.

---

## 4. Log Aggregation: OpenSearch vs Loki

### 4.1 Strategy

All services emit **structured JSON logs** (never unstructured printf-style text) with a consistent baseline schema: `timestamp`, `level`, `service`, `org_id`, `user_id` (when applicable), `trace_id`/`request_id`, `message`, plus event-specific fields. The `trace_id` field is what makes logs, metrics, and traces correlate: from a Grafana trace view you can jump straight to the matching log lines, and from an OpenSearch log line you can jump straight to the matching trace.

Given OpenSearch is **already a platform dependency** (used for search/indexing elsewhere in the product, e.g. Windows Event Log Analyzer's own log search feature, and as the AuditLogs WORM-adjacent index per the security doc), the pragmatic default is:

- **OpenSearch**: all **application and business logs** across every service, FastAPI request/response logs, AI orchestrator reasoning/tool-call logs, `execution-worker-service` job lifecycle logs, and auth/security events. These are logs a human (support engineer, auditor, customer OrgAdmin via a future "activity log" view) needs to search by business meaning: "show me every failed login for org X" or "show me every script execution that touched server Y." OpenSearch's full-text and structured query capability fits that access pattern well, and reusing an already-operated dependency avoids standing up a second stateful log store just for this.
- **Loki**: recommended as an add-on specifically for **infrastructure/container logs**, raw stdout/stderr from every Kubernetes pod, kubelet/systemd logs, sidecar/proxy logs. This is high-volume, low-cardinality-value data (mostly useful for "what did this pod print right before it crashed") that doesn't need OpenSearch's full-text search sophistication; Loki's cheaper index-light storage model (index only labels, not full text) is the better cost/operations fit for that volume, and it plugs directly into Grafana alongside the metrics/traces already living there for a single pane of glass during incident response.

If a team wants to run leaner and skip Loki entirely, OpenSearch can absorb container logs too (via the same Fluent Bit/Vector pipeline, just a second index pattern), the tradeoff is cost (OpenSearch's full-text indexing is more expensive per GB than Loki at high log volumes) versus operational simplicity (one less stateful system to run). Given OpenSearch is already in the stack for other reasons, starting with OpenSearch-only and adding Loki later if container-log volume/cost justifies it is a reasonable phased approach; this document specifies both paths so the team can decide based on observed volume after initial rollout.

### 4.2 Pipeline

- **Collection**: Fluent Bit (or Vector) as a DaemonSet on every Kubernetes node, tailing container stdout/stderr and any structured log files.
- **Routing**: Fluent Bit/Vector routes by log type, `service=execution-worker-service OR service=fastapi-backend OR log_type=business` -> OpenSearch; `log_type=container_stdout` (generic pod output, sidecar/proxy logs) -> Loki (if adopted).
- **Index/stream lifecycle**: OpenSearch index-lifecycle-management (ILM) rolls indices daily/weekly, hot tier for recent (fast query, e.g. 14 days), warm/cold tier for older data, eventually archived per the retention policy that lines up with `AuditLogs` retention where the two overlap (audit-relevant logs), and a shorter operational retention (e.g. 30-90 days) for pure debugging logs that aren't audit-relevant.
- **PII/secret scrubbing**: log pipeline includes a redaction filter (Fluent Bit Lua filter or Vector VRL transform) that strips known secret-shaped patterns and known sensitive field names before indexing, defense in depth on top of "never log the secret in the first place" application-level discipline.

---

## 5. Alert Routing

### 5.1 From signal to Alert Center / Notifications

Alerts originate from two places and converge on the same destination:

- **Prometheus/Grafana alerts**: Prometheus Alertmanager (or Grafana's unified alerting) evaluates alert rules (e.g. `approvals_pending{risk_tier="high"} > 10 for 15m`, `worker_queue_depth > threshold`, `up == 0` for any scraped target, Postgres replication lag, OpenSearch cluster yellow/red).
- **Internal platform alerts**: business-logic conditions detected directly in application code that aren't naturally metric-threshold shaped, e.g. "credential rotation overdue" (though also exposed as a metric per Section 1.2), "AI agent proposed a high-risk action outside business hours", "audit hash-chain verification failed" (a security-critical event that should never be silent).

Both paths funnel into a single internal **Alert Ingestion API** on the FastAPI backend:

1. Alertmanager's webhook receiver (or Grafana's contact point) POSTs to `/internal/alerts/ingest`, and internal platform code calls the same ingestion path directly (shared code path, not two divergent implementations).
2. The ingestion handler normalizes the payload into an **Alerts** row: `org_id` (nullable for platform-wide alerts), `severity`, `source` (`prometheus` | `internal`), `title`, `description`, `related_module`, `related_resource`, `trace_id` (if applicable), `status` (`open` | `acknowledged` | `resolved`), `created_at`.
3. The Alert Center module reads from `Alerts` directly, this is the module's primary data source, so any Prometheus-origin alert becomes immediately visible there without a separate sync job.
4. In parallel, the ingestion handler fans out a **Notifications** row per relevant user (OrgAdmin for org-scoped alerts, on-call SuperAdmin rotation for platform-wide alerts), respecting each user's notification preferences (in-app only vs in-app+email vs in-app+email+page) configured in Security Center/account settings.

### 5.2 Paging integrations

- **Slack**: Alertmanager/Grafana contact point posts to an org-specific or platform-ops Slack webhook/incoming app; severity determines channel routing (e.g. `#platform-critical` vs `#platform-warnings`), and the same message includes a deep link back into Alert Center for the full context and into the Grafana dashboard/trace for the technical detail.
- **PagerDuty**: high/critical severity alerts (both Prometheus-sourced and internal, e.g. "audit hash-chain verification failed", "execution-worker fleet unreachable") trigger a PagerDuty incident via the Events API v2, routed to the appropriate on-call schedule (platform SRE on-call for infra alerts, security on-call for audit-integrity/credential alerts). PagerDuty incident acknowledgement/resolution is webhooked back into the platform to keep the `Alerts.status` field in sync bidirectionally.
- **Email**: lower-severity and per-org informational alerts (e.g. "credential rotation due in 7 days", "AI budget at 80%") default to email via the Notifications pipeline's email channel (transactional email provider), rather than paging, since they're not time-critical.
- **Deduplication and grouping**: Alertmanager groups by `org_id` + `alertname` to avoid page storms from a single root cause (e.g. one Postgres outage shouldn't fire 50 separate per-route alerts); the same grouping key is preserved into the `Alerts` row via a `group_id` so Alert Center shows one collapsed incident, not fifty rows, with the ability to expand and see every underlying signal that contributed.

### 5.3 Severity-to-channel mapping (default policy, org/plan configurable)

| Severity | Alert Center | Notifications | Slack | PagerDuty | Email |
|---|---|---|---|---|---|
| Critical | Yes | Yes (immediate) | Yes | Yes | Yes |
| High | Yes | Yes (immediate) | Yes | Yes (business hours) or Yes (24/7 for security-tagged) | Yes |
| Medium | Yes | Yes (batched digest option) | Optional | No | Yes |
| Low / informational | Yes | Yes (digest) | No | No | Optional (digest) |

This mapping is stored as org-level policy (extendable per module, e.g. a customer may want every Group Policy Management high-severity alert to page regardless of the default) so OrgAdmins can tune noise without code changes.
