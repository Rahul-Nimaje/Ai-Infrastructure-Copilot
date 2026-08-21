"""Windows Agent — docs/06-ai-architecture.md Section 3. Collects Windows
diagnostic data via read-only tools and produces the reasoning/root-cause/
recommendation for the Reasoning-RCA and Recommendation graph steps."""
from __future__ import annotations

import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.provider_interface import get_llm_provider
from app.mcp_windows import eventlog_query

SYSTEM_PROMPT = (
    "You are the Windows Agent. You diagnose Windows Server, IIS, and Event Log issues using "
    "only the read-only tools available to you; you never restart a service, change a registry "
    "value, or modify IIS config directly. When a fix requires a mutating action, describe it "
    "precisely and hand it to the PowerShell Agent to generate a reviewable script.\n\n"
    "Given the event log entries below, respond as JSON with keys: hypothesis, confidence "
    "(0-1 float), evidence (list of short strings citing specific events), action (plain-language "
    "description of the recommended fix, or null if no action is needed), risk_level "
    "(low|medium|high, or null), requires_script (boolean)."
)


async def collect_and_diagnose(
    db: AsyncSession, *, organization_id: uuid.UUID, server_id: uuid.UUID, user_prompt: str
) -> dict:
    events = await eventlog_query(db, organization_id=organization_id, server_id=server_id, limit=25)

    if not events:
        return {
            "collected_data": {"events": []},
            "root_cause": {"hypothesis": "No recent event log data available for this server.", "confidence": 0.0, "evidence": []},
            "recommendation": None,
        }

    events_text = "\n".join(
        f"- [{e['level']}] {e['log_channel']} #{e['event_id']} ({e['occurred_at']}): {e['message']}" for e in events
    )
    provider = get_llm_provider()
    raw = await provider.complete(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=f"User question: {user_prompt}\n\nRecent event log entries:\n{events_text}",
        json_mode=True,
    )
    analysis = json.loads(raw)

    root_cause = {
        "hypothesis": analysis["hypothesis"],
        "confidence": analysis["confidence"],
        "evidence": analysis["evidence"],
    }
    recommendation = None
    if analysis.get("action"):
        recommendation = {
            "action": analysis["action"],
            "risk_level": analysis.get("risk_level") or "medium",
            "requires_script": bool(analysis.get("requires_script")),
        }
    return {"collected_data": {"events": events}, "root_cause": root_cause, "recommendation": recommendation}
