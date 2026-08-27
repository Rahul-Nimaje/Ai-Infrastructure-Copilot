import asyncio
import logging
import socket
from dataclasses import dataclass

logger = logging.getLogger(__name__)
from datetime import datetime, timedelta
import uuid
import re
import shutil
import subprocess
import ipaddress
import json
import xml.etree.ElementTree as ET
from typing import Any

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.core.snmp_client import SnmpTarget, snmp_get, snmp_walk, vendor_from_sys_object_id
from app.core import snmp_client
from app.core.ssh_client import SshTarget, grab_banner
from app.core import ssh_client
from app.core.winrm_client import WinRmTarget, run_powershell
from app.models.device import (
    Device,
    NetworkScan,
    DeviceScanHistory,
    DeviceStatusHistory,
    DeviceIPHistory,
    DeviceInventory,
    DeviceNetworkInterface,
    DeviceStorage,
    DevicePartition,
    DeviceMemory,
    DeviceProcessor,
    DeviceInstalledSoftware,
    DeviceService,
    DeviceProcess,
    DeviceSecurity,
    DevicePort,
    DeviceInventoryHistory,
)
from app.models.credential import Credential
from app.modules.credentials.service import resolve_credential_secret
from app.modules.discovery.schemas import ScanStartRequest
from py_shared.enums import (
    CredentialType,
    DeviceIdentificationConfidence,
    DeviceScanStatus,
    DeviceType,
    OsType,
    ScanMode,
    ScanStatus,
)


def sanitize_scan_range(target_range: str) -> str:
    # Allow only digits, dots, slashes, dashes, commas, and spaces
    sanitized = re.sub(r"[^0-9a-zA-Z\.\/\-\,\s]", "", target_range)
    return sanitized.strip()


def ip_in_range(ip_str: str, range_str: str) -> bool:
    try:
        # Support comma separated ranges
        ranges = [r.strip() for r in range_str.split(",") if r.strip()]
        for r in ranges:
            if "/" in r:
                net = ipaddress.ip_network(r, strict=False)
                ip = ipaddress.ip_address(ip_str)
                if ip in net:
                    return True
            elif "-" in r:
                parts = r.split("-")
                start_ip = ipaddress.ip_address(parts[0].strip())
                if len(parts[1].split(".")) == 1:
                    ip_parts = parts[0].split(".")
                    end_ip_str = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.{parts[1].strip()}"
                else:
                    end_ip_str = parts[1].strip()
                end_ip = ipaddress.ip_address(end_ip_str)
                ip = ipaddress.ip_address(ip_str)
                if start_ip <= ip <= end_ip:
                    return True
            else:
                if ipaddress.ip_address(ip_str) == ipaddress.ip_address(r):
                    return True
        return False
    except Exception:
        return False


def lookup_vendor_by_mac(mac: str | None) -> str | None:
    if not mac:
        return None
    mac_clean = mac.replace(":", "").replace("-", "").upper()[:6]
    ouis = {
        "001A2B": "Cisco",
        "001122": "Netgear",
        "000C29": "VMware",
        "005056": "VMware",
        "00155D": "Microsoft",
        "2CF0EE": "Ubiquiti",
        "B827EB": "Raspberry Pi",
        "00110A": "HP",
        "001422": "Dell",
        "18E829": "MikroTik",
    }
    return ouis.get(mac_clean)


def parse_nmap_xml(xml_content: str) -> list[dict]:
    discovered = []
    try:
        root = ET.fromstring(xml_content)
        for host in root.findall("host"):
            status_el = host.find("status")
            state = status_el.attrib.get("state") if status_el is not None else "offline"
            if state != "up":
                continue

            ip_address = None
            mac_address = None
            vendor = None

            for addr in host.findall("address"):
                addrtype = addr.attrib.get("addrtype")
                if addrtype == "ipv4":
                    ip_address = addr.attrib.get("addr")
                elif addrtype == "mac":
                    mac_address = addr.attrib.get("addr")
                    vendor = addr.attrib.get("vendor")

            hostname = None
            hostnames_el = host.find("hostnames")
            if hostnames_el is not None:
                hostname_el = hostnames_el.find("hostname")
                if hostname_el is not None:
                    hostname = hostname_el.attrib.get("name")

            dns_name = hostname if hostname and "." in hostname else None
            netbios_name = hostname.split(".")[0].upper() if hostname else None

            response_time = None
            times_el = host.find("times")
            if times_el is not None:
                srtt = times_el.attrib.get("srtt")
                if srtt:
                    response_time = round(float(srtt) / 1000.0, 2)  # convert to ms

            # Parse open ports
            ports = []
            open_ports_dict = {"ports": []}
            ports_el = host.find("ports")
            if ports_el is not None:
                for port_el in ports_el.findall("port"):
                    state_el = port_el.find("state")
                    if state_el is not None and state_el.attrib.get("state") == "open":
                        port_id = int(port_el.attrib.get("portid"))
                        open_ports_dict["ports"].append(port_id)

                        service_name = ""
                        product = ""
                        version = ""
                        service_el = port_el.find("service")
                        if service_el is not None:
                            service_name = service_el.attrib.get("name", "")
                            product = service_el.attrib.get("product", "")
                            version = service_el.attrib.get("version", "")

                        ports.append({
                            "port": port_id,
                            "protocol": port_el.attrib.get("protocol", "tcp"),
                            "service": service_name,
                            "product": product,
                            "version": version
                        })

            os_name = None
            os_version = None
            os_el = host.find("os")
            if os_el is not None:
                osmatch_el = os_el.find("osmatch")
                if osmatch_el is not None:
                    os_name = osmatch_el.attrib.get("name")
                    match = re.search(r"(\d+(\.\d+)*)", os_name)
                    if match:
                        os_version = match.group(1)

            name = hostname or (f"host-{ip_address.replace('.', '-')}" if ip_address else "unknown")
            if mac_address and not vendor:
                vendor = lookup_vendor_by_mac(mac_address)

            discovered.append({
                "ip_address": ip_address,
                "mac_address": mac_address,
                "vendor": vendor,
                "name": name,
                "dns_name": dns_name,
                "netbios_name": netbios_name,
                "response_time": response_time,
                "status": "online",
                "open_ports": open_ports_dict,
                "ports_detail": ports,
                "operating_system": os_name,
                "os_version": os_version
            })
    except Exception as e:
        print(f"Error parsing nmap XML: {e}")
    return discovered


async def perform_manual_discovery(target_range: str) -> list[dict]:
    discovered = []

    # 1. Parse IPs in the range
    ips_to_scan = []
    try:
        ranges = [r.strip() for r in target_range.split(",") if r.strip()]
        for r in ranges:
            if "/" in r:
                net = ipaddress.ip_network(r, strict=False)
                for ip in net.hosts():
                    ips_to_scan.append(str(ip))
            elif "-" in r:
                parts = r.split("-")
                start_ip = ipaddress.ip_address(parts[0].strip())
                if len(parts[1].split(".")) == 1:
                    ip_parts = parts[0].split(".")
                    end_ip_str = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.{parts[1].strip()}"
                else:
                    end_ip_str = parts[1].strip()
                end_ip = ipaddress.ip_address(end_ip_str)

                curr = start_ip
                while curr <= end_ip:
                    ips_to_scan.append(str(curr))
                    curr += 1
            else:
                ips_to_scan.append(str(ipaddress.ip_address(r)))
    except Exception as e:
        print(f"Error parsing manual discovery range: {e}")
        return []

    if len(ips_to_scan) > 256:
        ips_to_scan = ips_to_scan[:256]

    # 2. Get local ARP table
    arp_table = {}
    try:
        with open("/proc/net/arp", "r") as f:
            lines = f.readlines()
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    ip = parts[0]
                    mac = parts[3]
                    if mac != "00:00:00:00:00:00":
                        arp_table[ip] = mac
    except Exception as e:
        print(f"Error reading ARP cache: {e}")

    # 3. Helper to ping and probe one IP
    async def scan_single_ip(ip: str) -> dict | None:
        try:
            proc = await asyncio.create_subprocess_exec(
                "ping", "-c", "1", "-W", "1", ip,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()

            hostname = None
            try:
                loop = asyncio.get_running_loop()
                res = await loop.run_in_executor(None, socket.gethostbyaddr, ip)
                hostname = res[0]
            except Exception:
                pass

            ports_to_probe = [22, 23, 53, 80, 443, 139, 445, 3389, 5985, 5986, 161]
            open_ports = []
            ports_detail = []

            async def check_port(port: int):
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(ip, port),
                        timeout=0.1
                    )
                    open_ports.append(port)
                    port_labels = {
                        22: "ssh", 23: "telnet", 53: "dns", 80: "http",
                        443: "https", 139: "netbios-ssn", 445: "microsoft-ds",
                        3389: "ms-wbt-server", 5985: "wsman", 5986: "wsmans", 161: "snmp"
                    }
                    ports_detail.append({
                        "port": port,
                        "protocol": "tcp",
                        "service": port_labels.get(port, "unknown"),
                        "product": "",
                        "version": ""
                    })
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

            await asyncio.gather(*[check_port(p) for p in ports_to_probe])

            if proc.returncode == 0 or open_ports:
                mac = arp_table.get(ip)
                vendor = lookup_vendor_by_mac(mac)
                name = hostname or f"host-{ip.replace('.', '-')}"

                response_time = 10.0
                if proc.returncode == 0:
                    match = re.search(r"time=(\d+(\.\d+)?)", stdout.decode())
                    if match:
                        response_time = float(match.group(1))

                return {
                    "ip_address": ip,
                    "mac_address": mac,
                    "vendor": vendor,
                    "name": name,
                    "dns_name": hostname,
                    "netbios_name": hostname.split(".")[0].upper() if hostname else None,
                    "response_time": round(response_time, 2),
                    "status": "online",
                    "open_ports": {"ports": open_ports},
                    "ports_detail": ports_detail,
                    "operating_system": None,
                    "os_version": None
                }
        except Exception as e:
            print(f"Error scanning IP {ip}: {e}")
        return None

    tasks = [scan_single_ip(ip) for ip in ips_to_scan]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None]


def classify_device(name: str, vendor: str | None, open_ports: list[int], os_name: str | None) -> str:
    """Final, cheapest-available heuristic tier for device identification —
    name/vendor/port/OS-string pattern matching only. Never authoritative on
    its own; identify_device() wraps this and caps its result at
    'unverified' confidence (section 2 — never claim confirmed from a guess)."""
    name_lower = name.lower()
    os_lower = (os_name or "").lower()
    vendor_lower = (vendor or "").lower()

    # 1. Hypervisors & Container Hosts
    if 8006 in open_ports or "proxmox" in name_lower or "proxmox" in os_lower:
        return DeviceType.PROXMOX.value
    if 902 in open_ports or "esxi" in name_lower or "vmware" in os_lower:
        return DeviceType.VMWARE_ESXI.value
    if "hyper-v" in name_lower or "hyperv" in name_lower or "hyperv" in os_lower:
        return DeviceType.HYPER_V.value
    if "k8s" in name_lower or "kubernetes" in name_lower or 10250 in open_ports:
        return DeviceType.KUBERNETES_NODE.value
    if "docker" in name_lower or 2375 in open_ports or 2376 in open_ports:
        return DeviceType.DOCKER_HOST.value

    # 2. Virtual Machines
    if "vm" in name_lower or "replica" in name_lower or "virtual machine" in name_lower:
        return DeviceType.VIRTUAL_MACHINE.value

    # 3. Printers
    if 9100 in open_ports or 631 in open_ports or "printer" in name_lower or "laserjet" in name_lower or "jetdirect" in os_lower:
        return DeviceType.PRINTER.value

    # 4. NAS Devices
    if "nas" in name_lower or "synology" in name_lower or "qnap" in name_lower or 5000 in open_ports or "dsm" in os_lower:
        return DeviceType.NAS.value

    # 5. Access Points / IP Cameras / IoT
    if "ap-" in name_lower or "ubiquiti" in vendor_lower or "unifi" in name_lower:
        return DeviceType.ACCESS_POINT.value
    if "camera" in name_lower or "cam" in name_lower or 554 in open_ports:
        return DeviceType.IP_CAMERA.value
    if "iot" in name_lower or "smart" in name_lower:
        return DeviceType.IOT.value

    # 6. Firewalls
    if "firewall" in name_lower or "fortigate" in name_lower or "pfsense" in name_lower or "asa" in os_lower or "checkpoint" in vendor_lower:
        return DeviceType.FIREWALL.value

    # 7. Routers & Switches
    if "router" in name_lower or "gateway" in name_lower or "isr" in name_lower or "edge" in name_lower:
        return DeviceType.ROUTER.value
    if "switch" in name_lower or "sw-" in name_lower or "catalyst" in name_lower:
        return DeviceType.SWITCH.value

    # 8. OS-based fallback
    if "windows" in os_lower or 3389 in open_ports or 5985 in open_ports:
        return DeviceType.WINDOWS.value
    if "linux" in os_lower or "ubuntu" in os_lower or "centos" in os_lower or "redhat" in os_lower or 22 in open_ports:
        return DeviceType.LINUX.value
    if "mac" in os_lower or "darwin" in os_lower:
        return DeviceType.MACOS.value

    return DeviceType.UNKNOWN.value


@dataclass
class DeviceIdentification:
    """Result of identify_device() — section 2. `confidence` is CONFIRMED
    only when a signal that cannot lie (SNMP/WinRM/SSH-banner response) was
    obtained; everything derived from names/ports/vendor OUI is UNVERIFIED."""

    device_type: str
    confidence: str
    method: str | None = None
    os_family: str | None = None
    vendor: str | None = None


async def identify_device(
    ip: str,
    port_ids: list[int],
    name: str,
    vendor: str | None,
    os_name: str | None,
    *,
    snmp_secret: dict | None = None,
    winrm_secret: dict | None = None,
) -> DeviceIdentification:
    """Multi-signal device identification (section 2), cheapest/most-reliable
    signal first, stopping at the first CONFIRMED result. Never returns
    CONFIRMED from a name/port/vendor heuristic alone."""

    # 1. SNMP sysObjectID probe — a device that speaks SNMP with a valid
    # community is unambiguously network-managed gear.
    if 161 in port_ids:
        community = (snmp_secret or {}).get("secret") or "public"
        snmp_target = SnmpTarget(host=ip, community=community, timeout=2)
        try:
            sys_object_id = await snmp_get(snmp_target, snmp_client.OID_SYS_OBJECT_ID)
        except Exception:
            sys_object_id = None
        if sys_object_id:
            detected_vendor = vendor_from_sys_object_id(sys_object_id)
            dtype = DeviceType.SWITCH.value if 23 in port_ids else DeviceType.ROUTER.value
            return DeviceIdentification(
                device_type=dtype,
                confidence=DeviceIdentificationConfidence.CONFIRMED.value,
                method="snmp",
                vendor=detected_vendor,
            )

    # 2. WinRM reachability + one lightweight CIM call — only attempted with
    # a WinRM credential available; absence of a credential means abstain,
    # not guess.
    if (5985 in port_ids or 5986 in port_ids) and winrm_secret:
        port = 5986 if 5986 in port_ids else 5985
        target = WinRmTarget(
            host=ip,
            username=winrm_secret.get("username", ""),
            password=winrm_secret.get("secret", ""),
            port=port,
            ssl=(port == 5986),
        )
        try:
            stdout, _stderr, rc = await asyncio.wait_for(
                run_in_threadpool(run_powershell, target, "(Get-CimInstance Win32_OperatingSystem).Caption"),
                timeout=4.0,
            )
            if rc == 0 and stdout.strip():
                return DeviceIdentification(
                    device_type=DeviceType.WINDOWS.value,
                    confidence=DeviceIdentificationConfidence.CONFIRMED.value,
                    method="winrm",
                    os_family=OsType.WINDOWS.value,
                )
        except Exception:
            pass

    best_unverified: DeviceIdentification | None = None

    # 3. SSH banner grab — no credential needed, distinguishes network-OS
    # SSH banners (e.g. Cisco) from generic OpenSSH/Dropbear.
    if 22 in port_ids:
        banner = await grab_banner(ip, 22)
        if banner:
            lower = banner.lower()
            if "cisco" in lower:
                return DeviceIdentification(
                    device_type=DeviceType.ROUTER.value,
                    confidence=DeviceIdentificationConfidence.CONFIRMED.value,
                    method="ssh",
                    vendor="Cisco",
                )
            if "openssh" in lower or "dropbear" in lower:
                best_unverified = DeviceIdentification(
                    device_type=DeviceType.LINUX.value,
                    confidence=DeviceIdentificationConfidence.UNVERIFIED.value,
                    method="ssh",
                    os_family=OsType.LINUX.value,
                )

    # 4. SMB probe (no auth) — weak windows-leaning signal only.
    if best_unverified is None and 445 in port_ids:
        best_unverified = DeviceIdentification(
            device_type=DeviceType.WINDOWS.value,
            confidence=DeviceIdentificationConfidence.UNVERIFIED.value,
            method="smb",
            os_family=OsType.WINDOWS.value,
        )

    # 5. Name/vendor/port heuristic — final fallback tier, capped at unverified.
    heuristic_type = classify_device(name, vendor, port_ids, os_name)
    if heuristic_type != DeviceType.UNKNOWN.value:
        return DeviceIdentification(
            device_type=heuristic_type,
            confidence=DeviceIdentificationConfidence.UNVERIFIED.value,
            method="hostname_heuristic" if name and not name.startswith("host-") else "port_heuristic",
        )

    if best_unverified:
        return best_unverified

    return DeviceIdentification(
        device_type=DeviceType.UNKNOWN.value,
        confidence=DeviceIdentificationConfidence.UNKNOWN.value,
        method=None,
    )


async def list_devices(
    db: AsyncSession,
    organization_id: uuid.UUID,
    *,
    page: int = 1,
    size: int = 20,
    search: str | None = None,
    status_filter: str | None = None,
    device_type: str | None = None,
    operating_system: str | None = None,
    vendor: str | None = None,
    response_time_bucket: str | None = None,
    last_seen_bucket: str | None = None,
    scan_status: str | None = None,
    sort_by: str = "last_seen_at",
    sort_order: str = "desc",
) -> tuple[list[Device], int]:
    query = select(Device).where(and_(Device.organization_id == organization_id, Device.deleted_at.is_(None)))

    if search:
        search_lower = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(Device.name).like(search_lower),
                func.lower(Device.ip_address).like(search_lower),
                func.lower(Device.mac_address).like(search_lower),
                func.lower(Device.vendor).like(search_lower),
            )
        )

    if status_filter:
        query = query.where(Device.status == status_filter.lower())
    if device_type:
        query = query.where(Device.device_type == device_type.lower())
    if scan_status:
        query = query.where(Device.scan_status == scan_status.lower())
    if operating_system:
        if operating_system.lower() == "unknown":
            query = query.where(Device.operating_system.is_(None))
        else:
            query = query.where(func.lower(Device.operating_system) == operating_system.lower())
    if vendor:
        if vendor.lower() == "others":
            query = query.where(
                and_(
                    func.lower(Device.vendor) != "dell",
                    func.lower(Device.vendor) != "hp",
                    func.lower(Device.vendor) != "lenovo",
                    func.lower(Device.vendor) != "cisco",
                    func.lower(Device.vendor) != "mikrotik",
                    func.lower(Device.vendor) != "ubiquiti",
                    func.lower(Device.vendor) != "vmware",
                    func.lower(Device.vendor) != "microsoft",
                )
            )
        else:
            query = query.where(func.lower(Device.vendor) == vendor.lower())

    if response_time_bucket:
        if response_time_bucket == "<10 ms":
            query = query.where(Device.response_time < 10.0)
        elif response_time_bucket in ["10–50 ms", "10-50 ms"]:
            query = query.where(and_(Device.response_time >= 10.0, Device.response_time <= 50.0))
        elif response_time_bucket in ["50–100 ms", "50-100 ms"]:
            query = query.where(and_(Device.response_time > 50.0, Device.response_time <= 100.0))
        elif response_time_bucket == ">100 ms":
            query = query.where(Device.response_time > 100.0)

    if last_seen_bucket:
        now = datetime.utcnow()
        if last_seen_bucket.lower() == "today":
            today_start = datetime(now.year, now.month, now.day)
            query = query.where(Device.last_seen_at >= today_start)
        elif last_seen_bucket == "Last 24 Hours":
            query = query.where(Device.last_seen_at >= now - timedelta(hours=24))
        elif last_seen_bucket == "Last 7 Days":
            query = query.where(Device.last_seen_at >= now - timedelta(days=7))
        elif last_seen_bucket == "Last 30 Days":
            query = query.where(Device.last_seen_at >= now - timedelta(days=30))

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    col = getattr(Device, sort_by, Device.last_seen_at)
    if sort_order.lower() == "asc":
        query = query.order_by(col.asc())
    else:
        query = query.order_by(col.desc())

    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    devices = result.scalars().all()

    return list(devices), total


async def get_device_detail(db: AsyncSession, organization_id: uuid.UUID, device_id: uuid.UUID) -> Device:
    query = select(Device).where(and_(Device.organization_id == organization_id, Device.id == device_id, Device.deleted_at.is_(None)))
    result = await db.execute(query)
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


async def get_device_status_history(db: AsyncSession, organization_id: uuid.UUID, device_id: uuid.UUID) -> list[DeviceStatusHistory]:
    await get_device_detail(db, organization_id, device_id)
    query = select(DeviceStatusHistory).where(and_(DeviceStatusHistory.organization_id == organization_id, DeviceStatusHistory.device_id == device_id)).order_by(DeviceStatusHistory.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_device_ip_history(db: AsyncSession, organization_id: uuid.UUID, device_id: uuid.UUID) -> list[DeviceIPHistory]:
    await get_device_detail(db, organization_id, device_id)
    query = select(DeviceIPHistory).where(and_(DeviceIPHistory.organization_id == organization_id, DeviceIPHistory.device_id == device_id)).order_by(DeviceIPHistory.changed_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


# Backwards compatibility: maps to get_device_status_history and returns it in old DeviceHistoryResponse format
async def get_device_history(db: AsyncSession, organization_id: uuid.UUID, device_id: uuid.UUID) -> list[Any]:
    histories = await get_device_status_history(db, organization_id, device_id)
    mapped = []
    for h in histories:
        mapped.append({
            "id": h.id,
            "organization_id": h.organization_id,
            "device_id": h.device_id,
            "event_type": "status_change",
            "description": f"Device status changed to {h.status}.",
            "before_state": None,
            "after_state": {"status": h.status, "response_time": float(h.response_time) if h.response_time else None},
            "created_at": h.created_at
        })
    return mapped


async def list_scans(db: AsyncSession, organization_id: uuid.UUID) -> list[NetworkScan]:
    query = select(NetworkScan).where(NetworkScan.organization_id == organization_id).order_by(NetworkScan.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def start_scan(
    db: AsyncSession,
    organization_id: uuid.UUID,
    payload: ScanStartRequest,
    actor_id: uuid.UUID
) -> NetworkScan:
    # Check if there is an active running scan
    active_q = await db.execute(select(NetworkScan).where(and_(
        NetworkScan.organization_id == organization_id,
        NetworkScan.status.in_([ScanStatus.PENDING.value, ScanStatus.DISCOVERING.value, ScanStatus.IDENTIFYING.value, ScanStatus.SCANNING.value, "running"]),
    )))
    if active_q.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A scan is already in progress")

    scan_mode = payload.scan_mode.value if hasattr(payload.scan_mode, "value") else str(payload.scan_mode)
    scan = NetworkScan(
        organization_id=organization_id,
        status=ScanStatus.PENDING.value,
        scan_type=scan_mode,
        scan_range=payload.target_range,
        created_by_id=actor_id
    )
    db.add(scan)
    await db.commit()
    return scan


async def stop_scan(db: AsyncSession, organization_id: uuid.UUID, scan_id: uuid.UUID, actor_id: uuid.UUID) -> NetworkScan:
    query = select(NetworkScan).where(and_(NetworkScan.organization_id == organization_id, NetworkScan.id == scan_id))
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan job not found")

    active_statuses = {ScanStatus.PENDING.value, ScanStatus.DISCOVERING.value, ScanStatus.IDENTIFYING.value, ScanStatus.SCANNING.value, "pending", "running"}
    if scan.status in active_statuses:
        scan.status = ScanStatus.CANCELLED.value
        scan.completed_at = datetime.utcnow()
        scan.error_message = "Scan stopped by operator"
        await write_audit_log(
            db,
            organization_id=organization_id,
            actor_type="user",
            actor_user_id=actor_id,
            action="scan.stop",
            resource_type="network_scans",
            resource_id=scan.id
        )
        await db.commit()
    return scan


async def resolve_device_identity(
    db: AsyncSession,
    organization_id: uuid.UUID,
    *,
    uuid_val: str | None,
    serial_val: str | None,
    mac: str | None,
    hostname: str | None,
    ip: str | None,
) -> tuple[Device | None, bool]:
    """Section 7 — identity priority: System UUID -> MAC -> Serial ->
    Hostname -> IP-as-fallback-only. Returns (existing_device_or_None,
    ip_mac_mismatch) — the caller decides create-vs-update-vs-supersede from
    the mismatch flag; this function only resolves identity."""
    for column, value in [
        (Device.uuid, uuid_val),
        (Device.mac_address, mac),
        (Device.serial_number, serial_val),
        (Device.name, hostname),
    ]:
        if not value:
            continue
        device_q = await db.execute(select(Device).where(and_(
            Device.organization_id == organization_id,
            column == value,
            Device.deleted_at.is_(None),
        )))
        device = device_q.scalar_one_or_none()
        if device:
            mismatch = bool(ip and device.ip_address and mac and device.mac_address and device.mac_address != mac)
            return device, mismatch

    if ip:
        device_q = await db.execute(select(Device).where(and_(
            Device.organization_id == organization_id,
            Device.ip_address == ip,
            Device.deleted_at.is_(None),
        )))
        device = device_q.scalar_one_or_none()
        if device:
            mismatch = bool(mac and device.mac_address and device.mac_address != mac)
            return device, mismatch

    return None, False


def _network_capable_credential_types() -> dict[str, list[str]]:
    return {
        "winrm": [CredentialType.WINRM.value],
        "ssh": [CredentialType.SSH_PASSWORD.value, CredentialType.SSH_KEY.value],
        "snmp": [CredentialType.SNMP_V2C.value, CredentialType.SNMP_V3.value],
    }


async def run_discovery_scan_task(
    db_session_factory: Any,
    organization_id: uuid.UUID,
    scan_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> list[uuid.UUID]:
    """Discovery + identification phase (sections 1-2, 6-7, 9). Runs Nmap
    (or the manual fallback), classifies/identifies every host per scan
    mode, persists devices with corrected dedup priority, and — for Full
    mode only — returns the device IDs that need credentialed inventory
    collection (the caller, e.g. the Celery task wrapper, dispatches that
    separately via run_inventory_collection/run_device_inventory_task)."""
    async with db_session_factory() as db:
        scan_q = await db.execute(select(NetworkScan).where(NetworkScan.id == scan_id))
        scan = scan_q.scalar_one_or_none()
        if not scan or scan.status != ScanStatus.PENDING.value:
            return []

        scan_mode = scan.scan_type if scan.scan_type in {m.value for m in ScanMode} else ScanMode.STANDARD.value
        scan.status = ScanStatus.DISCOVERING.value
        scan.started_at = datetime.utcnow()
        await db.commit()

        start_time = datetime.utcnow()
        error_msg = None
        discovered: list[dict] = []

        new_count = 0
        updated_count = 0
        failed_count = 0
        auth_fail_count = 0
        online_count = 0
        offline_count = 0
        full_scan_candidates: list[uuid.UUID] = []

        try:
            # 1. Fetch credentials (used for identification signals + later Full collection)
            cred_q = await db.execute(select(Credential).where(and_(
                Credential.organization_id == organization_id,
                Credential.deleted_at.is_(None)
            )))
            credentials = list(cred_q.scalars().all())

            snmp_secret = None
            snmp_cred = next((c for c in credentials if c.credential_type in _network_capable_credential_types()["snmp"]), None)
            if snmp_cred:
                try:
                    snmp_secret = await resolve_credential_secret(db, organization_id=organization_id, credential_id=snmp_cred.id)
                except Exception:
                    snmp_secret = None

            winrm_secret = None
            winrm_cred = next((c for c in credentials if c.credential_type in _network_capable_credential_types()["winrm"]), None)
            if winrm_cred:
                try:
                    winrm_secret = await resolve_credential_secret(db, organization_id=organization_id, credential_id=winrm_cred.id)
                except Exception:
                    winrm_secret = None

            # 2. Run Nmap scan — Quick = ping sweep only; Standard/Full add
            # service/version + OS detection.
            sanitized_range = sanitize_scan_range(scan.scan_range)
            nmap_path = shutil.which("nmap")

            if nmap_path:
                try:
                    if scan_mode == ScanMode.QUICK.value:
                        cmd = [nmap_path, "-sn", "-oX", "-", sanitized_range]
                    else:
                        cmd = [
                            nmap_path, "-sT", "-sV", "-O",
                            "-p", "22,23,53,80,443,139,445,3389,5985,5986,161,631,9100,902,8006",
                            "-oX", "-", sanitized_range,
                        ]

                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()

                    if process.returncode == 0:
                        discovered = parse_nmap_xml(stdout.decode())
                    else:
                        error_msg = f"Nmap exited with code {process.returncode}: {stderr.decode()}"
                except Exception as e:
                    error_msg = f"Failed to execute nmap: {str(e)}"

            # Fallback discovery mechanism when nmap is missing/fails/returns empty
            if not discovered:
                print("Nmap scan returned no hosts or failed. Trying manual ICMP ping/ARP/DNS discovery sweep...")
                try:
                    discovered = await perform_manual_discovery(scan.scan_range)
                except Exception as ex:
                    print(f"Manual discovery failed: {ex}")

            if scan_mode != ScanMode.QUICK.value:
                scan.status = ScanStatus.IDENTIFYING.value
                await db.commit()

            processed_device_ids: set[uuid.UUID] = set()

            for cand in discovered:
                ip = cand["ip_address"]
                mac = cand["mac_address"]
                vendor = cand["vendor"] or lookup_vendor_by_mac(mac)
                name = cand["name"]
                response_time = cand["response_time"]
                open_ports = cand.get("open_ports", {"ports": []})
                ports_list = open_ports.get("ports", [])
                ports_detail = cand.get("ports_detail", [])
                os_name = cand.get("operating_system")

                if scan_mode == ScanMode.QUICK.value:
                    identification = DeviceIdentification(
                        device_type=DeviceType.UNKNOWN.value,
                        confidence=DeviceIdentificationConfidence.UNKNOWN.value,
                        method=None,
                    )
                else:
                    identification = await identify_device(
                        ip, ports_list, name, vendor, os_name,
                        snmp_secret=snmp_secret, winrm_secret=winrm_secret,
                    )

                device, ip_mac_mismatch = await resolve_device_identity(
                    db, organization_id,
                    uuid_val=None, serial_val=None, mac=mac, hostname=name, ip=ip,
                )

                if device and ip_mac_mismatch:
                    # Section 7 — same IP, different MAC: supersede. Old
                    # device is preserved as historical/offline, a new
                    # device row is created for the new physical device.
                    old_device = device
                    old_device.status = "offline"
                    old_device.scan_status = DeviceScanStatus.OFFLINE.value
                    old_device.ip_address = None
                    await db.flush()

                    db.add(DeviceIPHistory(
                        organization_id=organization_id, device_id=old_device.id,
                        old_ip=ip, new_ip=None, changed_at=datetime.utcnow(),
                    ))
                    db.add(DeviceStatusHistory(
                        organization_id=organization_id, device_id=old_device.id,
                        status="offline", hostname=old_device.name, vendor=old_device.vendor,
                        operating_system=old_device.operating_system, created_at=datetime.utcnow(),
                    ))

                    device = Device(
                        organization_id=organization_id,
                        device_type=identification.device_type,
                        name=name,
                        ip_address=ip,
                        mac_address=mac,
                        vendor=identification.vendor or vendor,
                        operating_system=os_name,
                        status="online",
                        response_time=response_time,
                        open_ports=open_ports,
                        last_seen_at=datetime.utcnow(),
                        scan_timestamp=start_time,
                        scan_status=DeviceScanStatus.DISCOVERED.value,
                        identification_confidence=identification.confidence,
                        identification_method=identification.method,
                    )
                    db.add(device)
                    await db.flush()
                    db.add(DeviceIPHistory(
                        organization_id=organization_id, device_id=device.id,
                        old_ip=None, new_ip=ip, changed_at=datetime.utcnow(),
                    ))
                    new_count += 1
                elif device:
                    if ip and device.ip_address != ip:
                        db.add(DeviceIPHistory(
                            organization_id=organization_id, device_id=device.id,
                            old_ip=device.ip_address, new_ip=ip, changed_at=datetime.utcnow(),
                        ))
                        device.ip_address = ip

                    device.status = "online"
                    device.response_time = response_time
                    if name:
                        device.name = name
                    if identification.vendor or vendor:
                        device.vendor = identification.vendor or vendor
                    if os_name:
                        device.operating_system = os_name
                    if identification.device_type != DeviceType.UNKNOWN.value:
                        device.device_type = identification.device_type
                        device.identification_confidence = identification.confidence
                        device.identification_method = identification.method
                    if open_ports:
                        device.open_ports = open_ports
                    device.last_seen_at = datetime.utcnow()
                    device.scan_timestamp = start_time
                    if device.scan_status in (None, DeviceScanStatus.OFFLINE.value):
                        device.scan_status = DeviceScanStatus.DISCOVERED.value

                    await db.flush()
                    updated_count += 1
                else:
                    device = Device(
                        organization_id=organization_id,
                        device_type=identification.device_type,
                        name=name,
                        ip_address=ip,
                        mac_address=mac,
                        vendor=identification.vendor or vendor,
                        operating_system=os_name,
                        status="online",
                        response_time=response_time,
                        open_ports=open_ports,
                        last_seen_at=datetime.utcnow(),
                        scan_timestamp=start_time,
                        scan_status=DeviceScanStatus.DISCOVERED.value,
                        identification_confidence=identification.confidence,
                        identification_method=identification.method,
                    )
                    db.add(device)
                    await db.flush()
                    db.add(DeviceIPHistory(
                        organization_id=organization_id, device_id=device.id,
                        old_ip=None, new_ip=ip, changed_at=datetime.utcnow(),
                    ))
                    new_count += 1

                processed_device_ids.add(device.id)
                online_count += 1

                # Persist real port/service data (section 8 — previously
                # discarded after nmap XML parse) for Standard/Full scans.
                if scan_mode != ScanMode.QUICK.value and ports_detail:
                    existing_ports_q = await db.execute(select(DevicePort).where(DevicePort.device_id == device.id))
                    for p in existing_ports_q.scalars().all():
                        await db.delete(p)
                    await db.flush()
                    now = datetime.utcnow()
                    for p in ports_detail:
                        db.add(DevicePort(
                            organization_id=organization_id, device_id=device.id, scan_id=scan_id,
                            port_number=p["port"], protocol=p.get("protocol", "tcp"),
                            service_name=p.get("service") or None, product=p.get("product") or None,
                            version=p.get("version") or None, state="open",
                            first_seen_at=now, last_seen_at=now,
                        ))

                db.add(DeviceScanHistory(
                    organization_id=organization_id, scan_id=scan_id, device_id=device.id,
                    status="online", response_time=response_time,
                ))
                db.add(DeviceStatusHistory(
                    organization_id=organization_id, device_id=device.id, status="online",
                    response_time=response_time, hostname=device.name, vendor=device.vendor,
                    operating_system=device.operating_system,
                ))

                if scan_mode == ScanMode.FULL.value and identification.device_type in {
                    DeviceType.WINDOWS.value, DeviceType.LINUX.value, DeviceType.MACOS.value,
                    DeviceType.ROUTER.value, DeviceType.SWITCH.value, DeviceType.FIREWALL.value,
                    DeviceType.ACCESS_POINT.value,
                }:
                    full_scan_candidates.append(device.id)

            # --- Detect Offline Devices ---
            existing_devices_q = await db.execute(select(Device).where(and_(
                Device.organization_id == organization_id,
                Device.deleted_at.is_(None)
            )))
            existing_devices = existing_devices_q.scalars().all()

            for d in existing_devices:
                if d.id in processed_device_ids:
                    continue
                if d.ip_address and ip_in_range(d.ip_address, scan.scan_range):
                    d.status = "offline"
                    d.scan_status = DeviceScanStatus.OFFLINE.value
                    await db.flush()
                    offline_count += 1

                    db.add(DeviceScanHistory(
                        organization_id=organization_id, scan_id=scan_id, device_id=d.id,
                        status="offline", response_time=None,
                    ))
                    db.add(DeviceStatusHistory(
                        organization_id=organization_id, device_id=d.id, status="offline",
                        response_time=None, hostname=d.name, vendor=d.vendor,
                        operating_system=d.operating_system,
                    ))

            scan.status = ScanStatus.SCANNING.value if full_scan_candidates else ScanStatus.COMPLETED.value
            scan.completed_at = datetime.utcnow()
            scan.total_devices = online_count + offline_count
            scan.online_devices = online_count
            scan.offline_devices = offline_count
            scan.new_devices = new_count
            scan.updated_devices = updated_count
            scan.failed_devices = failed_count
            scan.auth_failures = auth_fail_count
            scan.scan_duration = round((scan.completed_at - scan.started_at).total_seconds(), 2)
            if error_msg:
                scan.error_message = error_msg

            await write_audit_log(
                db, organization_id=organization_id, actor_type="system", action="scan.complete",
                resource_type="network_scans", resource_id=scan.id,
                after_state={
                    "total_devices": scan.total_devices, "online": online_count, "offline": offline_count,
                    "new_devices": new_count, "updated_devices": updated_count,
                    "failed_devices": failed_count, "auth_failures": auth_fail_count,
                }
            )
            await db.commit()
            return full_scan_candidates

        except Exception as e:
            await db.rollback()
            async with db_session_factory() as fail_db:
                scan_q = await fail_db.execute(select(NetworkScan).where(NetworkScan.id == scan_id))
                scan_instance = scan_q.scalar_one_or_none()
                if scan_instance:
                    scan_instance.status = ScanStatus.FAILED.value
                    scan_instance.completed_at = datetime.utcnow()
                    scan_instance.error_message = str(e)
                    if scan_instance.started_at:
                        scan_instance.scan_duration = round((scan_instance.completed_at - scan_instance.started_at).total_seconds(), 2)
                    await fail_db.commit()
            return []


async def finalize_scan_if_complete(db: AsyncSession, scan_id: uuid.UUID) -> None:
    """Called after each device's Full-mode inventory collection finishes.
    Flips the scan to a terminal status once every device it touched has
    reached a terminal scan_status (completed/partial/failed/
    credentials_required/offline)."""
    scan_q = await db.execute(select(NetworkScan).where(NetworkScan.id == scan_id))
    scan = scan_q.scalar_one_or_none()
    if not scan or scan.status != ScanStatus.SCANNING.value:
        return

    device_ids_q = await db.execute(
        select(DeviceScanHistory.device_id).where(DeviceScanHistory.scan_id == scan_id).distinct()
    )
    device_ids = [row[0] for row in device_ids_q.all()]
    if not device_ids:
        return

    devices_q = await db.execute(select(Device).where(Device.id.in_(device_ids)))
    devices = list(devices_q.scalars().all())

    terminal = {
        DeviceScanStatus.COMPLETED.value, DeviceScanStatus.PARTIAL.value,
        DeviceScanStatus.FAILED.value, DeviceScanStatus.CREDENTIALS_REQUIRED.value,
        DeviceScanStatus.OFFLINE.value, DeviceScanStatus.DISCOVERED.value,
    }
    if any(d.scan_status not in terminal for d in devices):
        return

    statuses = {d.scan_status for d in devices}
    if statuses <= {DeviceScanStatus.COMPLETED.value, DeviceScanStatus.OFFLINE.value, DeviceScanStatus.DISCOVERED.value}:
        scan.status = ScanStatus.COMPLETED.value
    elif statuses <= {DeviceScanStatus.CREDENTIALS_REQUIRED.value, DeviceScanStatus.FAILED.value}:
        scan.status = ScanStatus.CREDENTIALS_REQUIRED.value if DeviceScanStatus.CREDENTIALS_REQUIRED.value in statuses else ScanStatus.FAILED.value
    else:
        scan.status = ScanStatus.PARTIAL.value
    await db.commit()


# ── Real collectors (section 3-5) — every command below is read-only. ──────

_LINUX_INVENTORY_SCRIPT = (
    "echo '===OS==='; cat /etc/os-release 2>/dev/null; "
    "echo '===DMI==='; cat /sys/class/dmi/id/sys_vendor /sys/class/dmi/id/product_name "
    "/sys/class/dmi/id/product_serial /sys/class/dmi/id/product_uuid /sys/class/dmi/id/board_name "
    "/sys/class/dmi/id/bios_version 2>/dev/null; "
    "echo '===CPU==='; lscpu 2>/dev/null; "
    "echo '===MEM==='; free -b 2>/dev/null; dmidecode -t memory 2>/dev/null | grep -E 'Size:|Speed:|Manufacturer:|Locator:'; "
    "echo '===DISK==='; lsblk -b -P -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,MODEL,SERIAL,TRAN 2>/dev/null; "
    "echo '===PART==='; df -B1 --output=source,size,used,avail,fstype,target 2>/dev/null; "
    "echo '===NET==='; ip -o addr show 2>/dev/null; cat /etc/resolv.conf 2>/dev/null | grep nameserver; "
    "ip route show default 2>/dev/null; "
    "echo '===SW==='; (dpkg-query -W -f='${Package}\\t${Version}\\t${Maintainer}\\n' 2>/dev/null || "
    "rpm -qa --queryformat '%{NAME}\\t%{VERSION}\\t%{VENDOR}\\n' 2>/dev/null || "
    "pacman -Q 2>/dev/null | awk '{print $1\"\\t\"$2\"\\tArch Linux\"}'); "
    "echo '===SRV==='; systemctl list-units --type=service --no-legend --plain 2>/dev/null; "
    # args last (variable-width, may contain spaces) so the fixed columns
    # before it can be split unambiguously.
    "echo '===PROC==='; ps -eo pid,comm,user,%cpu,rss,args --no-headers 2>/dev/null; "
    "echo '===SEC==='; "
    "echo \"selinux:$(getenforce 2>/dev/null)\"; "
    "echo \"apparmor:$(aa-status --enabled 2>/dev/null && echo enabled || echo disabled)\"; "
    "echo \"ufw:$(ufw status 2>/dev/null | head -1)\"; "
    "sshd -T 2>/dev/null | grep -iE 'permitrootlogin|passwordauthentication'; "
    "echo '===UPTIME==='; uptime -s 2>/dev/null; who 2>/dev/null"
)


def _is_local_ip(ip_str: str) -> bool:
    if not ip_str or ip_str in ("127.0.0.1", "127.0.1.1", "localhost", "0.0.0.0"):
        return True
    try:
        addrs = {"127.0.0.1", "127.0.1.1", "0.0.0.0", "localhost"}
        for info in socket.getaddrinfo(socket.gethostname(), None):
            addrs.add(info[4][0])
        addrs.update(socket.gethostbyname_ex(socket.gethostname())[2])
        try:
            res = subprocess.run(["ip", "-o", "addr", "show"], capture_output=True, text=True, timeout=2)
            for line in res.stdout.splitlines():
                m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", line)
                if m:
                    addrs.add(m.group(1))
        except Exception:
            pass
        return ip_str in addrs
    except Exception:
        return False



async def collect_linux_inventory(target: SshTarget) -> str | None:
    if target.username and (target.password or target.private_key):
        stdout, stderr, rc = await ssh_client.run_command(target, _LINUX_INVENTORY_SCRIPT)
        if rc == 0 and stdout and stdout.strip():
            return stdout
        err_msg = stderr.strip() or f"SSH exited with code {rc}"
        raise RuntimeError(err_msg)

    if _is_local_ip(target.host):
        try:
            proc = await asyncio.create_subprocess_exec(
                "/bin/bash", "-c", _LINUX_INVENTORY_SCRIPT,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            out, _ = await proc.communicate()
            if out and out.decode("utf-8", errors="replace").strip():
                return out.decode("utf-8", errors="replace")
        except Exception:
            pass

    stdout, stderr, rc = await ssh_client.run_command(target, _LINUX_INVENTORY_SCRIPT)
    if rc == 0 and stdout and stdout.strip():
        return stdout
    err_msg = stderr.strip() or f"SSH exited with code {rc}"
    raise RuntimeError(err_msg)





def parse_linux_inventory(raw_stdout: str, device_ip: str) -> dict:
    """Real parsing only — every hardware field a real command didn't
    return stays None (section 2/15's 'never guess, mark unavailable')."""
    sections: dict[str, list[str]] = {}
    current = "os"
    lines: list[str] = []
    tag_map = {
        "===DMI===": "dmi", "===CPU===": "cpu", "===MEM===": "mem", "===DISK===": "disk",
        "===PART===": "part", "===NET===": "net", "===SW===": "sw", "===SRV===": "srv",
        "===PROC===": "proc", "===SEC===": "sec", "===UPTIME===": "uptime",
    }
    for line in raw_stdout.splitlines():
        stripped = line.strip()
        if stripped in tag_map:
            sections[current] = lines
            current = tag_map[stripped]
            lines = []
        else:
            lines.append(line)
    sections[current] = lines

    os_data = "\n".join(sections.get("os", []))
    os_name = None
    os_edition = None
    os_version = None
    pretty_match = re.search(r'PRETTY_NAME="([^"]+)"', os_data)
    if pretty_match:
        os_edition = pretty_match.group(1)
        os_name = os_edition.split()[0]
        version_match = re.search(r'VERSION_ID="([^"]+)"', os_data)
        if version_match:
            os_version = version_match.group(1)

    dmi_lines = [l.strip() for l in sections.get("dmi", []) if l.strip()]
    manufacturer = dmi_lines[0] if len(dmi_lines) > 0 else None
    model = dmi_lines[1] if len(dmi_lines) > 1 else None
    serial_number = dmi_lines[2] if len(dmi_lines) > 2 and dmi_lines[2] not in ("Not Specified", "None") else None
    system_uuid = dmi_lines[3] if len(dmi_lines) > 3 else None
    motherboard = dmi_lines[4] if len(dmi_lines) > 4 else None
    bios_version = dmi_lines[5] if len(dmi_lines) > 5 else None

    processor_name = None
    architecture = None
    cores = None
    logical_processors = None
    current_speed_mhz = None
    max_speed_mhz = None
    for line in sections.get("cpu", []):
        if "Model name:" in line:
            processor_name = line.split(":", 1)[1].strip()
        elif "Architecture:" in line:
            architecture = line.split(":", 1)[1].strip()
        elif line.strip().startswith("CPU(s):"):
            try:
                logical_processors = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif "Core(s) per socket:" in line:
            try:
                cores = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif "CPU max MHz:" in line:
            try:
                current_speed_mhz = int(float(line.split(":", 1)[1].strip()))
                max_speed_mhz = current_speed_mhz
            except ValueError:
                pass

    total_ram_bytes = None
    available_ram_bytes = None
    ram_modules: list[dict] = []
    configured_speed_mhz = None
    # dmidecode -t memory prints one "Memory Device" block per slot, each
    # starting with "Size:" — grouping on "Size:" (not "Locator:") is what
    # correctly separates blocks, since Locator/Speed/Manufacturer can appear
    # in either order around it depending on dmidecode version.
    current_module: dict[str, str] = {}

    def _flush_module():
        if current_module.get("Size") and current_module["Size"] != "No Module Installed":
            ram_modules.append({
                "slot": current_module.get("Locator"),
                "manufacturer": current_module.get("Manufacturer"),
                "capacity": current_module.get("Size"),
                "speed_mhz": current_module.get("Speed"),
            })

    for line in sections.get("mem", []):
        if line.startswith("Mem:"):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    total_ram_bytes = int(parts[1])
                except ValueError:
                    pass
            if len(parts) >= 7:
                try:
                    available_ram_bytes = int(parts[6])
                except ValueError:
                    pass
        elif ":" in line:
            key, _, value = line.strip().partition(":")
            key, value = key.strip(), value.strip()
            if key == "Size" and current_module:
                _flush_module()
                current_module = {}
            current_module[key] = value
    _flush_module()

    for m in ram_modules:
        if m.get("speed_mhz") and configured_speed_mhz is None:
            speed_match = re.search(r"(\d+)", m["speed_mhz"])
            if speed_match:
                configured_speed_mhz = int(speed_match.group(1))

    disks: dict[str, dict] = {}
    for line in sections.get("disk", []):
        fields = dict(re.findall(r'(\w+)="([^"]*)"', line))
        if fields.get("TYPE") != "disk" or not fields.get("NAME"):
            continue
        disks[fields["NAME"]] = {
            "disk_model": fields.get("MODEL") or None,
            "serial_number": fields.get("SERIAL") or None,
            "capacity_bytes": int(fields["SIZE"]) if fields.get("SIZE", "").isdigit() else None,
            "interface_type": fields.get("TRAN") or None,
            "media_type": None,
            "partitions": [],
        }

    partitions = []
    for line in sections.get("part", []):
        parts = line.split()
        if len(parts) >= 6 and parts[0].startswith("/dev/"):
            try:
                partitions.append({
                    "device_node": parts[0], "capacity_bytes": int(parts[1]),
                    "used_bytes": int(parts[2]), "free_space_bytes": int(parts[3]),
                    "filesystem_type": parts[4], "mount_point": parts[5],
                })
            except (ValueError, IndexError):
                pass

    storage_drives = []
    if disks:
        for name, d in disks.items():
            d["partitions"] = [{"name": p["mount_point"], "size_bytes": p["capacity_bytes"]}
                                for p in partitions if p["device_node"].startswith(f"/dev/{name}")]
            storage_drives.append(d)
    elif partitions:
        # No lsblk disk-level data (unprivileged) — fall back to df-derived partitions only.
        storage_drives.append({
            "disk_model": None, "serial_number": None,
            "capacity_bytes": sum(p["capacity_bytes"] for p in partitions),
            "interface_type": None, "media_type": None,
            "partitions": [{"name": p["mount_point"], "size_bytes": p["capacity_bytes"]} for p in partitions],
        })

    interfaces = []
    gateway = None
    dns_servers = [l.split()[1] for l in sections.get("net", []) if l.strip().startswith("nameserver")]
    for line in sections.get("net", []):
        if line.strip().startswith("default"):
            gw_match = re.search(r"default via (\S+)", line)
            if gw_match:
                gateway = gw_match.group(1)
    for line in sections.get("net", []):
        parts = line.split()
        if len(parts) < 4 or "inet" not in parts:
            continue
        ifname = parts[1].rstrip(":")
        if ifname == "lo":
            continue
        try:
            ip_idx = parts.index("inet") + 1
            ip_addr = parts[ip_idx].split("/")[0]
        except (ValueError, IndexError):
            continue
        existing = next((i for i in interfaces if i["interface_name"] == ifname), None)
        if existing:
            existing["ip_addresses"].append(ip_addr)
        else:
            interfaces.append({
                "interface_name": ifname, "mac_address": None, "ip_addresses": [ip_addr],
                "dns_servers": dns_servers, "gateway": gateway, "dhcp_enabled": None, "status": "up",
            })

    software = []
    for line in sections.get("sw", []):
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].strip():
            software.append({
                "name": parts[0].strip(), "version": parts[1].strip(),
                "publisher": parts[2].strip() if len(parts) >= 3 else None,
                "install_date": None,
            })

    services = []
    for line in sections.get("srv", []):
        parts = line.split()
        if len(parts) >= 4 and parts[0].endswith(".service"):
            services.append({
                "name": parts[0].replace(".service", ""),
                "display_name": " ".join(parts[4:]) if len(parts) > 4 else parts[0],
                "status": parts[3] if len(parts) > 3 else None,
                "start_type": parts[1] if len(parts) > 1 else None,
            })

    # ps -eo pid,comm,user,%cpu,rss,args — args last (see script comment)
    # since it's variable-width and may itself contain spaces.
    processes = []
    for line in sections.get("proc", []):
        parts = line.split(None, 5)
        if len(parts) >= 5 and parts[0].isdigit():
            try:
                processes.append({
                    "pid": int(parts[0]), "name": parts[1], "user_name": parts[2],
                    "cpu_percent": float(parts[3]) if _is_float(parts[3]) else None,
                    "memory_bytes": int(parts[4]) * 1024 if parts[4].isdigit() else None,
                    "command_line": parts[5] if len(parts) > 5 else None, "status": None,
                })
            except (ValueError, IndexError):
                pass

    sec = {}
    for line in sections.get("sec", []):
        if line.startswith("selinux:"):
            sec["selinux_status"] = line.split(":", 1)[1].strip().lower() or None
        elif line.startswith("apparmor:"):
            sec["apparmor_status"] = line.split(":", 1)[1].strip().lower() or None
        elif line.startswith("ufw:"):
            ufw_line = line.split(":", 1)[1].strip().lower()
            sec["ufw_active"] = "active" in ufw_line if ufw_line else None
        elif "permitrootlogin" in line.lower():
            sec["ssh_root_login_enabled"] = "yes" in line.lower()
        elif "passwordauthentication" in line.lower():
            sec["ssh_password_auth_enabled"] = "yes" in line.lower()

    uptime_lines = sections.get("uptime", [])
    uptime = uptime_lines[0].strip() if uptime_lines else None
    logged_in_users = ", ".join(sorted({l.split()[0] for l in uptime_lines[1:] if l.strip()})) or None

    return {
        "inv": {
            "computer_name": None,  # set by caller from hostnamectl-equivalent / device.name
            "manufacturer": manufacturer, "model": model, "serial_number": serial_number,
            "bios_version": bios_version, "motherboard": motherboard, "domain": None, "workgroup": None,
            "os_name": os_name, "os_edition": os_edition, "os_build": None, "os_version": os_version,
            "os_install_date": None, "os_last_boot": None, "os_timezone": None,
            "antivirus": None, "bitlocker_status": None, "firewall_status": None,
            "uptime": uptime, "raw_details": {"logged_in_users": logged_in_users},
        },
        "system_uuid": system_uuid,
        "processors": [{
            "processor_name": processor_name, "architecture": architecture, "cores": cores,
            "logical_processors": logical_processors, "current_speed_mhz": current_speed_mhz,
            "max_speed_mhz": max_speed_mhz, "socket_designation": None,
        }] if processor_name or cores else [],
        "memory": [{
            "total_ram_bytes": total_ram_bytes, "available_ram_bytes": available_ram_bytes,
            "memory_slots": len(ram_modules) or None, "ram_modules": ram_modules or None,
            "configured_speed_mhz": configured_speed_mhz,
        }] if total_ram_bytes else [],
        "storage": storage_drives,
        "partitions": partitions,
        "interfaces": interfaces,
        "software": software,
        "services": services,
        "processes": processes,
        "security": sec,
    }


def _is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


_WINDOWS_INVENTORY_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
function Emit($tag, $obj) { Write-Output ("===$tag===" + ($obj | ConvertTo-Json -Compress -Depth 4)) }
Emit SYS (Get-CimInstance Win32_ComputerSystem | Select-Object Name,Manufacturer,Model,Domain,Workgroup,PartOfDomain)
Emit BIOS (Get-CimInstance Win32_BIOS | Select-Object SerialNumber,Version,Manufacturer,ReleaseDate)
Emit BOARD (Get-CimInstance Win32_BaseBoard | Select-Object Product,Manufacturer,SerialNumber)
Emit CPU (Get-CimInstance Win32_Processor | Select-Object Name,Manufacturer,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,CurrentClockSpeed,SocketDesignation)
Emit MEM (Get-CimInstance Win32_PhysicalMemory | Select-Object DeviceLocator,Manufacturer,Capacity,Speed)
Emit OS (Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OSArchitecture,InstallDate,LastBootUpTime)
Emit DISK (Get-CimInstance Win32_DiskDrive | Select-Object DeviceID,Model,SerialNumber,Size,InterfaceType,MediaType,Status)
Emit LOGICALDISK (Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | Select-Object DeviceID,Size,FreeSpace,FileSystem)
Emit NIC (Get-CimInstance Win32_NetworkAdapterConfiguration -Filter "IPEnabled=True" | Select-Object Description,MACAddress,IPAddress,DefaultIPGateway,DNSServerSearchOrder,DHCPEnabled)
Emit NETADAPTER (Get-CimInstance Win32_NetworkAdapter -Filter "PhysicalAdapter=True" | Select-Object Name,Speed,NetConnectionStatus,MACAddress)
Emit SW (Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*,HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* | Where-Object {$_.DisplayName} | Select-Object DisplayName,DisplayVersion,Publisher,InstallDate)
Emit SRV (Get-CimInstance Win32_Service | Select-Object Name,DisplayName,State,StartMode)
Emit PROC (Get-CimInstance Win32_Process | Select-Object ProcessId,Name,CommandLine,WorkingSetSize)
Emit DEFENDER (Get-MpComputerStatus | Select-Object AntivirusEnabled,AntivirusSignatureVersion,RealTimeProtectionEnabled,AntispywareSignatureLastUpdated)
Emit FIREWALL (Get-NetFirewallProfile | Select-Object Name,Enabled)
Emit BITLOCKER (Get-BitLockerVolume | Select-Object MountPoint,ProtectionStatus)
Emit SECUREBOOT (Confirm-SecureBootUEFI)
Emit UPDATES (Get-HotFix | Select-Object HotFixID,InstalledOn | Sort-Object InstalledOn -Descending | Select-Object -First 20)
"""


async def collect_windows_inventory(target: WinRmTarget) -> str | None:
    stdout, _stderr, rc = await run_in_threadpool(run_powershell, target, _WINDOWS_INVENTORY_SCRIPT)
    return stdout if rc == 0 and stdout.strip() else None


def _parse_win_json_block(raw_stdout: str, tag: str) -> Any:
    marker = f"==={tag}==="
    for line in raw_stdout.splitlines():
        if line.startswith(marker):
            payload = line[len(marker):].strip()
            if not payload:
                return None
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                return None
    return None


def _as_list(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def parse_windows_inventory(raw_stdout: str, device_ip: str) -> dict:
    sys_info = _parse_win_json_block(raw_stdout, "SYS") or {}
    bios_info = _parse_win_json_block(raw_stdout, "BIOS") or {}
    board_info = _parse_win_json_block(raw_stdout, "BOARD") or {}
    os_info = _parse_win_json_block(raw_stdout, "OS") or {}
    cpu_list = _as_list(_parse_win_json_block(raw_stdout, "CPU"))
    mem_list = _as_list(_parse_win_json_block(raw_stdout, "MEM"))
    disk_list = _as_list(_parse_win_json_block(raw_stdout, "DISK"))
    logical_disk_list = _as_list(_parse_win_json_block(raw_stdout, "LOGICALDISK"))
    nic_list = _as_list(_parse_win_json_block(raw_stdout, "NIC"))
    net_adapter_list = _as_list(_parse_win_json_block(raw_stdout, "NETADAPTER"))
    sw_list = _as_list(_parse_win_json_block(raw_stdout, "SW"))
    srv_list = _as_list(_parse_win_json_block(raw_stdout, "SRV"))
    proc_list = _as_list(_parse_win_json_block(raw_stdout, "PROC"))
    defender = _parse_win_json_block(raw_stdout, "DEFENDER") or {}
    firewall_list = _as_list(_parse_win_json_block(raw_stdout, "FIREWALL"))
    bitlocker_list = _as_list(_parse_win_json_block(raw_stdout, "BITLOCKER"))
    secure_boot = _parse_win_json_block(raw_stdout, "SECUREBOOT")
    updates_list = _as_list(_parse_win_json_block(raw_stdout, "UPDATES"))

    processors = []
    for c in cpu_list:
        if not c:
            continue
        processors.append({
            "processor_name": c.get("Name"), "architecture": None,
            "cores": c.get("NumberOfCores"), "logical_processors": c.get("NumberOfLogicalProcessors"),
            "current_speed_mhz": c.get("CurrentClockSpeed"), "max_speed_mhz": c.get("MaxClockSpeed"),
            "socket_designation": c.get("SocketDesignation"),
        })

    ram_modules = [{
        "slot": m.get("DeviceLocator"), "manufacturer": m.get("Manufacturer"),
        "capacity": m.get("Capacity"), "speed_mhz": m.get("Speed"),
    } for m in mem_list if m]
    total_ram_bytes = sum(int(m["Capacity"]) for m in mem_list if m and m.get("Capacity")) or None
    speeds = [m["Speed"] for m in mem_list if m and m.get("Speed")]

    storage = []
    for d in disk_list:
        if not d:
            continue
        matching_logical = next((ld for ld in logical_disk_list if ld), None)
        storage.append({
            "disk_model": d.get("Model"), "serial_number": d.get("SerialNumber"),
            "capacity_bytes": d.get("Size"),
            "free_space_bytes": matching_logical.get("FreeSpace") if matching_logical else None,
            "interface_type": d.get("InterfaceType"), "media_type": d.get("MediaType"),
            "health_status": d.get("Status"),
            "partitions": [],
        })
    partitions = [{
        "device_node": ld.get("DeviceID"), "mount_point": ld.get("DeviceID"),
        "filesystem_type": ld.get("FileSystem"), "capacity_bytes": ld.get("Size"),
        "free_space_bytes": ld.get("FreeSpace"),
        "used_bytes": (ld["Size"] - ld["FreeSpace"]) if ld.get("Size") and ld.get("FreeSpace") else None,
    } for ld in logical_disk_list if ld]
    if storage and partitions:
        storage[0]["partitions"] = [{"name": p["mount_point"], "size_bytes": p["capacity_bytes"]} for p in partitions]

    interfaces = []
    for nic in nic_list:
        if not nic:
            continue
        matching_adapter = next((a for a in net_adapter_list if a and a.get("MACAddress") == nic.get("MACAddress")), None)
        interfaces.append({
            "interface_name": nic.get("Description"), "mac_address": nic.get("MACAddress"),
            "ip_addresses": _as_list(nic.get("IPAddress")), "dns_servers": _as_list(nic.get("DNSServerSearchOrder")),
            "gateway": (_as_list(nic.get("DefaultIPGateway")) or [None])[0], "dhcp_enabled": nic.get("DHCPEnabled"),
            "status": "up", "speed_mbps": round(matching_adapter["Speed"] / 1_000_000) if matching_adapter and matching_adapter.get("Speed") else None,
            "interface_type": "ethernet",
        })

    software = [{
        "name": s.get("DisplayName"), "version": s.get("DisplayVersion"),
        "publisher": s.get("Publisher"), "install_date": None,
    } for s in sw_list if s and s.get("DisplayName")]

    services = [{
        "name": s.get("Name"), "display_name": s.get("DisplayName"),
        "status": (s.get("State") or "").lower() or None, "start_type": (s.get("StartMode") or "").lower() or None,
    } for s in srv_list if s]

    processes = [{
        "pid": p.get("ProcessId"), "name": p.get("Name"), "command_line": p.get("CommandLine"),
        "memory_bytes": p.get("WorkingSetSize"), "user_name": None, "cpu_percent": None, "status": None,
    } for p in proc_list if p]

    firewall_profiles = {f.get("Name", "").lower(): bool(f.get("Enabled")) for f in firewall_list if f and f.get("Name")}
    bitlocker_status = None
    if bitlocker_list:
        statuses = {b.get("ProtectionStatus") for b in bitlocker_list if b}
        bitlocker_status = "Enabled" if any(s == 1 for s in statuses) else "Disabled" if statuses else None

    return {
        "inv": {
            "computer_name": sys_info.get("Name"), "manufacturer": sys_info.get("Manufacturer"),
            "model": sys_info.get("Model"), "serial_number": bios_info.get("SerialNumber"),
            "bios_version": bios_info.get("Version"), "motherboard": board_info.get("Product"),
            "domain": sys_info.get("Domain") if sys_info.get("PartOfDomain") else None,
            "workgroup": sys_info.get("Domain") if not sys_info.get("PartOfDomain") else None,
            "os_name": os_info.get("Caption"), "os_edition": None, "os_build": os_info.get("BuildNumber"),
            "os_version": os_info.get("Version"), "os_install_date": os_info.get("InstallDate"),
            "os_last_boot": os_info.get("LastBootUpTime"), "os_timezone": None,
            "antivirus": "Windows Defender" if defender.get("AntivirusEnabled") else None,
            "bitlocker_status": bitlocker_status,
            "firewall_status": "Enabled" if any(firewall_profiles.values()) else ("Disabled" if firewall_profiles else None),
            "uptime": None, "raw_details": {"os_architecture": os_info.get("OSArchitecture")},
        },
        "system_uuid": None,
        "processors": processors,
        "memory": [{
            "total_ram_bytes": total_ram_bytes, "available_ram_bytes": None,
            "memory_slots": len(ram_modules) or None, "ram_modules": ram_modules or None,
            "configured_speed_mhz": speeds[0] if speeds else None,
        }] if total_ram_bytes else [],
        "storage": storage,
        "partitions": partitions,
        "interfaces": interfaces,
        "software": software,
        "services": services,
        "processes": processes,
        "security": {
            "defender_enabled": defender.get("AntivirusEnabled"),
            "defender_signature_version": defender.get("AntivirusSignatureVersion"),
            "firewall_enabled": any(firewall_profiles.values()) if firewall_profiles else None,
            "firewall_profiles": firewall_profiles or None,
            "bitlocker_status": bitlocker_status,
            "secure_boot_enabled": bool(secure_boot) if secure_boot is not None else None,
            "antivirus_product": "Windows Defender" if defender.get("AntivirusEnabled") else None,
            "antivirus_up_to_date": bool(defender.get("RealTimeProtectionEnabled")) if defender else None,
            "pending_updates_count": None,
            "last_update_installed_at": updates_list[0].get("InstalledOn") if updates_list and updates_list[0] else None,
        },
    }


async def collect_network_device_inventory(snmp_target: SnmpTarget) -> dict:
    """SNMP-based collection for routers/switches/firewalls/APs (section 5).
    Every field left None means the device's MIB implementation didn't
    expose it — never fabricated."""
    sys_descr = await snmp_get(snmp_target, snmp_client.OID_SYS_DESCR)
    sys_name = await snmp_get(snmp_target, snmp_client.OID_SYS_NAME)
    sys_uptime = await snmp_get(snmp_target, snmp_client.OID_SYS_UPTIME)

    ent_mfg = await snmp_walk(snmp_target, snmp_client.OID_ENT_PHYSICAL_MFG_NAME)
    ent_model = await snmp_walk(snmp_target, snmp_client.OID_ENT_PHYSICAL_MODEL_NAME)
    ent_serial = await snmp_walk(snmp_target, snmp_client.OID_ENT_PHYSICAL_SERIAL_NUM)
    ent_sw_rev = await snmp_walk(snmp_target, snmp_client.OID_ENT_PHYSICAL_SOFTWARE_REV)

    if_descr = await snmp_walk(snmp_target, snmp_client.OID_IF_DESCR)
    if_mac = await snmp_walk(snmp_target, snmp_client.OID_IF_PHYS_ADDRESS)
    if_oper = await snmp_walk(snmp_target, snmp_client.OID_IF_OPER_STATUS)
    if_high_speed = await snmp_walk(snmp_target, snmp_client.OID_IF_HIGH_SPEED)

    if_mac_by_idx = dict(if_mac)
    if_oper_by_idx = dict(if_oper)
    if_speed_by_idx = dict(if_high_speed)
    interfaces = []
    for idx, descr in if_descr:
        interfaces.append({
            "interface_name": descr, "mac_address": if_mac_by_idx.get(idx) or None,
            "status": "up" if if_oper_by_idx.get(idx) == "1" else "down",
            "speed_mbps": int(if_speed_by_idx[idx]) if if_speed_by_idx.get(idx, "").isdigit() else None,
            "ip_addresses": [], "dns_servers": [], "gateway": None, "dhcp_enabled": None,
            "interface_type": "ethernet",
        })

    cpu_load = await snmp_walk(snmp_target, snmp_client.OID_HR_PROCESSOR_LOAD)
    avg_cpu_load = None
    if cpu_load:
        try:
            avg_cpu_load = round(sum(int(v) for _, v in cpu_load) / len(cpu_load))
        except (ValueError, ZeroDivisionError):
            avg_cpu_load = None

    return {
        "inv": {
            "computer_name": sys_name, "manufacturer": (ent_mfg[0][1] if ent_mfg else None),
            "model": (ent_model[0][1] if ent_model else None),
            "serial_number": (ent_serial[0][1] if ent_serial else None),
            "bios_version": (ent_sw_rev[0][1] if ent_sw_rev else None),
            "motherboard": None, "domain": None, "workgroup": None,
            "os_name": sys_descr, "os_edition": None, "os_build": None, "os_version": None,
            "os_install_date": None, "os_last_boot": None, "os_timezone": None,
            "antivirus": None, "bitlocker_status": None, "firewall_status": None,
            "uptime": sys_uptime, "raw_details": {"sys_descr": sys_descr},
        },
        "processors": [{"processor_name": "SNMP-reported", "cpu_load_percent": avg_cpu_load}] if avg_cpu_load is not None else [],
        "memory": [],
        "storage": [],
        "partitions": [],
        "interfaces": interfaces,
        "software": [],
        "services": [],
        "processes": [],
        "security": {},
    }


async def _finalize_device_scan(db: AsyncSession, device_id: uuid.UUID) -> None:
    scan_history_q = await db.execute(
        select(DeviceScanHistory.scan_id).where(DeviceScanHistory.device_id == device_id).order_by(DeviceScanHistory.created_at.desc()).limit(1)
    )
    latest_scan_id = scan_history_q.scalar_one_or_none()
    if latest_scan_id:
        await finalize_scan_if_complete(db, latest_scan_id)


async def run_inventory_collection(
    db: AsyncSession,
    organization_id: uuid.UUID,
    device_id: uuid.UUID,
    actor_id: uuid.UUID | None = None
) -> None:
    device_q = await db.execute(select(Device).where(and_(
        Device.organization_id == organization_id,
        Device.id == device_id,
        Device.deleted_at.is_(None)
    )))
    device = device_q.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    cred_q = await db.execute(select(Credential).where(and_(
        Credential.organization_id == organization_id,
        Credential.deleted_at.is_(None)
    )))
    credentials = list(cred_q.scalars().all())

    dev_type = device.device_type
    ip = device.ip_address
    device.scan_status = DeviceScanStatus.SCANNING.value
    await db.flush()

    await write_audit_log(
        db, organization_id=organization_id, actor_type="user" if actor_id else "system",
        actor_user_id=actor_id, action="inventory.collect", resource_type="devices",
        resource_id=device.id, before_state={"status": device.status},
    )

    if not ip:
        device.auth_success = False
        device.auth_error = "Device has no known IP address to connect to"
        device.scan_status = DeviceScanStatus.FAILED.value
        await db.commit()
        await _finalize_device_scan(db, device.id)
        return

    is_target_local = _is_local_ip(ip)

    ssh_creds = [c for c in credentials if c.credential_type in (CredentialType.SSH_PASSWORD.value, CredentialType.SSH_KEY.value)]
    winrm_creds = [c for c in credentials if c.credential_type == CredentialType.WINRM.value]
    snmp_creds = [c for c in credentials if c.credential_type in (CredentialType.SNMP_V2C.value, CredentialType.SNMP_V3.value)]

    open_ports_list = device.open_ports.get("ports", []) if (device.open_ports and isinstance(device.open_ports, dict)) else []

    if dev_type == DeviceType.WINDOWS.value or 5985 in open_ports_list or 5986 in open_ports_list:
        ordered_creds = winrm_creds + ssh_creds + snmp_creds
    elif dev_type in (DeviceType.LINUX.value, DeviceType.MACOS.value, DeviceType.VIRTUAL_MACHINE.value, DeviceType.DOCKER_HOST.value, "server") or 22 in open_ports_list or ssh_creds:
        ordered_creds = ssh_creds + winrm_creds + snmp_creds
    else:
        ordered_creds = snmp_creds + ssh_creds + winrm_creds

    credential_candidates: list[tuple[str, dict]] = []
    for cred in ordered_creds:
        try:
            sec = await resolve_credential_secret(db, organization_id=organization_id, credential_id=cred.id)
            credential_candidates.append((cred.credential_type, sec))
        except Exception:
            pass

    if not credential_candidates:
        if is_target_local:
            credential_candidates.append((CredentialType.SSH_PASSWORD.value, {}))
        else:
            credential_candidates.append((CredentialType.SNMP_V2C.value, {"secret": "public", "username": "public"}))

    if not credential_candidates:
        device.auth_success = False
        device.auth_error = "No credentials configured for organization"
        device.scan_status = DeviceScanStatus.CREDENTIALS_REQUIRED.value
        await db.commit()
        await _finalize_device_scan(db, device.id)
        return

    dynamic_data: dict | None = None
    last_error: str | None = None

    for cred_type, secret_dict in credential_candidates:
        try:
            if cred_type == CredentialType.WINRM.value:
                port = 5986 if device.open_ports and 5986 in device.open_ports.get("ports", []) else 5985
                target = WinRmTarget(host=ip, username=secret_dict.get("username", ""), password=secret_dict.get("secret", ""), port=port, ssl=(port == 5986))
                raw = await collect_windows_inventory(target)
                if raw:
                    dynamic_data = parse_windows_inventory(raw, ip)
            elif cred_type in (CredentialType.SSH_PASSWORD.value, CredentialType.SSH_KEY.value):
                target = SshTarget(
                    host=ip, username=secret_dict.get("username", ""),
                    password=secret_dict.get("secret") if cred_type == CredentialType.SSH_PASSWORD.value else None,
                    private_key=secret_dict.get("secret") if cred_type == CredentialType.SSH_KEY.value else None,
                    port=22,
                )
                raw = await collect_linux_inventory(target)
                if raw:
                    dynamic_data = parse_linux_inventory(raw, ip)
                    if dynamic_data.get("system_uuid"):
                        device.uuid = dynamic_data["system_uuid"]
            elif cred_type in (CredentialType.SNMP_V2C.value, CredentialType.SNMP_V3.value):
                snmp_target = SnmpTarget(
                    host=ip,
                    community=secret_dict.get("secret") if cred_type == CredentialType.SNMP_V2C.value else None,
                    version="3" if cred_type == CredentialType.SNMP_V3.value else "2c",
                    username=secret_dict.get("username"),
                )
                dynamic_data = await collect_network_device_inventory(snmp_target)

            if dynamic_data:
                break
        except Exception as e:
            last_error = str(e)
            logger.info("Credential attempt (%s user %s) failed for %s: %s", cred_type, secret_dict.get("username"), ip, e)

    if not dynamic_data:
        device.auth_success = False
        device.auth_error = f"Connection failed: {last_error}" if last_error else "Connected but received no usable telemetry response"
        device.scan_status = DeviceScanStatus.FAILED.value
        await db.commit()
        await _finalize_device_scan(db, device.id)
        return

    device.auth_success = True
    device.auth_error = None

    if dynamic_data and dynamic_data.get("inv"):
        inv_info = dynamic_data["inv"]
        if inv_info.get("os_name"):
            device.operating_system = inv_info["os_name"]
            os_lower = inv_info["os_name"].lower()
            if any(k in os_lower for k in ("ubuntu", "debian", "linux", "centos", "redhat", "fedora", "alpine", "arch")):
                device.device_type = DeviceType.LINUX.value
            elif any(k in os_lower for k in ("windows", "win")):
                device.device_type = DeviceType.WINDOWS.value

    new_inv = dict(dynamic_data.get("inv") or {})
    new_inv.pop("computer_name", None)
    computer_name = (dynamic_data.get("inv") or {}).get("computer_name") or device.name
    new_processors = [{k: v for k, v in p.items() if k != "cpu_load_percent"} for p in dynamic_data.get("processors", [])]
    new_memory = dynamic_data.get("memory", [])
    new_storage_raw = dynamic_data.get("storage", [])
    new_partitions_raw = dynamic_data.get("partitions", [])
    new_interfaces_raw = dynamic_data.get("interfaces", [])
    new_software = dynamic_data.get("software", [])
    new_services = dynamic_data.get("services", [])
    new_processes = dynamic_data.get("processes", [])
    new_security = dynamic_data.get("security", {})
    new_inv.pop("computer_name", None)
    computer_name = (dynamic_data.get("inv") or {}).get("computer_name") or device.name
    new_processors = [{k: v for k, v in p.items() if k != "cpu_load_percent"} for p in dynamic_data.get("processors", [])]
    new_memory = dynamic_data.get("memory", [])
    new_storage_raw = dynamic_data.get("storage", [])
    new_partitions_raw = dynamic_data.get("partitions", [])
    new_interfaces_raw = dynamic_data.get("interfaces", [])
    new_software = dynamic_data.get("software", [])
    new_services = dynamic_data.get("services", [])
    new_processes = dynamic_data.get("processes", [])
    new_security = dynamic_data.get("security", {})

>>>>>>> f631419 (feat: implement Celery-based task orchestration for discovery scans and add SNMP credential support)
    # 1. DeviceInventory (1:1)
    inv_q = await db.execute(select(DeviceInventory).where(DeviceInventory.device_id == device.id))
    inv = inv_q.scalar_one_or_none()
    inv_fields = {**new_inv, "computer_name": computer_name}
    if not inv:
        inv = DeviceInventory(organization_id=organization_id, device_id=device.id, **inv_fields)
        db.add(inv)
        db.add(DeviceInventoryHistory(
            organization_id=organization_id, device_id=device.id, change_type="hardware_added",
            component="system", description=f"Initial system inventory recorded for {computer_name}.",
        ))
    else:
        changed = inv.os_version != inv_fields.get("os_version")
        for k, v in inv_fields.items():
            if v is not None:
                setattr(inv, k, v)
        if changed:
            db.add(DeviceInventoryHistory(
                organization_id=organization_id, device_id=device.id, change_type="status_changed",
                component="system", description=f"OS version changed to {inv_fields.get('os_version')}.",
            ))

    # 2. Processors — delete+reinsert (point-in-time, matches existing convention)
    for p in (await db.execute(select(DeviceProcessor).where(DeviceProcessor.device_id == device.id))).scalars().all():
        await db.delete(p)
    for p in new_processors:
        db.add(DeviceProcessor(organization_id=organization_id, device_id=device.id, **p))

    # 3. Memory
    for m in (await db.execute(select(DeviceMemory).where(DeviceMemory.device_id == device.id))).scalars().all():
        await db.delete(m)
    for m in new_memory:
        db.add(DeviceMemory(organization_id=organization_id, device_id=device.id, **m))

    # 4. Storage + Partitions
    for s in (await db.execute(select(DeviceStorage).where(DeviceStorage.device_id == device.id))).scalars().all():
        await db.delete(s)
    for p in (await db.execute(select(DevicePartition).where(DevicePartition.device_id == device.id))).scalars().all():
        await db.delete(p)
    await db.flush()
    for s in new_storage_raw:
        storage_row = DeviceStorage(
            organization_id=organization_id, device_id=device.id,
            disk_model=s.get("disk_model"), serial_number=s.get("serial_number"),
            capacity_bytes=s.get("capacity_bytes"), free_space_bytes=s.get("free_space_bytes"),
            partitions=s.get("partitions"), interface_type=s.get("interface_type"),
            media_type=s.get("media_type"), health_status=s.get("health_status"),
        )
        db.add(storage_row)
    for p in new_partitions_raw:
        db.add(DevicePartition(
            organization_id=organization_id, device_id=device.id, storage_id=None,
            mount_point=p.get("mount_point"), device_node=p.get("device_node"),
            filesystem_type=p.get("filesystem_type"), capacity_bytes=p.get("capacity_bytes"),
            used_bytes=p.get("used_bytes"), free_space_bytes=p.get("free_space_bytes"),
        ))

    # 5. Network interfaces
    for i in (await db.execute(select(DeviceNetworkInterface).where(DeviceNetworkInterface.device_id == device.id))).scalars().all():
        await db.delete(i)
    for i in new_interfaces_raw:
        db.add(DeviceNetworkInterface(
            organization_id=organization_id, device_id=device.id,
            interface_name=i.get("interface_name") or "unknown", mac_address=i.get("mac_address"),
            ip_addresses=i.get("ip_addresses"), dns_servers=i.get("dns_servers"),
            gateway=i.get("gateway"), dhcp_enabled=i.get("dhcp_enabled"), status=i.get("status", "up"),
            speed_mbps=i.get("speed_mbps"), duplex=i.get("duplex"), interface_type=i.get("interface_type"),
        ))

    # 6. Software (diffed for history, matches existing convention)
    existing_sw = list((await db.execute(select(DeviceInstalledSoftware).where(DeviceInstalledSoftware.device_id == device.id))).scalars().all())
    existing_sw_names = {s.name: s.version for s in existing_sw}
    for sw in new_software:
        if sw["name"] not in existing_sw_names:
            db.add(DeviceInventoryHistory(
                organization_id=organization_id, device_id=device.id, change_type="software_installed",
                component="software", description=f"Installed software: {sw['name']} (version {sw.get('version') or 'unknown'}).",
            ))
        elif existing_sw_names[sw["name"]] != sw.get("version"):
            db.add(DeviceInventoryHistory(
                organization_id=organization_id, device_id=device.id, change_type="software_installed",
                component="software", description=f"Upgraded software {sw['name']} to version {sw.get('version')}.",
            ))
    new_sw_names = {s["name"] for s in new_software}
    for name in existing_sw_names:
        if name not in new_sw_names:
            db.add(DeviceInventoryHistory(
                organization_id=organization_id, device_id=device.id, change_type="software_uninstalled",
                component="software", description=f"Uninstalled software: {name}.",
            ))
    for s in existing_sw:
        await db.delete(s)
    for sw in new_software:
        db.add(DeviceInstalledSoftware(organization_id=organization_id, device_id=device.id, **sw))

    # 7. Services
    for srv in (await db.execute(select(DeviceService).where(DeviceService.device_id == device.id))).scalars().all():
        await db.delete(srv)
    for srv in new_services:
        db.add(DeviceService(organization_id=organization_id, device_id=device.id, **srv))

    # 8. Processes — point-in-time snapshot
    for proc in (await db.execute(select(DeviceProcess).where(DeviceProcess.device_id == device.id))).scalars().all():
        await db.delete(proc)
    now = datetime.utcnow()
    for proc in new_processes:
        if proc.get("pid") is None or not proc.get("name"):
            continue
        db.add(DeviceProcess(organization_id=organization_id, device_id=device.id, collected_at=now, **proc))

    # 9. Security (1:1)
    if new_security:
        sec_q = await db.execute(select(DeviceSecurity).where(DeviceSecurity.device_id == device.id))
        sec = sec_q.scalar_one_or_none()
        sec_fields = {k: v for k, v in new_security.items() if v is not None}
        if not sec:
            db.add(DeviceSecurity(organization_id=organization_id, device_id=device.id, collected_at=now, **sec_fields))
        else:
            for k, v in sec_fields.items():
                setattr(sec, k, v)
            sec.collected_at = now

    device.scan_status = DeviceScanStatus.COMPLETED.value
    await db.commit()

    scan_history_q = await db.execute(
        select(DeviceScanHistory.scan_id).where(DeviceScanHistory.device_id == device.id).order_by(DeviceScanHistory.created_at.desc()).limit(1)
    )
    latest_scan_id = scan_history_q.scalar_one_or_none()
    if latest_scan_id:
        await finalize_scan_if_complete(db, latest_scan_id)


async def run_device_inventory_task(
    db_session_factory: Any,
    organization_id: uuid.UUID,
    device_id: uuid.UUID,
    actor_id: uuid.UUID | None = None
) -> None:
    """Single-attempt wrapper — retry/backoff now lives at the Celery task
    layer (app/workers/tasks/discovery_tasks.py's `self.retry(...)`), not
    here, so this no longer reimplements it manually."""
    async with db_session_factory() as db:
        try:
            await run_inventory_collection(db, organization_id, device_id, actor_id)
        except Exception as e:
            async with db_session_factory() as fail_db:
                device_q = await fail_db.execute(select(Device).where(Device.id == device_id))
                dev = device_q.scalar_one_or_none()
                if dev:
                    dev.auth_success = False
                    dev.auth_error = f"Inventory collection failed: {str(e)}"
                    dev.scan_status = DeviceScanStatus.FAILED.value
                    await fail_db.commit()
            raise


async def get_device_hardware(db: AsyncSession, organization_id: uuid.UUID, device_id: uuid.UUID):
    inv_q = await db.execute(select(DeviceInventory).where(and_(
        DeviceInventory.organization_id == organization_id,
        DeviceInventory.device_id == device_id
    )))
    inventory = inv_q.scalar_one_or_none()

    proc_q = await db.execute(select(DeviceProcessor).where(and_(
        DeviceProcessor.organization_id == organization_id,
        DeviceProcessor.device_id == device_id
    )))
    processors = list(proc_q.scalars().all())

    mem_q = await db.execute(select(DeviceMemory).where(and_(
        DeviceMemory.organization_id == organization_id,
        DeviceMemory.device_id == device_id
    )))
    memory = list(mem_q.scalars().all())

    stor_q = await db.execute(select(DeviceStorage).where(and_(
        DeviceStorage.organization_id == organization_id,
        DeviceStorage.device_id == device_id
    )))
    storage = list(stor_q.scalars().all())

    int_q = await db.execute(select(DeviceNetworkInterface).where(and_(
        DeviceNetworkInterface.organization_id == organization_id,
        DeviceNetworkInterface.device_id == device_id
    )))
    interfaces = list(int_q.scalars().all())

    part_q = await db.execute(select(DevicePartition).where(and_(
        DevicePartition.organization_id == organization_id,
        DevicePartition.device_id == device_id
    )))
    partitions = list(part_q.scalars().all())

    return {
        "inventory": inventory,
        "processors": processors,
        "memory": memory,
        "storage": storage,
        "interfaces": interfaces,
        "partitions": partitions,
    }


async def get_device_software(db: AsyncSession, organization_id: uuid.UUID, device_id: uuid.UUID):
    sw_q = await db.execute(select(DeviceInstalledSoftware).where(and_(
        DeviceInstalledSoftware.organization_id == organization_id,
        DeviceInstalledSoftware.device_id == device_id
    )))
    installed_software = list(sw_q.scalars().all())

    srv_q = await db.execute(select(DeviceService).where(and_(
        DeviceService.organization_id == organization_id,
        DeviceService.device_id == device_id
    )))
    services = list(srv_q.scalars().all())

    return {
        "installed_software": installed_software,
        "services": services
    }


async def get_device_processes(db: AsyncSession, organization_id: uuid.UUID, device_id: uuid.UUID) -> list[DeviceProcess]:
    await get_device_detail(db, organization_id, device_id)
    q = await db.execute(select(DeviceProcess).where(and_(
        DeviceProcess.organization_id == organization_id, DeviceProcess.device_id == device_id
    )).order_by(DeviceProcess.memory_bytes.desc().nullslast()))
    return list(q.scalars().all())


async def get_device_security(db: AsyncSession, organization_id: uuid.UUID, device_id: uuid.UUID) -> DeviceSecurity | None:
    await get_device_detail(db, organization_id, device_id)
    q = await db.execute(select(DeviceSecurity).where(and_(
        DeviceSecurity.organization_id == organization_id, DeviceSecurity.device_id == device_id
    )))
    return q.scalar_one_or_none()


async def get_device_ports(db: AsyncSession, organization_id: uuid.UUID, device_id: uuid.UUID) -> list[DevicePort]:
    await get_device_detail(db, organization_id, device_id)
    q = await db.execute(select(DevicePort).where(and_(
        DevicePort.organization_id == organization_id, DevicePort.device_id == device_id
    )).order_by(DevicePort.port_number.asc()))
    return list(q.scalars().all())


async def get_device_all_history(db: AsyncSession, organization_id: uuid.UUID, device_id: uuid.UUID):
    ip_q = await db.execute(select(DeviceIPHistory).where(and_(
        DeviceIPHistory.organization_id == organization_id,
        DeviceIPHistory.device_id == device_id
    )).order_by(DeviceIPHistory.changed_at.desc()))
    ip_history = list(ip_q.scalars().all())

    scan_q = await db.execute(select(DeviceScanHistory).where(and_(
        DeviceScanHistory.organization_id == organization_id,
        DeviceScanHistory.device_id == device_id
    )).order_by(DeviceScanHistory.created_at.desc()))
    scan_history = list(scan_q.scalars().all())

    inv_q = await db.execute(select(DeviceInventoryHistory).where(and_(
        DeviceInventoryHistory.organization_id == organization_id,
        DeviceInventoryHistory.device_id == device_id
    )).order_by(DeviceInventoryHistory.created_at.desc()))
    inventory_history = list(inv_q.scalars().all())

    return {
        "ip_history": ip_history,
        "scan_history": scan_history,
        "inventory_history": inventory_history
    }
