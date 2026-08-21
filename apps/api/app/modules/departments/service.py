import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.models.department_designation import Department
from app.modules.departments.schemas import DepartmentCreate, DepartmentUpdate


async def list_departments(
    db: AsyncSession,
    organization_id: uuid.UUID,
    page: int = 1,
    size: int = 20,
    search: str | None = None,
    status_filter: str | None = None,
) -> tuple[list[Department], int]:
    offset = (page - 1) * size

    # Base query for non-deleted departments
    stmt = select(Department).where(
        and_(Department.organization_id == organization_id, Department.deleted_at.is_(None))
    )

    if search:
        stmt = stmt.where(Department.name.ilike(f"%{search}%"))

    if status_filter:
        stmt = stmt.where(Department.status == status_filter)

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # Get records ordered by name
    stmt = stmt.order_by(Department.name.asc()).offset(offset).limit(size)
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    return items, total


async def list_active_departments(db: AsyncSession, organization_id: uuid.UUID) -> list[Department]:
    stmt = select(Department).where(
        and_(
            Department.organization_id == organization_id,
            Department.status == "active",
            Department.deleted_at.is_(None),
        )
    ).order_by(Department.name.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_department(
    db: AsyncSession,
    organization_id: uuid.UUID,
    payload: DepartmentCreate,
    actor_id: uuid.UUID,
) -> Department:
    # Check for duplicates (case insensitive)
    dup_stmt = select(Department).where(
        and_(
            Department.organization_id == organization_id,
            func.lower(Department.name) == func.lower(payload.name),
            Department.deleted_at.is_(None),
        )
    )
    dup_result = await db.execute(dup_stmt)
    if dup_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Department with name '{payload.name}' already exists.",
        )

    dept = Department(
        organization_id=organization_id,
        name=payload.name,
        description=payload.description,
        status=payload.status,
    )
    db.add(dept)
    await db.flush()

    # Write audit log
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_type="user",
        actor_user_id=actor_id,
        action="department.create",
        resource_type="departments",
        resource_id=dept.id,
        after_state={"name": dept.name, "status": dept.status},
    )

    await db.commit()
    return dept


async def update_department(
    db: AsyncSession,
    organization_id: uuid.UUID,
    department_id: uuid.UUID,
    payload: DepartmentUpdate,
    actor_id: uuid.UUID,
) -> Department:
    # Fetch department
    stmt = select(Department).where(
        and_(
            Department.organization_id == organization_id,
            Department.id == department_id,
            Department.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found.",
        )

    before_state = {"name": dept.name, "status": dept.status}

    # If updating name, check for duplicates
    if payload.name and payload.name.lower() != dept.name.lower():
        dup_stmt = select(Department).where(
            and_(
                Department.organization_id == organization_id,
                func.lower(Department.name) == func.lower(payload.name),
                Department.deleted_at.is_(None),
            )
        )
        dup_result = await db.execute(dup_stmt)
        if dup_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Department with name '{payload.name}' already exists.",
            )
        dept.name = payload.name

    if payload.description is not None:
        dept.description = payload.description

    if payload.status is not None:
        dept.status = payload.status

    dept.updated_at = datetime.utcnow()
    await db.flush()

    after_state = {"name": dept.name, "status": dept.status}

    # Write audit log
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_type="user",
        actor_user_id=actor_id,
        action="department.update",
        resource_type="departments",
        resource_id=dept.id,
        before_state=before_state,
        after_state=after_state,
    )

    await db.commit()
    return dept


async def delete_department(
    db: AsyncSession,
    organization_id: uuid.UUID,
    department_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> None:
    # Fetch department
    stmt = select(Department).where(
        and_(
            Department.organization_id == organization_id,
            Department.id == department_id,
            Department.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found.",
        )

    # Soft delete department
    dept.deleted_at = datetime.utcnow()
    dept.status = "inactive"  # Set to inactive as well
    await db.flush()

    # Write audit log
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_type="user",
        actor_user_id=actor_id,
        action="department.delete",
        resource_type="departments",
        resource_id=department_id,
    )

    await db.commit()
