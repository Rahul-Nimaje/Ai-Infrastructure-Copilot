"""SSH client wrapper using Paramiko / asyncio for device inventory collection."""
from __future__ import annotations

import asyncio
import io
import logging
import os
import tempfile
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SshTarget:
    host: str
    username: str
    password: str | None = None
    private_key: str | None = None
    port: int = 22
    connect_timeout: int = 5
    command_timeout: int = 30


def _run_paramiko(target: SshTarget, command: str) -> tuple[str, str, int]:
    import paramiko

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    kwargs = {
        "hostname": target.host,
        "port": target.port,
        "username": target.username,
        "timeout": target.connect_timeout,
        "banner_timeout": target.connect_timeout,
        "auth_timeout": target.connect_timeout,
    }

    if target.private_key:
        try:
            key_file = io.StringIO(target.private_key)
            pkey = paramiko.RSAKey.from_private_key(key_file)
        except Exception:
            try:
                key_file = io.StringIO(target.private_key)
                pkey = paramiko.Ed25519Key.from_private_key(key_file)
            except Exception:
                key_file = io.StringIO(target.private_key)
                pkey = paramiko.ECDSAKey.from_private_key(key_file)
        kwargs["pkey"] = pkey
    elif target.password:
        kwargs["password"] = target.password

    try:
        client.connect(**kwargs)
        _stdin, stdout_file, stderr_file = client.exec_command(command, timeout=target.command_timeout)
        stdout = stdout_file.read().decode(errors="replace")
        stderr = stderr_file.read().decode(errors="replace")
        exit_code = stdout_file.channel.recv_exit_status()
        return stdout, stderr, exit_code
    finally:
        client.close()


async def run_command(target: SshTarget, command: str) -> tuple[str, str, int]:
    """Runs `command` over SSH using Paramiko thread pool."""
    try:
        return await asyncio.to_thread(_run_paramiko, target, command)
    except Exception as e:
        logger.warning("Paramiko SSH attempt failed for %s@%s: %s", target.username, target.host, e)
        return "", f"Authentication failed for user '{target.username}' ({str(e)})", 1


async def grab_banner(host: str, port: int = 22, timeout: float = 3.0) -> str | None:
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        try:
            line = await asyncio.wait_for(reader.readline(), timeout=timeout)
            return line.decode(errors="replace").strip() or None
        finally:
            writer.close()
    except Exception:
        return None
