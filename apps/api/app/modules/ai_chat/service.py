"""AI Chat module — docs/05-api-design.md Section 11. This is the front door
to the AI workflow: it persists the user's message, calls apps/ai-orchestrator
(app/graph.py) for the diagnosis/proposal, and — because this implementation's
ai-orchestrator never writes to Postgres itself (see that service's
app/graph.py docstring) — turns any `proposal` event into a real Script +
Task row via app/modules/scripts/service.py, so the approval gate (tasks
module) has something real to approve. The AI Chat module never bypasses that
gate; it only creates the pending_approval row and surfaces it.
"""
from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai import AiConversation, AiMessage
from app.modules.scripts import service as scripts_service


async def create_conversation(
    db: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID, title: str | None, module_context: str | None
) -> AiConversation:
    conversation = AiConversation(
        organization_id=organization_id, user_id=user_id, title=title, module_context=module_context,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def list_conversations(db: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID) -> list[AiConversation]:
    result = await db.execute(
        select(AiConversation)
        .where(AiConversation.organization_id == organization_id, AiConversation.user_id == user_id)
        .order_by(AiConversation.last_message_at.desc().nullslast(), AiConversation.created_at.desc())
    )
    return list(result.scalars().all())


async def get_conversation(db: AsyncSession, *, organization_id: uuid.UUID, conversation_id: uuid.UUID) -> AiConversation | None:
    result = await db.execute(
        select(AiConversation).where(
            AiConversation.id == conversation_id, AiConversation.organization_id == organization_id
        )
    )
    return result.scalar_one_or_none()


async def list_messages(db: AsyncSession, *, conversation_id: uuid.UUID) -> list[AiMessage]:
    result = await db.execute(
        select(AiMessage).where(AiMessage.conversation_id == conversation_id).order_by(AiMessage.created_at)
    )
    return list(result.scalars().all())


def _parse_sse(raw: str) -> dict[str, Any] | None:
    event_type, data_line = None, None
    for line in raw.splitlines():
        if line.startswith("event:"):
            event_type = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            data_line = line.removeprefix("data:").strip()
    if event_type is None or data_line is None:
        return None
    return {"event": event_type, "data": json.loads(data_line)}


async def stream_message(
    db: AsyncSession, *, organization_id: uuid.UUID, user_id: uuid.UUID, conversation_id: uuid.UUID, content: str
) -> AsyncGenerator[dict[str, Any], None]:
    user_message = AiMessage(conversation_id=conversation_id, role="user", content=content)
    db.add(user_message)
    await db.flush()
    await db.commit()

    final_message = ""
    referenced_task_id: uuid.UUID | None = None

    async with httpx.AsyncClient(base_url=settings.ai_orchestrator_url, timeout=120.0) as client:
        async with client.stream(
            "POST",
            "/run",
            json={
                "org_id": str(organization_id),
                "conversation_id": str(conversation_id),
                "user_id": str(user_id),
                "user_prompt": content,
            },
        ) as response:
            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    raw_event, buffer = buffer.split("\n\n", 1)
                    event = _parse_sse(raw_event)
                    if event is None:
                        continue

                    if event["event"] == "proposal":
                        proposal = event["data"]
                        script = await scripts_service.create_script(
                            db, organization_id=organization_id, user_id=user_id, name=proposal["name"],
                            language=proposal["language"], category=None, content=proposal["content"],
                            risk_level=proposal["risk_level"], is_ai_generated=True,
                        )
                        task = await scripts_service.request_execution(
                            db, organization_id=organization_id, user_id=user_id, script_id=script.id,
                            target_server_id=uuid.UUID(proposal["target_server_id"]), parameters={},
                        )
                        referenced_task_id = task.id
                        yield {
                            "event": "task_created",
                            "data": {
                                "task_id": str(task.id), "status": task.status, "risk_level": proposal["risk_level"],
                                "summary": proposal["name"], "explanation": proposal["explanation"],
                            },
                        }
                        continue

                    if event["event"] == "done":
                        final_message = event["data"].get("final_message", final_message)

                    yield event

    assistant_message = AiMessage(
        conversation_id=conversation_id, role="assistant", content=final_message,
        referenced_task_id=referenced_task_id, model_used="ai-orchestrator",
    )
    db.add(assistant_message)
    conversation = await get_conversation(db, organization_id=organization_id, conversation_id=conversation_id)
    if conversation is not None:
        conversation.last_message_at = datetime.utcnow()
    await db.commit()
