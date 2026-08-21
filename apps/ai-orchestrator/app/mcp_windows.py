"""`mcp-windows-server` tools — docs/06-ai-architecture.md Section 3, Windows
Agent, and Section 5.2's server topology table.

Plan simplification #6: these are plain async functions with the same
name/schema/`read`-vs-`propose` annotation as the documented MCP tool server,
not a standalone MCP process. `read` tools query Postgres directly (read-only,
same instance as apps/api); no tool here ever opens a WinRM connection to a
customer target — that only happens inside apps/api's execution runner, after
Human Approval, matching the mutation boundary in that doc's Section 5.3.
"""
from __future__ import annotations

import uuid
from typing import Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

ToolAnnotation = Literal["read", "propose"]


async def eventlog_query(
    db: AsyncSession, *, organization_id: uuid.UUID, server_id: uuid.UUID, min_level: str | None = None, limit: int = 25
) -> list[dict]:
    """annotation: read"""
    query = """
        SELECT id, log_channel, event_id, level, source_provider, message, occurred_at
        FROM event_log_entries
        WHERE organization_id = :org_id AND server_id = :server_id
    """
    params: dict = {"org_id": str(organization_id), "server_id": str(server_id)}
    if min_level:
        query += " AND level = :min_level"
        params["min_level"] = min_level
    query += " ORDER BY occurred_at DESC LIMIT :limit"
    params["limit"] = limit
    result = await db.execute(text(query), params)
    return [dict(row._mapping) for row in result.fetchall()]


async def get_server_by_hostname_hint(db: AsyncSession, *, organization_id: uuid.UUID, prompt: str) -> dict | None:
    """annotation: read — Planner's lightweight entity resolution: find a
    server whose hostname is literally mentioned in the prompt. A real
    deployment would use structured-output entity extraction; a substring
    match is a defensible, fully-testable Phase 1 stand-in."""
    result = await db.execute(
        text("SELECT id, hostname, os_type, os_version, health_status FROM servers WHERE organization_id = :org_id AND deleted_at IS NULL"),
        {"org_id": str(organization_id)},
    )
    # `id` comes back as a uuid.UUID from asyncpg; normalize to str here so
    # every downstream consumer (JSON-serialized SSE events, uuid.UUID(...)
    # re-parsing in app/graph.py and app/agents/coordinator_agent.py) can
    # treat this dict's fields as plain JSON-safe values, not driver types.
    servers = [{**dict(row._mapping), "id": str(row._mapping["id"])} for row in result.fetchall()]
    prompt_lower = prompt.lower()
    for server in servers:
        if server["hostname"].lower() in prompt_lower:
            return server
    return servers[0] if len(servers) == 1 else None


async def service_restart(*, service_name: str, target_server_id: uuid.UUID) -> dict:
    """annotation: propose — never contacts the target. Returns the exact
    action description; apps/api turns this into a Scripts/Tasks row via
    app/graph.py's proposal handling, per the mutation boundary in
    docs/06-ai-architecture.md Section 5.3."""
    return {
        "action": f"Restart Windows service '{service_name}'",
        "target_server_id": str(target_server_id),
        "risk_level": "medium",
    }
