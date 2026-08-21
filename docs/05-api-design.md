# 05. API Design

## 1. Conventions

- **Base URL / versioning**: all endpoints are prefixed `/api/v1/`. Breaking changes ship as `/api/v2/` with the previous version kept alive per the deprecation policy; non-breaking additive changes (new optional fields, new endpoints) do not bump the version.
- **Transport**: HTTPS only (TLS 1.2+). The single FastAPI backend service serves all REST endpoints plus the streaming/WebSocket surface used by AI Chat.
- **Authentication**: Bearer JWT in the `Authorization` header on every request except `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, and `POST /api/v1/auth/password/forgot`.

  ```
  Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
  ```

  Access tokens are short-lived (15 minutes), scoped to a single `organization_id` and `user_id`, and embed the user's resolved permission codes to avoid a DB round trip on every request. Refresh tokens are long-lived (30 days), stored hashed server-side (in Postgres, `user_refresh_tokens`, not shown in the core schema as it is auth-infrastructure rather than domain data), and rotated on every use (`POST /api/v1/auth/refresh` issues a new refresh token and invalidates the old one, detecting reuse as a signal of token theft).
- **Multi-tenancy**: `organization_id` is never accepted as a client-supplied parameter for scoping a request; it is derived from the authenticated JWT and enforced by Row-Level Security at the database layer (see `04-database-design.md`, Section 2). It does appear as a field in response payloads for clarity/debugging.
- **Pagination**: list endpoints use offset-style pagination by default via `page` and `page_size` query params (`page_size` max 100, default 20), returned inside a `pagination` block. Endpoints over high-volume time-series data (`/events`, `/logs`, `/performance-metrics`) additionally support cursor-based pagination via `cursor`/`next_cursor` for stable iteration over fast-moving data.
- **Filtering & sorting**: list endpoints accept resource-specific filter query params (e.g. `?status=open&severity=critical`) and a common `sort` param (e.g. `sort=-created_at` for descending). Unrecognized filter params return `400 VALIDATION_ERROR`, not a silent no-op.
- **Idempotency**: mutating endpoints that trigger real-world side effects (`POST /scripts/{id}/execute`, `POST /tasks/{id}/approve`) accept an optional `Idempotency-Key` header; replays with the same key return the original result rather than double-executing.
- **Error envelope**: every non-2xx response uses a consistent shape:

  ```json
  {
    "error": {
      "code": "RESOURCE_NOT_FOUND",
      "message": "Server 3f9e2b... was not found in your organization.",
      "details": {},
      "request_id": "req_9f3a1c7e"
    }
  }
  ```

  Common `code` values: `VALIDATION_ERROR` (400), `UNAUTHENTICATED` (401), `FORBIDDEN` (403), `RESOURCE_NOT_FOUND` (404), `CONFLICT` (409), `APPROVAL_REQUIRED` (409, used when a client attempts to bypass the approval gate), `RATE_LIMITED` (429), `INTERNAL_ERROR` (500).
- **Success envelope**: single resource responses are wrapped as `{ "data": { ... } }`; list responses as `{ "data": [ ... ], "pagination": { ... } }`. This document omits the wrapper in a few inline examples for brevity but every implementation must include it.
- **Rate limiting**: enforced per `organization_id` + per `user_id` via Redis token buckets; responses include `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers.

## 2. Authentication

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Create a new organization + first admin user (self-serve signup). |
| POST | `/api/v1/auth/login` | Exchange email/password for an access + refresh token pair. |
| POST | `/api/v1/auth/refresh` | Exchange a valid refresh token for a new access/refresh pair (rotates the refresh token). |
| POST | `/api/v1/auth/logout` | Revoke the current refresh token. |
| GET | `/api/v1/auth/me` | Return the authenticated user, organization, and resolved permissions. |
| POST | `/api/v1/auth/mfa/enable` | Begin TOTP MFA enrollment; returns a provisioning URI. |
| POST | `/api/v1/auth/mfa/verify` | Verify a TOTP code to complete login or enrollment. |
| POST | `/api/v1/auth/password/forgot` | Trigger a password reset email. |
| POST | `/api/v1/auth/password/reset` | Complete a password reset using the emailed token. |

### Example: `POST /api/v1/auth/login`

Request:
```json
{
  "email": "rahul.nimaje@trootech.com",
  "password": "correct-horse-battery-staple"
}
```

Response `200 OK` (or `202 Accepted` with `"mfa_required": true` if MFA is enabled, in which case the client calls `/auth/mfa/verify` with the returned `mfa_challenge_id`):
```json
{
  "data": {
    "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "rtok_5f3c...e91a",
    "token_type": "Bearer",
    "expires_in": 900,
    "user": {
      "id": "6d2e1a4c-9b3f-4e2a-8c1d-0a9f7b6e5d4c",
      "organization_id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
      "email": "rahul.nimaje@trootech.com",
      "full_name": "Rahul Nimaje",
      "status": "active",
      "roles": ["Admin"]
    }
  }
}
```

### Refresh token flow

1. Client stores `access_token` in memory and `refresh_token` in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie (web) or secure keychain storage (native).
2. When a request returns `401 UNAUTHENTICATED` with `code: "TOKEN_EXPIRED"`, the client calls `POST /api/v1/auth/refresh` with the refresh token.
3. The server validates the refresh token against its hashed record, issues a new access/refresh pair, and marks the old refresh token as used. Reuse of an already-rotated refresh token immediately revokes the entire token family and forces re-login, treated as a possible token-theft signal and logged to `audit_logs`.

## 3. RBAC (Users, Roles, Permissions)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/users` | List users in the organization. Filters: `status`, `role_id`. |
| POST | `/api/v1/users` | Invite a new user. |
| GET | `/api/v1/users/{id}` | Get a single user. |
| PATCH | `/api/v1/users/{id}` | Update a user (name, status). |
| DELETE | `/api/v1/users/{id}` | Soft-delete (deactivate) a user. |
| GET | `/api/v1/roles` | List roles. |
| POST | `/api/v1/roles` | Create a custom role. |
| GET | `/api/v1/roles/{id}` | Get a role and its granted permissions. |
| PATCH | `/api/v1/roles/{id}` | Update a role's name/description. |
| DELETE | `/api/v1/roles/{id}` | Soft-delete a non-system role. |
| GET | `/api/v1/permissions` | List the global permission catalog. |
| PUT | `/api/v1/roles/{id}/permissions` | Replace the permission set granted to a role. |
| POST | `/api/v1/users/{id}/roles` | Assign a role to a user. |
| DELETE | `/api/v1/users/{id}/roles/{role_id}` | Remove a role from a user. |

### Example: `POST /api/v1/users/{id}/roles`

Request:
```json
{
  "role_id": "8f1c2e3d-4a5b-6c7d-8e9f-0a1b2c3d4e5f"
}
```

Response `201 Created`:
```json
{
  "data": {
    "user_id": "6d2e1a4c-9b3f-4e2a-8c1d-0a9f7b6e5d4c",
    "role_id": "8f1c2e3d-4a5b-6c7d-8e9f-0a1b2c3d4e5f",
    "role_name": "Server Operator",
    "granted_by": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
    "granted_at": "2026-07-13T09:12:00Z"
  }
}
```

## 4. Infrastructure

Covers Infrastructure Inventory, Active Directory Management, Group Policy Management, DNS Manager, DHCP Manager, IIS Copilot, VMware Management, Hyper-V Management, and Cloud Management.

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/servers` | List servers. Filters: `health_status`, `environment`, `os_type`, `search`. |
| POST | `/api/v1/servers` | Register a new server. |
| GET | `/api/v1/servers/{id}` | Get server detail, including denormalized health fields. |
| PATCH | `/api/v1/servers/{id}` | Update server metadata (tags, environment, credential). |
| DELETE | `/api/v1/servers/{id}` | Soft-delete a server. |
| GET | `/api/v1/devices` | List devices. Filters: `device_type`, `status`. |
| POST | `/api/v1/devices` | Register a device. |
| GET | `/api/v1/inventory` | List consolidated inventory across all asset types. |
| POST | `/api/v1/inventory/scan` | Trigger a discovery scan (read-only; auto-runs without approval). |
| GET | `/api/v1/active-directory/users` | List cached AD users. Filters: `account_enabled`, `locked_out`. |
| GET | `/api/v1/active-directory/groups` | List cached AD groups. |
| GET | `/api/v1/active-directory/groups/{id}/members` | List members of an AD group. |
| GET | `/api/v1/group-policy/objects` | List GPOs. |
| GET | `/api/v1/group-policy/objects/{id}` | Get GPO detail including linked OUs and settings summary. |
| GET | `/api/v1/dns/zones` | List DNS zones. |
| GET | `/api/v1/dns/zones/{id}/records` | List records in a zone. |
| POST | `/api/v1/dns/zones/{id}/records` | Propose a new DNS record (mutating -> creates a `pending_approval` task). |
| GET | `/api/v1/dhcp/scopes` | List DHCP scopes. |
| GET | `/api/v1/dhcp/scopes/{id}/leases` | List leases in a scope. |
| GET | `/api/v1/iis/sites` | List IIS sites. |
| POST | `/api/v1/iis/sites/{id}/restart` | Request a site restart (mutating -> `pending_approval` task). |
| GET | `/api/v1/vmware/vms` | List VMware VMs. |
| POST | `/api/v1/vmware/vms/{id}/power-actions` | Request a power action (start/stop/reset) (mutating -> `pending_approval` task). |
| GET | `/api/v1/hyperv/vms` | List Hyper-V VMs. |
| GET | `/api/v1/cloud/accounts` | List connected cloud accounts. |
| GET | `/api/v1/cloud/resources` | List discovered cloud resources. Filters: `provider`, `resource_type`, `region`. |

### Example: `GET /api/v1/servers/{id}`

Response `200 OK`:
```json
{
  "data": {
    "id": "3f9e2b1a-7c4d-4e8f-9a1b-2c3d4e5f6a7b",
    "organization_id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
    "hostname": "web-prod-03",
    "ip_address": "10.20.4.17",
    "os_type": "windows",
    "os_version": "Windows Server 2022",
    "environment": "production",
    "credential_id": "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e",
    "health_status": "warning",
    "cpu_usage_pct": 78.40,
    "memory_usage_pct": 65.10,
    "disk_usage_pct": 42.00,
    "open_alerts_count": 2,
    "tags": { "team": "platform", "tier": "web" },
    "last_seen_at": "2026-07-13T10:58:00Z",
    "created_at": "2025-11-02T08:00:00Z",
    "updated_at": "2026-07-13T10:58:00Z"
  }
}
```

### Example: `POST /api/v1/vmware/vms/{id}/power-actions` (mutating, routes through approval)

Request:
```json
{
  "action": "reset"
}
```

Response `202 Accepted` (note: the VM is **not** reset yet, a task is created):
```json
{
  "data": {
    "task_id": "c4d5e6f7-8a9b-4c0d-9e1f-2a3b4c5d6e7f",
    "type": "workflow_step",
    "status": "pending_approval",
    "target_resource": { "type": "vmware_vm", "id": "vm-1042", "name": "APP-DB-02" },
    "requested_by_user_id": "6d2e1a4c-9b3f-4e2a-8c1d-0a9f7b6e5d4c",
    "created_at": "2026-07-13T11:02:00Z"
  }
}
```

## 5. Monitoring

Covers Performance Analyzer, Windows Event Log Analyzer, Server Health Dashboard, and Security Center.

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/dashboard/summary` | Aggregate counts for the Server Health Dashboard (healthy/warning/critical, open alerts, pending approvals). |
| GET | `/api/v1/servers/{id}/health` | Latest health snapshot for a server. |
| GET | `/api/v1/servers/{id}/health/history` | Historical health snapshots (from `health_snapshots`). |
| GET | `/api/v1/servers/{id}/metrics` | Time-series performance metrics. Query: `metric_name`, `from`, `to`, `granularity`. |
| GET | `/api/v1/events` | List normalized events. Filters: `server_id`, `event_type`, `severity`, `from`, `to`. Cursor-paginated. |
| GET | `/api/v1/events/{id}` | Get a single event's raw payload. |
| GET | `/api/v1/logs` | Search application/system logs. Filters: `log_type`, `level`, `source`, `q` (full-text, backed by OpenSearch). |
| GET | `/api/v1/security/findings` | List security findings. Filters: `severity`, `status`, `finding_type`. |
| POST | `/api/v1/security/findings/{id}/remediate` | Request remediation via the linked script (mutating -> `pending_approval` task). |

### Example: `GET /api/v1/servers/{id}/metrics?metric_name=cpu_pct&from=2026-07-13T00:00:00Z&to=2026-07-13T12:00:00Z&granularity=15m`

Response `200 OK`:
```json
{
  "data": {
    "server_id": "3f9e2b1a-7c4d-4e8f-9a1b-2c3d4e5f6a7b",
    "metric_name": "cpu_pct",
    "unit": "percent",
    "points": [
      { "collected_at": "2026-07-13T00:00:00Z", "value": 22.10 },
      { "collected_at": "2026-07-13T00:15:00Z", "value": 24.85 },
      { "collected_at": "2026-07-13T00:30:00Z", "value": 78.40 }
    ]
  }
}
```

## 6. Scripts

Covers PowerShell Generator, Bash Script Generator, and Script Library, plus the execution/approval hand-off.

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/scripts` | List scripts. Filters: `language`, `category`, `risk_level`, `is_ai_generated`. |
| POST | `/api/v1/scripts` | Save a new script (manually authored or AI-generated). |
| GET | `/api/v1/scripts/{id}` | Get script detail. |
| PATCH | `/api/v1/scripts/{id}` | Update a script (creates a new `script_versions` row). |
| DELETE | `/api/v1/scripts/{id}` | Soft-delete a script. |
| GET | `/api/v1/scripts/{id}/versions` | List version history. |
| POST | `/api/v1/scripts/generate` | Ask the AI to generate a PowerShell/Bash script for a described task. |
| POST | `/api/v1/scripts/{id}/execute` | **Request execution.** Read-only scripts (`risk_level: "low"` and flagged diagnostic) may auto-run; anything else creates a `pending_approval` task. |
| GET | `/api/v1/script-library/collections` | List script library collections. |
| POST | `/api/v1/script-library/collections/{id}/items` | Add a script to a collection. |

### Example: `POST /api/v1/scripts/{id}/execute` (the core Human Approval gate)

Request:
```json
{
  "target_server_id": "3f9e2b1a-7c4d-4e8f-9a1b-2c3d4e5f6a7b",
  "parameters": { "service_name": "W3SVC", "action": "restart" }
}
```

Response `202 Accepted` for a mutating script (execution is deferred, not performed):
```json
{
  "data": {
    "task_id": "d5e6f7a8-9b0c-4d1e-8f2a-3b4c5d6e7f8a",
    "type": "script_execution",
    "status": "pending_approval",
    "script_id": "e6f7a8b9-0c1d-4e2f-9a3b-4c5d6e7f8a9b",
    "target_server_id": "3f9e2b1a-7c4d-4e8f-9a1b-2c3d4e5f6a7b",
    "execution_method": "winrm",
    "requires_approval": true,
    "requested_by_user_id": "6d2e1a4c-9b3f-4e2a-8c1d-0a9f7b6e5d4c",
    "payload": { "parameters": { "service_name": "W3SVC", "action": "restart" } },
    "created_at": "2026-07-13T11:10:00Z"
  }
}
```

If the script is a read-only diagnostic (e.g. `Get-EventLog`), the response is `200 OK` with `status: "completed"` and a populated `result` object immediately, since the Execution Safety Rule permits read-only diagnostics to auto-run.

Approval and execution then happen via the Automation domain below: `POST /api/v1/tasks/{id}/approve` is the only path that causes the WinRM/SSH call to actually fire.

## 7. Automation

Covers Automation Workflows and the Task/approval lifecycle shared by every mutating action in the platform (this is where the AI workflow's **Human Approval -> Execution -> Audit Log** steps are implemented).

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/workflows` | List workflows. |
| POST | `/api/v1/workflows` | Create a workflow (LangGraph graph definition + trigger config). |
| GET | `/api/v1/workflows/{id}` | Get workflow detail. |
| PATCH | `/api/v1/workflows/{id}` | Update a workflow. |
| POST | `/api/v1/workflows/{id}/trigger` | Manually trigger a workflow run. |
| GET | `/api/v1/automation-jobs` | List workflow run history. Filters: `workflow_id`, `status`. |
| GET | `/api/v1/automation-jobs/{id}` | Get job detail, including spawned tasks. |
| GET | `/api/v1/tasks` | List tasks (the approval queue). Filters: `status`, `type`, `target_server_id`. |
| GET | `/api/v1/tasks/{id}` | Get task detail. |
| POST | `/api/v1/tasks/{id}/approve` | **Approve a pending task.** Triggers execution via WinRM/SSH and writes an `audit_logs` entry. |
| POST | `/api/v1/tasks/{id}/reject` | Reject a pending task with a required reason. |
| POST | `/api/v1/tasks/{id}/cancel` | Cancel a task that is queued/running (best-effort). |

### Example: `POST /api/v1/tasks/{id}/approve`

Request:
```json
{
  "comment": "Confirmed with app team, restarting W3SVC during the approved maintenance window."
}
```

Response `200 OK` (execution is now dispatched asynchronously; poll `GET /api/v1/tasks/{id}` or subscribe via the notification channel for completion):
```json
{
  "data": {
    "id": "d5e6f7a8-9b0c-4d1e-8f2a-3b4c5d6e7f8a",
    "status": "approved",
    "approved_by_user_id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
    "approved_at": "2026-07-13T11:14:00Z",
    "execution_method": "winrm",
    "started_at": null,
    "result": null
  }
}
```

The backend transitions the task `approved -> running -> completed|failed` as the WinRM/SSH execution engine reports back, and appends a corresponding `audit_logs` row (`action: "task.approve"`, then `action: "task.execute"`) with `before_state`/`after_state` snapshots for full traceability. `POST /tasks/{id}/reject` performs the equivalent transition to `rejected` and never calls the execution engine.

## 8. Alerts

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/alerts` | List alerts. Filters: `status`, `severity`, `server_id`, `source_module`. |
| GET | `/api/v1/alerts/{id}` | Get alert detail. |
| POST | `/api/v1/alerts/{id}/acknowledge` | Acknowledge an open alert. |
| POST | `/api/v1/alerts/{id}/resolve` | Mark an alert resolved. |
| POST | `/api/v1/alerts/{id}/suppress` | Suppress an alert (e.g. known/expected condition). |
| GET | `/api/v1/alerts/rules` | List alert-generating policy rules. |

### Example: `POST /api/v1/alerts/{id}/acknowledge`

Request: `{}` (empty body; actor and timestamp are derived server-side)

Response `200 OK`:
```json
{
  "data": {
    "id": "f7a8b9c0-1d2e-4f3a-8b4c-5d6e7f8a9b0c",
    "status": "acknowledged",
    "acknowledged_by_user_id": "6d2e1a4c-9b3f-4e2a-8c1d-0a9f7b6e5d4c",
    "acknowledged_at": "2026-07-13T11:20:00Z"
  }
}
```

## 9. Notifications

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/notifications` | List notifications for the current user. Filters: `is_read`, `type`. |
| GET | `/api/v1/notifications/unread-count` | Get the unread count (used for the nav badge). |
| POST | `/api/v1/notifications/{id}/read` | Mark a single notification read. |
| POST | `/api/v1/notifications/mark-all-read` | Mark all notifications read. |

Real-time delivery: in addition to polling, clients subscribe to a per-user Socket.IO room (`user:{user_id}`) on which the backend emits a `notification.created` event carrying the same payload shape as the REST resource, used to drive toast notifications and the unread badge without polling.

### Example: `GET /api/v1/notifications?is_read=false&page=1&page_size=20`

Response `200 OK`:
```json
{
  "data": [
    {
      "id": "a1b2c3d4-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
      "type": "approval_request",
      "title": "Script execution awaiting your approval",
      "body": "Restart W3SVC on web-prod-03",
      "link_url": "/tasks/d5e6f7a8-9b0c-4d1e-8f2a-3b4c5d6e7f8a",
      "is_read": false,
      "created_at": "2026-07-13T11:10:05Z"
    }
  ],
  "pagination": { "page": 1, "page_size": 20, "total_items": 1, "total_pages": 1 }
}
```

## 10. Reports

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/reports` | List generated reports. Filters: `report_type`, `status`. |
| POST | `/api/v1/reports` | Request generation of a new report (async). |
| GET | `/api/v1/reports/{id}` | Get report metadata/status. |
| GET | `/api/v1/reports/{id}/download` | Download the generated file (redirects to a signed object-storage URL). |
| DELETE | `/api/v1/reports/{id}` | Delete a report record and its file. |

### Example: `POST /api/v1/reports`

Request:
```json
{
  "report_type": "security_audit",
  "format": "pdf",
  "parameters": { "from": "2026-06-01", "to": "2026-06-30", "severity_min": "warning" }
}
```

Response `202 Accepted`:
```json
{
  "data": {
    "id": "b2c3d4e5-6f7a-4b8c-9d0e-1f2a3b4c5d6e",
    "report_type": "security_audit",
    "status": "generating",
    "format": "pdf",
    "generated_by_user_id": "6d2e1a4c-9b3f-4e2a-8c1d-0a9f7b6e5d4c",
    "created_at": "2026-07-13T11:25:00Z"
  }
}
```

Clients poll `GET /api/v1/reports/{id}` (or listen for a `report.ready` notification) until `status` becomes `ready`, then call the download endpoint.

## 11. AI Chat

Backs the AI Chat module and is the entry point to the full AI workflow: **User Prompt -> Planner -> Agent Selection -> Tool Calling -> Data Collection -> Reasoning -> Root Cause Analysis -> Recommendation -> Script Generation -> Human Approval -> Execution -> Audit Log**.

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/ai/conversations` | List the user's conversations. |
| POST | `/api/v1/ai/conversations` | Start a new conversation. |
| GET | `/api/v1/ai/conversations/{id}` | Get conversation detail with message history. |
| DELETE | `/api/v1/ai/conversations/{id}` | Archive/delete a conversation. |
| POST | `/api/v1/ai/conversations/{id}/messages` | Send a user message; kicks off the LangGraph agent run. |
| GET | `/api/v1/ai/conversations/{id}/stream` | **Server-Sent Events (SSE)** stream of the assistant's response as it is generated (also exposed as a Socket.IO channel `conversation:{id}` for clients already using WebSockets elsewhere in the app; both surfaces carry identical event payloads). |

### Example: `POST /api/v1/ai/conversations/{id}/messages`

Request:
```json
{
  "content": "web-prod-03 is running hot on CPU, can you find out why and fix it?"
}
```

Response `202 Accepted` (the response body only echoes the stored user message; the assistant's reply is delivered via the stream below):
```json
{
  "data": {
    "id": "c3d4e5f6-7a8b-4c9d-0e1f-2a3b4c5d6e7f",
    "conversation_id": "d4e5f6a7-8b9c-4d0e-1f2a-3b4c5d6e7f8a",
    "role": "user",
    "content": "web-prod-03 is running hot on CPU, can you find out why and fix it?",
    "created_at": "2026-07-13T11:30:00Z"
  }
}
```

### Streaming: `GET /api/v1/ai/conversations/{id}/stream` (SSE)

The client opens this connection immediately after posting the message. Events are emitted as the LangGraph agent progresses through the workflow stages, so the UI can show live status ("Selecting agent...", "Collecting performance data...", "Analyzing root cause...") rather than a blank spinner:

```
event: agent_step
data: {"stage": "planner", "detail": "Classifying request as performance diagnosis"}

event: agent_step
data: {"stage": "tool_calling", "detail": "Invoking MCP tool: get_performance_metrics(server_id=3f9e2b1a...)"}

event: token
data: {"delta": "I checked web-prod-03's last 30 minutes of CPU data. "}

event: token
data: {"delta": "Usage spiked to 78% coinciding with a W3SVC worker process restart loop."}

event: task_created
data: {"task_id": "d5e6f7a8-9b0c-4d1e-8f2a-3b4c5d6e7f8a", "status": "pending_approval", "summary": "Restart W3SVC application pool on web-prod-03"}

event: done
data: {"message_id": "e5f6a7b8-9c0d-4e1f-8a2b-3c4d5e6f7a8b", "tokens_used": 412, "model_used": "gpt-4.1"}
```

If the recommended fix is a mutating action, the agent does not execute it: it calls the same script-generation and `POST /api/v1/scripts/{id}/execute` path internally, which creates a `pending_approval` task exactly as described in Section 6/7, and emits `task_created` so the chat UI can render an inline "Approve / Reject" card. The human's approval action still goes through `POST /api/v1/tasks/{id}/approve`; the AI Chat module never bypasses the approval gate, it only surfaces it.

## 12. Cross-Domain Conventions Recap

- **Versioning**: `/api/v1/` now; additive changes stay within v1, breaking changes move to `/api/v2/` with v1 supported for a published deprecation window (minimum 6 months).
- **Human Approval gate**: any endpoint that would mutate managed infrastructure (`POST .../execute`, `POST .../restart`, `POST .../power-actions`, `POST .../records`, `POST .../remediate`, workflow steps) returns `202 Accepted` with a `tasks` resource in `pending_approval` state instead of performing the action. The only endpoint that transitions a task toward real execution is `POST /api/v1/tasks/{id}/approve`. Read-only diagnostic endpoints (`GET` requests, `POST /inventory/scan`, `POST /scripts/{id}/execute` for scripts flagged read-only) execute immediately and return `200 OK`/`completed`.
- **Streaming**: AI Chat is the only endpoint family that streams; it uses SSE as the primary transport with an equivalent Socket.IO channel for clients that already hold a WebSocket connection (e.g. to also receive `notification.created` events on the same socket).
- **Auth**: Bearer JWT (15-minute access token, 30-day rotating refresh token), organization and permissions embedded in the token claims, enforced again at the database layer via Row-Level Security as defense in depth.
