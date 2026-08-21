from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, computed_field

from py_shared.enums import ScanMode


class ScanStartRequest(BaseModel):
    target_range: str = Field(..., description="Target subnet range, e.g. 192.168.1.0/24")
    scan_mode: ScanMode = Field(
        ScanMode.STANDARD,
        description="quick (IP/hostname/MAC/vendor/status only) | standard (+ports/services/OS) | full (+ credentialed hardware/software/security inventory)",
    )
    credential_ids: list[UUID] | None = Field(default=None, description="Optional credentials to try for authentication")


class NetworkScanResponse(BaseModel):
    id: UUID
    organization_id: UUID
    scan_range: str
    status: str
    scan_type: str
    started_at: datetime | None
    completed_at: datetime | None
    total_devices: int
    online_devices: int
    offline_devices: int
    new_devices: int
    updated_devices: int
    failed_devices: int
    auth_failures: int
    scan_duration: float | None
    error_message: str | None
    created_by_id: UUID | None
    created_at: datetime

    class Config:
        from_attributes = True


# For backwards compatibility with the existing UI
class DeviceScanResponse(BaseModel):
    id: UUID
    organization_id: UUID
    status: str
    scan_type: str
    target_range: str | None
    started_at: datetime | None
    completed_at: datetime | None
    devices_found: int
    error_message: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceResponse(BaseModel):
    id: UUID
    organization_id: UUID
    device_type: str
    name: str
    ip_address: str | None
    mac_address: str | None
    vendor: str | None
    model: str | None
    operating_system: str | None
    status: str
    response_time: float | None
    open_ports: dict | None
    network_interface: str | None
    last_seen_at: datetime | None
    first_seen_at: datetime
    scan_timestamp: datetime | None
    
    dns_name: str | None
    netbios_name: str | None
    mdns_name: str | None
    os_version: str | None
    device_vendor: str | None
    serial_number: str | None
    uuid: str | None
    asset_tag: str | None
    bios_version: str | None
    cpu_details: str | None
    memory_ram: str | None
    storage_details: str | None
    installed_software: list | None
    installed_updates: list | None
    logged_in_user: str | None
    uptime: str | None
    domain_info: str | None
    interfaces: list | None
    raw_details: dict | None
    auth_success: bool
    auth_error: str | None

    scan_status: str | None
    identification_confidence: str | None
    identification_method: str | None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @computed_field  # type: ignore[prop-decorator]
    @property
    def needs_credentials(self) -> bool:
        return self.scan_status == "credentials_required"


class DeviceScanHistoryResponse(BaseModel):
    id: UUID
    organization_id: UUID
    scan_id: UUID
    device_id: UUID
    status: str
    response_time: float | None
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceStatusHistoryResponse(BaseModel):
    id: UUID
    organization_id: UUID
    device_id: UUID
    status: str
    response_time: float | None
    hostname: str | None
    vendor: str | None
    operating_system: str | None
    created_at: datetime

    class Config:
        from_attributes = True


# For backwards compatibility
class DeviceHistoryResponse(BaseModel):
    id: UUID
    organization_id: UUID
    device_id: UUID
    event_type: str
    description: str | None
    before_state: dict | None = None
    after_state: dict | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceIPHistoryResponse(BaseModel):
    id: UUID
    organization_id: UUID
    device_id: UUID
    old_ip: str | None
    new_ip: str
    changed_at: datetime

    class Config:
        from_attributes = True


class DeviceInventoryResponse(BaseModel):
    computer_name: str | None
    manufacturer: str | None
    model: str | None
    serial_number: str | None
    bios_version: str | None
    motherboard: str | None
    domain: str | None
    workgroup: str | None
    os_name: str | None
    os_edition: str | None
    os_build: str | None
    os_version: str | None
    os_install_date: datetime | None
    os_last_boot: datetime | None
    os_timezone: str | None
    antivirus: str | None
    bitlocker_status: str | None
    firewall_status: str | None
    uptime: str | None

    class Config:
        from_attributes = True


class DeviceNetworkInterfaceResponse(BaseModel):
    id: UUID
    interface_name: str
    mac_address: str | None
    ip_addresses: list | None
    dns_servers: list | None
    gateway: str | None
    dhcp_enabled: bool | None
    status: str | None
    speed_mbps: int | None = None
    duplex: str | None = None
    interface_type: str | None = None

    class Config:
        from_attributes = True


class DevicePartitionResponse(BaseModel):
    id: UUID
    mount_point: str | None
    device_node: str | None
    filesystem_type: str | None
    label: str | None = None
    capacity_bytes: int | None
    used_bytes: int | None = None
    free_space_bytes: int | None

    class Config:
        from_attributes = True


class DeviceStorageResponse(BaseModel):
    id: UUID
    disk_model: str | None
    serial_number: str | None
    capacity_bytes: int | None
    free_space_bytes: int | None
    partitions: list | None
    interface_type: str | None = None
    media_type: str | None = None
    health_status: str | None = None

    class Config:
        from_attributes = True


class DeviceMemoryResponse(BaseModel):
    id: UUID
    total_ram_bytes: int | None
    available_ram_bytes: int | None
    memory_slots: int | None
    ram_modules: list | None
    configured_speed_mhz: int | None = None

    class Config:
        from_attributes = True


class DeviceProcessorResponse(BaseModel):
    id: UUID
    processor_name: str | None
    architecture: str | None
    cores: int | None
    logical_processors: int | None
    current_speed_mhz: int | None
    max_speed_mhz: int | None = None
    socket_designation: str | None = None

    class Config:
        from_attributes = True


class DeviceHardwareDetailsResponse(BaseModel):
    inventory: DeviceInventoryResponse | None
    processors: list[DeviceProcessorResponse]
    memory: list[DeviceMemoryResponse]
    storage: list[DeviceStorageResponse]
    interfaces: list[DeviceNetworkInterfaceResponse]
    partitions: list[DevicePartitionResponse] = []


class DeviceProcessResponse(BaseModel):
    id: UUID
    pid: int
    name: str
    command_line: str | None
    user_name: str | None
    cpu_percent: float | None
    memory_bytes: int | None
    status: str | None
    collected_at: datetime

    class Config:
        from_attributes = True


class DeviceSecurityResponse(BaseModel):
    id: UUID
    defender_enabled: bool | None
    defender_signature_version: str | None
    firewall_enabled: bool | None
    firewall_profiles: dict | None
    bitlocker_status: str | None
    secure_boot_enabled: bool | None
    antivirus_product: str | None
    antivirus_up_to_date: bool | None
    pending_updates_count: int | None
    last_update_installed_at: datetime | None
    selinux_status: str | None
    apparmor_status: str | None
    ufw_active: bool | None
    iptables_rule_count: int | None
    ssh_root_login_enabled: bool | None
    ssh_password_auth_enabled: bool | None
    collected_at: datetime

    class Config:
        from_attributes = True


class DevicePortResponse(BaseModel):
    id: UUID
    port_number: int
    protocol: str
    service_name: str | None
    product: str | None
    version: str | None
    state: str
    first_seen_at: datetime
    last_seen_at: datetime

    class Config:
        from_attributes = True


class DeviceInstalledSoftwareResponse(BaseModel):
    id: UUID
    name: str
    version: str | None
    publisher: str | None
    install_date: datetime | None

    class Config:
        from_attributes = True


class DeviceServiceResponse(BaseModel):
    id: UUID
    name: str
    display_name: str | None
    status: str | None
    start_type: str | None

    class Config:
        from_attributes = True


class DeviceSoftwareDetailsResponse(BaseModel):
    installed_software: list[DeviceInstalledSoftwareResponse]
    services: list[DeviceServiceResponse]


class DeviceInventoryHistoryResponse(BaseModel):
    id: UUID
    change_type: str
    component: str
    description: str
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceAllHistoryResponse(BaseModel):
    ip_history: list[DeviceIPHistoryResponse]
    scan_history: list[DeviceScanHistoryResponse]
    inventory_history: list[DeviceInventoryHistoryResponse]
