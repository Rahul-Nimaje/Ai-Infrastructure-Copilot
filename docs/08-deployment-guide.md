# 08 — Deployment Guide

This guide describes how AI Infrastructure Copilot is packaged, deployed, and rolled out across
environments. It covers container images, Kubernetes/Helm structure, Terraform module layout,
CI/CD pipelines, and release strategy — including the stricter rollout rules for
`execution-worker`, since it is the component that actually executes approved actions against
customer infrastructure.

Services referenced throughout: `apps/web` (Next.js), `apps/api` (FastAPI), `apps/execution-worker`
(job runner), `apps/ai-orchestrator` (LangGraph/MCP orchestration service).

---

## 1. Docker Images

Each service ships as an independently versioned, independently deployable image. All images are
built with multi-stage Dockerfiles to keep runtime images small and free of build tooling / source
maps / dev dependencies.

### 1.1 `apps/web` (Next.js)

- **Base image (build stage):** `node:20-bookworm-slim`
- **Base image (runtime stage):** `node:20-bookworm-slim` (or `gcr.io/distroless/nodejs20-debian12`
  once the team is comfortable debugging without a shell)
- **Stages:**
  1. `deps` — install dependencies with `npm ci` (or `pnpm install --frozen-lockfile`), cached via
     Docker layer caching on the lockfile only.
  2. `builder` — copy source, run `next build` with `output: 'standalone'` so only the minimal
     server bundle + required `node_modules` are produced.
  3. `runner` — copy `.next/standalone`, `.next/static`, and `public/` from `builder`; run as
     non-root user `nextjs` (uid 1001); expose port 3000; `CMD ["node", "server.js"]`.
- **Build args:** `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_WS_URL`, `SENTRY_RELEASE` (public/build-time
  env vars only — no secrets baked into the image).
- **Image size target:** < 200MB.
- **Healthcheck:** `GET /api/health` (lightweight Next.js route handler, not a full page render).

### 1.2 `apps/api` (FastAPI)

- **Base image (build stage):** `python:3.12-slim-bookworm`
- **Base image (runtime stage):** `python:3.12-slim-bookworm`
- **Stages:**
  1. `builder` — install `uv` (or `poetry`), resolve and build wheels into a virtualenv at
     `/opt/venv` using `--no-dev`.
  2. `runner` — copy `/opt/venv` and application code only; install `curl` or use Python for the
     healthcheck (avoid full build toolchain in final image); run as non-root user `apiuser`
     (uid 1001); expose port 8000.
- **Process manager:** `uvicorn` workers behind `gunicorn` in production
  (`gunicorn -k uvicorn.workers.UvicornWorker -w <N> apps.api.main:app`), with `N` sized to CPU
  request (typically `2 * vCPU + 1`, capped at 4 per pod since horizontal scaling handles the rest).
- **Healthcheck:** `GET /health/live` (process up) and `GET /health/ready` (DB, Redis, OpenSearch
  connectivity) — used by both Docker `HEALTHCHECK` and Kubernetes probes.
- **Image size target:** < 400MB.

### 1.3 `apps/execution-worker`

- **Base image:** `python:3.12-slim-bookworm` (same toolchain as `api` for consistency; deliberately
  *not* given any Docker-in-Docker, SSH client tooling, or cloud CLI baked in by default — anything
  needed to execute scripts against target infra is invoked through narrowly scoped, audited
  connector libraries, not by shelling into arbitrary tools).
- **Stages:** same `builder`/`runner` split as `api`.
- **Runtime posture:** this image intentionally has the smallest possible attack surface because it
  is the component with real-world blast radius. No package managers, no compilers, no shell
  utilities beyond what the connector SDKs require are left in the runtime layer (`apt-get purge`
  build deps in the same layer they're installed, or use a `distroless`-based runtime image once
  connector dependencies allow it).
- **Process:** consumes jobs from a queue (Redis-backed job queue / stream), never accepts inbound
  HTTP traffic from the public internet (see NetworkPolicy in §2.5).
- **Healthcheck:** a liveness probe that checks the process is alive and can reach the queue; no
  public-facing readiness endpoint is required since it is never behind an Ingress.

### 1.4 `apps/ai-orchestrator`

- **Base image:** `python:3.12-slim-bookworm`
- **Stages:** same `builder`/`runner` pattern.
- **Notes:** bundles LangGraph graph definitions and MCP client/server glue. Model provider
  credentials (OpenAI API key, local LLM endpoint config) are injected via environment variables
  sourced from Vault at deploy time, never baked into the image.
- **Healthcheck:** `GET /health/ready` verifies it can reach the configured LLM provider(s) and the
  vector store (pgvector) without making a billed inference call (e.g., a lightweight models-list
  or embeddings-store ping).

### 1.5 Common conventions across all images

- Every Dockerfile lives at `apps/<service>/Dockerfile` and is built with repo root as build context
  so `packages/shared-types` can be copied in for TypeScript builds.
- All images are tagged `<service>:<git-sha>` and additionally `<service>:<semver>` on release
  branches; `latest` is never deployed, only used for local dev convenience.
- All images run as non-root, set `readOnlyRootFilesystem: true` where the app allows it (writable
  `/tmp` mounted as an `emptyDir` volume where needed), and drop all Linux capabilities
  (`cap_drop: ["ALL"]`).
- SBOMs are generated at build time (`syft` or `docker buildx imagetools`) and attached to each image
  for later vulnerability triage.

---

## 2. Kubernetes / Helm Structure

### 2.1 Chart layout

An **umbrella chart** composes one **subchart per service**, so each service can still be deployed,
versioned, and rolled back independently while environments can also deploy "the whole platform" in
one `helm upgrade`.

```
infra/k8s/
  charts/
    ai-copilot/                  # umbrella chart
      Chart.yaml                 # dependencies: web, api, execution-worker, ai-orchestrator
      values.yaml                # shared defaults (image registry, common labels, domain)
      values-dev.yaml
      values-staging.yaml
      values-prod.yaml
      charts/
        web/
          Chart.yaml
          values.yaml
          templates/
            deployment.yaml
            service.yaml
            ingress.yaml
            hpa.yaml
            pdb.yaml
            networkpolicy.yaml
            configmap.yaml
            serviceaccount.yaml
        api/
          templates/
            deployment.yaml
            service.yaml
            ingress.yaml
            hpa.yaml
            pdb.yaml
            networkpolicy.yaml
            configmap.yaml
            secret-external.yaml   # ExternalSecret referencing Vault
            serviceaccount.yaml
        execution-worker/
          templates/
            deployment.yaml
            service.yaml            # ClusterIP, internal only, no ingress ever
            hpa.yaml
            pdb.yaml
            networkpolicy.yaml      # deny-all + narrow allow (see 2.5)
            configmap.yaml
            secret-external.yaml
            serviceaccount.yaml
        ai-orchestrator/
          templates/
            deployment.yaml
            service.yaml
            hpa.yaml
            pdb.yaml
            networkpolicy.yaml
            configmap.yaml
            secret-external.yaml
            serviceaccount.yaml
```

### 2.2 Deployment

Common conventions across all `deployment.yaml` templates:

- `strategy.type: RollingUpdate` with `maxUnavailable: 0, maxSurge: 1` for `api`/`ai-orchestrator`
  (never reduce capacity during rollout); `execution-worker` uses `maxUnavailable: 1, maxSurge: 0`
  to avoid running two versions of job-executing code against the same queue simultaneously more
  than briefly.
- `resources.requests`/`limits` set per service, tuned from load testing; `api` and
  `ai-orchestrator` set CPU requests conservatively since LLM calls are I/O-bound, not CPU-bound.
- `livenessProbe` / `readinessProbe` / `startupProbe` defined per service using the health
  endpoints from §1.
- `securityContext`: `runAsNonRoot: true`, `readOnlyRootFilesystem: true`,
  `allowPrivilegeEscalation: false`, `capabilities.drop: ["ALL"]`, `seccompProfile.type:
  RuntimeDefault`.
- `topologySpreadConstraints` across nodes/zones for `api`, `execution-worker`, and
  `ai-orchestrator` to avoid correlated failure.
- Pod annotations wire up Prometheus scraping (`prometheus.io/scrape: "true"`).

### 2.3 Service / Ingress

- `web` and `api` each get a `ClusterIP` Service fronted by a shared **Ingress** (NGINX Ingress
  Controller or a service mesh gateway, e.g., Istio `Gateway`/`VirtualService`), terminating TLS
  with certificates issued via `cert-manager`.
  - `app.aicopilot.io` → `web` Service.
  - `api.aicopilot.io` → `api` Service.
- `ai-orchestrator` gets a `ClusterIP` Service reachable only from `api` (internal service-to-service
  call, no Ingress).
- `execution-worker` gets a `ClusterIP` Service used **only** for its metrics/health port; it has
  **no Ingress resource at all** — it is not routable from outside the cluster and not reachable
  from the public internet under any configuration.

### 2.4 HPA / PodDisruptionBudget

- `api`: HPA on CPU (60% target) and a custom metric (in-flight requests per pod via Prometheus
  Adapter); min 3 / max 20 replicas in prod. PDB `minAvailable: 2`.
- `web`: HPA on CPU (60%); min 2 / max 10. PDB `minAvailable: 1`.
- `ai-orchestrator`: HPA on a custom metric (queue depth of pending AI reasoning requests); min 2 /
  max 12. PDB `minAvailable: 1`.
- `execution-worker`: HPA scales on **queue depth** (jobs waiting per job-type queue), not CPU, since
  workers are largely idle between executions; min 2 / max 15. PDB `minAvailable: 1` — the cluster
  must always be able to drain at least one worker's in-flight job before terminating another.

### 2.5 NetworkPolicy — locking down `execution-worker`

`execution-worker` is the highest-risk component: it holds credentials and executes approved
scripts against real customer servers/devices. Its `NetworkPolicy` follows default-deny with a
narrow allow-list:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: execution-worker-lockdown
  namespace: ai-copilot
spec:
  podSelector:
    matchLabels:
      app: execution-worker
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # Only Prometheus can scrape metrics; nothing else may initiate a connection in.
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: monitoring
          podSelector:
            matchLabels:
              app: prometheus
      ports:
        - protocol: TCP
          port: 9090
  egress:
    # Redis-backed job queue (pull jobs, push status/results)
    - to:
        - podSelector:
              matchLabels:
                app: redis
      ports:
        - protocol: TCP
          port: 6379
    # PostgreSQL (write execution results, audit log entries)
    - to:
        - podSelector:
              matchLabels:
                app: postgresql
      ports:
        - protocol: TCP
          port: 5432
    # Vault (short-lived credential retrieval for target servers/devices)
    - to:
        - podSelector:
              matchLabels:
                app: vault
      ports:
        - protocol: TCP
          port: 8200
    # DNS
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: UDP
          port: 53
    # Egress to customer-managed targets is NOT granted here as a blanket rule; per-environment
    # egress to specific managed-network CIDRs (customer VPN/VPC ranges, jump hosts) is added via
    # additional narrowly scoped NetworkPolicy/Egress-Gateway rules maintained in
    # infra/terraform/modules/network, never as an open 0.0.0.0/0 egress.
```

Key rules enforced by this policy and reviewed on every change:

- No ingress from the Ingress Controller / public internet, ever — `execution-worker` is never a
  proxy target.
- No ingress from `web`. `web` never talks to `execution-worker` directly; all execution requests
  flow `web → api → queue → execution-worker`, so `api` is the only writer to the queue and
  `execution-worker` is purely a consumer.
- Egress is limited to the queue, the database (for result/audit writes), Vault (for
  just-in-time credentials), DNS, and explicitly declared target-network CIDRs per environment. No
  wildcard internet egress.
- Any PR that modifies `execution-worker`'s `networkpolicy.yaml` requires the mandatory review
  described in `docs/12-coding-standards.md` (Human Approval / execution-worker gate).

`api` and `ai-orchestrator` get their own default-deny NetworkPolicies too (ingress only from the
Ingress Controller / internal callers, egress limited to DB, Redis, OpenSearch, Vault, LLM provider
endpoints, and — for `api` only — `ai-orchestrator`), but `execution-worker`'s is the strictest and
is treated as a security-critical artifact.

---

## 3. Terraform Module Structure

```
infra/terraform/
  modules/
    network/        # VPC/VNet, subnets (public/app/data/execution), route tables, NAT, egress gateway rules
    k8s-cluster/     # Managed Kubernetes cluster (EKS/GKE/AKS), node pools, IRSA/workload identity
    database/        # Managed PostgreSQL (with pgvector extension enabled), Redis, OpenSearch
    vault/           # Vault cluster or managed secrets backend, auth methods, policies
    dns/             # Zones, records, cert-manager DNS-01 delegation
  environments/
    dev/
      main.tf        # composes modules above with dev-sized inputs
      terraform.tfvars
      backend.tf      # remote state: separate state file/backend per environment
    staging/
      main.tf
      terraform.tfvars
      backend.tf
    prod/
      main.tf
      terraform.tfvars
      backend.tf
```

### 3.1 Module responsibilities

- **`modules/network`**: VPC, subnet tiers (`public`, `app`, `data`, and a dedicated `execution`
  subnet for `execution-worker` node pool with tighter route tables/NAT egress rules), security
  groups/firewall rules, VPC peering or Transit Gateway attachments to customer networks where
  applicable.
- **`modules/k8s-cluster`**: cluster control plane, node pools (a separate node pool for
  `execution-worker` so it can carry distinct taints/labels — e.g., `workload=execution-worker:NoSchedule`
  — and tighter node-level security policies than general app workloads), cluster autoscaler config,
  workload identity/IRSA roles per service (so `execution-worker`'s pod identity has narrowly scoped
  cloud permissions, distinct from `api`'s).
- **`modules/database`**: managed PostgreSQL instance(s) with the `pgvector` extension enabled,
  automated backups, read replicas (staging/prod), managed Redis (job queue + cache), OpenSearch
  domain/cluster for logs and full-text search. Outputs connection endpoints and writes credentials
  into Vault rather than into Terraform state/outputs in plaintext.
- **`modules/vault`**: Vault deployment (or managed secrets manager equivalent), Kubernetes auth
  method configuration so pods authenticate via their ServiceAccount, policy definitions scoping
  which paths each service's identity may read (`execution-worker` policy is the narrowest — only
  the specific credential paths it needs, with short TTL leases).
- **`modules/dns`**: hosted zone, records for `app.`, `api.` subdomains, DNS-01 records for
  `cert-manager` certificate issuance.

### 3.2 Environment composition

Each environment (`dev`, `staging`, `prod`) is a thin root module that instantiates the shared
modules with environment-specific sizing/variables — it does not duplicate module logic:

```hcl
# infra/terraform/environments/prod/main.tf
module "network" {
  source        = "../../modules/network"
  environment   = "prod"
  cidr_block    = "10.20.0.0/16"
  az_count      = 3
}

module "k8s_cluster" {
  source              = "../../modules/k8s-cluster"
  environment         = "prod"
  vpc_id              = module.network.vpc_id
  subnet_ids          = module.network.app_subnet_ids
  execution_subnet_ids = module.network.execution_subnet_ids
  node_pools = {
    general           = { min = 3, max = 12, instance_type = "m6i.large" }
    execution-worker  = { min = 2, max = 15, instance_type = "m6i.large", taint = "workload=execution-worker:NoSchedule" }
  }
}

module "database" {
  source          = "../../modules/database"
  environment     = "prod"
  vpc_id          = module.network.vpc_id
  subnet_ids      = module.network.data_subnet_ids
  multi_az        = true
  backup_retention_days = 35
}

module "vault" {
  source      = "../../modules/vault"
  environment = "prod"
  vpc_id      = module.network.vpc_id
  k8s_cluster = module.k8s_cluster.cluster_name
}

module "dns" {
  source      = "../../modules/dns"
  environment = "prod"
  domain      = "aicopilot.io"
}
```

- `dev`: single-AZ, smaller instance sizes, shared node pool (no dedicated execution-worker pool
  needed for cost reasons, but the NetworkPolicy restrictions still apply), shorter backup
  retention.
- `staging`: mirrors prod topology (multi-AZ, dedicated execution-worker node pool) at reduced
  scale, used as the pre-prod validation environment and canary reference.
- `prod`: multi-AZ, dedicated execution-worker node pool with taints, full backup retention,
  stricter Vault policies, DNS with production certificates.
- Remote state is stored per-environment in a versioned, encrypted backend (e.g., S3 + DynamoDB
  lock table, or Terraform Cloud workspaces per environment) — environments never share state.
- All Terraform changes go through `terraform plan` posted as a PR comment (via GitHub Actions) and
  require review before `terraform apply`; `prod` applies require a second approver.

---

## 4. GitHub Actions CI/CD Pipelines

Each deployable service has its own workflow so unrelated services aren't rebuilt/redeployed on
every change, and each workflow follows the same staged pipeline:

```
lint → unit test → build → container scan (Trivy) → integration test → push image → deploy
```

### 4.1 Workflow files

```
.github/workflows/
  web-ci-cd.yaml
  api-ci-cd.yaml
  execution-worker-ci-cd.yaml
  ai-orchestrator-ci-cd.yaml
  terraform-plan-apply.yaml
  shared-types-ci.yaml
```

Each `*-ci-cd.yaml` is path-filtered so it only triggers on changes to its own `apps/<service>/**`
plus `packages/shared-types/**` (since that package is a build-time dependency for both
`apps/web` and the Python services' generated clients).

### 4.2 Common pipeline stages (illustrated for `api-ci-cd.yaml`)

1. **Lint** — `ruff check .` and `black --check .` against `apps/api`; fails fast on style/lint
   violations before running anything expensive.
2. **Unit test** — `pytest apps/api/tests/unit --cov=apps/api --cov-fail-under=80`; coverage
   report uploaded as an artifact / to Codecov.
3. **Build** — `docker buildx build` the multi-stage Dockerfile, tagged `api:<git-sha>`, pushed to
   an ephemeral/internal registry cache layer (not yet the release registry).
4. **Container scan** — Trivy scans the built image for OS and dependency CVEs
   (`trivy image --exit-code 1 --severity CRITICAL,HIGH api:<git-sha>`); build fails the pipeline
   on any unpatched CRITICAL/HIGH finding without an accepted risk exception recorded in
   `docs/`. SBOM from the build stage is also scanned.
5. **Integration test** — spins up `docker-compose` (or `kind` cluster) with Postgres, Redis,
   OpenSearch test containers; runs `pytest apps/api/tests/integration` against the real image,
   exercising DB migrations, queue interactions, and API contract tests against
   `packages/shared-types`.
6. **Push image** — on success and only on `main`/release branches, image is re-tagged and pushed
   to the production registry (`ghcr.io/aicopilot/api:<git-sha>` and `:<semver>` on tagged
   releases).
7. **Deploy** — triggers the Helm-based deploy job (§5) to `dev` automatically on `main`; `staging`
   and `prod` deploys are separate, manually approved GitHub Environments with required reviewers.

### 4.3 Service-specific notes

- **`web-ci-cd.yaml`**: lint stage runs `eslint` + `prettier --check`; unit test runs
  `vitest`/`jest` + component tests; adds a `next build` type-check stage; integration stage runs
  Playwright against a built preview deployment.
- **`api-ci-cd.yaml`**: as above; integration stage also runs Alembic migrations against a fresh
  test database to catch migration errors before merge.
- **`execution-worker-ci-cd.yaml`**: identical stages, but with two additions:
  - An extra **policy test** stage that runs a fixed suite of "must require approval" tests —
    asserting that every mutating job type in the worker's registry is rejected unless it carries a
    valid approval token, so it is structurally impossible to merge a change that silently
    bypasses the Human Approval gate.
  - The deploy job never auto-promotes past `dev`; promotion to `staging`/`prod` requires the
    canary process described in §5.3, gated by a required reviewer group that includes at least one
    engineer from the security/platform team (see `docs/12-coding-standards.md` for the PR review
    rule).
- **`ai-orchestrator-ci-cd.yaml`**: adds a stage that runs LangGraph graph unit tests with a mocked
  LLM provider (no live API calls / spend in CI) plus a small "golden set" of prompts run against a
  pinned model version to catch prompt-regression drift; flags (does not hard-fail) on drift beyond
  a similarity threshold for manual review.

### 4.4 Deploy job mechanics

The `deploy` job in each workflow:

1. Assumes a short-lived cloud credential via OIDC federation (no long-lived cloud keys stored in
   GitHub secrets).
2. Fetches the target environment's kubeconfig.
3. Runs `helm upgrade --install <service> infra/k8s/charts/ai-copilot/charts/<service> -f
   values-<env>.yaml --set image.tag=<git-sha> --atomic --timeout 5m`.
4. `--atomic` ensures a failed rollout auto-rolls-back to the previous release.
5. Posts a deployment summary (image tag, changed files, migration diff if any) to the team's
   deploy notification channel.

---

## 5. Release Strategy

### 5.1 Blue-green for `api` and `web`

`api` and `web` are stateless, horizontally scaled, and safe to run two versions side by side, so
they use **blue-green with gradual traffic shifting** at the Ingress/service-mesh layer:

1. Deploy the new version (`green`) alongside the current live version (`blue`) as a fully separate
   Deployment/ReplicaSet with its own labels (`version: green`), scaled to a small fraction of
   normal capacity.
2. The Ingress/mesh (Istio `VirtualService` weighted routing, or NGINX canary annotations) shifts
   traffic in stages: **5% → 25% → 50% → 100%**, pausing at each stage (default 10 minutes, longer
   for prod) to observe health signals.
3. At each stage, an automated gate checks:
   - HTTP 5xx rate on `green` vs. `blue` baseline (fail if `green` error rate exceeds baseline by a
     defined margin, e.g., > 2x or > 1% absolute).
   - p95/p99 latency on `green` vs. `blue`.
   - For `api`: DB error rate, queue publish failure rate, auth failure rate.
   - For `web`: client-side error rate reported via telemetry, Core Web Vitals regression.
4. **Rollback triggers** (automatic): any of the above thresholds breached during a traffic-shift
   stage triggers an immediate revert of traffic weight to 100% `blue` and pages the on-call
   engineer. Rollback is also manually triggerable with a single `helm rollback` / traffic-weight
   reset command documented in the runbook.
5. Once `green` reaches 100% and remains healthy for a soak period (e.g., 30–60 minutes in prod),
   `blue`'s replicas are scaled down and the release is marked complete. `blue`'s ReplicaSet is kept
   at zero replicas (not deleted) for a fast-path rollback window before full cleanup.

### 5.2 `ai-orchestrator`

Follows the same blue-green pattern as `api` since it is also stateless request/response
infrastructure, but its automated gate additionally checks LLM call error/timeout rate and
cost-per-request anomalies (a spike often indicates a prompt/graph regression) before advancing
traffic weight.

### 5.3 Canary rollout for `execution-worker` (deliberately conservative)

`execution-worker` is treated differently because it executes approved actions against real
customer infrastructure — a bad rollout here has consequences beyond the platform itself. Rather
than shifting a percentage of *traffic*, it shifts a percentage of **job types**:

1. New worker version is deployed alongside the current version, both consuming from the same
   queue but the new version is initially configured (via feature-flag/config, not code) to only
   pull jobs for a small, low-risk allow-list of job types — e.g., read-only diagnostics and a
   single well-understood mutating job type that has the most test coverage and lowest blast radius
   (such as "restart a specific known-safe service" on a small subset of tagged non-critical test
   servers).
2. The canary runs for a fixed soak window (minimum several hours, longer for prod, spanning at
   least one full business cycle where practical) while the platform monitors:
   - Job success/failure rate for canary job types vs. historical baseline.
   - Any unexpected/unapproved execution attempts (should be zero — the Human Approval gate is
     independent of worker version and is enforced upstream in `api`, but this is verified as a
     defense-in-depth check).
   - Audit log completeness (every canary execution has a matching approval record and audit
     entry).
   - Rollback/idempotency behavior: script failures on canary jobs must fail safe (no partial
     unrecoverable state) — verified against the job-type's declared idempotency contract.
3. If the canary soak is clean, the allow-list of job types routed to the new version is expanded
   in further stages (e.g., add the next tier of mutating job types), not a traffic percentage —
   this bounds the *kind* of risk exposed at each stage, not just the *volume*.
4. Only after all job types have been exercised successfully on the canary version does it become
   the sole consumer of the queue, at which point the old version's replicas are scaled down.
5. **Rollback triggers**: any canary job failure caused by the new code (not by the target
   infrastructure itself), any audit-log/approval mismatch, or any breach of the idempotency
   contract immediately reverts the job-type allow-list to route 100% of jobs back to the previous
   worker version, and blocks further promotion until root-caused. Rollback here means "stop
   routing new job types to the new version" — in-flight jobs on the canary version are allowed to
   complete or fail according to their own idempotency/compensation logic, never forcibly killed
   mid-execution against a target unless the job's own safety contract allows it.
6. Because `execution-worker` deploys are the most consequential, promotion past the canary stage in
   `staging`/`prod` always requires the mandatory reviewer group defined in
   `docs/12-coding-standards.md`, and is never fully automated end-to-end — a human explicitly
   advances each stage.
