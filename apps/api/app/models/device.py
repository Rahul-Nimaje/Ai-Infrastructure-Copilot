import uuid
from datetime import datetime
from sqlalchemy import ForeignKey, String, Numeric, Text, DateTime, Integer, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class NetworkScan(Base):
    __tablename__ = "network_scans"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    scan_range: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, running, completed, failed
    scan_type: Mapped[str] = mapped_column(String(50), default="ping")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    total_devices: Mapped[int] = mapped_column(Integer, default=0)
    online_devices: Mapped[int] = mapped_column(Integer, default=0)
    offline_devices: Mapped[int] = mapped_column(Integer, default=0)
    new_devices: Mapped[int] = mapped_column(Integer, default=0)
    updated_devices: Mapped[int] = mapped_column(Integer, default=0)
    failed_devices: Mapped[int] = mapped_column(Integer, default=0)
    auth_failures: Mapped[int] = mapped_column(Integer, default=0)
    scan_duration: Mapped[float | None] = mapped_column(Numeric(10, 2), default=None)  # in seconds
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    device_scans: Mapped[list["DeviceScanHistory"]] = relationship("DeviceScanHistory", back_populates="scan", cascade="all, delete-orphan")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    device_type: Mapped[str] = mapped_column(String(50), default="unknown")
    name: Mapped[str] = mapped_column(String(255), index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), default=None, index=True)
    mac_address: Mapped[str | None] = mapped_column(String(17), default=None, index=True)
    vendor: Mapped[str | None] = mapped_column(String(100), default=None)
    model: Mapped[str | None] = mapped_column(String(100), default=None)
    operating_system: Mapped[str | None] = mapped_column(String(100), default=None)
    status: Mapped[str] = mapped_column(String(20), default="unknown", index=True)  # online, offline
    response_time: Mapped[float | None] = mapped_column(Numeric(10, 2), default=None)  # milliseconds
    open_ports: Mapped[dict | None] = mapped_column(JSONB, default=None)  # {"ports": [22, 80]}
    network_interface: Mapped[str | None] = mapped_column(String(100), default=None)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, default=None, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    scan_timestamp: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    
    # Advanced Fingerprinting & Credential Data
    dns_name: Mapped[str | None] = mapped_column(String(255), default=None)
    netbios_name: Mapped[str | None] = mapped_column(String(255), default=None)
    mdns_name: Mapped[str | None] = mapped_column(String(255), default=None)
    os_version: Mapped[str | None] = mapped_column(String(100), default=None)
    device_vendor: Mapped[str | None] = mapped_column(String(100), default=None)
    serial_number: Mapped[str | None] = mapped_column(String(255), default=None, index=True)
    uuid: Mapped[str | None] = mapped_column(String(255), default=None, index=True)
    asset_tag: Mapped[str | None] = mapped_column(String(255), default=None, index=True)
    bios_version: Mapped[str | None] = mapped_column(String(100), default=None)
    cpu_details: Mapped[str | None] = mapped_column(String(255), default=None)
    memory_ram: Mapped[str | None] = mapped_column(String(100), default=None)
    storage_details: Mapped[str | None] = mapped_column(String(255), default=None)
    installed_software: Mapped[list | None] = mapped_column(JSONB, default=None)
    installed_updates: Mapped[list | None] = mapped_column(JSONB, default=None)
    logged_in_user: Mapped[str | None] = mapped_column(String(255), default=None)
    uptime: Mapped[str | None] = mapped_column(String(100), default=None)
    domain_info: Mapped[str | None] = mapped_column(String(255), default=None)
    interfaces: Mapped[list | None] = mapped_column(JSONB, default=None)
    raw_details: Mapped[dict | None] = mapped_column(JSONB, default=None)
    
    # Auth status tracking
    auth_success: Mapped[bool] = mapped_column(default=False)
    auth_error: Mapped[str | None] = mapped_column(Text, default=None)

    # Inventory lifecycle (section 9) and identification confidence (section 2)
    scan_status: Mapped[str | None] = mapped_column(String(30), default="discovered", index=True)
    identification_confidence: Mapped[str | None] = mapped_column(String(20), default=None)  # confirmed | unverified | unknown
    identification_method: Mapped[str | None] = mapped_column(String(50), default=None)  # snmp | winrm | ssh | smb | port_heuristic | hostname_heuristic

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    # Relationships
    scan_history: Mapped[list["DeviceScanHistory"]] = relationship("DeviceScanHistory", back_populates="device", cascade="all, delete-orphan")
    status_history: Mapped[list["DeviceStatusHistory"]] = relationship("DeviceStatusHistory", back_populates="device", cascade="all, delete-orphan")
    ip_history: Mapped[list["DeviceIPHistory"]] = relationship("DeviceIPHistory", back_populates="device", cascade="all, delete-orphan")

    inventory: Mapped["DeviceInventory"] = relationship("DeviceInventory", back_populates="device", uselist=False, cascade="all, delete-orphan")
    network_interfaces: Mapped[list["DeviceNetworkInterface"]] = relationship("DeviceNetworkInterface", back_populates="device", cascade="all, delete-orphan")
    storage_devices: Mapped[list["DeviceStorage"]] = relationship("DeviceStorage", back_populates="device", cascade="all, delete-orphan")
    memory_info: Mapped[list["DeviceMemory"]] = relationship("DeviceMemory", back_populates="device", cascade="all, delete-orphan")
    processors: Mapped[list["DeviceProcessor"]] = relationship("DeviceProcessor", back_populates="device", cascade="all, delete-orphan")
    installed_software_list: Mapped[list["DeviceInstalledSoftware"]] = relationship("DeviceInstalledSoftware", back_populates="device", cascade="all, delete-orphan")
    services_list: Mapped[list["DeviceService"]] = relationship("DeviceService", back_populates="device", cascade="all, delete-orphan")
    inventory_history: Mapped[list["DeviceInventoryHistory"]] = relationship("DeviceInventoryHistory", back_populates="device", cascade="all, delete-orphan")
    processes: Mapped[list["DeviceProcess"]] = relationship("DeviceProcess", back_populates="device", cascade="all, delete-orphan")
    security: Mapped["DeviceSecurity"] = relationship("DeviceSecurity", back_populates="device", uselist=False, cascade="all, delete-orphan")
    ports: Mapped[list["DevicePort"]] = relationship("DevicePort", back_populates="device", cascade="all, delete-orphan")


class DeviceInventory(Base):
    __tablename__ = "device_inventory"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), unique=True)
    
    # System
    computer_name: Mapped[str | None] = mapped_column(String(255), default=None)
    manufacturer: Mapped[str | None] = mapped_column(String(100), default=None)
    model: Mapped[str | None] = mapped_column(String(100), default=None)
    serial_number: Mapped[str | None] = mapped_column(String(255), default=None)
    bios_version: Mapped[str | None] = mapped_column(String(100), default=None)
    motherboard: Mapped[str | None] = mapped_column(String(100), default=None)
    domain: Mapped[str | None] = mapped_column(String(255), default=None)
    workgroup: Mapped[str | None] = mapped_column(String(255), default=None)

    # OS
    os_name: Mapped[str | None] = mapped_column(String(100), default=None)
    os_edition: Mapped[str | None] = mapped_column(String(100), default=None)
    os_build: Mapped[str | None] = mapped_column(String(50), default=None)
    os_version: Mapped[str | None] = mapped_column(String(100), default=None)
    os_install_date: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    os_last_boot: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    os_timezone: Mapped[str | None] = mapped_column(String(100), default=None)

    # Security / Extra
    antivirus: Mapped[str | None] = mapped_column(String(255), default=None)
    bitlocker_status: Mapped[str | None] = mapped_column(String(100), default=None)
    firewall_status: Mapped[str | None] = mapped_column(String(100), default=None)
    uptime: Mapped[str | None] = mapped_column(String(100), default=None)
    
    raw_details: Mapped[dict | None] = mapped_column(JSONB, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="inventory")


class DeviceNetworkInterface(Base):
    __tablename__ = "device_network_interfaces"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    
    interface_name: Mapped[str] = mapped_column(String(100))
    mac_address: Mapped[str | None] = mapped_column(String(17), default=None)
    ip_addresses: Mapped[list | None] = mapped_column(JSONB, default=None)  # ["192.168.1.10"]
    dns_servers: Mapped[list | None] = mapped_column(JSONB, default=None)   # ["8.8.8.8"]
    gateway: Mapped[str | None] = mapped_column(String(45), default=None)
    dhcp_enabled: Mapped[bool | None] = mapped_column(default=None)
    status: Mapped[str | None] = mapped_column(String(50), default="up")
    speed_mbps: Mapped[int | None] = mapped_column(Integer, default=None)
    duplex: Mapped[str | None] = mapped_column(String(20), default=None)
    interface_type: Mapped[str | None] = mapped_column(String(50), default=None)  # ethernet | loopback | vlan | wifi
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="network_interfaces")


class DeviceStorage(Base):
    __tablename__ = "device_storage"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    
    disk_model: Mapped[str | None] = mapped_column(String(255), default=None)
    serial_number: Mapped[str | None] = mapped_column(String(255), default=None)
    capacity_bytes: Mapped[int | None] = mapped_column(BigInteger, default=None)
    free_space_bytes: Mapped[int | None] = mapped_column(BigInteger, default=None)
    partitions: Mapped[list | None] = mapped_column(JSONB, default=None)
    interface_type: Mapped[str | None] = mapped_column(String(50), default=None)  # SATA | NVMe | SAS | USB
    media_type: Mapped[str | None] = mapped_column(String(50), default=None)  # SSD | HDD | unknown
    health_status: Mapped[str | None] = mapped_column(String(50), default=None)  # OK | Warning | Predict-Failure
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="storage_devices")
    partition_entries: Mapped[list["DevicePartition"]] = relationship("DevicePartition", back_populates="storage", cascade="all, delete-orphan")


class DeviceMemory(Base):
    __tablename__ = "device_memory"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    
    total_ram_bytes: Mapped[int | None] = mapped_column(BigInteger, default=None)
    available_ram_bytes: Mapped[int | None] = mapped_column(BigInteger, default=None)
    memory_slots: Mapped[int | None] = mapped_column(default=None)
    ram_modules: Mapped[list | None] = mapped_column(JSONB, default=None)  # [{"slot","manufacturer","capacity_bytes","speed_mhz"}]
    configured_speed_mhz: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="memory_info")


class DeviceProcessor(Base):
    __tablename__ = "device_processors"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    
    processor_name: Mapped[str | None] = mapped_column(String(255), default=None)
    architecture: Mapped[str | None] = mapped_column(String(50), default=None)
    cores: Mapped[int | None] = mapped_column(default=None)
    logical_processors: Mapped[int | None] = mapped_column(default=None)
    current_speed_mhz: Mapped[int | None] = mapped_column(default=None)
    max_speed_mhz: Mapped[int | None] = mapped_column(Integer, default=None)
    socket_designation: Mapped[str | None] = mapped_column(String(50), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="processors")


class DeviceInstalledSoftware(Base):
    __tablename__ = "device_installed_software"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    
    name: Mapped[str] = mapped_column(String(255), index=True)
    version: Mapped[str | None] = mapped_column(String(100), default=None)
    publisher: Mapped[str | None] = mapped_column(String(255), default=None)
    install_date: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="installed_software_list")


class DeviceService(Base):
    __tablename__ = "device_services"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    
    name: Mapped[str] = mapped_column(String(255), index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), default=None)
    status: Mapped[str | None] = mapped_column(String(50), default=None)
    start_type: Mapped[str | None] = mapped_column(String(50), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="services_list")


class DeviceInventoryHistory(Base):
    __tablename__ = "device_inventory_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    
    change_type: Mapped[str] = mapped_column(String(50))
    component: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="inventory_history")


class DeviceScanHistory(Base):
    __tablename__ = "device_scan_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    scan_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("network_scans.id", ondelete="CASCADE"))
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20))
    response_time: Mapped[float | None] = mapped_column(Numeric(10, 2), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    scan: Mapped["NetworkScan"] = relationship("NetworkScan", back_populates="device_scans")
    device: Mapped["Device"] = relationship("Device", back_populates="scan_history")


class DeviceStatusHistory(Base):
    __tablename__ = "device_status_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20))
    response_time: Mapped[float | None] = mapped_column(Numeric(10, 2), default=None)
    hostname: Mapped[str | None] = mapped_column(String(255), default=None)
    vendor: Mapped[str | None] = mapped_column(String(100), default=None)
    operating_system: Mapped[str | None] = mapped_column(String(100), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="status_history")


class DeviceIPHistory(Base):
    __tablename__ = "device_ip_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    old_ip: Mapped[str | None] = mapped_column(String(45), default=None)
    new_ip: Mapped[str] = mapped_column(String(45))
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="ip_history")


class DevicePartition(Base):
    """Normalized disk partitions — DeviceStorage.partitions (JSONB) stays for
    the simple one-disk-one-partition case (typical Windows logical disk);
    this table is populated for the detailed multi-partition case (Linux
    lsblk/df), enabling per-partition filtering/history that JSONB can't."""

    __tablename__ = "device_partitions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    storage_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("device_storage.id", ondelete="CASCADE"), default=None)

    mount_point: Mapped[str | None] = mapped_column(String(255), default=None)
    device_node: Mapped[str | None] = mapped_column(String(100), default=None)  # e.g. /dev/sda1, C:
    filesystem_type: Mapped[str | None] = mapped_column(String(50), default=None)  # ext4 | xfs | ntfs
    label: Mapped[str | None] = mapped_column(String(100), default=None)
    capacity_bytes: Mapped[int | None] = mapped_column(BigInteger, default=None)
    used_bytes: Mapped[int | None] = mapped_column(BigInteger, default=None)
    free_space_bytes: Mapped[int | None] = mapped_column(BigInteger, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    device: Mapped["Device"] = relationship("Device")
    storage: Mapped["DeviceStorage"] = relationship("DeviceStorage", back_populates="partition_entries")


class DeviceProcess(Base):
    """Point-in-time process snapshot — delete-all-for-device then bulk
    insert on each Full scan, same pattern already used for DeviceProcessor/
    DeviceStorage rather than a diffed/historized table."""

    __tablename__ = "device_processes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))

    pid: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(255), index=True)
    command_line: Mapped[str | None] = mapped_column(Text, default=None)
    user_name: Mapped[str | None] = mapped_column(String(100), default=None)
    cpu_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), default=None)
    memory_bytes: Mapped[int | None] = mapped_column(BigInteger, default=None)
    status: Mapped[str | None] = mapped_column(String(50), default=None)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="processes")


class DeviceSecurity(Base):
    """1:1 security posture, superset of DeviceInventory's legacy antivirus/
    bitlocker_status/firewall_status columns (left frozen there for backward
    compat — collectors write to both during the transition)."""

    __tablename__ = "device_security"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), unique=True)

    # Windows
    defender_enabled: Mapped[bool | None] = mapped_column(default=None)
    defender_signature_version: Mapped[str | None] = mapped_column(String(100), default=None)
    firewall_enabled: Mapped[bool | None] = mapped_column(default=None)
    firewall_profiles: Mapped[dict | None] = mapped_column(JSONB, default=None)  # {"domain":true,"private":true,"public":false}
    bitlocker_status: Mapped[str | None] = mapped_column(String(50), default=None)
    secure_boot_enabled: Mapped[bool | None] = mapped_column(default=None)
    antivirus_product: Mapped[str | None] = mapped_column(String(255), default=None)
    antivirus_up_to_date: Mapped[bool | None] = mapped_column(default=None)
    pending_updates_count: Mapped[int | None] = mapped_column(Integer, default=None)
    last_update_installed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    # Linux
    selinux_status: Mapped[str | None] = mapped_column(String(50), default=None)  # enforcing | permissive | disabled
    apparmor_status: Mapped[str | None] = mapped_column(String(50), default=None)
    ufw_active: Mapped[bool | None] = mapped_column(default=None)
    iptables_rule_count: Mapped[int | None] = mapped_column(Integer, default=None)
    ssh_root_login_enabled: Mapped[bool | None] = mapped_column(default=None)
    ssh_password_auth_enabled: Mapped[bool | None] = mapped_column(default=None)

    raw_details: Mapped[dict | None] = mapped_column(JSONB, default=None)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="security")


class DevicePort(Base):
    """Normalizes open ports/services (previously only in Device.open_ports
    JSONB and a nmap-parsed ports_detail list that was discarded after parse
    and never persisted) so port history/diffing across scans works."""

    __tablename__ = "device_ports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    scan_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("network_scans.id", ondelete="SET NULL"), default=None)

    port_number: Mapped[int] = mapped_column(Integer)
    protocol: Mapped[str] = mapped_column(String(10), default="tcp")
    service_name: Mapped[str | None] = mapped_column(String(100), default=None)
    product: Mapped[str | None] = mapped_column(String(255), default=None)
    version: Mapped[str | None] = mapped_column(String(100), default=None)
    state: Mapped[str] = mapped_column(String(20), default="open")
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="ports")
