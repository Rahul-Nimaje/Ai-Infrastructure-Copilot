"""Initial Phase 1 schema — subset of docs/04-database-design.md Section 5/6.

Revision ID: 0001
Revises:
Create Date: 2026-07-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    # pgvector enabled now (even though no vector columns yet) so Phase 4's
    # Memory Agent / RAG work is a column addition, not an extension migration.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "organizations",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("plan_tier", sa.String(50), nullable=False, server_default="starter"),
        sa.Column("status", sa.String(20), nullable=False, server_default="trial"),
        sa.Column("settings", pg.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "users",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="invited"),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("mfa_secret_ref", sa.String(255), nullable=True),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "idx_users_org_email", "users", ["organization_id", "email"], unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "user_refresh_tokens",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("family_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_refresh_tokens_family", "user_refresh_tokens", ["family_id"])

    op.create_table(
        "roles",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system_role", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "idx_roles_org_name", "roles", ["organization_id", "name"], unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "permissions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(150), nullable=False, unique=True),
        sa.Column("module", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", pg.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column(
            "permission_id", pg.UUID(as_uuid=True), sa.ForeignKey("permissions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", pg.UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("granted_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("granted_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )

    op.create_table(
        "credentials",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("credential_type", sa.String(30), nullable=False),
        sa.Column("vault_engine", sa.String(30), nullable=False, server_default="local_encrypted"),
        sa.Column("vault_path", sa.String(500), nullable=False),
        sa.Column("vault_key_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("encrypted_metadata", pg.JSONB, nullable=False, server_default="{}"),
        sa.Column("rotation_policy", sa.String(30), nullable=True, server_default="manual"),
        sa.Column("last_rotated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_credentials_org", "credentials", ["organization_id"], postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("idx_credentials_vault_path", "credentials", ["vault_path"], unique=True)

    op.create_table(
        "servers",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("os_type", sa.String(20), nullable=False),
        sa.Column("os_version", sa.String(100), nullable=True),
        sa.Column("environment", sa.String(30), nullable=False, server_default="production"),
        sa.Column("credential_id", pg.UUID(as_uuid=True), sa.ForeignKey("credentials.id"), nullable=True),
        sa.Column("health_status", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("cpu_usage_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("memory_usage_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("disk_usage_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("open_alerts_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("tags", pg.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "idx_servers_org_hostname", "servers", ["organization_id", "hostname"], unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("idx_servers_org_health", "servers", ["organization_id", "health_status"])

    op.create_table(
        "infrastructure_inventory",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("asset_type", sa.String(30), nullable=False),
        sa.Column("asset_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("discovered_via", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("attributes", pg.JSONB, nullable=False, server_default="{}"),
        sa.Column("last_scanned_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "idx_inventory_org_asset", "infrastructure_inventory", ["organization_id", "asset_type", "asset_id"],
        unique=True,
    )

    op.create_table(
        "scripts",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("language", sa.String(20), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("is_ai_generated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_approved_template", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_scripts_org_lang", "scripts", ["organization_id", "language"])

    op.create_table(
        "script_versions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("script_id", pg.UUID(as_uuid=True), sa.ForeignKey("scripts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("changed_by_user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("script_id", "version"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending_approval"),
        sa.Column("target_server_id", pg.UUID(as_uuid=True), sa.ForeignKey("servers.id"), nullable=True),
        sa.Column("script_id", pg.UUID(as_uuid=True), sa.ForeignKey("scripts.id"), nullable=True),
        sa.Column("execution_method", sa.String(10), nullable=True),
        sa.Column("payload", pg.JSONB, nullable=False, server_default="{}"),
        sa.Column("result", pg.JSONB, nullable=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("requested_by_user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("requested_by_ai", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("approved_by_user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("rejected_reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_tasks_org_status", "tasks", ["organization_id", "status", "created_at"])
    op.create_index("idx_tasks_org_target_server", "tasks", ["organization_id", "target_server_id"])

    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("server_id", pg.UUID(as_uuid=True), sa.ForeignKey("servers.id"), nullable=True),
        sa.Column("event_source", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("raw_payload", pg.JSONB, nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_events_org_server_time", "events", ["organization_id", "server_id", "occurred_at"])

    op.create_table(
        "event_log_entries",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("server_id", pg.UUID(as_uuid=True), sa.ForeignKey("servers.id"), nullable=False),
        sa.Column("log_channel", sa.String(50), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("source_provider", sa.String(150), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("raw_xml", sa.Text(), nullable=True),
        sa.Column("ai_classified_category", sa.String(100), nullable=True),
        sa.Column("correlation_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_eventlog_org_server_time", "event_log_entries", ["organization_id", "server_id", "occurred_at"])
    op.create_index("idx_eventlog_org_level", "event_log_entries", ["organization_id", "level", "occurred_at"])

    op.create_table(
        "ai_conversations",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("module_context", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("last_message_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_ai_conversations_org_user", "ai_conversations", ["organization_id", "user_id", "last_message_at"])

    op.create_table(
        "ai_messages",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id", pg.UUID(as_uuid=True),
            sa.ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_calls", pg.JSONB, nullable=True),
        sa.Column("referenced_task_id", pg.UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_ai_messages_conversation_time", "ai_messages", ["conversation_id", "created_at"])

    op.create_table(
        "audit_logs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", pg.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("actor_user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(150), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("before_state", pg.JSONB, nullable=True),
        sa.Column("after_state", pg.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_audit_logs_org_time", "audit_logs", ["organization_id", "created_at"])
    op.create_index("idx_audit_logs_org_resource", "audit_logs", ["organization_id", "resource_type", "resource_id"])

    # Row-Level Security — docs/04-database-design.md Section 2. Applied to every
    # tenant-scoped table as a defense-in-depth backstop behind the application
    # layer's mandatory organization_id filtering.
    tenant_scoped_tables = [
        "users", "roles", "credentials", "servers", "infrastructure_inventory",
        "scripts", "tasks", "events", "event_log_entries", "ai_conversations",
        "audit_logs",
    ]
    for table in tenant_scoped_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
                USING (organization_id = current_setting('app.current_org_id', true)::uuid)
            """
        )
    # The REVOKE UPDATE, DELETE ON audit_logs FROM app_role grant in
    # docs/04-database-design.md Section 5.18 requires a dedicated non-superuser
    # DB role; deferred until the deployment pipeline provisions one (Phase 2+).
    #
    # KNOWN MVP GAP: Postgres RLS does not apply to a table's owning role by
    # default (the migration-running / app DB user here IS the owner), so
    # these policies are inert until a separate least-privilege `app_role`
    # is created and `FORCE ROW LEVEL SECURITY` is set — tracked for the
    # Phase 2 credential-vault hardening work. Application-layer org_id
    # filtering (every repository call) is the real enforcement for now.


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("ai_messages")
    op.drop_table("ai_conversations")
    op.drop_table("event_log_entries")
    op.drop_table("events")
    op.drop_table("tasks")
    op.drop_table("script_versions")
    op.drop_table("scripts")
    op.drop_table("infrastructure_inventory")
    op.drop_table("servers")
    op.drop_table("credentials")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("user_refresh_tokens")
    op.drop_table("users")
    op.drop_table("organizations")
