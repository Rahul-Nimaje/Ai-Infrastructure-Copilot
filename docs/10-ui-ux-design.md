# UI/UX Design

This document specifies every application page for AI Infrastructure Copilot: layout, components, interactions, data states, and (where relevant) the human-approval gate that stands between an AI-proposed action and real execution against infrastructure. It is written so a frontend team can start building screens directly against it, using the fixed stack: Next.js 15 (App Router), React, TypeScript, Tailwind CSS, shadcn/ui, React Query, and Socket.IO.

The 15 pages below are the navigable surface of the product. Internally they are composed from the 20 canonical product modules (see `docs/README.md`). The mapping, so module-level docs (LLD, API design) line up with page-level docs:

| Page | Module(s) it renders |
|---|---|
| Dashboard | Server Health Dashboard (fleet summary), Alert Center (top alerts widget), AI Chat (quick-launch) |
| Infrastructure | Infrastructure Inventory, VMware Management, Hyper-V Management, Cloud Management |
| Servers | Infrastructure Inventory (server detail), Server Health Dashboard (per-server), Performance Analyzer |
| Linux | Bash Script Generator, Performance Analyzer (Linux hosts), Server Health Dashboard (Linux filter) |
| Windows | Windows Event Log Analyzer, IIS Copilot, DNS Manager, DHCP Manager, PowerShell Generator |
| Active Directory | Active Directory Management |
| Group Policy | Group Policy Management |
| Monitoring | Performance Analyzer, Server Health Dashboard (deep metrics) |
| Security | Security Center |
| Automation | Automation Workflows |
| Scripts | PowerShell Generator, Bash Script Generator, Script Library |
| Reports | Cross-module reporting (built on Alerts, AuditLogs, Logs, InfrastructureInventory) |
| Settings | Authentication, org/user/role administration |
| Alerts | Alert Center |
| AI Chat | AI Chat |

## Navigation, global chrome, and design system

**Overall shell.** Every authenticated route renders inside a single app shell: a persistent left sidebar, a top bar, and a scrollable main content area. The shell is a server component wrapper (`app/(dashboard)/layout.tsx`) with client islands for the interactive chrome.

**Left sidebar.** Built from shadcn/ui's `Sidebar` primitive (with `SidebarProvider`, `SidebarHeader`, `SidebarContent`, `SidebarGroup`, `SidebarMenu`, `SidebarMenuButton`, `SidebarFooter`, `SidebarTrigger` for collapse/expand). Navigation items are organized into module groups, each an accordion-style `SidebarGroup` with a `Collapsible` label:

- **Overview**: Dashboard
- **Infrastructure**: Infrastructure, Servers, Linux, Windows
- **Directory & Policy**: Active Directory, Group Policy
- **Monitoring & Response**: Monitoring, Alerts, Security
- **Automation**: Automation, Scripts
- **Insights**: Reports
- **AI**: AI Chat (pinned near the top, also reachable as a floating launcher, see below)
- **Admin**: Settings

The active route is highlighted with the shadcn `active` variant on `SidebarMenuButton`; a `Badge` on "Alerts" shows the live unread/critical count pushed via Socket.IO. Collapsed (icon-only) mode uses `Tooltip` to show the label on hover. Items the current role cannot access are hidden rather than disabled, except for a small set of role-gated sub-actions inside a page (those use a disabled control plus `Tooltip` explaining the required role).

**Top bar.** A fixed header containing, left to right:
- Breadcrumb (`Breadcrumb` component) reflecting the current page/section.
- Global command palette trigger (shadcn `Command` in a `Dialog`, opened with `Cmd/Ctrl+K`) for jumping to any server, script, workflow, GPO, or page by fuzzy search.
- Org switcher: a `Popover`-driven `Command` combobox listing organizations the user belongs to (relevant for MSP-style SuperAdmin/OrgAdmin users managing multiple orgs); switching org triggers a full React Query cache reset (`queryClient.clear()`) and Socket.IO re-join into the new `org:{org_id}` room.
- Notification bell: a `Popover` anchored icon button with a `Badge` count, backed by the `Notifications` entity. It opens a scrollable list of recent notifications (`ScrollArea` + grouped by day) sourced from a React Query–cached `GET /notifications` plus live Socket.IO pushes (`alert.created`, `alert.updated`, `approval.requested`, `approval.resolved`, `task.completed`, `task.failed`, `audit.appended` events append to the top of the list and bump the badge in real time; see `docs/02-HLD.md` §10 for the event contract). Clicking a notification deep-links into the owning page (e.g. an `approval.requested` notification opens the AI Chat task or Automation run that needs approval).
- Theme toggle (light/dark/system) using `next-themes`, switching Tailwind's `dark:` class strategy; all shadcn tokens (background, foreground, border, primary, destructive, warning, success, muted) are defined as CSS variables so both themes stay in sync automatically.
- User menu: `DropdownMenu` off an `Avatar`, showing name, current role badge (SuperAdmin/OrgAdmin/Operator/Viewer/Auditor), links to Settings > Profile, and Sign out.

**Floating AI Chat launcher.** A persistent bottom-right button (visible on every page except the AI Chat page itself, where it's redundant) opens AI Chat in a `Sheet` (slide-over) pre-scoped to the current page's context (e.g. opened from a Server detail page, the chat is pre-seeded with that server as context). This lets an admin ask a question without losing their place.

**Design system.** Tailwind CSS utility classes for layout/spacing/typography; shadcn/ui ("New York" style) for all interactive primitives (`Button`, `Card`, `Table`, `Tabs`, `Dialog`, `Sheet`, `Command`, `Badge`, `Skeleton`, `DropdownMenu`, `Popover`, `Tooltip`, `Select`, `Combobox`, `Form` with `react-hook-form` + `zod`, `Toast`/`Sonner` for transient feedback, `Alert` for inline banners, `Progress`, `Separator`, `ScrollArea`, `Avatar`, `Breadcrumb`, `Pagination`, `Collapsible`, `AlertDialog` for destructive confirmations). Dark and light themes are both first-class; all custom colors (risk levels, health status) are defined as semantic tokens layered on top of shadcn's CSS variables rather than hard-coded hex values, so charts and badges stay consistent across themes.

**Data and real-time patterns (apply to every page below).**
- **React Query** owns all server state. Query keys are namespaced per entity and scope, e.g. `["servers", orgId, filters]`, `["gpo", gpoId]`, `["alerts", orgId, status]`. Mutations (approve, reject, run script, create workflow) use `useMutation` with optimistic updates where safe (e.g. marking an alert "acknowledged") and always `invalidateQueries` on settle for anything touching shared lists.
- **Socket.IO** is wrapped in a single client provider (`SocketProvider`) that connects once per session, joins `org:{org_id}` and `user:{user_id}` rooms, and dispatches incoming events either into the React Query cache directly (`queryClient.setQueryData` for point updates like `task.progress`) or by triggering `invalidateQueries` for list-shaped changes (`alert.created`, `inventory.changed`). Pages that show a specific resource (a server, a task, a workflow run) additionally join a scoped room (`server:{id}`, `task:{id}`) while mounted and leave it on unmount.
- **Skeletons everywhere.** Every page that fetches data defines a matching `Skeleton` layout (cards, table rows, chat bubbles) shown while `isLoading` is true, so the page never pops from blank to populated.
- **Errors** use a consistent `Alert variant="destructive"` block with the error message, a "Retry" button wired to React Query's `refetch`, and, for full-page failures, an illustrated empty-state style card.
- **Empty states** use a centered `Card` with an icon, one-line explanation, and a primary call-to-action (e.g. "Connect your first server").

**RBAC pattern.** Roles are SuperAdmin, OrgAdmin, Operator, Viewer, Auditor. As a baseline used throughout this document:
- **Viewer** and **Auditor** are read-only everywhere; Auditor additionally has full read access to audit trails and compliance data that other non-admin roles may not see (e.g. Security Center's audit log tab, Reports' compliance exports).
- **Operator** can generate scripts, propose actions, run workflows, and **approve/reject low- and medium-risk** proposed actions on resources they're scoped to.
- **OrgAdmin** can approve any risk level within their org, manage users/roles, and edit Settings.
- **SuperAdmin** has all OrgAdmin capabilities across every org (used by the vendor/MSP operating the platform).
Anywhere an action is gated, the UI still renders the "Proposed Action" content for visibility (per the transparency principle) but disables the mutating control with a `Tooltip`: "Requires Operator role or higher" / "Requires OrgAdmin approval for high-risk actions".

**Approval workflow pattern (used on Active Directory, Group Policy, Scripts, Automation, and AI Chat).** Whenever the AI (or a human) proposes a mutating action, the UI renders a **Proposed Action card**: a bordered `Card` with a colored left accent matching a risk `Badge` (Low = green/success, Medium = amber/warning, High = orange, Critical = red/destructive), a one-line summary, an expandable diff/preview, and two primary buttons, "Approve & Run" (`Button variant="default"`) and "Reject" (`Button variant="outline"`, opens an `AlertDialog` requiring a reason). The full diff (before/after config, PowerShell/Bash source, GPO setting changes) opens in a `Dialog` (for short diffs) or a full-height `Sheet` (for long script output), using `Tabs` to switch between "Diff", "Raw Script", and "Impact" (affected object count, affected servers) views. No mutating action ever runs without this card being explicitly approved; there is no "auto-apply" control anywhere in the product for actions classified as mutating.

---

## Dashboard

**Purpose.** Give an admin, in one glance on login, the health of the entire fleet, what needs attention right now, and a fast path into AI Chat to ask a question or kick off a task.

**Layout.** Single scrollable page, no sub-tabs. A responsive grid: a top row of KPI `Card`s, a two-column layout below (main column ~2/3 width for the alert feed and fleet health chart, side column ~1/3 width for quick actions and the AI Chat quick-launch panel). Uses shadcn `Card`, `Badge`, `Skeleton`, `Tabs` (to switch the fleet chart between "By Platform" and "By Region/Site").

**Key components.**
- **Fleet health cards**: four `Card`s (Servers Online, Active Alerts, Pending Approvals, Automation Jobs Running), each with a big number, a delta vs. yesterday, and a colored status dot.
- **Fleet health chart**: a stacked bar or donut (per the dataviz conventions used across the app) breaking servers down by health status (Healthy/Warning/Critical/Offline) and by platform (Windows/Linux/VMware/Hyper-V/Cloud).
- **Alert feed widget**: the 5-10 most recent/severe alerts as compact rows (icon, server name, message, relative time, severity `Badge`), "View all" linking to Alerts.
- **Pending approvals widget**: list of Proposed Action cards (condensed) awaiting the current user's approval across all modules, each linking to its source page (AI Chat, Automation, Group Policy, Scripts).
- **AI Chat quick-launch**: an input box styled like the AI Chat composer ("Ask anything about your infrastructure...") that, on submit, navigates to `/ai-chat` with the prompt pre-filled and already sent.
- **Recent activity**: a compact timeline of the latest `AuditLogs` entries (who did what, when).

**Primary interactions.** Clicking a KPI card deep-links to the filtered view (e.g. "Active Alerts" -> Alerts page pre-filtered to open/critical). Typing into the quick-launch and pressing Enter creates a new `AIConversation` and routes to AI Chat. Clicking a pending-approval row opens that item's Proposed Action detail in place via `Dialog` without leaving the dashboard. All widgets refetch via React Query with a short `staleTime` (e.g. 30s) and are additionally nudged live by `alert.created`, `alert.updated`, `approval.requested`, `approval.resolved`, and `task.completed` Socket.IO events (each patches the relevant widget's cache rather than a full page refetch).

**States.** Empty: shown only for a brand-new org with no servers onboarded yet, replacing the whole grid with a single "Connect your first server or start a discovery scan" card linking to Infrastructure. Loading: every card and the feed render `Skeleton` blocks matching their final shape. Error: a page-level `Alert variant="destructive"` under the KPI row if the summary endpoint fails, with per-widget granular retry if only one widget's fetch failed.

**Approval-gate touchpoints.** The Dashboard surfaces pending approvals but does not host the full decision UI beyond the condensed card, clicking through opens the authoritative Proposed Action view on the owning page (AI Chat, Automation, Group Policy, or Scripts), keeping one source of truth for the diff and audit trail.

---

## Infrastructure

**Purpose.** Give the admin a single inventory of every managed asset (physical/virtual Windows and Linux servers, VMware and Hyper-V objects, and cloud resources) so they can discover, tag, group, and drill into anything the platform manages.

**Layout.** Left nav + top bar shell as usual; page-level `Tabs` across the top of the content area: "All", "Physical/VM Servers", "VMware", "Hyper-V", "Cloud". Each tab renders a filterable `Table` with a persistent filter bar above it (`Input` search, `Select` filters for platform/OS/site/tag, a `Combobox` for tag multi-select) and a `Badge`-decorated status column.

**Key components.**
- **Inventory table**: columns for Name, Type/Platform icon, OS/Version, Status (`Badge`: Healthy/Warning/Critical/Offline), Site/Region, Tags, Last Seen, Actions (`DropdownMenu` with "View details", "Run diagnostic", "Add to workflow").
- **Discovery panel**: a `Sheet` triggered by "Discover" button, letting the admin add a new subnet/vCenter/Hyper-V host/cloud account credential to scan, with a live progress `Progress` bar during the scan (via `task.progress` Socket.IO events).
- **Bulk actions bar**: appears when rows are selected via row `Checkbox`es, offering bulk tag, bulk "Add to Automation Workflow", or bulk export.
- **Detail `Sheet`** (quick view without full navigation): summary card, recent alerts, and a "Open full page" link into Servers (for physical/VM hosts), or into the relevant VMware/Hyper-V/Cloud sub-view.

**Primary interactions.** Typing in search filters client-side over a React Query–cached page of results (`["inventory", orgId, filters]`), with server-side pagination (`Pagination`) for large fleets. Clicking a row opens the quick-view `Sheet`; clicking the row's name navigates to the Servers detail page. Running "Discover" kicks off a background scan; `inventory.changed` Socket.IO events invalidate the inventory query so new/updated assets appear without a manual refresh.

**States.** Empty: "No infrastructure connected yet" card with a "Start discovery" CTA (first-run state). Loading: `Skeleton` table rows (5-8 shimmering rows matching column widths). Error: inline `Alert` above the table with retry; if only the discovery scan fails, a `Toast` error is shown instead so the rest of the page remains usable.

**Approval-gate touchpoints.** Inventory browsing and discovery are read-only/non-mutating against target infrastructure (they collect metadata only), so no approval gate applies here. Any action that would change a target server (diagnostics that only read data are auto-run; anything that mutates state routes to Scripts, Automation, or AI Chat's approval flow instead of executing from this table).

---

## Servers

**Purpose.** Let an admin drill into one specific server (physical, VM, or cloud instance) to see its health, performance history, services, event logs, and take diagnostic or remediation action on it.

**Layout.** A server detail page: header block (server name, platform icon, status `Badge`, quick actions `DropdownMenu`) followed by `Tabs`: "Overview", "Performance", "Event Logs" (Windows) / "Logs" (Linux), "Services", "Scripts Run", "Alerts". Overview tab uses a `Card` grid; Performance uses full-width charts; other tabs use `Table`.

**Key components.**
- **Overview tab**: identity card (OS, IP, uptime, agent/connection status), resource gauges (CPU/RAM/Disk as radial or bar meters), an "Ask AI about this server" button that opens the floating AI Chat `Sheet` pre-scoped to this server.
- **Performance tab**: time-series charts (CPU, memory, disk I/O, network) with a `Select` for time range (1h/24h/7d/30d), consistent with Monitoring page charts.
- **Event Logs / Logs tab**: a `Table` of recent log entries with severity `Badge`, a `Combobox` filter for log source, and an "Analyze with AI" button that sends the visible/filtered logs to AI Chat for root-cause analysis.
- **Services tab**: table of services/daemons with status `Badge` (Running/Stopped) and a "Restart" action per row, this is a mutating action and always routes through a Proposed Action confirmation before execution.
- **Scripts Run tab**: history of scripts executed against this server, linking into Script Library's run detail.
- **Alerts tab**: alerts scoped to this server, same row format as the Alerts page.

**Primary interactions.** Switching tabs is client-side (`Tabs`) and each tab's data is fetched lazily on first activation via React Query, cached per `["server", serverId, tab]`. The page joins the `server:{id}` Socket.IO room while mounted so `task.progress`, `alert.created`, and metric-tick events update the Overview gauges and Alerts tab live. Clicking "Restart" on a service opens the Proposed Action `Dialog` showing the exact command that will run and its blast radius (this service only, or dependent services).

**States.** Empty: N/A at the page level (a server always has identity data); the Scripts Run and Alerts tabs individually show "No scripts have been run against this server yet" / "No alerts" cards when empty. Loading: header shows `Skeleton` placeholders for name/status while identity loads; each tab shows its own `Skeleton` (gauge skeletons, chart skeleton, table row skeletons). Error: if the server is unreachable/agent offline, a persistent `Alert` banner sits under the header ("Last successful check-in: 3h ago") and Performance/Logs tabs show a "Data unavailable, connection lost" state instead of stale charts.

**Approval-gate touchpoints.** Any action from this page that mutates the server (service restart, applying a suggested fix, running a script) opens the same Proposed Action card pattern used elsewhere: risk `Badge`, diff/command preview, "Approve & Run"/"Reject". Operator can approve Low/Medium risk actions on servers within their assigned scope; OrgAdmin/SuperAdmin can approve any risk level; Viewer and Auditor see the proposal read-only with disabled controls.

---

## Linux

**Purpose.** Give Linux-focused admins a dedicated home for their fleet: quick access to Bash script generation, Linux-specific performance signals, and package/service state, without wading through Windows-only tooling.

**Layout.** Left nav + top bar; content splits into a left server-picker `Table`/list (filtered to Linux platform) and a right detail panel that mirrors the relevant parts of the Servers page (Overview/Performance/Logs), plus a persistent "Generate Bash Script" `Card` pinned at the top for quick access to the Bash Script Generator module.

**Key components.**
- **Linux fleet list**: compact rows (hostname, distro/version icon, status `Badge`, load average sparkline).
- **Quick script composer**: a `Textarea` ("Describe what you want the script to do...") plus a distro/target `Select`, submitting routes into the Bash Script Generator flow on the Scripts page (or renders inline in a `Sheet` for a fast one-off).
- **Package/service snapshot**: `Table` of key services (systemd units) and installed package versions relevant to flagged CVEs (cross-referenced from Security Center).
- **Log tail viewer**: a live-updating panel (via Socket.IO `task.progress`-style streaming) for `journalctl`/syslog tail on a selected server, with a `Badge` per severity and a `Command`-driven filter.

**Primary interactions.** Selecting a server from the list loads its detail panel (React Query key `["server", serverId]`, shared cache with the Servers page so navigating between Linux and Servers doesn't refetch). Submitting the quick script composer creates a script generation request; the resulting script always lands as a Proposed Action requiring approval before it can run on any target. Live log tail uses a scoped Socket.IO room (`server:{id}:logs`) and pauses/resumes with a `Switch` control.

**States.** Empty: "No Linux servers found" card with a link to Infrastructure > Discover. Loading: fleet list shows `Skeleton` rows; detail panel shows the same skeleton treatment as the Servers page. Error: connection-lost banner identical in style to Servers; log tail shows a "Streaming disconnected, click to reconnect" inline state instead of a full-page error.

**Approval-gate touchpoints.** Any Bash script generated here is not runnable directly from this page; it always hands off to the Scripts page's Proposed Action flow (diff of the script, target server list, risk badge based on static analysis of the script's operations, e.g. `rm -rf`/service stop = higher risk) before "Approve & Run" becomes available. Same RBAC rule as elsewhere: Operator approves Low/Medium, OrgAdmin/SuperAdmin approves any level.

---

## Windows

**Purpose.** Give Windows-focused admins a single hub for the Windows-specific modules: Event Log analysis, IIS site/app-pool management, DNS zone/record management, and DHCP scope/lease management, plus a fast path to PowerShell generation.

**Layout.** Left nav + top bar; content uses top-level `Tabs`: "Event Logs", "IIS", "DNS", "DHCP". Each tab is its own mini-workspace: a `Table` (sites, zones, scopes, or log entries) on the left/top and a detail `Card`/`Sheet` on selection.

**Key components.**
- **Event Logs tab**: filterable `Table` (server, log name, severity `Badge`, Event ID, message excerpt, time), a `Combobox` to filter by Event ID/source, and "Analyze with AI" to send selected entries to AI Chat for root-cause analysis and a suggested fix.
- **IIS tab**: `Table` of sites/app pools per server with status `Badge` (Started/Stopped), bindings, and actions (`DropdownMenu`: Restart App Pool, Recycle, View Config). A config diff `Dialog` shows current vs. proposed `web.config`/binding changes when the AI suggests a fix.
- **DNS tab**: `Table` of zones, expandable to records (`Accordion` or nested `Table`), with "Add/Edit/Delete record" opening a `Form` in a `Dialog` that produces a Proposed Action rather than writing directly.
- **DHCP tab**: `Table` of scopes with utilization bars, a leases sub-view, and scope edit actions following the same proposal pattern as DNS.
- **PowerShell quick-launch**: pinned card, same pattern as Linux's Bash quick-launch, routes into the Scripts page's PowerShell Generator.

**Primary interactions.** Switching tabs lazily fetches that tab's data (`["windows", tab, filters]`). Selecting a table row opens a detail `Sheet` with full config and history. Any create/edit/delete on IIS/DNS/DHCP opens a `Form`-driven `Dialog`, and submitting it does not call a write endpoint directly, it creates a proposed change that renders as a Proposed Action card at the top of the relevant tab, awaiting approval. Event Log "Analyze with AI" opens the floating AI Chat `Sheet` pre-loaded with the selected log entries as context.

**States.** Empty: each tab has its own empty state ("No IIS sites discovered on this server", "No DNS zones found") with a relevant CTA (re-scan inventory, or check agent connectivity). Loading: `Skeleton` tables per tab, loaded independently so switching tabs doesn't block on unrelated data. Error: per-tab `Alert` with retry; a global banner appears only if the underlying server/agent is unreachable for all tabs simultaneously.

**Approval-gate touchpoints.** IIS app-pool restarts/recycles, DNS record changes, and DHCP scope/lease edits are all mutating actions and always render a Proposed Action card (diff of the config before/after, affected bindings/records/leases, risk `Badge`) with "Approve & Run"/"Reject" before anything executes via WinRM. Operator can approve Low/Medium risk (e.g. a single DNS record edit); OrgAdmin/SuperAdmin required for High/Critical (e.g. deleting a DHCP scope in active use, stopping a production IIS site). Viewer/Auditor see the same card read-only.

---

## Active Directory

**Purpose.** Let admins search and manage AD objects (users, groups, OUs, computers), review AI-suggested cleanups (stale accounts, group membership issues), and safely apply changes with a full preview before anything touches the directory.

**Layout.** Left nav + top bar; split layout: a left `Tabs`-switchable tree/`Table` (OU tree view as `Collapsible` nested list, or flat searchable `Table` of users/groups/computers), and a right detail panel for the selected object. A top filter/search bar with `Command`-style type-ahead search across all AD object types.

**Key components.**
- **OU tree / object table**: `Collapsible` tree for OUs, `Table` for users/groups/computers with columns (Name, Type icon, Status `Badge` for enabled/disabled/locked, Last Logon, OU path).
- **Object detail panel**: attributes `Card` (identity, group memberships as `Badge` chips, account flags), an "AI Suggestions" `Card` listing detected issues (e.g. "Account inactive 120 days", "Member of privileged group with no recent logon") each with a "Propose Fix" button.
- **Bulk operations bar**: for multi-select actions (disable N accounts, add N users to a group), appearing on row selection.
- **Proposed Action card**: for any AD write (disable account, remove from group, move OU, reset password), showing a clear before/after attribute diff (`Tabs`: "Diff", "Impact") and the exact LDAP/PowerShell operation that will run.

**Primary interactions.** Typing in the search bar hits a debounced React Query search (`["ad-search", term]`). Selecting an object loads its detail panel (`["ad-object", objectId]`). Clicking "Propose Fix" on an AI suggestion generates a Proposed Action inline in the detail panel rather than navigating away. Bulk-selecting rows and choosing a bulk action (e.g. "Disable selected") produces one Proposed Action covering all selected objects, with the diff listing each affected object.

**States.** Empty: "No Active Directory connection configured" card with a CTA to Settings > Integrations if AD isn't connected yet; if connected but a search returns nothing, a simple "No results for '{term}'" inline message. Loading: tree/table `Skeleton` rows; detail panel shows `Skeleton` cards while an object loads. Error: `Alert` if the AD connector is unreachable, with the last successful sync timestamp shown for context.

**Approval-gate touchpoints.** Every AD write (disable/enable account, group membership change, OU move, password reset, attribute edit) is mutating and is never applied directly. It always surfaces as a Proposed Action card with a full before/after attribute diff, an Impact tab (number of objects, downstream group/GPO effects), and a risk `Badge` (e.g. disabling a single stale user = Low, removing a user from Domain Admins = High). "Approve & Run" is enabled only for roles meeting the risk threshold: Operator for Low/Medium, OrgAdmin/SuperAdmin for High/Critical (privileged group changes, bulk operations above a configurable object-count threshold always escalate to at least OrgAdmin). Rejecting requires a reason (`Textarea` in the `AlertDialog`) which is written to `AuditLogs`.

---

## Group Policy

**Purpose.** Let admins review existing GPOs, detect conflicts/redundancies across the domain, and safely edit or create policies with a diff-based preview before linking or modifying anything.

**Layout.** Left nav + top bar; main content is a `Table` list of GPOs (Name, Linked OUs count, Status, Conflict `Badge`, Last Modified) with a detail view opening in a `Sheet` or full-width panel below the table on row click. A dedicated "Diff Viewer" `Dialog`/`Sheet` for proposed changes.

**Key components.**
- **GPO list table**: rows with a **conflict `Badge`** (e.g. "2 conflicts") when the AI detects overlapping/contradictory settings across linked GPOs; hovering or clicking the badge opens a small `Popover` summarizing the conflicting settings.
- **GPO detail panel**: settings tree (`Collapsible` groups: Computer Configuration / User Configuration), linked OUs list, security filtering, and a version/history timeline.
- **Diff viewer**: side-by-side or unified diff (`Tabs`: "Side-by-side", "Unified") showing current settings vs. proposed settings for any AI-suggested or admin-drafted change, with changed lines highlighted (added/removed/modified using semantic color tokens, not just red/green hard-coded).
- **Conflict resolution card**: when opening a conflicted GPO, a `Card` explains which other GPO(s) it conflicts with and offers an AI-suggested resolution as a Proposed Action.
- **New/Edit GPO form**: `Form` (react-hook-form + zod) for setting values, always produces a draft that must go through the Proposed Action/diff flow rather than saving directly to the domain.

**Primary interactions.** Selecting a GPO loads its detail (`["gpo", gpoId]`) and settings tree lazily. Editing a setting opens the diff viewer showing exactly what will change; the admin can iterate on the draft (which stays client-side/draft-persisted) before submitting for approval. Clicking a conflict badge can jump directly to the conflicting GPO for comparison. `audit.appended` and `approval.resolved` events update the GPO's history timeline live if another admin approves/rejects a pending change concurrently.

**States.** Empty: "No Group Policy Objects found" (if AD/GPO connector has nothing indexed yet) with a re-sync CTA. Loading: table `Skeleton` rows; detail panel `Skeleton` for the settings tree. Error: `Alert` banner if the GPO connector sync fails, with last successful sync time.

**Approval-gate touchpoints.** This is a primary approval-gated page. Any GPO create, edit, link, unlink, or delete renders as a Proposed Action with the full diff viewer (current vs. proposed settings, affected linked OUs, estimated affected computer/user count as the "Impact" tab) and a risk `Badge` (editing a setting on a GPO linked to a single test OU = Low/Medium; editing a GPO linked at the domain root, or one affecting security/password policy = High/Critical). "Approve & Run" applies the change via the AD/GPO connector only after explicit approval; "Reject" requires a reason. Operator may approve Low/Medium-risk GPO changes on OUs they are scoped to; OrgAdmin/SuperAdmin required for High/Critical or domain-root-linked GPOs. Viewer/Auditor are read-only and can view the diff and history but never see enabled approval controls.

---

## Monitoring

**Purpose.** Give admins a deep, cross-fleet view of performance telemetry (CPU, memory, disk, network, and service-level metrics) to spot trends and feed root-cause analysis, going beyond the Dashboard's summary.

**Layout.** Left nav + top bar; a filter bar (server multi-`Combobox`, metric `Select`, time-range `Select`/date picker) above a grid of chart `Card`s, plus a `Tabs` switch between "Overview" (fleet-wide aggregates) and "Compare" (overlay multiple servers on the same chart for side-by-side comparison).

**Key components.**
- **Metric chart cards**: line/area charts per metric (CPU %, memory %, disk I/O, network throughput), each with its own time-range override, hover tooltips, and a threshold line for configured alert thresholds.
- **Comparison view**: same chart types but with a legend keyed by server (multi-select `Combobox` picks up to N servers), consistent color-by-series per the dataviz color conventions.
- **Anomaly markers**: annotated points on charts where the AI flagged an anomaly, clicking a marker opens a `Popover` with a short explanation and a "Investigate with AI" button.
- **Top offenders table**: a `Table` ranking servers by a chosen metric (e.g. highest sustained CPU) over the selected window, each row linking to that server's detail page.

**Primary interactions.** Changing filters re-queries React Query (`["metrics", metric, servers, range]`) with sensible caching so scrubbing the time range feels instant for cached windows. Live metrics stream in via Socket.IO for the "last N minutes" view, appending new points to the chart without a full refetch. Clicking "Investigate with AI" on an anomaly opens the floating AI Chat `Sheet` pre-loaded with that anomaly's context (server, metric, time window).

**States.** Empty: "No metrics available yet, agents may still be reporting in" card if a server was just onboarded. Loading: chart-shaped `Skeleton` blocks (rectangle with a shimmer, matching each `Card`'s final chart area). Error: per-chart `Alert` if that metric's query fails, without blocking other charts on the page.

**Approval-gate touchpoints.** Monitoring is read-only telemetry; it triggers no direct mutating actions. Any remediation suggested from an anomaly routes through AI Chat's or Automation's approval flow rather than acting from this page.

---

## Security

**Purpose.** Give security-focused admins and auditors one place to review vulnerability findings, compliance posture, credential/vault health, and the audit trail of every action taken through the platform.

**Layout.** Left nav + top bar; top-level `Tabs`: "Posture" (overview), "Vulnerabilities", "Compliance", "Audit Log". Posture uses a `Card` grid with score/status gauges; the other tabs use filterable `Table`s.

**Key components.**
- **Posture tab**: security score `Card` (with trend), risk-category breakdown (donut/bar per the dataviz conventions), and a "Top risks" list.
- **Vulnerabilities tab**: `Table` of findings (CVE, affected server, severity `Badge`, status: Open/Acknowledged/Remediated), with a detail `Sheet` per finding including an AI-suggested remediation script that hands off to Scripts.
- **Compliance tab**: framework `Tabs` or `Select` (e.g. CIS, custom baseline), a `Table` of controls with pass/fail `Badge` and drill-down evidence.
- **Audit Log tab**: the canonical view over `AuditLogs`, a dense `Table` (Timestamp, Actor, Action, Target, Result, Org) with powerful filters (`Combobox` for actor/action type, date range) and CSV/PDF export, primarily used by Auditor and OrgAdmin/SuperAdmin roles.
- **Credential vault health card**: shows vaulted credential count, rotation status, and any expiring-soon warnings, without ever displaying secret values.

**Primary interactions.** Tab switches lazily load data per tab (`["security", tab, filters]`). Clicking a vulnerability finding opens its detail `Sheet`; "Generate Fix" routes to Scripts with the finding's context pre-filled. Audit Log rows can be expanded inline (`Collapsible` row) to show the full before/after payload of that action. `audit.appended` Socket.IO events prepend new rows to the Audit Log tab live when it's the active tab.

**States.** Empty: "No vulnerabilities detected yet" positive-framed empty state (with a green check illustration) for the Vulnerabilities tab when clean; "No audit events yet" for a brand-new org. Loading: `Skeleton` gauges on Posture, `Skeleton` table rows elsewhere. Error: `Alert` with retry per tab; Audit Log failures are called out prominently since it's compliance-critical data, showing a distinct warning-styled `Alert` rather than the generic error style.

**Approval-gate touchpoints.** Security Center itself doesn't originate mutating actions directly, "Generate Fix" and any remediation always exit into Scripts/AI Chat's Proposed Action flow. The Audit Log tab is the durable record of every approval decision made anywhere in the product (who approved/rejected, when, and why), and is visible in full to Auditor, OrgAdmin, and SuperAdmin; Operator sees only audit entries for actions within their scope; Viewer has no access to this tab.

---

## Automation

**Purpose.** Let admins build, schedule, and monitor multi-step automation workflows (chains of diagnostics, script runs, and notifications) that still stop for human approval at every mutating step.

**Layout.** Left nav + top bar; a `Table` list of workflows (Name, Trigger type, Last Run status `Badge`, Owner) as the landing view, with "Create Workflow" opening a builder in a dedicated route (`/automation/[id]/edit`) using a node-based or step-list canvas, plus a separate "Runs" `Tabs` view for execution history.

**Key components.**
- **Workflow list table**: status `Badge` (Active/Paused/Draft), next scheduled run (if time-triggered), a `DropdownMenu` per row (Run now, Pause, Duplicate, Delete).
- **Workflow builder**: an ordered step list (drag-to-reorder) where each step is a `Card` representing a diagnostic, a script run, a conditional branch, or a notification; steps that mutate infrastructure are visually marked with a "Requires Approval" `Badge` that cannot be turned off.
- **Run detail view**: a vertical stepper (`Progress`/custom timeline) showing each step's status (Pending/Running/Awaiting Approval/Completed/Failed) updated live via `task.progress` Socket.IO events, with expandable step output.
- **Proposed Action card (inline in run detail)**: appears exactly at the step awaiting approval, pausing the workflow run until resolved.
- **Schedule/trigger config**: `Form` with `Select` for trigger type (Manual, Schedule/cron via a friendly recurrence picker, Alert-triggered) and target scope (`Combobox` of servers/groups/tags).

**Primary interactions.** Creating/editing a workflow auto-saves the draft (debounced) via React Query mutation; "Run now" or hitting a schedule enqueues a workflow run and opens the run detail view, which joins a `task:{id}` Socket.IO room for live step updates. When a step requiring approval is reached, the run visibly pauses ("Awaiting Approval" `Badge` pulses) and the Proposed Action card renders inline; approving resumes the run, rejecting marks the run as stopped/failed at that step with the rejection reason recorded.

**States.** Empty: "No automation workflows yet" card with "Create your first workflow" CTA and 2-3 template suggestions (e.g. "Nightly disk cleanup", "Weekly patch compliance check"). Loading: `Skeleton` rows for the list; run detail shows a `Skeleton` stepper while the run's step list loads. Error: `Alert` on the list if workflows fail to load; within a run, a failed step shows a distinct red step state with the error output expandable, without blocking visibility into prior/later steps.

**Approval-gate touchpoints.** This page is a primary approval surface. Every workflow step classified as mutating (script execution, service restart, GPO/DNS/DHCP/AD changes invoked as a step) pauses the run and renders the same Proposed Action card pattern (diff/preview, risk `Badge`, Approve & Run/Reject) used elsewhere; a workflow can never be configured to skip this gate, "Requires Approval" is not a toggle. `approval.requested` events notify all users with an approver-capable role via the notification bell; `approval.resolved` resumes or halts the run. RBAC: Operator can approve Low/Medium-risk steps within workflows they own or are scoped to; OrgAdmin/SuperAdmin can approve any step; Viewer/Auditor can watch run progress read-only.

---

## Scripts

**Purpose.** The unified home for generating PowerShell and Bash scripts from natural language, browsing/reusing the vetted Script Library, and running any script against target servers, always ending in a human-approved execution.

**Layout.** Left nav + top bar; top-level `Tabs`: "Generate" (composer for new scripts), "Library" (browse/search existing scripts), "Runs" (execution history). "Generate" is a split view: left composer, right live-generated script with syntax highlighting.

**Key components.**
- **Generate tab**: a `Textarea` composer ("Describe the task..."), a `Select` for target language (PowerShell/Bash, often auto-suggested by target OS) and target server(s) (`Combobox`), and a streaming code preview panel (tokens stream in as the AI generates, using the same streaming pattern as AI Chat) with `Tabs` for "Script" vs. "Explanation".
- **Library tab**: a searchable/filterable `Table` (Name, Language `Badge`, Category, Last Used, Approval history count), a detail `Sheet` per script showing full source with version history, and a "Run" button.
- **Runs tab**: `Table` of past executions (Script, Target(s), Triggered by, Status `Badge`, Duration), each row opening a run detail view with full stdout/stderr in a `ScrollArea` code block, updated live via Socket.IO while running.
- **Proposed Action card**: appears whenever a generated or library script is about to run, showing the full script body (`Tabs`: "Script", "Target Impact"), the target list, and a risk `Badge` derived from static analysis of the script's operations.

**Primary interactions.** Submitting the Generate composer streams the script into the preview panel token-by-token (Socket.IO or streaming HTTP, consistent with AI Chat's approach) and, once complete, offers "Save to Library" and "Run" actions. Clicking "Run" (from Generate or Library) always opens the Proposed Action card first; it never executes on click. Approving triggers execution via the execution worker and the Runs tab's live view opens automatically, following `task.progress` events until `task.completed`/`task.failed`.

**States.** Empty: Library tab shows "No scripts saved yet" with a CTA to generate one; Runs tab shows "No scripts have been run yet". Loading: `Skeleton` for the streaming preview area before generation starts is a simple pulsing placeholder distinct from the token-streaming state (so users don't confuse "waiting to start" with "actively streaming"). Error: if generation fails, an inline `Alert` in the preview panel with "Try again"; if a run fails, the Runs table row shows a Failed `Badge` and the run detail shows the captured error output.

**Approval-gate touchpoints.** This is a primary approval surface, identical pattern to the other gated pages. No script, generated or from the Library, executes without an explicit "Approve & Run" on its Proposed Action card, which always shows the exact script body, the resolved target list, and a risk `Badge` (e.g. a read-only diagnostic script may be classified Low even here, while anything with delete/stop/restart/registry-write operations is Medium or higher). Operator approves Low/Medium; OrgAdmin/SuperAdmin required for High/Critical or for scripts targeting more than a configurable number of servers at once. Rejected runs and their reasons are written to `AuditLogs` and visible in Security Center's Audit Log tab.

---

## Reports

**Purpose.** Let admins and auditors generate, schedule, and export point-in-time or recurring reports (compliance posture, performance trends, alert/incident summaries, automation activity) for stakeholders outside the day-to-day console.

**Layout.** Left nav + top bar; a `Table` of saved/scheduled reports as the landing view, with "New Report" opening a builder `Dialog`/`Sheet` (template `Select`, scope filters, schedule options), and a preview pane for generated output.

**Key components.**
- **Report list table**: Name, Type (Compliance/Performance/Security/Automation Activity), Last Generated, Schedule (`Badge`: Manual/Daily/Weekly/Monthly), Actions (`DropdownMenu`: View, Regenerate, Edit schedule, Delete).
- **Report builder**: `Form` with a template gallery (`Card` grid of report types), scope filters (org/site/server-group/tag `Combobox`, date range), and output format (`Select`: PDF, CSV, on-screen dashboard).
- **Report preview/viewer**: rendered report content (charts and tables reusing the same dataviz components as Monitoring/Security) inside a scrollable panel, with "Download" and "Share link" actions.
- **Schedule config**: recurrence picker (`Select` + `Form` fields) and a recipient list (`Combobox` of org users or external email) for auto-delivery.

**Primary interactions.** Choosing a template and scope in the builder generates a preview on submit (React Query mutation, since it may take a few seconds for larger reports, shown with a `Progress` indicator). Saving a report with a schedule creates a recurring job; subsequent runs appear automatically in the list as new "Last Generated" entries, with the notification bell surfacing completion. Clicking "View" opens the latest generated instance in the preview pane; "Download" streams the PDF/CSV.

**States.** Empty: "No reports yet" card with template suggestions as quick-start CTAs. Loading: `Skeleton` rows for the list; the preview pane shows a `Skeleton` layout matching a generic report shape (header block + a few chart/table placeholders) while generating. Error: `Alert` in the builder if generation fails (e.g. no data in the selected range), with guidance to adjust filters; list-level fetch errors use the standard retry `Alert`.

**Approval-gate touchpoints.** Report generation and scheduling are read-only over existing data and do not mutate infrastructure, so no approval gate applies. Reports may, however, surface links back into pages that do require approval (e.g. a compliance report linking to an open Security Center finding whose fix routes through Scripts).

---

## Settings

**Purpose.** Central administration for the organization: users and roles, authentication/SSO configuration, integrations/connectors (AD, hypervisors, cloud accounts, credential vault), notification preferences, and org-level policies.

**Layout.** Left nav + top bar; Settings uses its own secondary left sub-navigation (a narrower `Sidebar`-style list within the content area, or a `Tabs` rail) with sections: "Profile", "Users & Roles", "Organization", "Authentication", "Integrations", "Notifications", "Credential Vault", "Audit & Compliance" (deep-links into Security Center's Audit Log for convenience).

**Key components.**
- **Users & Roles**: `Table` of org members (Name, Email, Role `Badge`, Status: Active/Invited/Disabled, Last Login), "Invite User" `Dialog` (email + role `Select`), row `DropdownMenu` for role change/disable/remove.
- **Authentication**: `Form` for SSO/SAML/OIDC configuration, MFA enforcement toggle, session timeout settings; sensitive fields (client secrets) use masked `Input` with a reveal-on-focus pattern and are never echoed back in full from the API.
- **Integrations**: `Card` grid, one per connector type (Active Directory, VMware vCenter, Hyper-V, AWS/Azure/GCP, ticketing), each showing connection status `Badge` and a "Configure"/"Test Connection" action.
- **Credential Vault**: `Table` of stored credentials (Name, Type, Linked to (server/connector), Rotation status), "Add Credential" `Dialog`, values are always write-only in the UI.
- **Notifications**: preference toggles (`Switch`) per event category (alerts, approvals, audit) and per channel (in-app, email), scoped to the current user.
- **Organization**: org profile fields (name, logo, default time zone), org switcher management (for SuperAdmin managing multiple orgs).

**Primary interactions.** Each section is its own React Query-backed form (`["settings", section]`), saved via `useMutation` with `Toast` confirmation on success. Inviting a user sends an invite and adds an "Invited" row optimistically, reconciled on the real response. Testing an integration connection shows a `Progress`/spinner inline on the card and resolves to a success/failure `Badge` without a full page reload.

**States.** Empty: "No integrations configured" state per connector category before first setup; "No custom credentials stored" for a fresh vault. Loading: `Skeleton` forms/tables per section, loaded independently since Settings sections are rarely all needed at once. Error: inline field-level validation errors (via `zod` + `react-hook-form`) for form submissions; connector test failures show a red `Badge` plus an expandable error detail rather than a blocking page error.

**Approval-gate touchpoints.** Settings changes (role changes, SSO config, integration credentials) are administrative rather than infrastructure-mutating and are gated by RBAC (only OrgAdmin/SuperAdmin can access Users & Roles, Authentication, and Integrations; Operator/Viewer/Auditor have no write access here, Auditor may have read-only visibility into Users & Roles and Audit & Compliance for review purposes) rather than by the Proposed Action approval flow used for infrastructure changes. Role changes and credential additions/rotations are still fully recorded in `AuditLogs`.

---

## Alerts

**Purpose.** The operational triage queue: every alert generated by monitoring, log analysis, or security scanning across the fleet, so admins can see what's actively wrong, acknowledge it, and jump straight to remediation.

**Layout.** Left nav + top bar; a dense `Table` as the primary view with a persistent filter bar (`Select` for severity/status, `Combobox` for server/tag, search `Input`), and a detail `Sheet` on row click. A `Tabs` or `Select` toggle for "Active" vs. "Acknowledged" vs. "Resolved" vs. "All".

**Key components.**
- **Alert table**: Severity `Badge` (Info/Warning/Critical), Title, Server, Source module (Monitoring/Security/Event Log), Age, Status `Badge`, quick actions (`DropdownMenu`: Acknowledge, Assign, Snooze).
- **Alert detail `Sheet`**: full context (metric graph or log excerpt that triggered it), related alerts on the same server, an "Investigate with AI" button, and a timeline of status changes.
- **Bulk triage bar**: on multi-select, bulk-acknowledge or bulk-assign.
- **Severity summary strip**: small counts row above the table (Critical/Warning/Info counts) that double as quick filters when clicked.

**Primary interactions.** New alerts appear at the top of the table in real time via `alert.created` Socket.IO events (React Query cache is patched directly for a snappy "new row slides in" effect, with a brief highlight animation). Acknowledging or assigning is an optimistic mutation (`useMutation` with immediate local state update, rolled back on failure). Clicking "Investigate with AI" opens the floating AI Chat `Sheet` pre-loaded with the alert's context, letting the AI propose a root cause and, if applicable, a remediation script.

**States.** Empty: a calm, positive "No active alerts, everything's healthy" state (green check illustration) rather than a generic empty table. Loading: `Skeleton` table rows including a skeleton `Badge` shape for severity. Error: standard retry `Alert`; if the live Socket.IO connection drops, a small non-blocking `Badge` ("Live updates paused, reconnecting...") appears near the table header rather than a full error state, since cached data is still valid to view.

**Approval-gate touchpoints.** Acknowledging, assigning, and snoozing alerts are triage actions, not infrastructure mutations, so they are not gated by the approval flow (any role with at least Operator-level access can acknowledge; Viewer can view but not acknowledge). Any remediation action taken from an alert (via "Investigate with AI" or a suggested fix) routes into AI Chat's or Scripts' Proposed Action flow before anything runs.

---

## AI Chat

**Purpose.** The conversational entry point for the whole platform: an admin describes a problem or asks a question in natural language, the AI investigates across modules, explains its reasoning, and, if a fix is warranted, proposes an action for explicit human approval before anything executes.

**Layout.** Left nav + top bar; a two-pane layout: a left `Sidebar`-style conversation list (past `AIConversations`, `ScrollArea` + search) and a right main pane with the active message thread (`ScrollArea`) and a fixed composer at the bottom. The same thread UI is reused inside the floating `Sheet` launcher available on other pages, just without the conversation list pane.

**Key components.**
- **Conversation list**: `Table`-free list of past conversations (title auto-summarized, last message preview, relative time), "New Chat" button at the top, `Command`-style search across conversation history.
- **Message thread**: user messages and AI messages as distinct bubble styles; AI messages render **streaming tokens** (progressive text render as the model generates, consistent with the Scripts page's generation preview) and can include rich inline content: a metric chart, a log excerpt block, or a **Proposed Action card**.
- **Proposed Action card (inline in the thread)**: exactly the shared pattern described in the intro, a summary line, risk `Badge` (Low/Medium/High/Critical), an expandable diff/script preview (`Tabs`: "Diff"/"Script", "Impact"), and "Approve & Run"/"Reject" buttons docked to the card. Multiple proposed actions in one conversation each render as their own card and are tracked independently.
- **Task progress inline block**: once approved, the same message thread shows a live progress block (`Progress` bar plus streaming step log) fed by `task.progress` Socket.IO events, transitioning to a completed/failed summary block on `task.completed`/`task.failed`.
- **Composer**: multi-line `Textarea` with an attach-context chip row (e.g. "Server: WEB-01" chip when opened from a scoped launcher), a `Select` for advanced options (e.g. preferred script language), and a send `Button` (disabled while a response is streaming, with a stop/interrupt control).
- **Context chips**: above the composer, removable `Badge` chips showing what context is attached to the next message (a server, an alert, a GPO), populated automatically when AI Chat is opened from another page.

**Primary interactions.** Sending a message posts to the backend which creates/continues an `AIConversation`/`AIMessage`, and the response streams back token-by-token over Socket.IO (or SSE) into a new AI message bubble. If the AI's investigation concludes a fix is needed, the response includes a Proposed Action card rather than free text describing the fix in prose alone. Clicking "Approve & Run" opens a final confirmation only for High/Critical risk actions (`AlertDialog`, "This will restart 3 production servers, continue?"); Low/Medium risk actions execute immediately on click since the card itself already served as the preview. Clicking "Reject" opens an `AlertDialog` for an optional reason, which is stored and shown to the AI as feedback for the rest of the conversation. Switching conversations in the left list swaps the thread pane's React Query key (`["conversation", id]`) and re-joins that conversation's Socket.IO room if a task within it is still running.

**States.** Empty: a fresh "New Chat" shows a centered composer with a few suggested prompts ("Why is WEB-01's CPU spiking?", "Generate a script to rotate IIS logs") rather than a blank thread. Loading: opening an existing conversation shows `Skeleton` message bubbles (alternating short/long shimmer blocks) while history loads; a new AI response being generated shows a small animated "thinking" indicator (three-dot pulse) before the first token streams in. Error: if generation fails mid-stream, the partial AI message is preserved with an inline `Alert` ("Response interrupted, retry?") and a retry button that resumes rather than restarting the whole conversation; if the Socket.IO connection drops mid-stream, the composer disables with a reconnecting indicator and re-enables automatically on reconnect.

**Approval-gate touchpoints.** AI Chat is the most frequent origin point for proposed actions across every module (AD changes, GPO edits, script runs, IIS/DNS/DHCP edits, service restarts) and always uses the shared Proposed Action card, no action the AI recommends is ever auto-executed from a chat response, regardless of how confident the AI's language sounds. Risk classification and RBAC gating are identical to the owning module's rules described above (e.g. an AD group-membership fix proposed in chat follows Active Directory's risk/role rules, a script proposed in chat follows Scripts' rules); AI Chat itself does not introduce a separate, looser approval standard. Every approval or rejection made from within a chat is written to `AuditLogs` and reflected back into the owning module's own history (e.g. an approved GPO change from chat also appears in the Group Policy page's version timeline), so there is one consistent audit trail regardless of where the approval happened.
