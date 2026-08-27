"""Celery tasks for network discovery / full device inventory scanning.

Replaces the old FastAPI BackgroundTasks-driven execution (no queue, no real
retry, lost on process restart) with proper background jobs: one task per
scan (discovery + identification), fanning out to one task per device for
Full-mode credentialed inventory collection — see the feature plan's
"Background jobs" section for the reasoning behind this split (nmap itself
already parallelizes host discovery; WinRM/SSH/SNMP collection is where
per-device concurrency limits, retry, and timeout actually matter).
"""
from __future__ import annotations

import asyncio
import logging
import uuid

from app.core.scan_concurrency import release_slot, try_acquire_slot
from app.socket_app import emit_to_org
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async function cleanly in an event loop (Celery workers are sync)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@celery_app.task(
    bind=True,
    name="app.workers.tasks.discovery_tasks.run_network_scan_task",
    max_retries=1,
    default_retry_delay=30,
    acks_late=True,
    time_limit=1800,
    soft_time_limit=1740,
)
def run_network_scan_task(self, scan_id: str, organization_id: str, actor_id: str):
    """Discovery + identification for one scan. `max_retries=1` deliberately
    diverges from this file's document_tasks.py sibling's default of 3 — a
    failed sweep with partial device state already committed shouldn't
    blindly retry multiple times."""
    logger.info("Running network scan %s for org %s", scan_id, organization_id)

    async def _do_scan():
        from app.core.db import SessionLocal
        from app.modules.discovery.service import run_discovery_scan_task

        await emit_to_org(
            "discovery.scan.progress",
            {"scan_id": scan_id, "phase": "discovering", "devices_total": 0, "devices_processed": 0},
            organization_id=organization_id,
        )
        candidate_ids = await run_discovery_scan_task(
            SessionLocal, uuid.UUID(organization_id), uuid.UUID(scan_id), uuid.UUID(actor_id),
        )
        
        if candidate_ids:
            await emit_to_org(
                "discovery.scan.progress",
                {"scan_id": scan_id, "phase": "scanning", "devices_total": len(candidate_ids), "devices_processed": 0},
                organization_id=organization_id,
            )
        else:
            await emit_to_org(
                "discovery.scan.completed",
                {"scan_id": scan_id, "status": "completed"},
                organization_id=organization_id,
            )
        return candidate_ids

    try:
        candidate_ids = _run_async(_do_scan())
    except Exception as exc:
        logger.exception("Network scan %s failed", scan_id)
        raise self.retry(exc=exc)

    if candidate_ids:
        for device_id in candidate_ids:
            run_device_inventory_task.delay(str(device_id), organization_id, scan_id, actor_id)

    logger.info("Network scan %s discovery phase complete (%d device(s) queued for full inventory)", scan_id, len(candidate_ids or []))


@celery_app.task(
    bind=True,
    name="app.workers.tasks.discovery_tasks.run_device_inventory_task",
    max_retries=3,
    default_retry_delay=15,
    acks_late=True,
    time_limit=180,
    soft_time_limit=150,
)
def run_device_inventory_task(self, device_id: str, organization_id: str, scan_id: str | None = None, actor_id: str | None = None):
    """Full-mode credentialed inventory collection for a single device."""
    logger.info("Collecting inventory for device %s (org %s)", device_id, organization_id)

    async def _do_inventory():
        from app.core.db import SessionLocal
        from sqlalchemy import select
        from app.models.device import Device
        from app.modules.discovery.service import run_inventory_collection

        from app.core.scan_concurrency import wait_for_slot
        await wait_for_slot(organization_id)
        try:
            async with SessionLocal() as db:
                await run_inventory_collection(
                    db, uuid.UUID(organization_id), uuid.UUID(device_id),
                    uuid.UUID(actor_id) if actor_id else None,
                )
        finally:
            await release_slot(organization_id)

        async with SessionLocal() as db:
            device_q = await db.execute(select(Device).where(Device.id == uuid.UUID(device_id)))
            device = device_q.scalar_one_or_none()
            await emit_to_org(
                "discovery.device.progress",
                {
                    "scan_id": scan_id, "device_id": device_id,
                    "device_name": device.name if device else None,
                    "status": device.scan_status if device else "failed",
                },
                organization_id=organization_id,
            )

    try:
        _run_async(_do_inventory())
    except Exception as exc:
        logger.exception("Device inventory collection failed for %s (attempt %d)", device_id, self.request.retries + 1)
        raise self.retry(exc=exc)

    logger.info("Device %s inventory collection complete", device_id)
