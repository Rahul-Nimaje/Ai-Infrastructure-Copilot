"""Thin SSH wrapper for read-only device-inventory collection. Mirrors
app/core/winrm_client.py's shape (a dataclass target + a run function), but
shells to the system `ssh` binary via asyncio subprocess rather than a Python
SSH library — consistent with how nmap is already invoked in
app/modules/discovery/service.py.

Read-only inventory collection only. This module must never be reused by
app/execution/runner.py's mutation path (see that module's docstring for the
human-approval boundary) — every caller here only ever runs read commands
(cat/ls/ps/systemctl list-units/etc.), never anything that changes device
state.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from dataclasses import dataclass


@dataclass
class SshTarget:
    host: str
    username: str
    password: str | None = None  # SSH_PASSWORD credentials — requires sshpass
    private_key: str | None = None  # SSH_KEY credentials — PEM contents
    port: int = 22
    connect_timeout: int = 5
    command_timeout: int = 30


async def run_command(target: SshTarget, command: str) -> tuple[str, str, int]:
    """Runs `command` over SSH and returns (stdout, stderr, returncode).
    Async-native (asyncio.create_subprocess_exec) since the `ssh` CLI is
    already invoked as a subprocess, unlike winrm_client's sync-wrapped shape."""
    key_path: str | None = None
    try:
        base_opts = [
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "BatchMode=yes" if not target.password else "BatchMode=no",
            "-o", f"ConnectTimeout={target.connect_timeout}",
            "-p", str(target.port),
        ]

        if target.private_key:
            fd, key_path = tempfile.mkstemp(prefix="disc-ssh-key-")
            os.write(fd, target.private_key.encode())
            os.close(fd)
            os.chmod(key_path, 0o600)
            cmd = ["ssh", "-i", key_path, *base_opts, f"{target.username}@{target.host}", command]
        elif target.password:
            # sshpass keeps the password out of argv by feeding it via env
            # var SSHPASS (-e), avoiding it showing up in `ps`.
            cmd = ["sshpass", "-e", "ssh", *base_opts, f"{target.username}@{target.host}", command]
        else:
            cmd = ["ssh", *base_opts, f"{target.username}@{target.host}", command]

        env = {**os.environ, "SSHPASS": target.password} if target.password and not target.private_key else None

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=target.command_timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return "", f"ssh command timed out after {target.command_timeout}s", -1

        return stdout.decode(errors="replace"), stderr.decode(errors="replace"), proc.returncode or 0
    finally:
        if key_path and os.path.exists(key_path):
            os.remove(key_path)


async def grab_banner(host: str, port: int = 22, timeout: float = 3.0) -> str | None:
    """Reads the raw SSH server version banner with no authentication — used
    by identify_device() to distinguish e.g. Cisco IOS SSH from OpenSSH
    without needing a credential."""
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        try:
            line = await asyncio.wait_for(reader.readline(), timeout=timeout)
            return line.decode(errors="replace").strip() or None
        finally:
            writer.close()
    except Exception:  # noqa: BLE001 — banner grab is best-effort, absence just means "abstain"
        return None
