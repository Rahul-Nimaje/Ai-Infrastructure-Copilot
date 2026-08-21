"""Discovery full-inventory RBAC permissions — discovery.inventory.read,
discovery.inventory.collect, discovery.credentials.assign. Follows the same
idempotent seed pattern as e0c3996d06bd_add_user_details_and_device_models.

Revision ID: 0007_discovery_permissions
Revises: 0006_device_inventory_expansion
Create Date: 2026-08-21
"""
import uuid
from alembic import op
import sqlalchemy as sa

revision = "0007_discovery_permissions"
down_revision = "0006_device_inventory_expansion"
branch_labels = None
depends_on = None


NEW_PERMISSIONS = [
    ("discovery.inventory.read", "Network Discovery"),
    ("discovery.inventory.collect", "Network Discovery"),
    ("discovery.credentials.assign", "Network Discovery"),
]

# Additive grants per existing default role name — Super Admin gets every
# permission automatically (see below), so it's excluded from this map.
ROLE_GRANTS = {
    "Network Administrator": [
        "discovery.inventory.read",
        "discovery.inventory.collect",
        "discovery.credentials.assign",
    ],
    "Infrastructure Admin": ["discovery.inventory.read", "discovery.inventory.collect"],
    "Windows Administrator": ["discovery.inventory.read"],
    "Linux Administrator": ["discovery.inventory.read"],
    "Security Administrator": ["discovery.inventory.read"],
    "Helpdesk Engineer": ["discovery.inventory.read"],
    "Read Only User": ["discovery.inventory.read"],
}


def upgrade() -> None:
    conn = op.get_bind()

    org_row = conn.execute(sa.text("SELECT id FROM organizations WHERE slug = 'acme-corp'")).fetchone()
    if org_row is None:
        return
    org_id = org_row[0]

    permission_ids = {}
    for code, module in NEW_PERMISSIONS:
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

    # Grant Super Admin every new code (it already has everything else).
    super_admin_row = conn.execute(
        sa.text("SELECT id FROM roles WHERE organization_id = :org_id AND name = 'Super Admin'"),
        {"org_id": org_id},
    ).fetchone()
    if super_admin_row is not None:
        role_id = super_admin_row[0]
        for code in permission_ids:
            _link_if_missing(conn, role_id, permission_ids[code])

    for role_name, codes in ROLE_GRANTS.items():
        role_row = conn.execute(
            sa.text("SELECT id FROM roles WHERE organization_id = :org_id AND name = :name"),
            {"org_id": org_id, "name": role_name},
        ).fetchone()
        if role_row is None:
            continue
        role_id = role_row[0]
        for code in codes:
            perm_id = permission_ids.get(code)
            if perm_id:
                _link_if_missing(conn, role_id, perm_id)


def _link_if_missing(conn, role_id, permission_id) -> None:
    exists = conn.execute(
        sa.text("SELECT 1 FROM role_permissions WHERE role_id = :r_id AND permission_id = :p_id"),
        {"r_id": role_id, "p_id": permission_id},
    ).fetchone()
    if not exists:
        conn.execute(
            sa.text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:r_id, :p_id)"),
            {"r_id": role_id, "p_id": permission_id},
        )


def downgrade() -> None:
    conn = op.get_bind()
    codes = [code for code, _ in NEW_PERMISSIONS]
    perm_rows = conn.execute(
        sa.text("SELECT id FROM permissions WHERE code = ANY(:codes)"), {"codes": codes}
    ).fetchall()
    perm_ids = [row[0] for row in perm_rows]
    if perm_ids:
        conn.execute(
            sa.text("DELETE FROM role_permissions WHERE permission_id = ANY(:ids)"), {"ids": perm_ids}
        )
        conn.execute(sa.text("DELETE FROM permissions WHERE id = ANY(:ids)"), {"ids": perm_ids})
