"""`mcp-scripting-server` tools — docs/06-ai-architecture.md Section 3,
PowerShell Agent.

Plan simplification: `script_save_draft` (the `propose` tool that persists a
pending_approval Scripts/Tasks row) is NOT implemented here. In this
implementation apps/api is the sole DB writer (see app/graph.py) — the
PowerShell Agent's output here is just content + risk metadata; api's
scripts.service module turns that into the actual Scripts/Tasks rows. The
`read`/`propose` mutation boundary from docs/06-ai-architecture.md Section
5.1 is unaffected: nothing in this module ever contacts a target host.
"""
from __future__ import annotations

import re

from app.llm.provider_interface import get_llm_provider

# docs/14-test-plan.md Section 6.3 static safety gate — dangerous-pattern
# denylist. A real deployment adds PSScriptAnalyzer; this is the Phase 1
# floor, applied to every AI-generated script before it is even eligible
# for the Human Approval queue.
_DANGEROUS_PATTERNS = [
    r"Remove-Item\s+.*-Recurse.*-Force",
    r"Format-Volume",
    r"Remove-LocalUser",
    r"Disable-WindowsOptionalFeature.*Windows-Defender",
    r"Set-MpPreference\s+-DisableRealtimeMonitoring\s+\$true",
    r"Stop-Computer",
    r"Restart-Computer\s+-Force",
    r"New-ADUser|Remove-ADUser|Remove-ADGroup",  # AD mutations must go through Active Directory Agent, not PowerShell Agent, in Phase 2
]

_SYSTEM_PROMPT = (
    "You are the PowerShell Agent. You only ever produce a script and a plain-language "
    "description of exactly what it will change and its risk level; you never run it. "
    "Always include a -WhatIf-safe dry-run path when the target cmdlet supports it. "
    "Respond as JSON with keys: name, content, risk_level (low|medium|high), explanation, rollback_plan."
)


def validate_syntax(content: str) -> tuple[bool, list[str]]:
    """annotation: read. Returns (is_safe, matched_dangerous_patterns)."""
    matches = [p for p in _DANGEROUS_PATTERNS if re.search(p, content, re.IGNORECASE)]
    return (len(matches) == 0, matches)


async def powershell_generate(*, description: str) -> dict:
    """annotation: read (generation itself is inert — docs/03-LLD.md Module 10
    Safety notes: "Generation itself is inert (no target contact) and auto-runs.")"""
    import json

    provider = get_llm_provider()
    raw = await provider.complete(system_prompt=_SYSTEM_PROMPT, user_prompt=description, json_mode=True)
    result = json.loads(raw)

    is_safe, matched = validate_syntax(result["content"])
    if not is_safe:
        result["risk_level"] = "high"
        result["explanation"] = (
            result.get("explanation", "")
            + f"\n\nSAFETY GATE: matched dangerous pattern(s): {', '.join(matched)}. Requires elevated approval."
        )
    return result
