"""SNMP wrapper shelling to net-snmp CLI binaries (snmpget/snmpwalk/
snmpbulkwalk) — consistent with how nmap/ssh are already invoked in this
codebase, rather than a Python SNMP library. Read-only GET/WALK only, never
SET; used for network-device (router/switch/firewall/AP) identification and
inventory collection.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

# MIB-II / ENTITY-MIB / HOST-RESOURCES-MIB OIDs used by identification and
# collection, given numerically since the container has no vendor MIB files
# loaded for symbolic resolution.
OID_SYS_DESCR = "1.3.6.1.2.1.1.1.0"
OID_SYS_OBJECT_ID = "1.3.6.1.2.1.1.2.0"
OID_SYS_UPTIME = "1.3.6.1.2.1.1.3.0"
OID_SYS_NAME = "1.3.6.1.2.1.1.5.0"
OID_ENT_PHYSICAL_DESCR = "1.3.6.1.2.1.47.1.1.1.1.2"
OID_ENT_PHYSICAL_MFG_NAME = "1.3.6.1.2.1.47.1.1.1.1.12"
OID_ENT_PHYSICAL_MODEL_NAME = "1.3.6.1.2.1.47.1.1.1.1.13"
OID_ENT_PHYSICAL_SERIAL_NUM = "1.3.6.1.2.1.47.1.1.1.1.11"
OID_ENT_PHYSICAL_SOFTWARE_REV = "1.3.6.1.2.1.47.1.1.1.1.10"
OID_IF_DESCR = "1.3.6.1.2.1.2.2.1.2"
OID_IF_PHYS_ADDRESS = "1.3.6.1.2.1.2.2.1.6"
OID_IF_ADMIN_STATUS = "1.3.6.1.2.1.2.2.1.7"
OID_IF_OPER_STATUS = "1.3.6.1.2.1.2.2.1.8"
OID_IF_SPEED = "1.3.6.1.2.1.2.2.1.5"
OID_IF_HIGH_SPEED = "1.3.6.1.2.1.31.1.1.1.15"
OID_HR_PROCESSOR_LOAD = "1.3.6.1.2.1.25.3.3.1.2"
OID_HR_STORAGE_DESCR = "1.3.6.1.2.1.25.2.3.1.3"
OID_HR_STORAGE_SIZE = "1.3.6.1.2.1.25.2.3.1.5"
OID_HR_STORAGE_USED = "1.3.6.1.2.1.25.2.3.1.6"
OID_HR_STORAGE_TYPE = "1.3.6.1.2.1.25.2.3.1.2"
OID_HR_STORAGE_TYPE_RAM = "1.3.6.1.2.1.25.2.1.2"
OID_CISCO_CPU_5MIN = "1.3.6.1.4.1.9.9.109.1.1.1.1.5"

# sysObjectID enterprise-number prefix -> vendor, used by identify_device().
VENDOR_ENTERPRISE_OIDS = {
    "1.3.6.1.4.1.9": "Cisco",
    "1.3.6.1.4.1.14988": "MikroTik",
    "1.3.6.1.4.1.41112": "Ubiquiti",
    "1.3.6.1.4.1.11": "HP",
    "1.3.6.1.4.1.14823": "Aruba",
    "1.3.6.1.4.1.12356": "Fortinet",
}


@dataclass
class SnmpTarget:
    host: str
    community: str | None = None  # v2c
    version: str = "2c"  # "2c" | "3"
    port: int = 161
    timeout: int = 3
    # v3 fields, only used when version == "3"
    username: str | None = None
    auth_protocol: str | None = None  # SHA | MD5
    auth_password: str | None = None
    priv_protocol: str | None = None  # AES | DES
    priv_password: str | None = None


def _base_args(target: SnmpTarget) -> list[str]:
    if target.version == "3":
        return [
            "-v", "3", "-u", target.username or "",
            "-l", "authPriv",
            "-a", target.auth_protocol or "SHA", "-A", target.auth_password or "",
            "-x", target.priv_protocol or "AES", "-X", target.priv_password or "",
            "-t", str(target.timeout), "-r", "1",
        ]
    return ["-v", "2c", "-c", target.community or "public", "-t", str(target.timeout), "-r", "1"]


async def _run(binary: str, args: list[str], timeout: float) -> tuple[str, int]:
    proc = await asyncio.create_subprocess_exec(
        binary, *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, _stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return "", -1
    return stdout.decode(errors="replace"), proc.returncode or 0


async def snmp_get(target: SnmpTarget, oid: str) -> str | None:
    args = [*_base_args(target), "-Oqv", f"{target.host}:{target.port}", oid]
    stdout, rc = await _run("snmpget", args, target.timeout + 2)
    return stdout.strip() if rc == 0 and stdout.strip() else None


async def snmp_walk(target: SnmpTarget, oid: str, *, bulk: bool = True) -> list[tuple[str, str]]:
    """Returns [(oid_suffix, value), ...]. Tries snmpbulkwalk first (much
    faster for ifTable-sized walks), falls back to snmpwalk on failure."""
    binary = "snmpbulkwalk" if bulk else "snmpwalk"
    args = [*_base_args(target), "-Oqn", f"{target.host}:{target.port}", oid]
    stdout, rc = await _run(binary, args, target.timeout + 5)
    if rc != 0 and bulk:
        return await snmp_walk(target, oid, bulk=False)
    results: list[tuple[str, str]] = []
    for line in stdout.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            suffix = parts[0][len(oid):].lstrip(".") if parts[0].startswith(oid) else parts[0]
            results.append((suffix, parts[1].strip()))
    return results


def vendor_from_sys_object_id(sys_object_id: str | None) -> str | None:
    """Maps a sysObjectID (e.g. '.1.3.6.1.4.1.9.1.749') to a known vendor by
    matching the longest known enterprise-OID prefix. Returns None (never a
    guess) when no known prefix matches."""
    if not sys_object_id:
        return None
    normalized = sys_object_id.lstrip(".")
    for prefix in sorted(VENDOR_ENTERPRISE_OIDS, key=len, reverse=True):
        if normalized == prefix or normalized.startswith(prefix + "."):
            return VENDOR_ENTERPRISE_OIDS[prefix]
    return None
