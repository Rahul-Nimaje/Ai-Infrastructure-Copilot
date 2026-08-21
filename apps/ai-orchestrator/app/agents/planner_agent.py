"""Planner Agent — docs/06-ai-architecture.md Section 3. The graph's entry
point: resolves scope (which server the prompt is about) and short-term
conversation memory. Does not diagnose or recommend."""
from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp_windows import get_server_by_hostname_hint

SYSTEM_PROMPT = (
    "You are the Planner Agent. Given a user's natural-language request, identify the true "
    "intent, the target scope (servers/devices/policies), and which specialist agent(s) are "
    "needed; never invent a diagnosis or fix yourself, only produce a plan. If the request is "
    "ambiguous, ask a clarifying question instead of guessing the scope."
)


async def get_recent_conversation_history(db: AsyncSession, *, conversation_id: uuid.UUID, limit: int = 10) -> list[dict]:
    """Stand-in for the Memory Agent's short-term memory (Phase 4 ships the
    real Memory Agent + pgvector RAG — see plan simplification #5)."""
    result = await db.execute(
        text(
            "SELECT role, content FROM ai_messages WHERE conversation_id = :cid "
            "ORDER BY created_at DESC LIMIT :limit"
        ),
        {"cid": str(conversation_id), "limit": limit},
    )
    rows = [dict(row._mapping) for row in result.fetchall()]
    return list(reversed(rows))


RAG_KEYWORDS = {
    "procedure", "process", "sop", "policy", "how do we", "how to", "backup",
    "configure", "configuration", "troubleshoot", "guideline", "documentation",
    "standard", "restart", "gpo", "group policy", "dns", "dhcp", "iis", "restore",
    "disaster recovery", "checklist", "inventory", "best practice", "company", "internal"
}


async def plan(db: AsyncSession, *, organization_id: uuid.UUID, conversation_id: uuid.UUID, user_prompt: str) -> dict:
    history = await get_recent_conversation_history(db, conversation_id=conversation_id)
    server = await get_server_by_hostname_hint(db, organization_id=organization_id, prompt=user_prompt)

    prompt_lower = user_prompt.lower()
    is_rag_query = any(keyword in prompt_lower for keyword in RAG_KEYWORDS) or "?" in user_prompt

    selected_agents: list[str] = []
    if is_rag_query:
        selected_agents.append("RAG Agent")
    if server:
        selected_agents.append("Windows Agent")

    # Default to general/RAG search if no specific agent selected
    if not selected_agents:
        selected_agents.append("RAG Agent")

    return {
        "history": history,
        "target_server": server,
        "selected_agents": selected_agents,
        "is_rag_query": is_rag_query,
        "plan_summary": (
            f"Diagnose {server['hostname']}" if server else "Retrieve knowledge base information"
        ),
    }

