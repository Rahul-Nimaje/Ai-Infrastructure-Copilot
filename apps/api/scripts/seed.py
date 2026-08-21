"""Seeds one Windows server plus a batch of realistic event_log_entries under
the default organization/admin that migration 0002_seed_default_admin.py
creates — so the Phase 1 AI Chat "why is X slow" flow is demonstrable without
a real Windows target on day one (EXECUTION_ENABLED=false by default).

This script no longer creates the organization/admin user itself (that moved
into the migration so a fresh DB always has a login without a manual seed
step); it only attaches demo infrastructure data to whatever org already
exists. Run with: python -m scripts.seed (from apps/api, venv active, after
`alembic upgrade head`).
"""
import asyncio
import sys
from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.vault import encrypt_secret
from app.models.credential import Credential
from app.models.event import EventLogEntry
from app.models.infrastructure import InfrastructureInventory, Server
from app.models.organization import Organization
from app.models.user import User

ADMIN_EMAIL = "admin@acmecorp.io"
ADMIN_PASSWORD = "ChangeMe123!"
ORG_SLUG = "acme-corp"
SERVER_HOSTNAME = "web-prod-03"


async def seed() -> None:
    async with SessionLocal() as db:
        org = (await db.execute(select(Organization).where(Organization.slug == ORG_SLUG))).scalar_one_or_none()
        if org is None:
            print(
                "No default organization found. Run `alembic upgrade head` first "
                "(migration 0002_seed_default_admin creates it)."
            )
            sys.exit(1)

        admin = (await db.execute(select(User).where(User.email == ADMIN_EMAIL))).scalar_one()

        existing_server = (
            await db.execute(select(Server).where(Server.organization_id == org.id, Server.hostname == SERVER_HOSTNAME))
        ).scalar_one_or_none()
        if existing_server is not None:
            print(f"'{SERVER_HOSTNAME}' already seeded for {org.name}; nothing to do.")
            return

        credential = Credential(
            organization_id=org.id,
            name=f"{SERVER_HOSTNAME}-winrm",
            credential_type="winrm",
            vault_engine="local_encrypted",
            vault_path=encrypt_secret({"username": "svc-winrm-demo", "secret": "demo-password-not-real"}),
            encrypted_metadata={"username": "svc-winrm-demo"},
            created_by_user_id=admin.id,
        )
        db.add(credential)
        await db.flush()

        server = Server(
            organization_id=org.id,
            hostname=SERVER_HOSTNAME,
            ip_address="10.20.4.17",
            os_type="windows",
            os_version="Windows Server 2022",
            environment="production",
            credential_id=credential.id,
            health_status="warning",
            cpu_usage_pct=78.40,
            memory_usage_pct=65.10,
            disk_usage_pct=42.00,
            last_seen_at=datetime.utcnow(),
        )
        db.add(server)
        await db.flush()
        db.add(
            InfrastructureInventory(
                organization_id=org.id, asset_type="server", asset_id=server.id,
                discovered_via="manual", attributes={"hostname": SERVER_HOSTNAME, "os_type": "windows"},
            )
        )

        # Mirrors the runbook example scenario in docs/06-ai-architecture.md
        # Section 6: a runaway backup process saturating disk I/O.
        now = datetime.utcnow()
        seeded_events = [
            (30, "System", 2004, "Warning", "srv", "Resource-Exhaustion-Detector detected process BackupAgent.exe consuming excessive CPU."),
            (28, "System", 7031, "Error", "Service Control Manager", "The Backup Agent service terminated unexpectedly and has restarted 3 times."),
            (25, "System", 2013, "Warning", "disk", "Disk queue length on volume C: has exceeded threshold for 10 minutes."),
            (20, "Application", 1000, "Error", "BackupAgent", "Backup job 'Nightly-Full' failed to complete within scheduled window."),
            (15, "System", 2004, "Warning", "srv", "Resource-Exhaustion-Detector detected process BackupAgent.exe consuming excessive CPU."),
            (5, "System", 6008, "Critical", "EventLog", "The previous system shutdown was unexpected."),
        ]
        for minutes_ago, channel, event_id, level, provider, message in seeded_events:
            db.add(
                EventLogEntry(
                    organization_id=org.id, server_id=server.id, log_channel=channel,
                    event_id=event_id, level=level, source_provider=provider, message=message,
                    occurred_at=now - timedelta(minutes=minutes_ago),
                )
            )

        await db.commit()

    print("Seed complete.")
    print(f"  Organization: {ORG_SLUG}")
    print(f"  Admin login:  {ADMIN_EMAIL} / {ADMIN_PASSWORD}  (created by migration 0002)")
    print(f"  Server:       {SERVER_HOSTNAME}")
    print("  Try asking AI Chat: \"why is web-prod-03 running slow?\"")


if __name__ == "__main__":
    asyncio.run(seed())
