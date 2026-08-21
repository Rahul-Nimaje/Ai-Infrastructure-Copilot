"""Auto Discovery — docs/03-LLD.md Module 2. Read-only network reconnaissance
(TCP connect probes + reverse DNS) against a CIDR range the caller explicitly
provides; never runs against an implicit/guessed range. Results are
candidates only — nothing is persisted here. Registering a candidate as a
Server still goes through app/modules/infrastructure_inventory/service.py's
register_server, same as manual registration, so there is exactly one
code path that writes a Server row.

Safety notes (docs/03-LLD.md Module 2 Safety notes): "Discovery itself is
read-only ... and auto-runs on schedule without approval" — no Human
Approval gate needed here since nothing is mutated; capped scan size keeps
this from being usable as a general-purpose network scanner against
arbitrary/unbounded ranges.
"""
from __future__ import annotations

import asyncio
import ipaddress
import socket

from fastapi import HTTPException

MAX_HOSTS_PER_SCAN = 1024
CONNECT_TIMEOUT_SECONDS = 0.75
MAX_CONCURRENT_PROBES = 200

# port -> (label, likely_os_type)
_PROBE_PORTS: dict[int, tuple[str, str]] = {
    22: ("ssh", "linux"),
    3389: ("rdp", "windows"),
    5985: ("winrm_http", "windows"),
    5986: ("winrm_https", "windows"),
}


def parse_cidr(cidr: str) -> ipaddress.IPv4Network:
    try:
        network = ipaddress.ip_network(cidr, strict=False)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "VALIDATION_ERROR", "message": f"Invalid CIDR: {exc}"}) from exc
    if network.num_addresses > MAX_HOSTS_PER_SCAN:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "VALIDATION_ERROR",
                "message": f"Range too large ({network.num_addresses} addresses); scan at most a /22 ({MAX_HOSTS_PER_SCAN} addresses) at a time.",
            },
        )
    return network


async def _probe_port(ip: str, port: int, semaphore: asyncio.Semaphore) -> bool:
    async with semaphore:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port), timeout=CONNECT_TIMEOUT_SECONDS
            )
        except (asyncio.TimeoutError, OSError):
            return False
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass
        return True


async def _reverse_dns(ip: str) -> str | None:
    loop = asyncio.get_running_loop()
    try:
        hostname, _aliases, _addrs = await asyncio.wait_for(
            loop.run_in_executor(None, socket.gethostbyaddr, ip), timeout=1.0
        )
        return hostname
    except (asyncio.TimeoutError, OSError, socket.herror):
        return None


async def scan_network(cidr: str) -> list[dict]:
    network = parse_cidr(cidr)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_PROBES)

    hosts = [str(ip) for ip in network.hosts()] or [str(network.network_address)]

    async def probe_host(ip: str) -> dict | None:
        open_ports = []
        for port in _PROBE_PORTS:
            if await _probe_port(ip, port, semaphore):
                open_ports.append(port)
        if not open_ports:
            return None

        likely_os_type = "windows" if any(_PROBE_PORTS[p][1] == "windows" for p in open_ports) else "linux"
        hostname = await _reverse_dns(ip)
        return {
            "ip_address": ip,
            "hostname_guess": hostname or ip,
            "likely_os_type": likely_os_type,
            "open_ports": [{"port": p, "service": _PROBE_PORTS[p][0]} for p in sorted(open_ports)],
        }

    results = await asyncio.gather(*(probe_host(ip) for ip in hosts))
    return [r for r in results if r is not None]
