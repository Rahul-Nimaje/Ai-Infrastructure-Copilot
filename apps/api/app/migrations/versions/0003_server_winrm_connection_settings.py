"""Add per-server WinRM connection settings (port, use_ssl).

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-13

"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("servers", sa.Column("winrm_port", sa.Integer(), nullable=False, server_default="5986"))
    op.add_column("servers", sa.Column("winrm_use_ssl", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("servers", "winrm_use_ssl")
    op.drop_column("servers", "winrm_port")
