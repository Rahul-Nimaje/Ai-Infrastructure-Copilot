"""PowerShell Agent — docs/06-ai-architecture.md Section 3. Renders a
Recommendation into a concrete, risk-rated script. Only invoked by
app/graph.py when `recommendation.requires_script` is true."""
from __future__ import annotations

from app.mcp_scripting import powershell_generate


async def generate_from_recommendation(*, action: str, hostname: str) -> dict:
    description = f"On Windows Server '{hostname}': {action}"
    return await powershell_generate(description=description)
