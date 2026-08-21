import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import AccessTokenClaims, require_permission
from app.dependencies import get_org_db
from app.modules.ai_chat import service
from app.modules.ai_chat.schemas import ConversationOut, CreateConversationRequest, MessageOut, SendMessageRequest

router = APIRouter(prefix="/api/v1/ai/conversations", tags=["ai-chat"])


@router.post("", response_model=None)
async def create_conversation(
    payload: CreateConversationRequest,
    user: AccessTokenClaims = Depends(require_permission("ai_chat.use")),
    db: AsyncSession = Depends(get_org_db),
):
    conversation = await service.create_conversation(
        db, organization_id=uuid.UUID(user.organization_id), user_id=uuid.UUID(user.user_id),
        title=payload.title, module_context=payload.module_context,
    )
    return {"data": ConversationOut.model_validate(conversation)}


@router.get("", response_model=None)
async def list_conversations(
    user: AccessTokenClaims = Depends(require_permission("ai_chat.use")),
    db: AsyncSession = Depends(get_org_db),
):
    conversations = await service.list_conversations(
        db, organization_id=uuid.UUID(user.organization_id), user_id=uuid.UUID(user.user_id)
    )
    return {"data": [ConversationOut.model_validate(c) for c in conversations]}


@router.get("/{conversation_id}", response_model=None)
async def get_conversation(
    conversation_id: uuid.UUID,
    user: AccessTokenClaims = Depends(require_permission("ai_chat.use")),
    db: AsyncSession = Depends(get_org_db),
):
    conversation = await service.get_conversation(db, organization_id=uuid.UUID(user.organization_id), conversation_id=conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "Conversation not found."})
    messages = await service.list_messages(db, conversation_id=conversation_id)
    return {
        "data": {
            "conversation": ConversationOut.model_validate(conversation),
            "messages": [MessageOut.model_validate(m) for m in messages],
        }
    }


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: uuid.UUID,
    payload: SendMessageRequest,
    user: AccessTokenClaims = Depends(require_permission("ai_chat.use")),
):
    """Combines "send message" and "stream" into one request (MVP
    simplification of docs/05-api-design.md Section 11's two-endpoint split —
    see the implementation plan). Manages its own DB session rather than using
    the get_org_db Depends(), because FastAPI closes generator dependencies
    right after the endpoint returns the StreamingResponse object, before the
    stream body itself has actually been sent — a session opened via Depends
    would be closed out from under the generator mid-stream.
    """
    organization_id = uuid.UUID(user.organization_id)
    user_id = uuid.UUID(user.user_id)

    async def event_stream():
        async with SessionLocal() as db:
            await db.execute(
                text("SELECT set_config('app.current_org_id', :org_id, true)"), {"org_id": str(organization_id)}
            )
            conversation = await service.get_conversation(db, organization_id=organization_id, conversation_id=conversation_id)
            if conversation is None:
                yield f"event: error\ndata: {json.dumps({'message': 'Conversation not found.'})}\n\n"
                return
            async for event in service.stream_message(
                db, organization_id=organization_id, user_id=user_id, conversation_id=conversation_id,
                content=payload.content,
            ):
                yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
