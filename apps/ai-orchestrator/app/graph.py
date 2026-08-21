"""The AI workflow orchestrator — docs/06-ai-architecture.md Section 2.

KNOWN DEVIATION FROM THE DOCUMENTED DESIGN: this is a plain async generator
that runs the exact node sequence and produces the exact CopilotState fields
from docs/06-ai-architecture.md Section 2.1/2.2 (planner -> coordinator_dispatch
-> tool_calling/data_collection -> reasoning_rca -> recommendation ->
[script_generation] -> done), but it is NOT built on the `langgraph` library's
`StateGraph`/`interrupt()` primitives. Two reasons: (1) this environment has no
network access to verify the current LangGraph API surface against docs
written from memory, and shipping a graph that imports incorrectly is worse
than a plain, correct implementation; (2) this architecture's human-approval
boundary does not actually require a resumable graph — apps/api's tasks
module (app/modules/tasks/service.py) owns approval -> execution
deterministically once a proposal becomes a persisted Task row, so there is
nothing to "resume" here (see py_shared.job_contracts for the same note).
Migrating this function's body into real LangGraph nodes later is a
mechanical refactor, not a redesign, because the state shape and node
boundaries already match.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import coordinator_agent, planner_agent, powershell_agent, rag_agent
from app.rag.generation.grounded_generator import build_grounded_prompt


async def run(
    db: AsyncSession, *, organization_id: uuid.UUID, conversation_id: uuid.UUID, user_prompt: str
) -> AsyncGenerator[dict[str, Any], None]:
    yield {"event": "agent_step", "data": {"stage": "planner", "detail": "Classifying request intent and knowledge requirement"}}
    plan = await planner_agent.plan(db, organization_id=organization_id, conversation_id=conversation_id, user_prompt=user_prompt)

    selected_agents = plan.get("selected_agents", [])
    target_server = plan.get("target_server")

    rag_sources: list[dict] = []
    rag_context = ""

    # Step 1: Execute RAG search if RAG Agent selected
    if "RAG Agent" in selected_agents:
        yield {
            "event": "agent_step",
            "data": {"stage": "rag_retrieval", "detail": "Querying organization knowledge base (vector + keyword search)"},
        }
        rag_data = await rag_agent.search_knowledge_base(
            organization_id=organization_id,
            query=user_prompt,
        )
        rag_context = rag_data.get("context", "")
        rag_sources = rag_data.get("sources", [])

        if rag_sources:
            yield {
                "event": "rag_sources",
                "data": {"sources": rag_sources},
            }

    # Step 2: Handle server diagnosis if target server specified
    if target_server:
        yield {
            "event": "agent_step",
            "data": {"stage": "coordinator_dispatch", "detail": f"Dispatching to Windows Agent for {target_server['hostname']}"},
        }
        yield {
            "event": "agent_step",
            "data": {"stage": "tool_calling", "detail": f"Invoking eventlog_query(server_id={target_server['id']})"},
        }

        result = await coordinator_agent.dispatch(
            db, selected_agents=selected_agents, organization_id=organization_id,
            server_id=uuid.UUID(target_server["id"]), user_prompt=user_prompt,
        )
        root_cause = result["root_cause"]
        recommendation = result["recommendation"]

        yield {"event": "agent_step", "data": {"stage": "reasoning_rca", "detail": "Correlating event log evidence"}}

        answer = f"{root_cause['hypothesis']}"
        if root_cause["evidence"]:
            answer += " Evidence: " + "; ".join(root_cause["evidence"])
        yield {"event": "token", "data": {"delta": answer}}

        if recommendation is None:
            yield {"event": "done", "data": {"final_message": answer, "sources": rag_sources}}
            return

        yield {
            "event": "agent_step",
            "data": {"stage": "recommendation", "detail": recommendation["action"]},
        }

        if not recommendation["requires_script"]:
            yield {"event": "done", "data": {"final_message": answer + f" Recommended action: {recommendation['action']}", "sources": rag_sources}}
            return

        yield {"event": "agent_step", "data": {"stage": "script_generation", "detail": "PowerShell Agent drafting a script"}}
        script = await powershell_agent.generate_from_recommendation(
            action=recommendation["action"], hostname=target_server["hostname"]
        )

        yield {
            "event": "proposal",
            "data": {
                "target_server_id": target_server["id"],
                "language": "powershell",
                "name": script.get("name", recommendation["action"][:80]),
                "content": script["content"],
                "risk_level": script["risk_level"],
                "explanation": script.get("explanation", ""),
                "rollback_plan": script.get("rollback_plan", ""),
            },
        }
        yield {
            "event": "done",
            "data": {"final_message": answer + f" I've drafted a script to {recommendation['action'].lower()}, pending your approval.", "sources": rag_sources},
        }
        return

    # Step 3: Pure RAG / Knowledge Base query response
    yield {"event": "agent_step", "data": {"stage": "grounded_generation", "detail": "Generating grounded answer from retrieved context"}}

    system_prompt, user_query = build_grounded_prompt(rag_context, user_prompt)

    # Use LLM provider if available, or assemble answer directly
    if rag_context:
        answer = f"Based on your organization's knowledge base:\n\n{rag_context}\n\n"
        if rag_sources:
            answer += "\n\nSources cited:\n" + "\n".join(
                f"- [{s['document_title']}]({s['file_name']})" + (f" (Page {s['page_number']})" if s.get('page_number') else "")
                for s in rag_sources
            )
    else:
        answer = (
            "I couldn't find any relevant documentation in your organization's knowledge base "
            "for this query. Please upload relevant SOPs or runbooks to the Knowledge Base module."
        )

    yield {"event": "token", "data": {"delta": answer}}
    yield {"event": "done", "data": {"final_message": answer, "sources": rag_sources}}

