"""Seed a default organization + admin user, baked into the migration so a
fresh database always has a login without a separate manual seed step.

`scripts/seed.py` still exists for demo data (a sample server + event log
entries) and is idempotent-unsafe by design (always inserts fresh demo rows);
this migration is the one-time, idempotent bootstrap of the login itself.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-13

"""
import uuid

import sqlalchemy as sa
from alembic import op
from argon2 import PasswordHasher

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

DEFAULT_ORG_NAME = "Acme Corp"
DEFAULT_ORG_SLUG = "acme-corp"
DEFAULT_ADMIN_EMAIL = "admin@acmecorp.io"
DEFAULT_ADMIN_PASSWORD = "ChangeMe123!"

# Mirrors app/modules/authentication/service.py's PHASE_1_PERMISSIONS.
# Duplicated deliberately rather than imported: migrations must stay valid
# and reproducible even if that module's constant changes later.
PHASE_1_PERMISSIONS = [
    ("servers.read", "Infrastructure Inventory"),
    ("servers.write", "Infrastructure Inventory"),
    ("events.read", "Windows Event Log Analyzer"),
    ("scripts.read", "PowerShell Generator"),
    ("scripts.write", "PowerShell Generator"),
    ("scripts.execute", "PowerShell Generator"),
    ("tasks.read", "PowerShell Generator"),
    ("tasks.approve", "PowerShell Generator"),
    ("ai_chat.use", "AI Chat"),
]


def upgrade() -> None:
    conn = op.get_bind()

    existing_org = conn.execute(
        sa.text("SELECT id FROM organizations WHERE slug = :slug"), {"slug": DEFAULT_ORG_SLUG}
    ).fetchone()
    if existing_org is not None:
        # Already seeded (e.g. migration re-run against a DB that already
        # has it) — leave everything as-is rather than duplicating rows.
        return

    org_id = uuid.uuid4()
    conn.execute(
        sa.text(
            "INSERT INTO organizations (id, name, slug, plan_tier, status) "
            "VALUES (:id, :name, :slug, 'starter', 'active')"
        ),
        {"id": org_id, "name": DEFAULT_ORG_NAME, "slug": DEFAULT_ORG_SLUG},
    )

    permission_ids: dict[str, uuid.UUID] = {}
    for code, module in PHASE_1_PERMISSIONS:
        row = conn.execute(sa.text("SELECT id FROM permissions WHERE code = :code"), {"code": code}).fetchone()
        if row is not None:
            permission_ids[code] = row[0]
            continue
        perm_id = uuid.uuid4()
        conn.execute(
            sa.text("INSERT INTO permissions (id, code, module) VALUES (:id, :code, :module)"),
            {"id": perm_id, "code": code, "module": module},
        )
        permission_ids[code] = perm_id

    role_id = uuid.uuid4()
    conn.execute(
        sa.text(
            "INSERT INTO roles (id, organization_id, name, is_system_role) "
            "VALUES (:id, :org_id, 'Admin', true)"
        ),
        {"id": role_id, "org_id": org_id},
    )
    for perm_id in permission_ids.values():
        conn.execute(
            sa.text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :perm_id)"),
            {"role_id": role_id, "perm_id": perm_id},
        )

    user_id = uuid.uuid4()
    password_hash = PasswordHasher().hash(DEFAULT_ADMIN_PASSWORD)
    conn.execute(
        sa.text(
            "INSERT INTO users (id, organization_id, email, password_hash, full_name, status) "
            "VALUES (:id, :org_id, :email, :password_hash, 'Admin User', 'active')"
        ),
        {"id": user_id, "org_id": org_id, "email": DEFAULT_ADMIN_EMAIL, "password_hash": password_hash},
    )
    conn.execute(
        sa.text("INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)"),
        {"user_id": user_id, "role_id": role_id},
    )


def downgrade() -> None:
    conn = op.get_bind()
    org_row = conn.execute(sa.text("SELECT id FROM organizations WHERE slug = :slug"), {"slug": DEFAULT_ORG_SLUG}).fetchone()
    if org_row is None:
        return
    org_id = org_row[0]

    # Delete in FK-safe order (0001's FKs default to ON DELETE RESTRICT).
    # Global `permissions` rows are left in place — they're a shared catalog,
    # not org-owned, per docs/04-database-design.md Section 2.
    conn.execute(
        sa.text(
            "DELETE FROM user_roles WHERE role_id IN (SELECT id FROM roles WHERE organization_id = :org_id)"
        ),
        {"org_id": org_id},
    )
    conn.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE role_id IN (SELECT id FROM roles WHERE organization_id = :org_id)"
        ),
        {"org_id": org_id},
    )
    conn.execute(sa.text("DELETE FROM users WHERE organization_id = :org_id"), {"org_id": org_id})
    conn.execute(sa.text("DELETE FROM roles WHERE organization_id = :org_id"), {"org_id": org_id})
    conn.execute(sa.text("DELETE FROM organizations WHERE id = :org_id"), {"org_id": org_id})
