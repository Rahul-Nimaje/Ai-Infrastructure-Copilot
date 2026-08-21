import uuid
from typing import Any
from fastapi import APIRouter, Depends, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.db import SessionLocal
from app.core.security import AccessTokenClaims, require_permission
from app.dependencies import get_org_db
from app.models.device import Device
from app.modules.discovery import service
from app.modules.discovery.schemas import (
    ScanStartRequest,
    NetworkScanResponse,
    DeviceScanResponse,
    DeviceResponse,
    DeviceScanHistoryResponse,
    DeviceStatusHistoryResponse,
    DeviceHistoryResponse,
    DeviceIPHistoryResponse,
    DeviceInventoryResponse,
    DeviceNetworkInterfaceResponse,
    DeviceStorageResponse,
    DeviceMemoryResponse,
    DeviceProcessorResponse,
    DeviceHardwareDetailsResponse,
    DeviceInstalledSoftwareResponse,
    DeviceServiceResponse,
    DeviceSoftwareDetailsResponse,
    DeviceInventoryHistoryResponse,
    DeviceAllHistoryResponse
)

# New router for explicit /network routes
network_router = APIRouter(prefix="/api/v1/network", tags=["network"])

# New router for inventory and devices routes
inventory_router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])
devices_router = APIRouter(prefix="/api/v1/devices", tags=["devices"])

# Legacy router for /discovery compatibility
discovery_router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])


# --- New Network Routes ---

@network_router.post("/scan", response_model=NetworkScanResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_network_scan(
    payload: ScanStartRequest,
    background_tasks: BackgroundTasks,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.scan")),
    db: AsyncSession = Depends(get_org_db),
):
    scan = await service.start_scan(
        db,
        uuid.UUID(current_user.organization_id),
        payload,
        uuid.UUID(current_user.user_id)
    )
    background_tasks.add_task(
        service.run_discovery_scan_task,
        SessionLocal,
        uuid.UUID(current_user.organization_id),
        scan.id,
        uuid.UUID(current_user.user_id)
    )
    return scan


@network_router.get("/scans", response_model=list[NetworkScanResponse])
async def list_network_scans(
    current_user: AccessTokenClaims = Depends(require_permission("discovery.read")),
    db: AsyncSession = Depends(get_org_db),
):
    return await service.list_scans(db, uuid.UUID(current_user.organization_id))


@network_router.get("/devices", response_model=dict[str, Any])
async def list_network_devices(
    page: int = 1,
    size: int = 20,
    search: str | None = None,
    status: str | None = None,
    device_type: str | None = None,
    operating_system: str | None = None,
    vendor: str | None = None,
    response_time: str | None = None,
    last_seen: str | None = None,
    sort_by: str = "last_seen_at",
    sort_order: str = "desc",
    current_user: AccessTokenClaims = Depends(require_permission("discovery.read")),
    db: AsyncSession = Depends(get_org_db),
):
    devices, total = await service.list_devices(
        db,
        uuid.UUID(current_user.organization_id),
        page=page,
        size=size,
        search=search,
        status_filter=status,
        device_type=device_type,
        operating_system=operating_system,
        vendor=vendor,
        response_time_bucket=response_time,
        last_seen_bucket=last_seen,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return {
        "items": [DeviceResponse.model_validate(d) for d in devices],
        "total": total,
        "page": page,
        "size": size
    }


@network_router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_network_device(
    device_id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.read")),
    db: AsyncSession = Depends(get_org_db),
):
    return await service.get_device_detail(db, uuid.UUID(current_user.organization_id), device_id)


@network_router.get("/devices/history/{device_id}", response_model=list[DeviceStatusHistoryResponse])
async def get_network_device_history(
    device_id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.read")),
    db: AsyncSession = Depends(get_org_db),
):
    return await service.get_device_status_history(db, uuid.UUID(current_user.organization_id), device_id)


@network_router.get("/ip-history/{device_id}", response_model=list[DeviceIPHistoryResponse])
async def get_network_device_ip_history(
    device_id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.read")),
    db: AsyncSession = Depends(get_org_db),
):
    return await service.get_device_ip_history(db, uuid.UUID(current_user.organization_id), device_id)


# --- Legacy Discovery Routes (for backward compatibility) ---

@discovery_router.post("/scan", response_model=DeviceScanResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_discovery_scan(
    payload: ScanStartRequest,
    background_tasks: BackgroundTasks,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.scan")),
    db: AsyncSession = Depends(get_org_db),
):
    scan = await service.start_scan(
        db,
        uuid.UUID(current_user.organization_id),
        payload,
        uuid.UUID(current_user.user_id)
    )
    background_tasks.add_task(
        service.run_discovery_scan_task,
        SessionLocal,
        uuid.UUID(current_user.organization_id),
        scan.id,
        uuid.UUID(current_user.user_id)
    )
    # Map NetworkScan to DeviceScanResponse format
    return {
        "id": scan.id,
        "organization_id": scan.organization_id,
        "status": scan.status,
        "scan_type": scan.scan_type,
        "target_range": scan.scan_range,
        "started_at": scan.started_at,
        "completed_at": scan.completed_at,
        "devices_found": scan.total_devices,
        "error_message": scan.error_message,
        "created_at": scan.created_at
    }


@discovery_router.delete("/scan/{scan_id}", response_model=DeviceScanResponse)
async def stop_discovery_scan(
    scan_id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.scan")),
    db: AsyncSession = Depends(get_org_db),
):
    scan = await service.stop_scan(db, uuid.UUID(current_user.organization_id), scan_id, uuid.UUID(current_user.user_id))
    return {
        "id": scan.id,
        "organization_id": scan.organization_id,
        "status": scan.status,
        "scan_type": scan.scan_type,
        "target_range": scan.scan_range,
        "started_at": scan.started_at,
        "completed_at": scan.completed_at,
        "devices_found": scan.total_devices,
        "error_message": scan.error_message,
        "created_at": scan.created_at
    }


@discovery_router.get("/scan", response_model=list[DeviceScanResponse])
async def list_discovery_scans(
    current_user: AccessTokenClaims = Depends(require_permission("discovery.read")),
    db: AsyncSession = Depends(get_org_db),
):
    scans = await service.list_scans(db, uuid.UUID(current_user.organization_id))
    res = []
    for s in scans:
        res.append({
            "id": s.id,
            "organization_id": s.organization_id,
            "status": s.status,
            "scan_type": s.scan_type,
            "target_range": s.scan_range,
            "started_at": s.started_at,
            "completed_at": s.completed_at,
            "devices_found": s.total_devices,
            "error_message": s.error_message,
            "created_at": s.created_at
        })
    return res


@discovery_router.get("/devices", response_model=dict[str, Any])
async def list_discovery_devices(
    page: int = 1,
    size: int = 20,
    search: str | None = None,
    status: str | None = None,
    device_type: str | None = None,
    operating_system: str | None = None,
    vendor: str | None = None,
    response_time: str | None = None,
    last_seen: str | None = None,
    sort_by: str = "last_seen_at",
    sort_order: str = "desc",
    current_user: AccessTokenClaims = Depends(require_permission("discovery.read")),
    db: AsyncSession = Depends(get_org_db),
):
    devices, total = await service.list_devices(
        db,
        uuid.UUID(current_user.organization_id),
        page=page,
        size=size,
        search=search,
        status_filter=status,
        device_type=device_type,
        operating_system=operating_system,
        vendor=vendor,
        response_time_bucket=response_time,
        last_seen_bucket=last_seen,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return {
        "items": [DeviceResponse.model_validate(d) for d in devices],
        "total": total,
        "page": page,
        "size": size
    }


@discovery_router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_discovery_device(
    device_id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.read")),
    db: AsyncSession = Depends(get_org_db),
):
    return await service.get_device_detail(db, uuid.UUID(current_user.organization_id), device_id)


@discovery_router.get("/devices/{device_id}/history", response_model=list[DeviceHistoryResponse])
async def get_discovery_device_history(
    device_id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.read")),
    db: AsyncSession = Depends(get_org_db),
):
    return await service.get_device_history(db, uuid.UUID(current_user.organization_id), device_id)


# --- Hardware Discovery & Inventory Routes ---

@network_router.post("/discover", response_model=NetworkScanResponse, status_code=status.HTTP_202_ACCEPTED)
async def discover_network(
    payload: ScanStartRequest,
    background_tasks: BackgroundTasks,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.scan")),
    db: AsyncSession = Depends(get_org_db),
):
    scan = await service.start_scan(
        db,
        uuid.UUID(current_user.organization_id),
        payload,
        uuid.UUID(current_user.user_id)
    )
    background_tasks.add_task(
        service.run_discovery_scan_task,
        SessionLocal,
        uuid.UUID(current_user.organization_id),
        scan.id,
        uuid.UUID(current_user.user_id)
    )
    return scan


@inventory_router.post("/collect/{deviceId}", status_code=status.HTTP_202_ACCEPTED)
async def collect_device_inventory(
    deviceId: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.scan")),
    db: AsyncSession = Depends(get_org_db),
):
    background_tasks.add_task(
        service.run_device_inventory_task,
        SessionLocal,
        uuid.UUID(current_user.organization_id),
        deviceId,
        uuid.UUID(current_user.user_id)
    )
    return {"status": "enqueued", "device_id": deviceId}


@inventory_router.post("/collect-all", status_code=status.HTTP_202_ACCEPTED)
async def collect_all_devices_inventory(
    background_tasks: BackgroundTasks,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.scan")),
    db: AsyncSession = Depends(get_org_db),
):
    devs_q = await db.execute(select(Device).where(and_(
        Device.organization_id == uuid.UUID(current_user.organization_id),
        Device.status == "online",
        Device.deleted_at.is_(None)
    )))
    devices = list(devs_q.scalars().all())
    
    for device in devices:
        background_tasks.add_task(
            service.run_device_inventory_task,
            SessionLocal,
            uuid.UUID(current_user.organization_id),
            device.id,
            uuid.UUID(current_user.user_id)
        )
    return {"status": "enqueued", "total_devices": len(devices)}


@devices_router.get("", response_model=dict[str, Any])
async def list_devices(
    page: int = 1,
    size: int = 20,
    search: str | None = None,
    status: str | None = None,
    device_type: str | None = None,
    operating_system: str | None = None,
    vendor: str | None = None,
    response_time: str | None = None,
    last_seen: str | None = None,
    sort_by: str = "last_seen_at",
    sort_order: str = "desc",
    current_user: AccessTokenClaims = Depends(require_permission("discovery.read")),
    db: AsyncSession = Depends(get_org_db),
):
    devices, total = await service.list_devices(
        db,
        uuid.UUID(current_user.organization_id),
        page=page,
        size=size,
        search=search,
        status_filter=status,
        device_type=device_type,
        operating_system=operating_system,
        vendor=vendor,
        response_time_bucket=response_time,
        last_seen_bucket=last_seen,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return {
        "items": [DeviceResponse.model_validate(d) for d in devices],
        "total": total,
        "page": page,
        "size": size
    }


@devices_router.get("/{id}", response_model=DeviceResponse)
async def get_device_summary(
    id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.read")),
    db: AsyncSession = Depends(get_org_db),
):
    return await service.get_device_detail(db, uuid.UUID(current_user.organization_id), id)


@devices_router.get("/{id}/hardware", response_model=DeviceHardwareDetailsResponse)
async def get_device_hardware_details(
    id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.read")),
    db: AsyncSession = Depends(get_org_db),
):
    return await service.get_device_hardware(db, uuid.UUID(current_user.organization_id), id)


@devices_router.get("/{id}/software", response_model=DeviceSoftwareDetailsResponse)
async def get_device_software_details(
    id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.read")),
    db: AsyncSession = Depends(get_org_db),
):
    return await service.get_device_software(db, uuid.UUID(current_user.organization_id), id)


@devices_router.get("/{id}/history", response_model=DeviceAllHistoryResponse)
async def get_device_histories(
    id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.read")),
    db: AsyncSession = Depends(get_org_db),
):
    return await service.get_device_all_history(db, uuid.UUID(current_user.organization_id), id)
