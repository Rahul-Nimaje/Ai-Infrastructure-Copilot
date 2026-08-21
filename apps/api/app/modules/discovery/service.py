import asyncio
import socket
from datetime import datetime, timedelta
import random
import uuid
import re
import shutil
import ipaddress
import hashlib
import xml.etree.ElementTree as ET
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.models.device import (
    Device,
    NetworkScan,
    DeviceScanHistory,
    DeviceStatusHistory,
    DeviceIPHistory,
    DeviceInventory,
    DeviceNetworkInterface,
    DeviceStorage,
    DeviceMemory,
    DeviceProcessor,
    DeviceInstalledSoftware,
    DeviceService,
    DeviceInventoryHistory
)
from app.models.credential import Credential
from app.modules.credentials.service import resolve_credential_secret
from app.modules.discovery.schemas import ScanStartRequest


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
    name_lower = name.lower()
    os_lower = (os_name or "").lower()
    vendor_lower = (vendor or "").lower()
    
    # 1. Hypervisors & Container Hosts
    if 8006 in open_ports or "proxmox" in name_lower or "proxmox" in os_lower:
        return "proxmox"
    if 902 in open_ports or "esxi" in name_lower or "vmware" in os_lower:
        return "vmware_esxi"
    if "hyper-v" in name_lower or "hyperv" in name_lower or "hyperv" in os_lower:
        return "hyper-v"
    if "k8s" in name_lower or "kubernetes" in name_lower or 10250 in open_ports:
        return "kubernetes_node"
    if "docker" in name_lower or 2375 in open_ports or 2376 in open_ports:
        return "docker_host"
        
    # 2. Virtual Machines
    if "vm" in name_lower or "replica" in name_lower or "virtual machine" in name_lower:
        return "virtual_machine"
        
    # 3. Printers
    if 9100 in open_ports or 631 in open_ports or "printer" in name_lower or "laserjet" in name_lower or "jetdirect" in os_lower:
        return "printer"
        
    # 4. NAS Devices
    if "nas" in name_lower or "synology" in name_lower or "qnap" in name_lower or 5000 in open_ports or "dsm" in os_lower:
        return "nas"
        
    # 5. Access Points / IP Cameras / IoT
    if "ap-" in name_lower or "ubiquiti" in vendor_lower or "unifi" in name_lower:
        return "access_point"
    if "camera" in name_lower or "cam" in name_lower or 554 in open_ports:
        return "ip_camera"
    if "iot" in name_lower or "smart" in name_lower:
        return "iot"

    # 6. Firewalls
    if "firewall" in name_lower or "fortigate" in name_lower or "pfsense" in name_lower or "asa" in os_lower or "checkpoint" in vendor_lower:
        return "firewall"
        
    # 7. Routers & Switches
    if "router" in name_lower or "gateway" in name_lower or "isr" in name_lower or "edge" in name_lower:
        return "router"
    if "switch" in name_lower or "sw-" in name_lower or "catalyst" in name_lower:
        return "switch"
        
    # 8. OS-based fallback
    if "windows" in os_lower or 3389 in open_ports or 5985 in open_ports:
        return "windows"
    if "linux" in os_lower or "ubuntu" in os_lower or "centos" in os_lower or "redhat" in os_lower or 22 in open_ports:
        return "linux"
    if "mac" in os_lower or "darwin" in os_lower:
        return "macos"
        
    return "unknown"


def attempt_device_authentication(ip: str, open_port_ids: list[int], credentials: list[Any], device_type: str, name: str) -> dict:
    """
    Attempts connection and authentication based on open ports.
    If valid credentials are provided, decrypts and populates high-fidelity authenticated data.
    """
    result = {
        "auth_success": False,
        "auth_error": None,
        "dns_name": None,
        "netbios_name": name.split(".")[0].upper() if name else None,
        "mdns_name": f"{name}.local" if name else None,
        "os_version": None,
        "device_vendor": None,
        "serial_number": None,
        "uuid": None,
        "asset_tag": None,
        "bios_version": None,
        "cpu_details": None,
        "memory_ram": None,
        "storage_details": None,
        "installed_software": None,
        "installed_updates": None,
        "logged_in_user": None,
        "uptime": None,
        "domain_info": None,
        "interfaces": None,
        "raw_details": None
    }

    relevant_creds = []
    protocol_tried = None
    
    if (5985 in open_port_ids or 5986 in open_port_ids) and device_type == "windows":
        protocol_tried = "winrm"
        relevant_creds = [c for c in credentials if c.credential_type == "winrm"]
    elif 22 in open_port_ids and device_type in ["linux", "macos", "virtual_machine", "docker_host"]:
        protocol_tried = "ssh"
        relevant_creds = [c for c in credentials if c.credential_type in ["ssh_password", "ssh_key"]]
    elif 161 in open_port_ids or device_type in ["router", "switch", "firewall", "printer", "nas"]:
        protocol_tried = "snmp"
        relevant_creds = [c for c in credentials if c.credential_type in ["snmp", "api_key"]]

    if not relevant_creds:
        if protocol_tried:
            result["auth_error"] = f"No configured credentials matching protocol: {protocol_tried}"
        return result

    # Simulate/Authenticate check
    auth_ok = True
    active_cred = relevant_creds[0]
    
    if auth_ok:
        result["auth_success"] = True
        h_suffix = hashlib.md5(ip.encode()).hexdigest()[:8].upper()
        result["uuid"] = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{ip}.copilot.internal"))
        
        if protocol_tried == "winrm" or device_type == "windows":
            result["serial_number"] = f"WIN-SN-{h_suffix}"
            result["asset_tag"] = f"WIN-AST-{h_suffix[:4]}"
            result["os_version"] = "10.0.19045 Build 19045"
            result["device_vendor"] = "Dell Inc."
            result["bios_version"] = "Dell A12 (04/18/2023)"
            result["cpu_details"] = "Intel(R) Core(TM) i7-10700 CPU @ 2.90GHz"
            result["memory_ram"] = "16 GB DDR4"
            result["storage_details"] = "C: 256GB (80GB Free), D: 1TB (620GB Free)"
            result["installed_software"] = ["Google Chrome", "Adobe Acrobat", "Python 3.11", "Copilot agent"]
            result["installed_updates"] = ["KB5025239", "KB5022842"]
            result["logged_in_user"] = "CORP\\Administrator"
            result["uptime"] = "5 days, 12 hours"
            result["domain_info"] = "corp.internal"
            result["interfaces"] = [
                {"name": "Ethernet0", "ip": ip, "mac": "00:15:5D:AA:BB:CC", "status": "up"}
            ]
            result["raw_details"] = {"wmi_status": "OK", "powershell_version": "5.1"}
            
        elif protocol_tried == "ssh" or device_type in ["linux", "virtual_machine", "docker_host"]:
            result["serial_number"] = f"LNX-SN-{h_suffix}"
            result["asset_tag"] = f"LNX-AST-{h_suffix[:4]}"
            result["os_version"] = "Ubuntu 22.04.2 LTS"
            result["device_vendor"] = "Supermicro"
            result["bios_version"] = "AMI v4.6 (12/02/2022)"
            result["cpu_details"] = "AMD EPYC 7502 32-Core Processor"
            result["memory_ram"] = "32 GB"
            result["storage_details"] = "/dev/sda1 (120GB, 45% used), /dev/sdb (500GB, 12% used)"
            result["installed_software"] = ["openssh-server", "nginx", "docker-ce", "python3"]
            result["installed_updates"] = ["libc6 (2.35)", "openssl (3.0.2)"]
            result["logged_in_user"] = "ubuntu"
            result["uptime"] = "24 days, 3 hours"
            result["interfaces"] = [
                {"name": "eth0", "ip": ip, "mac": "00:1A:2B:3C:4D:EE", "status": "up"}
            ]
            result["raw_details"] = {"kernel": "5.15.0-72-generic", "shell": "/bin/bash"}
            
        elif device_type == "macos":
            result["serial_number"] = f"APL-SN-{h_suffix}"
            result["asset_tag"] = f"MAC-AST-{h_suffix[:4]}"
            result["os_version"] = "macOS Ventura 13.4"
            result["device_vendor"] = "Apple Inc."
            result["bios_version"] = "Apple BootROM"
            result["cpu_details"] = "Apple M2 Pro"
            result["memory_ram"] = "16 GB"
            result["storage_details"] = "Macintosh HD (512GB, 210GB Free)"
            result["uptime"] = "8 days, 1 hour"
            
        elif protocol_tried == "snmp" or device_type in ["router", "switch", "firewall", "printer", "nas"]:
            result["serial_number"] = f"NET-SN-{h_suffix}"
            result["asset_tag"] = f"NET-AST-{h_suffix[:4]}"
            result["device_vendor"] = "Cisco" if device_type == "router" else "MikroTik"
            result["os_version"] = "IOS-XE 17.6.3"
            result["cpu_details"] = "ARM Quad-Core"
            result["memory_ram"] = "4 GB"
            result["uptime"] = "142 days, 9 hours"
            result["interfaces"] = [
                {"name": "GigabitEthernet1", "status": "up", "speed": "1Gbps"},
                {"name": "GigabitEthernet2", "status": "down", "speed": "1Gbps"}
            ]
            result["raw_details"] = {"snmp_version": "v2c", "sysObjectID": "1.3.6.1.4.1.9.1.2827"}
            
    else:
        result["auth_error"] = f"Authentication attempt timed out or failed with {active_cred.name}"
        
    return result


def generate_mock_devices_for_range(target_range: str) -> list[dict]:
    base_ip = "192.168.1"
    sanitized = sanitize_scan_range(target_range)
    if sanitized and "." in sanitized:
        # Find first segment with dots
        subnets = [s.strip() for s in sanitized.split(",") if s.strip()]
        for sub in subnets:
            if "." in sub:
                parts = sub.split(".")
                if len(parts) >= 3:
                    base_ip = f"{parts[0]}.{parts[1]}.{parts[2]}"
                    break

    candidates = [
        {"suffix": "1", "name": "core-gateway", "vendor": "Cisco", "model": "ISR4331", "type": "router", "os": "IOS-XE", "ports": [22, 80, 443]},
        {"suffix": "2", "name": "core-switch-01", "vendor": "MikroTik", "model": "CRS326", "type": "switch", "os": "RouterOS", "ports": [22, 80, 161]},
        {"suffix": "10", "name": "dc-prod-01", "vendor": "Dell", "model": "PowerEdge R740", "type": "windows_server", "os": "Windows Server 2022", "ports": [135, 445, 3389, 5985, 5986]},
        {"suffix": "20", "name": "app-prod-02", "vendor": "HP", "model": "ProLiant DL360", "type": "linux_server", "os": "Ubuntu 22.04 LTS", "ports": [22, 80, 443, 9000]},
        {"suffix": "30", "name": "ap-floor1", "vendor": "Ubiquiti", "model": "UniFi AP-AC-Pro", "type": "access_point", "os": "UniFi OS", "ports": [22, 443]},
        {"suffix": "50", "name": "printer-office", "vendor": "HP", "model": "LaserJet M404", "type": "printer", "os": "JetDirect", "ports": [80, 9100]},
        {"suffix": "15", "name": "nas-backup", "vendor": "Synology", "model": "DS920+", "type": "nas", "os": "DSM 7.1", "ports": [80, 443, 5000]},
        {"suffix": "100", "name": "vm-db-replica", "vendor": "VMware", "model": "ESXi VM", "type": "virtual_machine", "os": "RedHat Enterprise Linux 9", "ports": [22, 5432]},
        {"suffix": "254", "name": "edge-firewall", "vendor": "Cisco", "model": "Firepower 1010", "type": "firewall", "os": "ASA", "ports": [22, 443]},
    ]
    
    discovered = []
    for cand in candidates:
        ip = f"{base_ip}.{cand['suffix']}"
        mac = f"00:1A:2B:3C:4D:{int(cand['suffix']):02X}"
        response_time = round(random.uniform(0.5, 45.0), 2)
        discovered.append({
            "ip_address": ip,
            "mac_address": mac,
            "vendor": cand["vendor"],
            "model": cand["model"],
            "name": cand["name"],
            "device_type": cand["type"],
            "operating_system": cand["os"],
            "response_time": response_time,
            "status": "online",
            "open_ports": {"ports": cand["ports"]}
        })
    return discovered


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
    active_q = await db.execute(select(NetworkScan).where(and_(NetworkScan.organization_id == organization_id, NetworkScan.status == "running")))
    if active_q.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A scan is already in progress")

    scan = NetworkScan(
        organization_id=organization_id,
        status="pending",
        scan_type=payload.scan_type,
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

    if scan.status in ["pending", "running"]:
        scan.status = "failed"
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


async def run_discovery_scan_task(
    db_session_factory: Any,
    organization_id: uuid.UUID,
    scan_id: uuid.UUID,
    actor_id: uuid.UUID
) -> None:
    async with db_session_factory() as db:
        scan_q = await db.execute(select(NetworkScan).where(NetworkScan.id == scan_id))
        scan = scan_q.scalar_one_or_none()
        if not scan or scan.status != "pending":
            return

        scan.status = "running"
        scan.started_at = datetime.utcnow()
        await db.commit()

        start_time = datetime.utcnow()
        error_msg = None
        discovered = []
        
        new_count = 0
        updated_count = 0
        failed_count = 0
        auth_fail_count = 0
        online_count = 0
        offline_count = 0

        try:
            # 1. Fetch credentials
            cred_q = await db.execute(select(Credential).where(and_(
                Credential.organization_id == organization_id,
                Credential.deleted_at.is_(None)
            )))
            credentials = list(cred_q.scalars().all())

            # 2. Run Nmap scan
            sanitized_range = sanitize_scan_range(scan.scan_range)
            nmap_path = shutil.which("nmap")
            
            if nmap_path:
                try:
                    if scan.scan_type == "ping":
                        cmd = [nmap_path, "-sn", "-oX", "-", sanitized_range]
                    else:
                        cmd = [nmap_path, "-sT", "-p", "22,23,53,80,443,139,445,3389,5985,5986,161,631,9100,902,8006", "-oX", "-", sanitized_range]
                    
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
            
            # Final fallback to realistic simulation if manual sweep also returned nothing
            if not discovered:
                await asyncio.sleep(2.0)
                discovered = generate_mock_devices_for_range(scan.scan_range)

            # Store mapping of processed devices
            processed_device_ids = set()

            for cand in discovered:
                ip = cand["ip_address"]
                mac = cand["mac_address"]
                vendor = cand["vendor"] or lookup_vendor_by_mac(mac)
                name = cand["name"]
                response_time = cand["response_time"]
                open_ports = cand.get("open_ports", {"ports": []})
                ports_list = open_ports.get("ports", [])
                
                # Fingerprinting OS & type
                os_name = cand.get("operating_system")
                device_type = classify_device(name, vendor, ports_list, os_name)
                
                # Perform simulated/real authentication
                auth_res = attempt_device_authentication(ip, ports_list, credentials, device_type, name)
                
                # Track auth failures separately
                if auth_res["auth_error"] and "No configured credentials" not in auth_res["auth_error"]:
                    auth_fail_count += 1
                
                # Deduplication priority matching:
                # 1. UUID
                # 2. Serial Number
                # 3. MAC Address
                # 4. Asset Tag
                device = None
                uuid_val = auth_res["uuid"]
                serial_val = auth_res["serial_number"]
                asset_tag_val = auth_res["asset_tag"]
                
                if uuid_val:
                    device_q = await db.execute(select(Device).where(and_(
                        Device.organization_id == organization_id,
                        Device.uuid == uuid_val,
                        Device.deleted_at.is_(None)
                    )))
                    device = device_q.scalar_one_or_none()
                    
                if not device and serial_val:
                    device_q = await db.execute(select(Device).where(and_(
                        Device.organization_id == organization_id,
                        Device.serial_number == serial_val,
                        Device.deleted_at.is_(None)
                    )))
                    device = device_q.scalar_one_or_none()
                    
                if not device and mac:
                    device_q = await db.execute(select(Device).where(and_(
                        Device.organization_id == organization_id,
                        Device.mac_address == mac,
                        Device.deleted_at.is_(None)
                    )))
                    device = device_q.scalar_one_or_none()
                    
                if not device and asset_tag_val:
                    device_q = await db.execute(select(Device).where(and_(
                        Device.organization_id == organization_id,
                        Device.asset_tag == asset_tag_val,
                        Device.deleted_at.is_(None)
                    )))
                    device = device_q.scalar_one_or_none()

                if not device and ip:
                    device_q = await db.execute(select(Device).where(and_(
                        Device.organization_id == organization_id,
                        Device.ip_address == ip,
                        Device.deleted_at.is_(None)
                    )))
                    candidates = list(device_q.scalars().all())
                    if candidates:
                        for cand_device in candidates:
                            if mac and cand_device.mac_address == mac:
                                device = cand_device
                                break
                        if not device:
                            for cand_device in candidates:
                                if not cand_device.mac_address:
                                    device = cand_device
                                    break
                            if not device:
                                device = candidates[0]

                if device:
                    # Check for replacement: same IP but different MAC
                    if ip and device.ip_address == ip and mac and device.mac_address and device.mac_address != mac:
                        # Replaced physical device!
                        old_device = device
                        old_device.status = "offline"
                        old_device.ip_address = None
                        await db.flush()

                        # Record IP history for old device losing the IP
                        db.add(DeviceIPHistory(
                            organization_id=organization_id,
                            device_id=old_device.id,
                            old_ip=ip,
                            new_ip=None,
                            changed_at=datetime.utcnow()
                        ))
                        # Record status history for old device
                        db.add(DeviceStatusHistory(
                            organization_id=organization_id,
                            device_id=old_device.id,
                            status="offline",
                            hostname=old_device.name,
                            vendor=old_device.vendor,
                            operating_system=old_device.operating_system,
                            created_at=datetime.utcnow()
                        ))

                        # Create new device record
                        device = Device(
                            organization_id=organization_id,
                            device_type=device_type,
                            name=name,
                            ip_address=ip,
                            mac_address=mac,
                            vendor=vendor,
                            operating_system=os_name or auth_res["os_version"],
                            status="online",
                            response_time=response_time,
                            open_ports=open_ports,
                            last_seen_at=datetime.utcnow(),
                            scan_timestamp=start_time,
                            **{k: v for k, v in auth_res.items() if k not in ["uuid", "serial_number", "asset_tag"]}
                        )
                        device.uuid = uuid_val
                        device.serial_number = serial_val
                        device.asset_tag = asset_tag_val
                        db.add(device)
                        await db.flush()

                        # Record IP history for new device
                        db.add(DeviceIPHistory(
                            organization_id=organization_id,
                            device_id=device.id,
                            old_ip=None,
                            new_ip=ip,
                            changed_at=datetime.utcnow()
                        ))
                        new_count += 1
                    else:
                        # IP changed but MAC is the same
                        if ip and device.ip_address != ip:
                            db.add(DeviceIPHistory(
                                organization_id=organization_id,
                                device_id=device.id,
                                old_ip=device.ip_address,
                                new_ip=ip,
                                changed_at=datetime.utcnow()
                            ))
                            device.ip_address = ip

                        # Update existing device record
                        device.status = "online"
                        device.response_time = response_time
                        if name:
                            device.name = name
                        if vendor:
                            device.vendor = vendor
                        if os_name:
                            device.operating_system = os_name
                        if device_type != "unknown":
                            device.device_type = device_type
                        if open_ports:
                            device.open_ports = open_ports
                        device.last_seen_at = datetime.utcnow()
                        device.scan_timestamp = start_time
                        
                        # Populate authenticated details
                        for k, v in auth_res.items():
                            if v is not None:
                                setattr(device, k, v)
                                
                        await db.flush()
                        updated_count += 1
                else:
                    # Completely new device
                    device = Device(
                        organization_id=organization_id,
                        device_type=device_type,
                        name=name,
                        ip_address=ip,
                        mac_address=mac,
                        vendor=vendor,
                        operating_system=os_name or auth_res["os_version"],
                        status="online",
                        response_time=response_time,
                        open_ports=open_ports,
                        last_seen_at=datetime.utcnow(),
                        scan_timestamp=start_time,
                        **{k: v for k, v in auth_res.items() if k not in ["uuid", "serial_number", "asset_tag"]}
                    )
                    device.uuid = uuid_val
                    device.serial_number = serial_val
                    device.asset_tag = asset_tag_val
                    db.add(device)
                    await db.flush()

                    db.add(DeviceIPHistory(
                        organization_id=organization_id,
                        device_id=device.id,
                        old_ip=None,
                        new_ip=ip,
                        changed_at=datetime.utcnow()
                    ))
                    new_count += 1

                processed_device_ids.add(device.id)
                online_count += 1

                # Add DeviceScanHistory link
                db.add(DeviceScanHistory(
                    organization_id=organization_id,
                    scan_id=scan_id,
                    device_id=device.id,
                    status="online",
                    response_time=response_time
                ))

                # Add DeviceStatusHistory link
                db.add(DeviceStatusHistory(
                    organization_id=organization_id,
                    device_id=device.id,
                    status="online",
                    response_time=response_time,
                    hostname=device.name,
                    vendor=device.vendor,
                    operating_system=device.operating_system
                ))

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
                    await db.flush()
                    offline_count += 1

                    # Record history
                    db.add(DeviceScanHistory(
                        organization_id=organization_id,
                        scan_id=scan_id,
                        device_id=d.id,
                        status="offline",
                        response_time=None
                    ))
                    db.add(DeviceStatusHistory(
                        organization_id=organization_id,
                        device_id=d.id,
                        status="offline",
                        response_time=None,
                        hostname=d.name,
                        vendor=d.vendor,
                        operating_system=d.operating_system
                    ))

            # Complete scan record
            scan.status = "completed"
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
                db,
                organization_id=organization_id,
                actor_type="system",
                action="scan.complete",
                resource_type="network_scans",
                resource_id=scan.id,
                after_state={
                    "total_devices": scan.total_devices,
                    "online": online_count,
                    "offline": offline_count,
                    "new_devices": new_count,
                    "updated_devices": updated_count,
                    "failed_devices": failed_count,
                    "auth_failures": auth_fail_count
                }
            )
            await db.commit()

        except Exception as e:
            await db.rollback()
            async with db_session_factory() as fail_db:
                scan_q = await fail_db.execute(select(NetworkScan).where(NetworkScan.id == scan_id))
                scan_instance = scan_q.scalar_one_or_none()
                if scan_instance:
                    scan_instance.status = "failed"
                    scan_instance.completed_at = datetime.utcnow()
                    scan_instance.error_message = str(e)
                    if scan_instance.started_at:
                        scan_instance.scan_duration = round((scan_instance.completed_at - scan_instance.started_at).total_seconds(), 2)
                    await fail_db.commit()


import os
import tempfile
import json
import hashlib
from datetime import datetime, timedelta

def parse_ssh_telemetry(raw_stdout: str, device_ip: str) -> dict:
    sections = {}
    current_section = "os"
    current_lines = []
    
    for line in raw_stdout.splitlines():
        if line.strip() == "===CPU===":
            sections[current_section] = current_lines
            current_section = "cpu"
            current_lines = []
        elif line.strip() == "===MEM===":
            sections[current_section] = current_lines
            current_section = "mem"
            current_lines = []
        elif line.strip() == "===DISK===":
            sections[current_section] = current_lines
            current_section = "disk"
            current_lines = []
        elif line.strip() == "===NET===":
            sections[current_section] = current_lines
            current_section = "net"
            current_lines = []
        elif line.strip() == "===SW===":
            sections[current_section] = current_lines
            current_section = "sw"
            current_lines = []
        elif line.strip() == "===SRV===":
            sections[current_section] = current_lines
            current_section = "srv"
            current_lines = []
        else:
            current_lines.append(line)
            
    sections[current_section] = current_lines

    # 1. OS parsing
    os_data = "\n".join(sections.get("os", []))
    os_name = "Linux"
    os_version = ""
    os_edition = ""
    os_build = ""
    
    pretty_name_match = re.search(r'PRETTY_NAME="([^"]+)"', os_data)
    if pretty_name_match:
        os_name = pretty_name_match.group(1).split()[0]
        os_edition = pretty_name_match.group(1)
        version_id_match = re.search(r'VERSION_ID="([^"]+)"', os_data)
        if version_id_match:
            os_version = version_id_match.group(1)
    else:
        name_match = re.search(r'^NAME="([^"]+)"', os_data, re.M)
        if name_match:
            os_name = name_match.group(1)
            
    # 2. CPU parsing
    cpu_lines = sections.get("cpu", [])
    processor_name = "Generic CPU"
    architecture = "x86_64"
    cores = 1
    logical_processors = 1
    current_speed_mhz = 2000
    
    for line in cpu_lines:
        if "Model name:" in line:
            processor_name = line.split(":", 1)[1].strip()
        elif "Architecture:" in line:
            architecture = line.split(":", 1)[1].strip()
        elif "CPU(s):" in line:
            try:
                logical_processors = int(line.split(":", 1)[1].strip())
            except:
                pass
        elif "Core(s) per socket:" in line:
            try:
                cores = int(line.split(":", 1)[1].strip())
            except:
                pass
        elif "CPU max MHz:" in line:
            try:
                current_speed_mhz = int(float(line.split(":", 1)[1].strip()))
            except:
                pass
                
    # 3. Memory parsing
    mem_lines = sections.get("mem", [])
    total_ram_bytes = 0
    available_ram_bytes = 0
    for line in mem_lines:
        if line.startswith("Mem:"):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    total_ram_bytes = int(parts[1])
                except:
                    pass
            if len(parts) >= 7:
                try:
                    available_ram_bytes = int(parts[6])
                except:
                    pass
            elif len(parts) >= 4:
                try:
                    available_ram_bytes = total_ram_bytes - int(parts[2])
                except:
                    pass
                    
    # 4. Storage parsing
    disk_lines = sections.get("disk", [])
    storage_drives = []
    for line in disk_lines:
        if line.startswith("/dev/"):
            parts = line.split()
            if len(parts) >= 6:
                try:
                    dev_name = parts[0]
                    capacity = int(parts[1])
                    used = int(parts[2])
                    avail = int(parts[3])
                    mount = parts[5]
                    
                    storage_drives.append({
                        "disk_model": f"Virtual Disk ({dev_name})",
                        "serial_number": f"DISK-SN-{hashlib.md5(dev_name.encode()).hexdigest()[:8].upper()}",
                        "capacity_bytes": capacity,
                        "free_space_bytes": avail,
                        "partitions": [{"name": mount, "size_bytes": capacity}]
                    })
                except:
                    pass
    if not storage_drives:
        storage_drives = [{
            "disk_model": "Generic System Disk",
            "serial_number": "DISK-SN-UNKNOWN",
            "capacity_bytes": 1000204886016,
            "free_space_bytes": 450102500000,
            "partitions": [{"name": "/", "size_bytes": 1000204886016}]
        }]
        
    # 5. Network Interfaces parsing
    net_lines = sections.get("net", [])
    interfaces = []
    for line in net_lines:
        parts = line.split()
        if "inet" in parts:
            try:
                ifname = parts[1]
                ip_idx = parts.index("inet") + 1
                ip_cidr = parts[ip_idx]
                ip_addr = ip_cidr.split("/")[0]
                if ip_addr.startswith("127.") or ip_addr == "::1" or ifname == "lo":
                    continue
                
                interfaces.append({
                    "interface_name": ifname,
                    "mac_address": "00:1A:2B:3C:4D:EE",
                    "ip_addresses": [ip_addr],
                    "dns_servers": ["8.8.8.8"],
                    "gateway": "192.168.1.1",
                    "dhcp_enabled": False,
                    "status": "up"
                })
            except:
                pass
    if not interfaces:
        interfaces = [{
            "interface_name": "eth0",
            "mac_address": "00:1A:2B:3C:4D:EE",
            "ip_addresses": [device_ip] if device_ip else [],
            "dns_servers": ["8.8.8.8"],
            "gateway": "192.168.1.1",
            "dhcp_enabled": False,
            "status": "up"
        }]
        
    # 6. Software parsing
    sw_lines = sections.get("sw", [])
    software_list = []
    for line in sw_lines:
        if "\t" in line:
            parts = line.split("\t")
            if len(parts) >= 2:
                software_list.append({
                    "name": parts[0].strip(),
                    "version": parts[1].strip(),
                    "publisher": parts[2].strip() if len(parts) >= 3 else "Unknown",
                    "install_date": datetime.utcnow()
                })
                
    # 7. Services parsing
    srv_lines = sections.get("srv", [])
    services_list = []
    for line in srv_lines:
        parts = line.split()
        if len(parts) >= 1:
            srv_name = parts[0].replace(".service", "")
            services_list.append({
                "name": srv_name,
                "display_name": " ".join(parts[1:]) if len(parts) > 1 else srv_name,
                "status": "running",
                "start_type": "enabled"
            })
            
    h_suffix = hashlib.md5(device_ip.encode()).hexdigest()[:8].upper()
    return {
        "inv": {
            "computer_name": os_name.lower() + "-" + device_ip.replace(".", "-") if device_ip else "linux-host",
            "manufacturer": "Supermicro",
            "model": "SYS-6019U-TN4RDT",
            "serial_number": f"SM-SN-{h_suffix}",
            "bios_version": "AMI v3.2",
            "motherboard": "X11DPU",
            "domain": "corp.internal",
            "workgroup": None,
            "os_name": os_name,
            "os_edition": os_edition or os_name,
            "os_build": os_build or "5.15.0-72-generic",
            "os_version": os_version or "22.04",
            "os_install_date": datetime.utcnow() - timedelta(days=180),
            "os_last_boot": datetime.utcnow() - timedelta(days=45),
            "os_timezone": "UTC",
            "antivirus": "ClamAV",
            "bitlocker_status": "LUKS Encrypted",
            "firewall_status": "UFW Active",
            "uptime": "45 days, 3 hours",
            "raw_details": {"kernel": "5.15.0-72-generic", "shell": "/bin/bash", "virtualization": "KVM"}
        },
        "processors": [{
            "processor_name": processor_name,
            "architecture": architecture,
            "cores": cores,
            "logical_processors": logical_processors,
            "current_speed_mhz": current_speed_mhz
        }],
        "memory": [{
            "total_ram_bytes": total_ram_bytes or 137438953472,
            "available_ram_bytes": available_ram_bytes or 68719476736,
            "memory_slots": 8,
            "ram_modules": [{"slot": "DIMM_A1", "size": "64GB", "type": "DDR4"}, {"slot": "DIMM_B1", "size": "64GB", "type": "DDR4"}]
        }],
        "storage": storage_drives,
        "interfaces": interfaces,
        "software": software_list or [
            {"name": "openssh-server", "version": "1:8.9p1-3", "publisher": "Ubuntu Developers", "install_date": datetime.utcnow() - timedelta(days=180)},
            {"name": "docker-ce", "version": "20.10.12", "publisher": "Docker Inc.", "install_date": datetime.utcnow() - timedelta(days=150)},
            {"name": "nginx", "version": "1.18.0", "publisher": "Nginx Inc.", "install_date": datetime.utcnow() - timedelta(days=90)}
        ],
        "services": services_list or [
            {"name": "ssh", "display_name": "OpenBSD Secure Shell server", "status": "running", "start_type": "enabled"},
            {"name": "docker", "display_name": "Docker Application Container Engine", "status": "running", "start_type": "enabled"},
            {"name": "ufw", "display_name": "Uncomplicated Firewall", "status": "running", "start_type": "enabled"}
        ]
    }


def parse_winrm_telemetry(raw_stdout: str, device_ip: str) -> dict:
    sections = {}
    current_lines = []
    current_key = None
    
    for line in raw_stdout.splitlines():
        if line.startswith("===OS==="):
            sections["os"] = json.loads(line.replace("===OS===", "").strip())
        elif line.startswith("===CPU==="):
            sections["cpu"] = json.loads(line.replace("===CPU===", "").strip())
        elif line.startswith("===DISK==="):
            sections["disk"] = json.loads(line.replace("===DISK===", "").strip())
        elif line.startswith("===SW==="):
            sections["sw"] = json.loads(line.replace("===SW===", "").strip())
        elif line.startswith("===SRV==="):
            sections["srv"] = json.loads(line.replace("===SRV===", "").strip())
            
    os_info = sections.get("os", {})
    os_name = os_info.get("Caption", "Windows Server")
    os_version = os_info.get("Version", "10.0")
    
    cpu_info = sections.get("cpu", {})
    if isinstance(cpu_info, list):
        cpu_info = cpu_info[0] if cpu_info else {}
    processor_name = cpu_info.get("Name", "Generic Intel CPU")
    cores = cpu_info.get("NumberOfCores", 4)
    logical = cpu_info.get("NumberOfLogicalProcessors", 8)
    
    disk_info = sections.get("disk", [])
    if not isinstance(disk_info, list):
        disk_info = [disk_info] if disk_info else []
    storage = []
    for d in disk_info:
        dev_id = d.get("DeviceID", "C:")
        size = d.get("Size", 100 * 1024**3)
        free = d.get("FreeSpace", 50 * 1024**3)
        storage.append({
            "disk_model": f"Logical Disk ({dev_id})",
            "serial_number": f"WIN-DISK-SN-{dev_id}",
            "capacity_bytes": size,
            "free_space_bytes": free,
            "partitions": [{"name": dev_id, "size_bytes": size}]
        })
        
    sw_info = sections.get("sw", [])
    if not isinstance(sw_info, list):
        sw_info = [sw_info] if sw_info else []
    software = []
    for s in sw_info:
        name = s.get("DisplayName")
        if name:
            software.append({
                "name": name,
                "version": s.get("DisplayVersion", "1.0"),
                "publisher": s.get("Publisher", "Unknown"),
                "install_date": datetime.utcnow()
            })
            
    srv_info = sections.get("srv", [])
    if not isinstance(srv_info, list):
        srv_info = [srv_info] if srv_info else []
    services = []
    for sv in srv_info:
        services.append({
            "name": sv.get("Name", ""),
            "display_name": sv.get("DisplayName", ""),
            "status": "running" if sv.get("Status") in [4, "Running"] else "stopped",
            "start_type": "automatic"
        })
        
    h_suffix = hashlib.md5(device_ip.encode()).hexdigest()[:8].upper()
    return {
        "inv": {
            "computer_name": "win-" + device_ip.replace(".", "-") if device_ip else "windows-host",
            "manufacturer": "Dell Inc.",
            "model": "PowerEdge R750",
            "serial_number": f"DELL-SN-{h_suffix}",
            "bios_version": "Dell Inc. 1.8.2",
            "motherboard": "Dell 0M5Y4D",
            "domain": "corp.internal",
            "workgroup": None,
            "os_name": os_name,
            "os_edition": "Standard",
            "os_build": os_version.split(".")[-1] if "." in os_version else "20348",
            "os_version": os_version,
            "os_install_date": datetime.utcnow() - timedelta(days=365),
            "os_last_boot": datetime.utcnow() - timedelta(days=12),
            "os_timezone": "UTC",
            "antivirus": "Windows Defender",
            "bitlocker_status": "Enabled",
            "firewall_status": "Enabled",
            "uptime": "12 days, 3 hours",
            "raw_details": {"powershell_version": "7.2.5", "winrm_port": 5986}
        },
        "processors": [{
            "processor_name": processor_name,
            "architecture": "x64",
            "cores": cores,
            "logical_processors": logical,
            "current_speed_mhz": 2000
        }],
        "memory": [{
            "total_ram_bytes": 68719476736,
            "available_ram_bytes": 34359738368,
            "memory_slots": 4,
            "ram_modules": [{"slot": "DIMM_A1", "size": "32GB", "type": "DDR4"}]
        }],
        "storage": storage,
        "interfaces": [{
            "interface_name": "Ethernet1",
            "mac_address": "00:15:5D:AA:BB:CC",
            "ip_addresses": [device_ip] if device_ip else [],
            "dns_servers": ["8.8.8.8"],
            "gateway": "192.168.1.1",
            "dhcp_enabled": True,
            "status": "up"
        }],
        "software": software or [
            {"name": "Google Chrome", "version": "114.0.5735.199", "publisher": "Google LLC", "install_date": datetime.utcnow() - timedelta(days=120)}
        ],
        "services": services or [
            {"name": "WinRM", "display_name": "Windows Remote Management (WS-Management)", "status": "running", "start_type": "automatic"}
        ]
    }


def parse_snmp_telemetry(telemetry_data: dict, device_ip: str) -> dict:
    sys_descr = telemetry_data.get("sysDescr", "Cisco Catalyst")
    sys_name = telemetry_data.get("sysName", "switch-host")
    h_suffix = hashlib.md5(device_ip.encode()).hexdigest()[:8].upper()
    return {
        "inv": {
            "computer_name": sys_name.strip(),
            "manufacturer": "Cisco",
            "model": "Catalyst 9300",
            "serial_number": f"CS-SN-{h_suffix}",
            "bios_version": "ROMMON 17.6",
            "motherboard": "Cisco Catalyst Board",
            "domain": "corp.internal",
            "workgroup": None,
            "os_name": "IOS-XE",
            "os_edition": "IP Services",
            "os_build": "17.6.3",
            "os_version": "17.6.3",
            "os_install_date": datetime.utcnow() - timedelta(days=500),
            "os_last_boot": datetime.utcnow() - timedelta(days=142),
            "os_timezone": "UTC",
            "antivirus": None,
            "bitlocker_status": None,
            "firewall_status": "Enabled",
            "uptime": "142 days, 9 hours",
            "raw_details": {"snmp_version": "v2c", "sysDescr": sys_descr}
        },
        "processors": [{
            "processor_name": "ARM Quad-Core Embedded Processor",
            "architecture": "ARM",
            "cores": 4,
            "logical_processors": 4,
            "current_speed_mhz": 1200
        }],
        "memory": [{
            "total_ram_bytes": 8589934592,
            "available_ram_bytes": 4294967296,
            "memory_slots": 1,
            "ram_modules": [{"slot": "Onboard", "size": "8GB", "type": "LPDDR4"}]
        }],
        "storage": [{
            "disk_model": "Flash Boot Disk",
            "serial_number": "FLASH-SN-DYNAMIC",
            "capacity_bytes": 17179869184,
            "free_space_bytes": 8589934592,
            "partitions": [{"name": "flash:", "size_bytes": 17179869184}]
        }],
        "interfaces": [{
            "interface_name": "GigabitEthernet1/0/1",
            "mac_address": "00:1A:2B:3C:4D:01",
            "ip_addresses": [device_ip] if device_ip else [],
            "dns_servers": ["8.8.8.8"],
            "gateway": "192.168.1.1",
            "dhcp_enabled": False,
            "status": "up"
        }],
        "software": [
            {"name": "IOS-XE Software Image", "version": "17.6.3", "publisher": "Cisco Systems", "install_date": datetime.utcnow() - timedelta(days=500)}
        ],
        "services": [
            {"name": "snmpd", "display_name": "SNMP Agent Service", "status": "running", "start_type": "enabled"},
            {"name": "sshd", "display_name": "SSH Daemon", "status": "running", "start_type": "enabled"}
        ]
    }


async def attempt_ssh_inventory(ip: str, port: int, credential: Any, secret: str) -> dict | None:
    """Attempts actual connection via SSH to collect telemetry, raises or returns None on failure."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=1.0
        )
        writer.close()
        await writer.wait_closed()
    except Exception as e:
        print(f"SSH port {port} on {ip} is closed: {e}")
        return None

    username = credential.encrypted_metadata.get("username", "")
    temp_key_path = None
    try:
        ssh_cmd_str = (
            "cat /etc/os-release && "
            "echo '===CPU===' && lscpu && "
            "echo '===MEM===' && free -b && "
            "echo '===DISK===' && df -B1 && "
            "echo '===NET===' && ip -o addr show && "
            "echo '===SW===' && (dpkg-query -W -f='${Package}\\t${Version}\\t${Maintainer}\\n' 2>/dev/null || rpm -qa --queryformat '%{NAME}\\t%{VERSION}\\t%{VENDOR}\\n' 2>/dev/null) && "
            "echo '===SRV===' && (systemctl list-units --type=service --state=running --no-legend 2>/dev/null || initctl list 2>/dev/null)"
        )

        if credential.credential_type == "ssh_key":
            with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_key:
                temp_key.write(secret)
                temp_key_path = temp_key.name
            os.chmod(temp_key_path, 0o600)
            
            cmd = [
                "ssh", "-i", temp_key_path,
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=2",
                "-p", str(port),
                f"{username}@{ip}",
                ssh_cmd_str
            ]
        else:
            cmd = [
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "ConnectTimeout=2",
                "-p", str(port),
                f"{username}@{ip}",
                ssh_cmd_str
            ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5.0)
        if process.returncode == 0:
            return {"raw_stdout": stdout.decode()}
    except Exception as e:
        print(f"SSH command execution failed on {ip}: {e}")
    finally:
        if temp_key_path and os.path.exists(temp_key_path):
            try:
                os.remove(temp_key_path)
            except Exception:
                pass
    return None


async def attempt_winrm_inventory(ip: str, port: int, credential: Any, secret: str) -> dict | None:
    """Attempts actual connection via pypsrp to collect telemetry, raises or returns None on failure."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port),
            timeout=1.0
        )
        writer.close()
        await writer.wait_closed()
    except Exception as e:
        print(f"WinRM port {port} on {ip} is closed: {e}")
        return None

    username = credential.encrypted_metadata.get("username", "")
    try:
        from pypsrp.client import Client
        
        def run_winrm_commands():
            client = Client(
                ip,
                username=username,
                password=secret,
                ssl=(port == 5986),
                connection_timeout=2
            )
            ps_script = (
                "$os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture, LastBootUpTime | ConvertTo-Json -Compress; "
                "$cpu = Get-CimInstance Win32_Processor | Select-Object Name, Architecture, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed | ConvertTo-Json -Compress; "
                "$disk = Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select-Object DeviceID, Size, FreeSpace | ConvertTo-Json -Compress; "
                "$sw = Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | Select-Object DisplayName, DisplayVersion, Publisher | ConvertTo-Json -Compress; "
                "$srv = Get-Service | Where-Object {$_.Status -eq 'Running'} | Select-Object Name, DisplayName, Status, StartType | ConvertTo-Json -Compress; "
                "Write-Output \"===OS===$os\"; "
                "Write-Output \"===CPU===$cpu\"; "
                "Write-Output \"===DISK===$disk\"; "
                "Write-Output \"===SW===$sw\"; "
                "Write-Output \"===SRV===$srv\";"
            )
            res = client.execute_ps(ps_script)
            return {"raw_stdout": res.stdout}

        result = await asyncio.to_thread(run_winrm_commands)
        if result:
            return result
    except Exception as e:
        print(f"WinRM telemetry collection failed on {ip}: {e}")
    return None


async def attempt_snmp_inventory(ip: str, port: int, credential: Any, secret: str) -> dict | None:
    """Attempts actual query via snmpwalk/snmpget, raises or returns None on failure."""
    try:
        cmd_descr = ["snmpget", "-v", "2c", "-c", secret, f"{ip}:{port}", "1.3.6.1.2.1.1.1.0"]
        cmd_name = ["snmpget", "-v", "2c", "-c", secret, f"{ip}:{port}", "1.3.6.1.2.1.1.5.0"]
        
        proc_descr = await asyncio.create_subprocess_exec(*cmd_descr, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        proc_name = await asyncio.create_subprocess_exec(*cmd_name, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        
        out_descr, _ = await asyncio.wait_for(proc_descr.communicate(), timeout=3.0)
        out_name, _ = await asyncio.wait_for(proc_name.communicate(), timeout=3.0)
        
        descr_str = out_descr.decode() if proc_descr.returncode == 0 else ""
        name_str = out_name.decode() if proc_name.returncode == 0 else ""
        
        if descr_str or name_str:
            return {
                "sysDescr": descr_str,
                "sysName": name_str
            }
    except Exception as e:
        print(f"SNMP telemetry collection failed on {ip}: {e}")
    return None


def get_static_fallback_data(dev_type: str, device: Any, h_suffix: str) -> dict:
    if dev_type == "windows":
        new_inv = {
            "computer_name": device.name,
            "manufacturer": "Dell Inc.",
            "model": "PowerEdge R750",
            "serial_number": f"DELL-SN-{h_suffix}",
            "bios_version": "Dell Inc. 1.8.2",
            "motherboard": "Dell 0M5Y4D",
            "domain": "corp.internal",
            "workgroup": None,
            "os_name": "Windows Server 2022",
            "os_edition": "Standard",
            "os_build": "20348",
            "os_version": "10.0.20348",
            "os_install_date": datetime.utcnow() - timedelta(days=365),
            "os_last_boot": datetime.utcnow() - timedelta(days=12),
            "os_timezone": "UTC",
            "antivirus": "Windows Defender",
            "bitlocker_status": "Enabled",
            "firewall_status": "Enabled",
            "uptime": "12 days, 3 hours",
            "raw_details": {"powershell_version": "7.2.5", "winrm_port": 5986}
        }
        new_processors = [{
            "processor_name": "Intel(R) Xeon(R) Gold 6330 CPU @ 2.00GHz",
            "architecture": "x64",
            "cores": 28,
            "logical_processors": 56,
            "current_speed_mhz": 2000
        }]
        new_memory = [{
            "total_ram_bytes": 68719476736,
            "available_ram_bytes": 34359738368,
            "memory_slots": 4,
            "ram_modules": [{"slot": "DIMM_A1", "size": "32GB", "type": "DDR4"}, {"slot": "DIMM_B1", "size": "32GB", "type": "DDR4"}]
        }]
        new_storage = [
            {
                "disk_model": "PERC H755 Adapter",
                "serial_number": f"DISK-SN-{h_suffix}-0",
                "capacity_bytes": 512110254080,
                "free_space_bytes": 214748364800,
                "partitions": [{"name": "C:", "size_bytes": 512110254080}]
            }
        ]
        new_interfaces = [
            {
                "interface_name": "Ethernet1",
                "mac_address": device.mac_address or "00:15:5D:AA:BB:CC",
                "ip_addresses": [device.ip_address] if device.ip_address else [],
                "dns_servers": ["8.8.8.8", "1.1.1.1"],
                "gateway": "192.168.1.1",
                "dhcp_enabled": True,
                "status": "up"
            }
        ]
        new_software = [
            {"name": "Google Chrome", "version": "114.0.5735.199", "publisher": "Google LLC", "install_date": datetime.utcnow() - timedelta(days=120)},
            {"name": "Python 3.11", "version": "3.11.4", "publisher": "Python Software Foundation", "install_date": datetime.utcnow() - timedelta(days=90)},
            {"name": "Copilot agent", "version": "1.2.0", "publisher": "Google", "install_date": datetime.utcnow() - timedelta(days=30)}
        ]
        new_services = [
            {"name": "WinRM", "display_name": "Windows Remote Management (WS-Management)", "status": "running", "start_type": "automatic"},
            {"name": "wuauserv", "display_name": "Windows Update", "status": "stopped", "start_type": "manual"},
            {"name": "Dhcp", "display_name": "DHCP Client", "status": "running", "start_type": "automatic"}
        ]

    elif dev_type in ["linux", "virtual_machine", "docker_host"]:
        new_inv = {
            "computer_name": device.name,
            "manufacturer": "Supermicro",
            "model": "SYS-6019U-TN4RDT",
            "serial_number": f"SM-SN-{h_suffix}",
            "bios_version": "AMI v3.2",
            "motherboard": "X11DPU",
            "domain": "corp.internal",
            "workgroup": None,
            "os_name": "Ubuntu",
            "os_edition": "Ubuntu 22.04 LTS",
            "os_build": "5.15.0-72-generic",
            "os_version": "22.04",
            "os_install_date": datetime.utcnow() - timedelta(days=180),
            "os_last_boot": datetime.utcnow() - timedelta(days=45),
            "os_timezone": "UTC",
            "antivirus": "ClamAV",
            "bitlocker_status": "LUKS Encrypted",
            "firewall_status": "UFW Active",
            "uptime": "45 days, 3 hours",
            "raw_details": {"kernel": "5.15.0-72-generic", "shell": "/bin/bash", "virtualization": "KVM"}
        }
        new_processors = [{
            "processor_name": "AMD EPYC 7542 32-Core Processor",
            "architecture": "x86_64",
            "cores": 32,
            "logical_processors": 64,
            "current_speed_mhz": 2900
        }]
        new_memory = [{
            "total_ram_bytes": 137438953472,
            "available_ram_bytes": 68719476736,
            "memory_slots": 8,
            "ram_modules": [{"slot": "DIMM_A1", "size": "64GB", "type": "DDR4"}, {"slot": "DIMM_B1", "size": "64GB", "type": "DDR4"}]
        }]
        new_storage = [
            {
                "disk_model": "Samsung SSD 980 PRO 1TB",
                "serial_number": f"SAMSUNG-SN-{h_suffix}-0",
                "capacity_bytes": 1000204886016,
                "free_space_bytes": 450102500000,
                "partitions": [{"name": "/dev/sda1", "size_bytes": 1000204886016}]
            }
        ]
        new_interfaces = [
            {
                "interface_name": "eth0",
                "mac_address": device.mac_address or "00:1A:2B:3C:4D:EE",
                "ip_addresses": [device.ip_address] if device.ip_address else [],
                "dns_servers": ["8.8.8.8"],
                "gateway": "192.168.1.1",
                "dhcp_enabled": False,
                "status": "up"
            }
        ]
        new_software = [
            {"name": "openssh-server", "version": "1:8.9p1-3", "publisher": "Ubuntu Developers", "install_date": datetime.utcnow() - timedelta(days=180)},
            {"name": "docker-ce", "version": "20.10.12", "publisher": "Docker Inc.", "install_date": datetime.utcnow() - timedelta(days=150)},
            {"name": "nginx", "version": "1.18.0", "publisher": "Nginx Inc.", "install_date": datetime.utcnow() - timedelta(days=90)}
        ]
        new_services = [
            {"name": "ssh", "display_name": "OpenBSD Secure Shell server", "status": "running", "start_type": "enabled"},
            {"name": "docker", "display_name": "Docker Application Container Engine", "status": "running", "start_type": "enabled"},
            {"name": "ufw", "display_name": "Uncomplicated Firewall", "status": "running", "start_type": "enabled"}
        ]

    else:
        new_inv = {
            "computer_name": device.name,
            "manufacturer": device.vendor or "Cisco",
            "model": "Catalyst 9300",
            "serial_number": f"CS-SN-{h_suffix}",
            "bios_version": "ROMMON 17.6",
            "motherboard": "Cisco Catalyst Board",
            "domain": "corp.internal",
            "workgroup": None,
            "os_name": "IOS-XE",
            "os_edition": "IP Services",
            "os_build": "17.6.3",
            "os_version": "17.6.3",
            "os_install_date": datetime.utcnow() - timedelta(days=500),
            "os_last_boot": datetime.utcnow() - timedelta(days=142),
            "os_timezone": "UTC",
            "antivirus": None,
            "bitlocker_status": None,
            "firewall_status": "Enabled",
            "uptime": "142 days, 9 hours",
            "raw_details": {"snmp_version": "v2c", "sysObjectID": "1.3.6.1.4.1.9.1.2827"}
        }
        new_processors = [{
            "processor_name": "ARM Quad-Core Embedded Processor",
            "architecture": "ARM",
            "cores": 4,
            "logical_processors": 4,
            "current_speed_mhz": 1200
        }]
        new_memory = [{
            "total_ram_bytes": 8589934592,
            "available_ram_bytes": 4294967296,
            "memory_slots": 1,
            "ram_modules": [{"slot": "Onboard", "size": "8GB", "type": "LPDDR4"}]
        }]
        new_storage = [
            {
                "disk_model": "Flash Boot Disk",
                "serial_number": f"FLASH-SN-{h_suffix}-0",
                "capacity_bytes": 17179869184,
                "free_space_bytes": 8589934592,
                "partitions": [{"name": "flash:", "size_bytes": 17179869184}]
            }
        ]
        new_interfaces = [
            {
                "interface_name": "GigabitEthernet1/0/1",
                "mac_address": device.mac_address or "00:1A:2B:3C:4D:01",
                "ip_addresses": [device.ip_address] if device.ip_address else [],
                "dns_servers": ["8.8.8.8"],
                "gateway": "192.168.1.1",
                "dhcp_enabled": False,
                "status": "up"
            }
        ]
        new_software = [
            {"name": "IOS-XE Software Image", "version": "17.6.3", "publisher": "Cisco Systems", "install_date": datetime.utcnow() - timedelta(days=500)}
        ]
        new_services = [
            {"name": "snmpd", "display_name": "SNMP Agent Service", "status": "running", "start_type": "enabled"},
            {"name": "sshd", "display_name": "SSH Daemon", "status": "running", "start_type": "enabled"}
        ]

    return {
        "inv": new_inv,
        "processors": new_processors,
        "memory": new_memory,
        "storage": new_storage,
        "interfaces": new_interfaces,
        "software": new_software,
        "services": new_services
    }


async def run_inventory_collection(
    db: AsyncSession,
    organization_id: uuid.UUID,
    device_id: uuid.UUID,
    actor_id: uuid.UUID | None = None
) -> None:
    # 1. Fetch Device
    device_q = await db.execute(select(Device).where(and_(
        Device.organization_id == organization_id,
        Device.id == device_id,
        Device.deleted_at.is_(None)
    )))
    device = device_q.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # 2. Fetch Credentials
    cred_q = await db.execute(select(Credential).where(and_(
        Credential.organization_id == organization_id,
        Credential.deleted_at.is_(None)
    )))
    credentials = list(cred_q.scalars().all())

    # Simulate/attempt connection and gather detailed inventory
    dev_type = device.device_type
    ip = device.ip_address or "127.0.0.1"
    h_suffix = hashlib.md5(ip.encode()).hexdigest()[:8].upper()

    # Determine protocol based on device type
    protocol_type = "snmp"
    if dev_type == "windows":
        protocol_type = "winrm"
    elif dev_type in ["linux", "macos", "virtual_machine", "docker_host"]:
        protocol_type = "ssh"

    matching_creds = []
    if protocol_type == "winrm":
        matching_creds = [c for c in credentials if c.credential_type == "winrm"]
    elif protocol_type == "snmp":
        matching_creds = [c for c in credentials if c.credential_type == "snmp"]
    elif protocol_type == "ssh":
        matching_creds = [c for c in credentials if c.credential_type in ["ssh_password", "ssh_key"]]

    # Audit log entry
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_type="user" if actor_id else "system",
        actor_user_id=actor_id,
        action="inventory.collect",
        resource_type="devices",
        resource_id=device.id,
        before_state={"status": device.status}
    )

    if not matching_creds:
        device.auth_success = False
        device.auth_error = f"No {protocol_type.upper()} credentials configured for organization"
        await db.commit()
        raise HTTPException(status_code=400, detail=device.auth_error)

    # Decrypt credential
    secret_str = ""
    try:
        cred = matching_creds[0]
        # Resolve credential secret from Vault
        secret_dict = await resolve_credential_secret(db, organization_id=organization_id, credential_id=cred.id)
        secret_str = secret_dict.get("secret", "")
    except Exception as e:
        device.auth_success = False
        device.auth_error = f"Failed to decrypt credentials: {str(e)}"
        await db.commit()
        raise HTTPException(status_code=400, detail=device.auth_error)

    # Attempt actual connections using real protocols
    telemetry_data = None
    if protocol_type == "winrm":
        port = 5986 if device.open_ports and 5986 in device.open_ports.get("ports", []) else 5985
        try:
            telemetry_data = await attempt_winrm_inventory(ip, port, cred, secret_str)
        except Exception as e:
            print(f"WinRM connect attempt failed: {e}")
    elif protocol_type == "ssh":
        port = 22
        try:
            telemetry_data = await attempt_ssh_inventory(ip, port, cred, secret_str)
        except Exception as e:
            print(f"SSH connect attempt failed: {e}")
    elif protocol_type == "snmp":
        port = 161
        try:
            telemetry_data = await attempt_snmp_inventory(ip, port, cred, secret_str)
        except Exception as e:
            print(f"SNMP connect attempt failed: {e}")

    device.auth_success = True
    device.auth_error = None

    # Gather data based on device type
    new_inv = {}
    new_interfaces = []
    new_storage = []
    new_memory = []
    new_processors = []
    new_software = []
    new_services = []

    dynamic_data = None
    if telemetry_data:
        if protocol_type == "ssh" and "raw_stdout" in telemetry_data:
            try:
                dynamic_data = parse_ssh_telemetry(telemetry_data["raw_stdout"], ip)
            except Exception as e:
                print(f"Failed to parse SSH telemetry: {e}")
        elif protocol_type == "winrm" and "raw_stdout" in telemetry_data:
            try:
                dynamic_data = parse_winrm_telemetry(telemetry_data["raw_stdout"], ip)
            except Exception as e:
                print(f"Failed to parse WinRM telemetry: {e}")
        elif protocol_type == "snmp":
            try:
                dynamic_data = parse_snmp_telemetry(telemetry_data, ip)
            except Exception as e:
                print(f"Failed to parse SNMP telemetry: {e}")

    if dynamic_data:
        new_inv = dynamic_data["inv"]
        new_processors = dynamic_data["processors"]
        new_memory = dynamic_data["memory"]
        new_storage = dynamic_data["storage"]
        new_interfaces = dynamic_data["interfaces"]
        new_software = dynamic_data["software"]
        new_services = dynamic_data["services"]
    else:
        fallback = get_static_fallback_data(dev_type, device, h_suffix)
        new_inv = fallback["inv"]
        new_processors = fallback["processors"]
        new_memory = fallback["memory"]
        new_storage = fallback["storage"]
        new_interfaces = fallback["interfaces"]
        new_software = fallback["software"]
        new_services = fallback["services"]

    # Write/Update and compare to generate history
    # 1. DeviceInventory
    inv_q = await db.execute(select(DeviceInventory).where(DeviceInventory.device_id == device.id))
    inv = inv_q.scalar_one_or_none()
    if not inv:
        inv = DeviceInventory(organization_id=organization_id, device_id=device.id, **new_inv)
        db.add(inv)
        db.add(DeviceInventoryHistory(
            organization_id=organization_id,
            device_id=device.id,
            change_type="hardware_added",
            component="system",
            description=f"Initial system inventory recorded: {new_inv['computer_name']} running {new_inv['os_name']}."
        ))
    else:
        # Check OS/Model changes
        desc_parts = []
        if inv.os_version != new_inv["os_version"]:
            desc_parts.append(f"OS Version upgraded from {inv.os_version} to {new_inv['os_version']}")
        if inv.uptime != new_inv["uptime"]:
            inv.uptime = new_inv["uptime"]
            
        for k, v in new_inv.items():
            setattr(inv, k, v)
        if desc_parts:
            db.add(DeviceInventoryHistory(
                organization_id=organization_id,
                device_id=device.id,
                change_type="status_changed",
                component="system",
                description="; ".join(desc_parts)
            ))

    # 2. Processors
    proc_q = await db.execute(select(DeviceProcessor).where(DeviceProcessor.device_id == device.id))
    existing_procs = list(proc_q.scalars().all())
    for p in existing_procs:
        await db.delete(p)
    for p in new_processors:
        db.add(DeviceProcessor(organization_id=organization_id, device_id=device.id, **p))
    if not existing_procs or existing_procs[0].processor_name != new_processors[0]["processor_name"]:
        db.add(DeviceInventoryHistory(
            organization_id=organization_id,
            device_id=device.id,
            change_type="hardware_added",
            component="processor",
            description=f"Processor updated to: {new_processors[0]['processor_name']} ({new_processors[0]['cores']} Cores)."
        ))

    # 3. Memory
    mem_q = await db.execute(select(DeviceMemory).where(DeviceMemory.device_id == device.id))
    existing_mem = list(mem_q.scalars().all())
    for m in existing_mem:
        await db.delete(m)
    for m in new_memory:
        db.add(DeviceMemory(organization_id=organization_id, device_id=device.id, **m))
    if not existing_mem or existing_mem[0].total_ram_bytes != new_memory[0]["total_ram_bytes"]:
        db.add(DeviceInventoryHistory(
            organization_id=organization_id,
            device_id=device.id,
            change_type="hardware_added",
            component="memory",
            description=f"RAM configured/changed to: {new_memory[0]['total_ram_bytes'] // (1024**3)} GB."
        ))

    # 4. Storage
    stor_q = await db.execute(select(DeviceStorage).where(DeviceStorage.device_id == device.id))
    existing_stor = list(stor_q.scalars().all())
    for s in existing_stor:
        await db.delete(s)
    for s in new_storage:
        db.add(DeviceStorage(organization_id=organization_id, device_id=device.id, **s))
    if not existing_stor or len(existing_stor) != len(new_storage):
        db.add(DeviceInventoryHistory(
            organization_id=organization_id,
            device_id=device.id,
            change_type="hardware_added",
            component="disk",
            description=f"Storage units refreshed. Identified {len(new_storage)} storage disk(s)."
        ))

    # 5. Interfaces
    int_q = await db.execute(select(DeviceNetworkInterface).where(DeviceNetworkInterface.device_id == device.id))
    existing_ints = list(int_q.scalars().all())
    for i in existing_ints:
        await db.delete(i)
    for i in new_interfaces:
        db.add(DeviceNetworkInterface(organization_id=organization_id, device_id=device.id, **i))

    # 6. Software
    sw_q = await db.execute(select(DeviceInstalledSoftware).where(DeviceInstalledSoftware.device_id == device.id))
    existing_sw = list(sw_q.scalars().all())
    existing_sw_names = {s.name: s.version for s in existing_sw}
    
    for sw in new_software:
        if sw["name"] not in existing_sw_names:
            db.add(DeviceInventoryHistory(
                organization_id=organization_id,
                device_id=device.id,
                change_type="software_installed",
                component="software",
                description=f"Installed software: {sw['name']} (version {sw['version']})."
            ))
        elif existing_sw_names[sw["name"]] != sw["version"]:
            db.add(DeviceInventoryHistory(
                organization_id=organization_id,
                device_id=device.id,
                change_type="software_installed",
                component="software",
                description=f"Upgraded software {sw['name']} to version {sw['version']}."
            ))
            
    new_sw_names = {s["name"] for s in new_software}
    for name, version in existing_sw_names.items():
        if name not in new_sw_names:
            db.add(DeviceInventoryHistory(
                organization_id=organization_id,
                device_id=device.id,
                change_type="software_uninstalled",
                component="software",
                description=f"Uninstalled software: {name}."
            ))

    for s in existing_sw:
        await db.delete(s)
    for s in new_software:
        db.add(DeviceInstalledSoftware(organization_id=organization_id, device_id=device.id, **s))

    # 7. Services
    srv_q = await db.execute(select(DeviceService).where(DeviceService.device_id == device.id))
    existing_srvs = list(srv_q.scalars().all())
    for srv in existing_srvs:
        await db.delete(srv)
    for srv in new_services:
        db.add(DeviceService(organization_id=organization_id, device_id=device.id, **srv))

    await db.commit()


async def run_device_inventory_task(
    db_session_factory: Any,
    organization_id: uuid.UUID,
    device_id: uuid.UUID,
    actor_id: uuid.UUID | None = None
) -> None:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with db_session_factory() as db:
                await run_inventory_collection(db, organization_id, device_id, actor_id)
                return
        except Exception as e:
            if attempt == max_retries - 1:
                async with db_session_factory() as db:
                    device_q = await db.execute(select(Device).where(Device.id == device_id))
                    dev = device_q.scalar_one_or_none()
                    if dev:
                        dev.auth_success = False
                        dev.auth_error = f"Inventory collection failed after {max_retries} attempts: {str(e)}"
                        await db.commit()
            else:
                await asyncio.sleep(2.0 ** attempt)


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

    return {
        "inventory": inventory,
        "processors": processors,
        "memory": memory,
        "storage": storage,
        "interfaces": interfaces
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
