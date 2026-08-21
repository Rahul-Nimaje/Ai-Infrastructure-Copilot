"""network_discovery

Revision ID: 1c5e519833f1
Revises: 0004
Create Date: 2026-07-14 16:38:11.495882

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1c5e519833f1'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create network_scans table
    op.create_table(
        "network_scans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("scan_range", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("scan_type", sa.String(length=50), server_default="ping", nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("total_devices", sa.Integer(), server_default="0", nullable=False),
        sa.Column("online_devices", sa.Integer(), server_default="0", nullable=False),
        sa.Column("offline_devices", sa.Integer(), server_default="0", nullable=False),
        sa.Column("scan_duration", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Add columns to devices table
    op.add_column("devices", sa.Column("first_seen_at", sa.DateTime(), server_default=sa.func.now(), nullable=False))
    op.add_column("devices", sa.Column("scan_timestamp", sa.DateTime(), nullable=True))
    op.add_column("devices", sa.Column("network_interface", sa.String(length=100), nullable=True))

    # 3. Create indexes on devices table
    op.create_index("idx_devices_name", "devices", ["name"])
    op.create_index("idx_devices_ip_address", "devices", ["ip_address"])
    op.create_index("idx_devices_mac_address", "devices", ["mac_address"])
    op.create_index("idx_devices_status", "devices", ["status"])
    op.create_index("idx_devices_last_seen_at", "devices", ["last_seen_at"])

    # 4. Migrate data from device_scans to network_scans (if any)
    conn = op.get_bind()
    conn.execute(sa.text(
        "INSERT INTO network_scans (id, organization_id, scan_range, status, scan_type, started_at, completed_at, total_devices, created_by_id, created_at) "
        "SELECT id, organization_id, COALESCE(target_range, '192.168.1.0/24'), status, scan_type, started_at, completed_at, devices_found, created_by_id, created_at FROM device_scans"
    ))

    # 5. Create device_scan_history table
    op.create_table(
        "device_scan_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("response_time", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_id"], ["network_scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 6. Create device_status_history table
    op.create_table(
        "device_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("response_time", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("vendor", sa.String(length=100), nullable=True),
        sa.Column("operating_system", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 7. Create device_ip_history table
    op.create_table(
        "device_ip_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("old_ip", sa.String(length=45), nullable=True),
        sa.Column("new_ip", sa.String(length=45), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 8. Migrate data from device_history to device_status_history (if any)
    conn.execute(sa.text(
        "INSERT INTO device_status_history (id, organization_id, device_id, status, response_time, hostname, vendor, operating_system, created_at) "
        "SELECT h.id, h.organization_id, h.device_id, COALESCE(h.after_state->>'status', 'unknown'), "
        "CAST(h.after_state->>'response_time' AS NUMERIC), d.name, d.vendor, d.operating_system, h.created_at "
        "FROM device_history h JOIN devices d ON h.device_id = d.id"
    ))

    # 9. Drop old tables
    op.drop_table("device_history")
    op.drop_table("device_scans")


def downgrade() -> None:
    # 1. Re-create device_scans and device_history
    op.create_table(
        "device_scans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("scan_type", sa.String(length=50), nullable=False),
        sa.Column("target_range", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("devices_found", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    
    op.create_table(
        "device_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("before_state", sa.JSON(), nullable=True),
        sa.Column("after_state", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Drop the new history tables
    op.drop_table("device_ip_history")
    op.drop_table("device_status_history")
    op.drop_table("device_scan_history")
    op.drop_table("network_scans")

    # 3. Drop indexes on devices
    op.drop_index("idx_devices_last_seen_at", table_name="devices")
    op.drop_index("idx_devices_status", table_name="devices")
    op.drop_index("idx_devices_mac_address", table_name="devices")
    op.drop_index("idx_devices_ip_address", table_name="devices")
    op.drop_index("idx_devices_name", table_name="devices")

    # 4. Remove columns from devices
    op.drop_column("devices", "network_interface")
    op.drop_column("devices", "scan_timestamp")
    op.drop_column("devices", "first_seen_at")
