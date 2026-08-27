import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

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
    DeviceAllHistoryResponse,
    DeviceProcessResponse,
    DeviceSecurityResponse,
    DevicePortResponse,
)
from py_shared.enums import ScanMode


def _enqueue_scan(scan_id: uuid.UUID, organization_id: str, actor_id: str) -> None:
    from app.workers.tasks.discovery_tasks import run_network_scan_task
    run_network_scan_task.delay(str(scan_id), organization_id, actor_id)


def _enqueue_device_inventory(device_id: uuid.UUID, organization_id: str, actor_id: str) -> None:
    try:
        from app.workers.tasks.discovery_tasks import run_device_inventory_task
        run_device_inventory_task.delay(str(device_id), organization_id, None, actor_id)
    except Exception:
        pass

    import asyncio
    async def _bg_run():
        from app.core.db import SessionLocal
        from app.modules.discovery.service import run_inventory_collection
        try:
            async with SessionLocal() as db:
                await run_inventory_collection(
                    db,
                    uuid.UUID(organization_id),
                    device_id,
                    uuid.UUID(actor_id) if actor_id else None
                )
        except Exception as err:
            import logging
            logging.getLogger(__name__).warning("Asyncio inventory collection failed for device %s: %s", device_id, err)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_bg_run())
    except RuntimeError:
        asyncio.run(_bg_run())


import socket
import ipaddress

# New router for explicit /network routes
network_router = APIRouter(prefix="/api/v1/network", tags=["network"])

# New router for inventory and devices routes
inventory_router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])
devices_router = APIRouter(prefix="/api/v1/devices", tags=["devices"])

# Legacy router for /discovery compatibility
discovery_router = APIRouter(prefix="/api/v1/discovery", tags=["discovery"])


@network_router.get("/local-subnet")
@discovery_router.get("/local-subnet")
async def get_local_network_subnet(
    current_user: AccessTokenClaims = Depends(require_permission("discovery.read")),
):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        net = str(ipaddress.IPv4Interface(f"{local_ip}/24").network)
        return {
            "local_ip": local_ip,
            "cidr_range": net,
            "suggested_target": f"{local_ip.rsplit('.', 1)[0]}.0/24",
        }
    except Exception:
        return {
            "local_ip": "127.0.0.1",
            "cidr_range": "192.168.1.0/24",
            "suggested_target": "192.168.1.0/24",
        }



# --- New Network Routes ---

async def _require_full_scan_permission_if_needed(payload: ScanStartRequest, current_user: AccessTokenClaims) -> None:
    if payload.scan_mode == ScanMode.FULL:
        has_perm = "discovery.inventory.collect" in current_user.permissions or "discovery.scan" in current_user.permissions
        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "Missing permission: discovery.inventory.collect or discovery.scan (required for Full scans)"},
            )


@network_router.post("/scan", response_model=NetworkScanResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_network_scan(
    payload: ScanStartRequest,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.scan")),
    db: AsyncSession = Depends(get_org_db),
):
    await _require_full_scan_permission_if_needed(payload, current_user)
    scan = await service.start_scan(
        db,
        uuid.UUID(current_user.organization_id),
        payload,
        uuid.UUID(current_user.user_id)
    )
    _enqueue_scan(scan.id, current_user.organization_id, current_user.user_id)
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
    scan_status: str | None = None,
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
        scan_status=scan_status,
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
    current_user: AccessTokenClaims = Depends(require_permission("discovery.scan")),
    db: AsyncSession = Depends(get_org_db),
):
    await _require_full_scan_permission_if_needed(payload, current_user)
    scan = await service.start_scan(
        db,
        uuid.UUID(current_user.organization_id),
        payload,
        uuid.UUID(current_user.user_id)
    )
    _enqueue_scan(scan.id, current_user.organization_id, current_user.user_id)
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
    scan_status: str | None = None,
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
        scan_status=scan_status,
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
    current_user: AccessTokenClaims = Depends(require_permission("discovery.scan")),
    db: AsyncSession = Depends(get_org_db),
):
    await _require_full_scan_permission_if_needed(payload, current_user)
    scan = await service.start_scan(
        db,
        uuid.UUID(current_user.organization_id),
        payload,
        uuid.UUID(current_user.user_id)
    )
    _enqueue_scan(scan.id, current_user.organization_id, current_user.user_id)
    return scan


@inventory_router.post("/collect/{deviceId}", status_code=status.HTTP_202_ACCEPTED)
async def collect_device_inventory(
    deviceId: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.inventory.collect")),
    db: AsyncSession = Depends(get_org_db),
):
    _enqueue_device_inventory(deviceId, current_user.organization_id, current_user.user_id)
    return {"status": "enqueued", "device_id": deviceId}


@inventory_router.post("/collect-all", status_code=status.HTTP_202_ACCEPTED)
async def collect_all_devices_inventory(
    current_user: AccessTokenClaims = Depends(require_permission("discovery.inventory.collect")),
    db: AsyncSession = Depends(get_org_db),
):
    devs_q = await db.execute(select(Device).where(and_(
        Device.organization_id == uuid.UUID(current_user.organization_id),
        Device.status == "online",
        Device.deleted_at.is_(None)
    )))
    devices = list(devs_q.scalars().all())

    for device in devices:
        _enqueue_device_inventory(device.id, current_user.organization_id, current_user.user_id)
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
    scan_status: str | None = None,
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
        scan_status=scan_status,
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


@devices_router.get("/{id}/processes", response_model=list[DeviceProcessResponse])
async def get_device_processes(
    id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.inventory.read")),
    db: AsyncSession = Depends(get_org_db),
):
    return await service.get_device_processes(db, uuid.UUID(current_user.organization_id), id)


@devices_router.get("/{id}/security", response_model=DeviceSecurityResponse | None)
async def get_device_security(
    id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.inventory.read")),
    db: AsyncSession = Depends(get_org_db),
):
    return await service.get_device_security(db, uuid.UUID(current_user.organization_id), id)


@devices_router.get("/{id}/ports", response_model=list[DevicePortResponse])
async def get_device_ports(
    id: uuid.UUID,
    current_user: AccessTokenClaims = Depends(require_permission("discovery.read")),
    db: AsyncSession = Depends(get_org_db),
):
    return await service.get_device_ports(db, uuid.UUID(current_user.organization_id), id)
