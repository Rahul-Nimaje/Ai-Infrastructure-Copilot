"""Coordinator Agent — docs/06-ai-architecture.md Section 3. Sequences/
parallelizes the domain agents the Planner selected and merges their
findings. Phase 1 only ever dispatches to a single domain agent (Windows
Agent), so there is nothing to parallelize yet; this function keeps the same
shape (`dispatch(selected_agents, ...) -> merged collected_data`) so adding
Linux/Active Directory agents in Phase 2 is a fan-out change here, not a
rewrite of the graph."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import windows_agent


async def dispatch(
    db: AsyncSession, *, selected_agents: list[str], organization_id: uuid.UUID, server_id: uuid.UUID | None,
    user_prompt: str,
) -> dict:
    if "Windows Agent" in selected_agents and server_id is not None:
        return await windows_agent.collect_and_diagnose(
            db, organization_id=organization_id, server_id=server_id, user_prompt=user_prompt
        )
    return {
        "collected_data": {},
        "root_cause": {
            "hypothesis": "Could not identify a target server for this request.",
            "confidence": 0.0,
            "evidence": [],
        },
        "recommendation": None,
    }
