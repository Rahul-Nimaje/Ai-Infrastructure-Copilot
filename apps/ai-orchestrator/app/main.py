import json
import logging

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.db import SessionLocal
from app.graph import run as run_graph
from app.mcp_scripting import powershell_generate
from py_shared.job_contracts import RunGraphRequest

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Infrastructure Copilot — AI Orchestrator")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/run")
async def run(payload: RunGraphRequest):
    async def event_stream():
        # Opens its own session (rather than depending on get_db()'s single-
        # yield generator via async-for/break) so the session reliably closes
        # exactly when the stream ends — same reasoning as apps/api's
        # app/modules/ai_chat/router.py send_message endpoint.
        try:
            async with SessionLocal() as db:
                async for event in run_graph(
                    db, organization_id=payload.org_id, conversation_id=payload.conversation_id,
                    user_prompt=payload.user_prompt,
                ):
                    yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"
        except Exception:
            # Any failure mid-stream (LLM call error, tool error, etc.)
            # still ends the HTTP response with a well-formed SSE frame
            # rather than dropping the connection — the caller
            # (apps/api's ai_chat/service.py) and the browser both just
            # forward/display whatever event type they receive, so
            # "error" needs no special-casing on either side.
            logger.exception("AI workflow run failed for conversation %s", payload.conversation_id)
            yield f"event: error\ndata: {json.dumps({'message': 'The AI workflow failed unexpectedly. Please try again.'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


class GenerateScriptToolRequest(BaseModel):
    description: str
    language: str = "powershell"


@app.post("/tools/powershell/generate")
async def tools_powershell_generate(payload: GenerateScriptToolRequest):
    """Direct tool call used by apps/api's PowerShell Generator module
    (docs/03-LLD.md Module 10) — not the full diagnosis graph, since a user
    asking for a script directly isn't diagnosing anything."""
    result = await powershell_generate(description=payload.description)
    return result
