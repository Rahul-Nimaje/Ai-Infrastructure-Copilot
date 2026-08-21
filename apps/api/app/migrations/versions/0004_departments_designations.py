"""departments_designations

Revision ID: 0004
Revises: e0c3996d06bd
Create Date: 2026-07-14

"""
import uuid
from datetime import datetime
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "e0c3996d06bd"


branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create departments table
    op.create_table(
        "departments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_departments_org_name",
        "departments",
        ["organization_id", "name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # 2. Create designations table
    op.create_table(
        "designations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_designations_dept_name",
        "designations",
        ["department_id", "name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # 3. Add foreign key columns to users table
    op.add_column("users", sa.Column("department_id", sa.Uuid(), nullable=True))
    op.add_column("users", sa.Column("designation_id", sa.Uuid(), nullable=True))

    op.create_foreign_key(
        "users_department_id_fkey",
        "users",
        "departments",
        ["department_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "users_designation_id_fkey",
        "users",
        "designations",
        ["designation_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 4. Seed default Departments & Designations for Acme Corp
    conn = op.get_bind()
    org_row = conn.execute(sa.text("SELECT id FROM organizations WHERE slug = 'acme-corp'")).fetchone()
    if org_row is None:
        return
    org_id = org_row[0]

    now = datetime.utcnow()

    # Seed Departments
    departments_to_seed = [
        {"name": "IT Infrastructure", "desc": "Information Technology and Systems Management"},
        {"name": "Human Resources", "desc": "Personnel, Recruitment, and Employee Relations"},
        {"name": "Sales", "desc": "Customer Acquisition and Account Management"},
    ]

    dept_ids = {}
    for d in departments_to_seed:
        d_id = uuid.uuid4()
        conn.execute(
            sa.text(
                "INSERT INTO departments (id, organization_id, name, description, status, created_at, updated_at) "
                "VALUES (:id, :org_id, :name, :desc, 'active', :now, :now)"
            ),
            {"id": d_id, "org_id": org_id, "name": d["name"], "desc": d["desc"], "now": now},
        )
        dept_ids[d["name"]] = d_id

    # Seed Designations under IT Infrastructure
    it_designations = [
        "Super Administrator",
        "Software Engineer",
        "Senior Software Engineer",
        "System Administrator",
    ]
    designation_ids = {}
    for name in it_designations:
        des_id = uuid.uuid4()
        conn.execute(
            sa.text(
                "INSERT INTO designations (id, organization_id, department_id, name, description, status, created_at, updated_at) "
                "VALUES (:id, :org_id, :dept_id, :name, :desc, 'active', :now, :now)"
            ),
            {
                "id": des_id,
                "org_id": org_id,
                "dept_id": dept_ids["IT Infrastructure"],
                "name": name,
                "desc": f"{name} in IT",
                "now": now,
            },
        )
        designation_ids[name] = des_id

    # Seed Designations under HR
    hr_designations = ["HR Executive", "HR Manager"]
    for name in hr_designations:
        des_id = uuid.uuid4()
        conn.execute(
            sa.text(
                "INSERT INTO designations (id, organization_id, department_id, name, description, status, created_at, updated_at) "
                "VALUES (:id, :org_id, :dept_id, :name, :desc, 'active', :now, :now)"
            ),
            {
                "id": des_id,
                "org_id": org_id,
                "dept_id": dept_ids["Human Resources"],
                "name": name,
                "desc": f"{name} in HR",
                "now": now,
            },
        )

    # Seed Designations under Sales
    sales_designations = ["Sales Executive", "Sales Manager"]
    for name in sales_designations:
        des_id = uuid.uuid4()
        conn.execute(
            sa.text(
                "INSERT INTO designations (id, organization_id, department_id, name, description, status, created_at, updated_at) "
                "VALUES (:id, :org_id, :dept_id, :name, :desc, 'active', :now, :now)"
            ),
            {
                "id": des_id,
                "org_id": org_id,
                "dept_id": dept_ids["Sales"],
                "name": name,
                "desc": f"{name} in Sales",
                "now": now,
            },
        )

    # 5. Link Admin User to "IT Infrastructure" Department and "Super Administrator" Designation
    admin_user = conn.execute(sa.text("SELECT id FROM users WHERE email = 'admin@acmecorp.io'")).fetchone()
    if admin_user:
        admin_id = admin_user[0]
        conn.execute(
            sa.text(
                "UPDATE users SET department_id = :dept_id, designation_id = :des_id "
                "WHERE id = :admin_id"
            ),
            {
                "dept_id": dept_ids["IT Infrastructure"],
                "des_id": designation_ids["Super Administrator"],
                "admin_id": admin_id,
            },
        )


def downgrade() -> None:
    # Remove foreign keys
    op.drop_constraint("users_designation_id_fkey", "users", type_="foreignkey")
    op.drop_constraint("users_department_id_fkey", "users", type_="foreignkey")

    # Remove columns
    op.drop_column("users", "designation_id")
    op.drop_column("users", "department_id")

    # Drop tables
    op.drop_table("designations")
    op.drop_table("departments")
