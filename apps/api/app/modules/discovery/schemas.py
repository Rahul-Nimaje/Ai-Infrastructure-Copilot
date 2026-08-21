from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ScanStartRequest(BaseModel):
    target_range: str = Field(..., description="Target subnet range, e.g. 192.168.1.0/24")
    scan_type: str = Field("all", description="ping | arp | snmp | wmi | ssh | all")
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
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class DeviceStorageResponse(BaseModel):
    id: UUID
    disk_model: str | None
    serial_number: str | None
    capacity_bytes: int | None
    free_space_bytes: int | None
    partitions: list | None

    class Config:
        from_attributes = True


class DeviceMemoryResponse(BaseModel):
    id: UUID
    total_ram_bytes: int | None
    available_ram_bytes: int | None
    memory_slots: int | None
    ram_modules: list | None

    class Config:
        from_attributes = True


class DeviceProcessorResponse(BaseModel):
    id: UUID
    processor_name: str | None
    architecture: str | None
    cores: int | None
    logical_processors: int | None
    current_speed_mhz: int | None

    class Config:
        from_attributes = True


class DeviceHardwareDetailsResponse(BaseModel):
    inventory: DeviceInventoryResponse | None
    processors: list[DeviceProcessorResponse]
    memory: list[DeviceMemoryResponse]
    storage: list[DeviceStorageResponse]
    interfaces: list[DeviceNetworkInterfaceResponse]


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
