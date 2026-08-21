"""add_user_details_and_device_models

Revision ID: e0c3996d06bd
Revises: 0003
Create Date: 2026-07-14 12:05:19.800315

"""
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e0c3996d06bd'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create devices
    op.create_table('devices',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('device_type', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('mac_address', sa.String(length=17), nullable=True),
    sa.Column('vendor', sa.String(length=100), nullable=True),
    sa.Column('model', sa.String(length=100), nullable=True),
    sa.Column('operating_system', sa.String(length=100), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(), nullable=True),
    sa.Column('response_time', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('open_ports', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # 2. Create device scans
    op.create_table('device_scans',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('scan_type', sa.String(length=50), nullable=False),
    sa.Column('target_range', sa.String(length=255), nullable=True),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('devices_found', sa.Integer(), nullable=False),
    sa.Column('created_by_id', sa.Uuid(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # 3. Create device history
    op.create_table('device_history',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('device_id', sa.Uuid(), nullable=False),
    sa.Column('event_type', sa.String(length=50), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('before_state', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('after_state', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # 4. Add new columns to users table
    op.add_column('users', sa.Column('username', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('employee_id', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('phone_number', sa.String(length=30), nullable=True))
    op.add_column('users', sa.Column('department', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('designation', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('profile_picture', sa.String(length=500), nullable=True))
    op.add_column('users', sa.Column('created_by_id', sa.Uuid(), nullable=True))
    op.add_column('users', sa.Column('updated_by_id', sa.Uuid(), nullable=True))
    
    # Use explicit names for constraints so we can drop them easily in downgrade
    op.create_foreign_key('users_created_by_id_fkey', 'users', 'users', ['created_by_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('users_updated_by_id_fkey', 'users', 'users', ['updated_by_id'], ['id'], ondelete='SET NULL')

    # 5. Add custom indexes
    op.create_index('idx_users_org_username', 'users', ['organization_id', sa.text('lower(username)')], unique=True, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_devices_org_type', 'devices', ['organization_id', 'device_type'], postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_devices_org_mac', 'devices', ['organization_id', 'mac_address'], postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_devices_org_ip', 'devices', ['organization_id', 'ip_address'], postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_device_scans_org', 'device_scans', ['organization_id', 'status'])
    op.create_index('idx_device_history_device', 'device_history', ['device_id'])

    # 6. Seed permissions and default roles
    conn = op.get_bind()

    # Identify existing Acme Corp organization
    org_row = conn.execute(sa.text("SELECT id FROM organizations WHERE slug = 'acme-corp'")).fetchone()
    if org_row is None:
        return
    org_id = org_row[0]

    # Map of all permissions to be registered
    new_permissions = [
        ("users.read", "User Management"),
        ("users.create", "User Management"),
        ("users.update", "User Management"),
        ("users.delete", "User Management"),
        ("users.import", "User Management"),
        ("users.export", "User Management"),
        ("roles.read", "RBAC"),
        ("roles.create", "RBAC"),
        ("roles.update", "RBAC"),
        ("roles.delete", "RBAC"),
        ("roles.assign", "RBAC"),
        ("discovery.read", "Network Discovery"),
        ("discovery.scan", "Network Discovery"),
    ]

    permission_ids = {}
    for code, module in new_permissions:
        row = conn.execute(sa.text("SELECT id FROM permissions WHERE code = :code"), {"code": code}).fetchone()
        if row is not None:
            permission_ids[code] = row[0]
            continue
        perm_id = uuid.uuid4()
        conn.execute(
            sa.text("INSERT INTO permissions (id, code, module) VALUES (:id, :code, :module)"),
            {"id": perm_id, "code": code, "module": module}
        )
        permission_ids[code] = perm_id

    # Fetch all registered permissions (both phase 1 and the ones we just added)
    all_perms_q = conn.execute(sa.text("SELECT code, id FROM permissions")).fetchall()
    all_permissions = {row[0]: row[1] for row in all_perms_q}

    # Define standard enterprise roles
    default_roles = [
        {"name": "Super Admin", "description": "Full access to all tenant modules and configurations"},
        {"name": "Organization Admin", "description": "Manage users, custom roles, permissions and general organization settings"},
        {"name": "Infrastructure Admin", "description": "Full control over infrastructure assets, configurations, and tasks"},
        {"name": "Windows Administrator", "description": "Manage Windows hosts, directory services, and scripts"},
        {"name": "Linux Administrator", "description": "Manage Linux hosts, SSH scripts, and automation tasks"},
        {"name": "Network Administrator", "description": "Manage network discovery, switches, firewalls, and routing"},
        {"name": "Security Administrator", "description": "Manage RBAC assignments, credentials vault, audit logs, and MFA"},
        {"name": "Helpdesk Engineer", "description": "Read-only access to infrastructure; perform basic diagnostics"},
        {"name": "Read Only User", "description": "Read-only access to dashboards and inventory lists"}
    ]

    # Role to permissions mapping
    role_perms_mapping = {
        "Super Admin": list(all_permissions.keys()),
        "Organization Admin": [
            "users.read", "users.create", "users.update", "users.delete", "users.import", "users.export",
            "roles.read", "roles.create", "roles.update", "roles.delete", "roles.assign",
            "ai_chat.use"
        ],
        "Infrastructure Admin": [
            "servers.read", "servers.write", "discovery.read", "discovery.scan", 
            "tasks.read", "tasks.approve", "ai_chat.use"
        ],
        "Windows Administrator": [
            "servers.read", "servers.write", "events.read", "scripts.read", 
            "scripts.write", "scripts.execute", "tasks.read", "tasks.approve", "ai_chat.use"
        ],
        "Linux Administrator": [
            "servers.read", "servers.write", "scripts.read", "scripts.write", 
            "scripts.execute", "tasks.read", "tasks.approve", "ai_chat.use"
        ],
        "Network Administrator": [
            "discovery.read", "discovery.scan", "servers.read"
        ],
        "Security Administrator": [
            "roles.read", "roles.create", "roles.update", "roles.delete", "roles.assign",
            "users.read", "events.read"
        ],
        "Helpdesk Engineer": [
            "users.read", "servers.read", "discovery.read", "events.read"
        ],
        "Read Only User": [
            "users.read", "servers.read", "discovery.read", "events.read", "roles.read"
        ]
    }

    # Insert default roles & their permissions
    for role_info in default_roles:
        role_row = conn.execute(
            sa.text("SELECT id FROM roles WHERE organization_id = :org_id AND name = :name"),
            {"org_id": org_id, "name": role_info["name"]}
        ).fetchone()
        
        if role_row is not None:
            r_id = role_row[0]
            # Update description if system role
            conn.execute(
                sa.text("UPDATE roles SET description = :desc WHERE id = :id"),
                {"desc": role_info["description"], "id": r_id}
            )
        else:
            r_id = uuid.uuid4()
            conn.execute(
                sa.text(
                    "INSERT INTO roles (id, organization_id, name, description, is_system_role) "
                    "VALUES (:id, :org_id, :name, :desc, true)"
                ),
                {"id": r_id, "org_id": org_id, "name": role_info["name"], "desc": role_info["description"]}
            )

        # Clear existing role-permission linkages to refresh them clean
        conn.execute(sa.text("DELETE FROM role_permissions WHERE role_id = :role_id"), {"role_id": r_id})
        
        # Link permissions
        mapped_perm_codes = role_perms_mapping.get(role_info["name"], [])
        for code in mapped_perm_codes:
            p_id = all_permissions.get(code)
            if p_id:
                conn.execute(
                    sa.text("INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :perm_id)"),
                    {"role_id": r_id, "perm_id": p_id}
                )

    # 7. Update default Admin User to have username, designation, and map to Super Admin
    conn.execute(
        sa.text(
            "UPDATE users SET username = 'admin', employee_id = 'EMP-001', "
            "department = 'IT Infrastructure', designation = 'Super Administrator', "
            "status = 'active' WHERE email = 'admin@acmecorp.io'"
        )
    )

    # Link default user to 'Super Admin' role as well
    sa_role_row = conn.execute(
        sa.text("SELECT id FROM roles WHERE organization_id = :org_id AND name = 'Super Admin'"),
        {"org_id": org_id}
    ).fetchone()
    admin_user_row = conn.execute(sa.text("SELECT id FROM users WHERE email = 'admin@acmecorp.io'")).fetchone()
    
    if sa_role_row and admin_user_row:
        sa_role_id = sa_role_row[0]
        admin_user_id = admin_user_row[0]
        # Check link
        link_check = conn.execute(
            sa.text("SELECT 1 FROM user_roles WHERE user_id = :u_id AND role_id = :r_id"),
            {"u_id": admin_user_id, "r_id": sa_role_id}
        ).fetchone()
        if not link_check:
            conn.execute(
                sa.text("INSERT INTO user_roles (user_id, role_id) VALUES (:u_id, :r_id)"),
                {"u_id": admin_user_id, "r_id": sa_role_id}
            )


def downgrade() -> None:
    # Drop custom indexes
    op.drop_index('idx_device_history_device', table_name='device_history')
    op.drop_index('idx_device_scans_org', table_name='device_scans')
    op.drop_index('idx_devices_org_ip', table_name='devices')
    op.drop_index('idx_devices_org_mac', table_name='devices')
    op.drop_index('idx_devices_org_type', table_name='devices')
    op.drop_index('idx_users_org_username', table_name='users')

    # Drop FK constraints on users
    op.drop_constraint('users_created_by_id_fkey', 'users', type_='foreignkey')
    op.drop_constraint('users_updated_by_id_fkey', 'users', type_='foreignkey')

    # Drop columns on users
    op.drop_column('users', 'updated_by_id')
    op.drop_column('users', 'created_by_id')
    op.drop_column('users', 'profile_picture')
    op.drop_column('users', 'designation')
    op.drop_column('users', 'department')
    op.drop_column('users', 'phone_number')
    op.drop_column('users', 'employee_id')
    op.drop_column('users', 'username')

    # Drop tables
    op.drop_table('device_scans')
    op.drop_table('device_history')
    op.drop_table('devices')
