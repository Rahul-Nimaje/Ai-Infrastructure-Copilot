"""Device inventory expansion — normalized partitions/processes/security/ports
tables plus hardware detail columns, for the full inventory scan feature.

Revision ID: 0006_device_inventory_expansion
Revises: 0005_knowledge_base
Create Date: 2026-08-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_device_inventory_expansion"
down_revision = "0005_knowledge_base"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New columns on devices — lifecycle + identification confidence (sections 2, 9)
    op.add_column("devices", sa.Column("scan_status", sa.String(length=30), nullable=True))
    op.add_column("devices", sa.Column("identification_confidence", sa.String(length=20), nullable=True))
    op.add_column("devices", sa.Column("identification_method", sa.String(length=50), nullable=True))

    # New columns — CPU max speed / socket
    op.add_column("device_processors", sa.Column("max_speed_mhz", sa.Integer(), nullable=True))
    op.add_column("device_processors", sa.Column("socket_designation", sa.String(length=50), nullable=True))

    # New column — RAM array configured speed
    op.add_column("device_memory", sa.Column("configured_speed_mhz", sa.Integer(), nullable=True))

    # New columns — disk interface/media/health
    op.add_column("device_storage", sa.Column("interface_type", sa.String(length=50), nullable=True))
    op.add_column("device_storage", sa.Column("media_type", sa.String(length=50), nullable=True))
    op.add_column("device_storage", sa.Column("health_status", sa.String(length=50), nullable=True))

    # New columns — network interface speed/duplex/type
    op.add_column("device_network_interfaces", sa.Column("speed_mbps", sa.Integer(), nullable=True))
    op.add_column("device_network_interfaces", sa.Column("duplex", sa.String(length=20), nullable=True))
    op.add_column("device_network_interfaces", sa.Column("interface_type", sa.String(length=50), nullable=True))

    # New table: device_partitions
    op.create_table(
        "device_partitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("storage_id", sa.Uuid(), nullable=True),
        sa.Column("mount_point", sa.String(length=255), nullable=True),
        sa.Column("device_node", sa.String(length=100), nullable=True),
        sa.Column("filesystem_type", sa.String(length=50), nullable=True),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("capacity_bytes", sa.BigInteger(), nullable=True),
        sa.Column("used_bytes", sa.BigInteger(), nullable=True),
        sa.Column("free_space_bytes", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["storage_id"], ["device_storage.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_device_partitions_device", "device_partitions", ["device_id"])

    # New table: device_processes (point-in-time snapshot)
    op.create_table(
        "device_processes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("pid", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("command_line", sa.Text(), nullable=True),
        sa.Column("user_name", sa.String(length=100), nullable=True),
        sa.Column("cpu_percent", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("memory_bytes", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("collected_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_device_processes_device", "device_processes", ["device_id"])
    op.create_index(op.f("ix_device_processes_name"), "device_processes", ["name"], unique=False)

    # New table: device_security (1:1)
    op.create_table(
        "device_security",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("defender_enabled", sa.Boolean(), nullable=True),
        sa.Column("defender_signature_version", sa.String(length=100), nullable=True),
        sa.Column("firewall_enabled", sa.Boolean(), nullable=True),
        sa.Column("firewall_profiles", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("bitlocker_status", sa.String(length=50), nullable=True),
        sa.Column("secure_boot_enabled", sa.Boolean(), nullable=True),
        sa.Column("antivirus_product", sa.String(length=255), nullable=True),
        sa.Column("antivirus_up_to_date", sa.Boolean(), nullable=True),
        sa.Column("pending_updates_count", sa.Integer(), nullable=True),
        sa.Column("last_update_installed_at", sa.DateTime(), nullable=True),
        sa.Column("selinux_status", sa.String(length=50), nullable=True),
        sa.Column("apparmor_status", sa.String(length=50), nullable=True),
        sa.Column("ufw_active", sa.Boolean(), nullable=True),
        sa.Column("iptables_rule_count", sa.Integer(), nullable=True),
        sa.Column("ssh_root_login_enabled", sa.Boolean(), nullable=True),
        sa.Column("ssh_password_auth_enabled", sa.Boolean(), nullable=True),
        sa.Column("raw_details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("collected_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id"),
    )

    # New table: device_ports
    op.create_table(
        "device_ports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=True),
        sa.Column("port_number", sa.Integer(), nullable=False),
        sa.Column("protocol", sa.String(length=10), nullable=False),
        sa.Column("service_name", sa.String(length=100), nullable=True),
        sa.Column("product", sa.String(length=255), nullable=True),
        sa.Column("version", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_id"], ["network_scans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_device_ports_device_port", "device_ports", ["device_id", "port_number", "protocol"]
    )


def downgrade() -> None:
    op.drop_index("idx_device_ports_device_port", table_name="device_ports")
    op.drop_table("device_ports")

    op.drop_table("device_security")

    op.drop_index(op.f("ix_device_processes_name"), table_name="device_processes")
    op.drop_index("idx_device_processes_device", table_name="device_processes")
    op.drop_table("device_processes")

    op.drop_index("idx_device_partitions_device", table_name="device_partitions")
    op.drop_table("device_partitions")

    op.drop_column("device_network_interfaces", "interface_type")
    op.drop_column("device_network_interfaces", "duplex")
    op.drop_column("device_network_interfaces", "speed_mbps")

    op.drop_column("device_storage", "health_status")
    op.drop_column("device_storage", "media_type")
    op.drop_column("device_storage", "interface_type")

    op.drop_column("device_memory", "configured_speed_mhz")

    op.drop_column("device_processors", "socket_designation")
    op.drop_column("device_processors", "max_speed_mhz")

    op.drop_column("devices", "identification_method")
    op.drop_column("devices", "identification_confidence")
    op.drop_column("devices", "scan_status")
