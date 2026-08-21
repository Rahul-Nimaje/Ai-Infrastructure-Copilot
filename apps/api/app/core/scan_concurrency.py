"""Per-organization in-flight counter for Full-scan credentialed inventory
collection (section 11/16) — caps simultaneous WinRM/SSH/SNMP connections
per org regardless of overall Celery worker concurrency, protecting the
target device fleet rather than this server's own resources. Backed by the
same Redis instance already used as the Celery broker, so no new
infrastructure is introduced.
"""
from __future__ import annotations

import redis.asyncio as aioredis

from app.core.config import settings

_KEY_PREFIX = "discovery:inflight:"
_SLOT_TTL_SECONDS = 300  # auto-expire a slot if a worker crashes mid-collection

_redis: aioredis.Redis | None = None


def _client() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def try_acquire_slot(organization_id: str, *, max_in_flight: int | None = None) -> bool:
    """Best-effort acquire — increments the org's in-flight counter and
    returns False (without incrementing) if it's already at the cap."""
    cap = max_in_flight if max_in_flight is not None else settings.discovery_max_concurrent_inventory
    client = _client()
    key = f"{_KEY_PREFIX}{organization_id}"
    current = await client.incr(key)
    if current == 1:
        await client.expire(key, _SLOT_TTL_SECONDS)
    if current > cap:
        await client.decr(key)
        return False
    return True


async def release_slot(organization_id: str) -> None:
    client = _client()
    key = f"{_KEY_PREFIX}{organization_id}"
    new_value = await client.decr(key)
    if new_value <= 0:
        await client.delete(key)


async def wait_for_slot(organization_id: str, *, max_in_flight: int | None = None, poll_interval: float = 1.0) -> None:
    """Blocks (via polling) until a slot is available, then holds it.
    Callers must call release_slot() in a finally block."""
    import asyncio

    while not await try_acquire_slot(organization_id, max_in_flight=max_in_flight):
        await asyncio.sleep(poll_interval)
