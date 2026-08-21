"""Thin WinRM/PowerShell-remoting wrapper used by the event-log sync endpoint
and the execution runner. Only ever invoked when EXECUTION_ENABLED=true and a
real credential is resolved — see docs/06-ai-architecture.md Section 5.1's
mutation boundary and plan simplification #3.
"""
from __future__ import annotations

from dataclasses import dataclass

from pypsrp.client import Client


@dataclass
class WinRmTarget:
    host: str
    username: str
    password: str
    port: int = 5986
    ssl: bool = True


def run_powershell(target: WinRmTarget, script: str) -> tuple[str, str, int]:
    """Runs `script` over WinRM and returns (stdout, stderr, return_code).
    Synchronous — callers on the async event loop should invoke this via
    `run_in_threadpool` (see app/execution/runner.py)."""
    with Client(target.host, username=target.username, password=target.password, port=target.port, ssl=target.ssl) as client:
        stdout, stderr, rc = client.execute_ps(script)
    return stdout, stderr, rc
