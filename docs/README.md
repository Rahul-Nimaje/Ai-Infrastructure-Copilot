# AI Infrastructure Copilot — Documentation

Enterprise blueprint for an AI-powered assistant that lets Windows/Linux/Cloud/
Virtualization administrators monitor, troubleshoot, automate, and manage
infrastructure using natural language.

## Mission

Understand an organization's infrastructure and perform troubleshooting,
monitoring, automation, reporting, and administrative tasks across Windows,
Linux, Cloud, and Virtualization platforms, always keeping a human in the loop
before any mutating action executes, and a full audit trail behind everything.

## Canonical reference

These names are used consistently across every document below. If a new
document introduces a module, agent, or entity not listed here, this section
must be updated first.

**20 product modules**: Authentication, Infrastructure Inventory, Active
Directory Management, Group Policy Management, Windows Event Log Analyzer,
IIS Copilot, DNS Manager, DHCP Manager, Performance Analyzer, PowerShell
Generator, Bash Script Generator, Script Library, Server Health Dashboard,
Alert Center, Security Center, AI Chat, Automation Workflows, VMware
Management, Hyper-V Management, Cloud Management.

**15 AI agents**: Infrastructure, Windows, Linux, Cloud, Active Directory,
PowerShell, Security, Network, VMware, Hyper-V, Automation, Reporting,
Planner, Memory, Coordinator.

**Core DB entities**: Organizations, Users, Roles, Permissions, Servers,
Devices, Credentials (vaulted), Scripts, Tasks, AutomationJobs, Workflows,
Policies, Alerts, Events, Logs, Reports, AuditLogs, AIConversations,
AIMessages, InfrastructureInventory, Notifications.

**AI workflow**: User Prompt → Planner → Agent Selection → Tool Calling →
Data Collection → Reasoning → Root Cause Analysis → Recommendation → Script
Generation → Human Approval → Execution (via WinRM/SSH) → Audit Log.

**Backend**: FastAPI as the single backend service.

**LLM layer**: provider-agnostic interface supporting both OpenAI API and a
local model (Llama/Qwen/Mistral via vLLM/Ollama), selectable per deployment.

**Execution safety**: every mutating action (GPO change, script execution,
service restart) requires explicit human approval; read-only diagnostics may
auto-run.

## Table of contents

| # | Document | Covers |
|---|----------|--------|
| 01 | [SRS](01-SRS.md) | Software Requirement Specification |
| 02 | [HLD](02-HLD.md) | System architecture, deployment topology, HA/DR |
| 03 | [LLD](03-LLD.md) | Per-module low-level design (all 20 modules) |
| 04 | [Database Design](04-database-design.md) | Full PostgreSQL schema + ER diagram |
| 05 | [API Design](05-api-design.md) | REST API spec per domain |
| 06 | [AI Architecture](06-ai-architecture.md) | Multi-agent design, LangGraph, RAG, MCP |
| 07 | [Security Architecture](07-security-architecture.md) | RBAC, MFA, vault, audit, zero trust |
| 08 | [Deployment Guide](08-deployment-guide.md) | Docker/K8s/Terraform/CI-CD |
| 09 | [Monitoring & Observability](09-monitoring-observability.md) | Prometheus/Grafana/OTel/ELK/Loki |
| 10 | [UI/UX Design](10-ui-ux-design.md) | Every application page |
| 11 | [Folder Structure](11-folder-structure.md) | Repo layout |
| 12 | [Coding Standards](12-coding-standards.md) | Conventions per language/framework |
| 13 | [Microservice Breakdown](13-microservice-breakdown.md) | Service boundaries |
| 14 | [Test Plan](14-test-plan.md) | Unit/integration/e2e + AI-agent eval strategy |
| 15 | [Roadmap](15-roadmap.md) | Phased delivery plan (MVP → GA) |
| 16 | [Checklists](16-checklists.md) | Deployment + production-readiness checklists |
| 17 | [Future Enhancements](17-future-enhancements.md) | Post-GA ideas, incl. deferred user/admin manuals |

## Status

All 18 documents above are complete. `user-manual.md` and `admin-manual.md` are
intentionally not written yet; see [17-future-enhancements.md](17-future-enhancements.md)
for why they're deferred until Phase 1 (MVP) ships against real screens.

A cross-document consistency pass has been run: the 20 modules, 15 agents, and core DB
entities are named identically everywhere they're referenced (the one drift found during
review — `03-LLD.md` initially inventing its own 15-agent names — was corrected to match
this canonical reference).
