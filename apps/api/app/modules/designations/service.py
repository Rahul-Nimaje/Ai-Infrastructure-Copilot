import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.models.department_designation import Department, Designation
from app.modules.designations.schemas import DesignationCreate, DesignationUpdate


async def list_designations(
    db: AsyncSession,
    organization_id: uuid.UUID,
    department_id: uuid.UUID | None = None,
    page: int = 1,
    size: int = 20,
    search: str | None = None,
    status_filter: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    offset = (page - 1) * size

    # Base query joining departments to get department_name
    stmt = (
        select(Designation, Department.name.label("department_name"))
        .join(Department, Department.id == Designation.department_id)
        .where(
            and_(
                Designation.organization_id == organization_id,
                Designation.deleted_at.is_(None),
                Department.deleted_at.is_(None),
            )
        )
    )

    if department_id:
        stmt = stmt.where(Designation.department_id == department_id)

    if search:
        stmt = stmt.where(Designation.name.ilike(f"%{search}%"))

    if status_filter:
        stmt = stmt.where(Designation.status == status_filter)

    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # Get records ordered by designation name
    stmt = stmt.order_by(Designation.name.asc()).offset(offset).limit(size)
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for row in rows:
        designation = row.Designation
        dept_name = row.department_name
        # Add dynamic attribute for pydantic serialization
        designation.department_name = dept_name
        items.append(designation)

    return items, total


async def list_active_designations(
    db: AsyncSession,
    organization_id: uuid.UUID,
    department_id: uuid.UUID | None = None,
) -> list[Designation]:
    stmt = (
        select(Designation, Department.name.label("department_name"))
        .join(Department, Department.id == Designation.department_id)
        .where(
            and_(
                Designation.organization_id == organization_id,
                Designation.status == "active",
                Designation.deleted_at.is_(None),
                Department.status == "active",
                Department.deleted_at.is_(None),
            )
        )
    )

    if department_id:
        stmt = stmt.where(Designation.department_id == department_id)

    stmt = stmt.order_by(Designation.name.asc())
    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for row in rows:
        designation = row.Designation
        designation.department_name = row.department_name
        items.append(designation)

    return items


async def create_designation(
    db: AsyncSession,
    organization_id: uuid.UUID,
    payload: DesignationCreate,
    actor_id: uuid.UUID,
) -> Designation:
    # 1. Verify Department exists, belongs to organization, and is active
    dept_stmt = select(Department).where(
        and_(
            Department.organization_id == organization_id,
            Department.id == payload.department_id,
            Department.deleted_at.is_(None),
        )
    )
    dept_result = await db.execute(dept_stmt)
    dept = dept_result.scalar_one_or_none()
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found.",
        )
    if dept.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign designation to an inactive department.",
        )

    # 2. Check for duplicate designation name within the same department
    dup_stmt = select(Designation).where(
        and_(
            Designation.department_id == payload.department_id,
            func.lower(Designation.name) == func.lower(payload.name),
            Designation.deleted_at.is_(None),
        )
    )
    dup_result = await db.execute(dup_stmt)
    if dup_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Designation '{payload.name}' already exists in this department.",
        )

    des = Designation(
        organization_id=organization_id,
        department_id=payload.department_id,
        name=payload.name,
        description=payload.description,
        status=payload.status,
    )
    db.add(des)
    await db.flush()

    # Add dynamic attribute for pydantic serialization
    des.department_name = dept.name

    # Write audit log
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_type="user",
        actor_user_id=actor_id,
        action="designation.create",
        resource_type="designations",
        resource_id=des.id,
        after_state={"name": des.name, "department_id": des.department_id, "status": des.status},
    )

    await db.commit()
    return des


async def update_designation(
    db: AsyncSession,
    organization_id: uuid.UUID,
    designation_id: uuid.UUID,
    payload: DesignationUpdate,
    actor_id: uuid.UUID,
) -> Designation:
    # Fetch designation
    stmt = (
        select(Designation, Department.name.label("department_name"))
        .join(Department, Department.id == Designation.department_id)
        .where(
            and_(
                Designation.organization_id == organization_id,
                Designation.id == designation_id,
                Designation.deleted_at.is_(None),
            )
        )
    )
    result = await db.execute(stmt)
    row = result.fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Designation not found.",
        )
    des = row.Designation
    dept_name = row.department_name

    before_state = {
        "name": des.name,
        "department_id": des.department_id,
        "status": des.status,
    }

    # If updating department_id
    target_dept_id = payload.department_id or des.department_id
    if payload.department_id and payload.department_id != des.department_id:
        dept_stmt = select(Department).where(
            and_(
                Department.organization_id == organization_id,
                Department.id == payload.department_id,
                Department.deleted_at.is_(None),
            )
        )
        dept_result = await db.execute(dept_stmt)
        dept = dept_result.scalar_one_or_none()
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Department not found.",
            )
        if dept.status != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign designation to an inactive department.",
            )
        des.department_id = payload.department_id
        dept_name = dept.name

    # If name is updated (or department changed), check uniqueness
    target_name = payload.name or des.name
    if (payload.name and payload.name.lower() != des.name.lower()) or (
        payload.department_id and payload.department_id != des.department_id
    ):
        dup_stmt = select(Designation).where(
            and_(
                Designation.department_id == target_dept_id,
                func.lower(Designation.name) == func.lower(target_name),
                Designation.deleted_at.is_(None),
                Designation.id != designation_id,
            )
        )
        dup_result = await db.execute(dup_stmt)
        if dup_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Designation '{target_name}' already exists in the selected department.",
            )
        if payload.name:
            des.name = payload.name

    if payload.description is not None:
        des.description = payload.description

    if payload.status is not None:
        des.status = payload.status

    des.updated_at = datetime.utcnow()
    await db.flush()

    des.department_name = dept_name

    after_state = {
        "name": des.name,
        "department_id": des.department_id,
        "status": des.status,
    }

    # Write audit log
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_type="user",
        actor_user_id=actor_id,
        action="designation.update",
        resource_type="designations",
        resource_id=des.id,
        before_state=before_state,
        after_state=after_state,
    )

    await db.commit()
    return des


async def delete_designation(
    db: AsyncSession,
    organization_id: uuid.UUID,
    designation_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> None:
    # Fetch designation
    stmt = select(Designation).where(
        and_(
            Designation.organization_id == organization_id,
            Designation.id == designation_id,
            Designation.deleted_at.is_(None),
        )
    )
    result = await db.execute(stmt)
    des = result.scalar_one_or_none()
    if not des:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Designation not found.",
        )

    # Soft delete
    des.deleted_at = datetime.utcnow()
    des.status = "inactive"
    await db.flush()

    # Write audit log
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_type="user",
        actor_user_id=actor_id,
        action="designation.delete",
        resource_type="designations",
        resource_id=designation_id,
    )

    await db.commit()
