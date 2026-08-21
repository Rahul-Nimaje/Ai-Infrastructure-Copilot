import csv
import io
from datetime import datetime
import uuid
from typing import Any
from fastapi import HTTPException, status
from sqlalchemy import select, func, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.core.audit import write_audit_log
from app.models.user import User
from app.models.rbac import Role, UserRole
from app.models.department_designation import Department, Designation
from app.modules.users.schemas import UserCreate, UserUpdate


async def list_users(
    db: AsyncSession,
    organization_id: uuid.UUID,
    *,
    page: int = 1,
    size: int = 20,
    search: str | None = None,
    status_filter: str | None = None,
    department: str | None = None,
    role_name: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> tuple[list[dict[str, Any]], int]:
    # Base query for active (non-soft-deleted) users in this organization
    query = select(User).where(and_(User.organization_id == organization_id, User.deleted_at.is_(None)))

    # Apply filters
    if search:
        search_lower = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(User.full_name).like(search_lower),
                func.lower(User.email).like(search_lower),
                func.lower(User.username).like(search_lower),
                func.lower(User.employee_id).like(search_lower),
            )
        )

    if status_filter:
        query = query.where(User.status == status_filter)

    if department:
        query = query.where(User.department == department)

    # Join role to filter if requested
    if role_name:
        query = query.join(UserRole, UserRole.user_id == User.id).join(Role, Role.id == UserRole.role_id).where(Role.name == role_name)

    # Total count query
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    col = getattr(User, sort_by, User.created_at)
    if sort_order.lower() == "asc":
        query = query.order_by(col.asc())
    else:
        query = query.order_by(col.desc())

    # Apply pagination
    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    users = result.scalars().all()

    # Load roles for each user
    users_with_roles = []
    for user in users:
        role_names = await _get_user_role_names(db, user.id)
        user_dict = {
            "id": user.id,
            "organization_id": user.organization_id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "status": user.status,
            "employee_id": user.employee_id,
            "phone_number": user.phone_number,
            "department": user.department,
            "designation": user.designation,
            "department_id": user.department_id,
            "designation_id": user.designation_id,
            "profile_picture": user.profile_picture,
            "mfa_enabled": user.mfa_enabled,
            "roles": role_names,
            "created_by_id": user.created_by_id,
            "updated_by_id": user.updated_by_id,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
        users_with_roles.append(user_dict)

    return users_with_roles, total


async def get_user_detail(db: AsyncSession, organization_id: uuid.UUID, user_id: uuid.UUID) -> dict[str, Any]:
    query = select(User).where(and_(User.organization_id == organization_id, User.id == user_id, User.deleted_at.is_(None)))
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    role_names = await _get_user_role_names(db, user.id)
    return {
        "id": user.id,
        "organization_id": user.organization_id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "status": user.status,
        "employee_id": user.employee_id,
        "phone_number": user.phone_number,
        "department": user.department,
        "designation": user.designation,
        "department_id": user.department_id,
        "designation_id": user.designation_id,
        "profile_picture": user.profile_picture,
        "mfa_enabled": user.mfa_enabled,
        "roles": role_names,
        "created_by_id": user.created_by_id,
        "updated_by_id": user.updated_by_id,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


async def create_user(
    db: AsyncSession,
    organization_id: uuid.UUID,
    payload: UserCreate,
    created_by_id: uuid.UUID
) -> dict[str, Any]:
    # Check email uniqueness within org
    email_check = await db.execute(
        select(User).where(
            and_(
                User.organization_id == organization_id,
                func.lower(User.email) == payload.email.lower(),
                User.deleted_at.is_(None)
            )
        )
    )
    if email_check.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists in this organization")

    # Check username uniqueness within org
    username_check = await db.execute(
        select(User).where(
            and_(
                User.organization_id == organization_id,
                func.lower(User.username) == payload.username.lower(),
                User.deleted_at.is_(None)
            )
        )
    )
    if username_check.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists in this organization")

    # 1. Fetch and validate department
    dept_stmt = select(Department).where(
        and_(
            Department.organization_id == organization_id,
            Department.id == payload.department_id,
            Department.deleted_at.is_(None)
        )
    )
    dept_result = await db.execute(dept_stmt)
    dept = dept_result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected department not found")
    if dept.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected department is inactive")

    # 2. Fetch and validate designation
    des_stmt = select(Designation).where(
        and_(
            Designation.organization_id == organization_id,
            Designation.id == payload.designation_id,
            Designation.deleted_at.is_(None)
        )
    )
    des_result = await db.execute(des_stmt)
    des = des_result.scalar_one_or_none()
    if not des:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected designation not found")
    if des.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected designation is inactive")
    if des.department_id != dept.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected designation does not belong to the selected department")

    # 3. Validate roles
    if not payload.roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one role is required")
    for rname in payload.roles:
        role_q = await db.execute(select(Role).where(and_(Role.organization_id == organization_id, Role.name == rname, Role.deleted_at.is_(None))))
        role = role_q.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Role '{rname}' does not exist or is inactive")

    # Create the user
    user = User(
        organization_id=organization_id,
        email=payload.email.lower(),
        username=payload.username.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        status=payload.status,
        employee_id=payload.employee_id,
        phone_number=payload.phone_number,
        department=dept.name,
        designation=des.name,
        department_id=dept.id,
        designation_id=des.id,
        profile_picture=payload.profile_picture,
        created_by_id=created_by_id,
        updated_by_id=created_by_id
    )
    db.add(user)
    await db.flush()

    # Assign roles
    for rname in payload.roles:
        role_q = await db.execute(select(Role).where(and_(Role.organization_id == organization_id, Role.name == rname)))
        role = role_q.scalar_one_or_none()
        if role:
            db.add(UserRole(user_id=user.id, role_id=role.id, granted_by=created_by_id))
    
    await db.flush()

    # Write audit log
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_type="user",
        actor_user_id=created_by_id,
        action="user.create",
        resource_type="users",
        resource_id=user.id,
        after_state={"email": user.email, "username": user.username, "roles": payload.roles}
    )

    await db.commit()
    return await get_user_detail(db, organization_id, user.id)


async def update_user(
    db: AsyncSession,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: UserUpdate,
    updated_by_id: uuid.UUID
) -> dict[str, Any]:
    # Fetch user
    user_q = await db.execute(select(User).where(and_(User.organization_id == organization_id, User.id == user_id, User.deleted_at.is_(None))))
    user = user_q.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    before_state = {
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "status": user.status,
        "employee_id": user.employee_id,
        "phone_number": user.phone_number,
        "department": user.department,
        "designation": user.designation,
        "profile_picture": user.profile_picture,
    }

    # Validate uniqueness if email updated
    if payload.email and payload.email.lower() != user.email:
        email_check = await db.execute(
            select(User).where(
                and_(
                    User.organization_id == organization_id,
                    func.lower(User.email) == payload.email.lower(),
                    User.id != user_id,
                    User.deleted_at.is_(None)
                )
            )
        )
        if email_check.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists in this organization")
        user.email = payload.email.lower()

    # Validate uniqueness if username updated
    if payload.username and payload.username.lower() != user.username:
        username_check = await db.execute(
            select(User).where(
                and_(
                    User.organization_id == organization_id,
                    func.lower(User.username) == payload.username.lower(),
                    User.id != user_id,
                    User.deleted_at.is_(None)
                )
            )
        )
        if username_check.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists in this organization")
        user.username = payload.username.lower()

    # Apply updates
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.employee_id is not None:
        user.employee_id = payload.employee_id
    if payload.phone_number is not None:
        user.phone_number = payload.phone_number

    # Validate and apply department / designation changes
    dept_id = payload.department_id
    des_id = payload.designation_id

    if dept_id is not None or des_id is not None:
        final_dept_id = dept_id if dept_id is not None else user.department_id
        final_des_id = des_id if des_id is not None else user.designation_id

        if final_dept_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department is required")
        if final_des_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Designation is required")

        # Validate department
        dept_stmt = select(Department).where(
            and_(
                Department.organization_id == organization_id,
                Department.id == final_dept_id,
                Department.deleted_at.is_(None)
            )
        )
        dept_result = await db.execute(dept_stmt)
        dept = dept_result.scalar_one_or_none()
        if not dept:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected department not found")
        if dept_id is not None and dept.status != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected department is inactive")

        # Validate designation
        des_stmt = select(Designation).where(
            and_(
                Designation.organization_id == organization_id,
                Designation.id == final_des_id,
                Designation.deleted_at.is_(None)
            )
        )
        des_result = await db.execute(des_stmt)
        des = des_result.scalar_one_or_none()
        if not des:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected designation not found")
        if des_id is not None and des.status != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected designation is inactive")

        if des.department_id != dept.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selected designation does not belong to the selected department")

        user.department_id = final_dept_id
        user.department = dept.name
        user.designation_id = final_des_id
        user.designation = des.name

    if payload.profile_picture is not None:
        user.profile_picture = payload.profile_picture
    if payload.status is not None:
        user.status = payload.status

    user.updated_by_id = updated_by_id
    user.updated_at = datetime.utcnow()

    # Update roles if specified
    if payload.roles is not None:
        if not payload.roles:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one role is required")
        for rname in payload.roles:
            role_q = await db.execute(select(Role).where(and_(Role.organization_id == organization_id, Role.name == rname, Role.deleted_at.is_(None))))
            role = role_q.scalar_one_or_none()
            if not role:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Role '{rname}' does not exist or is inactive")

        # Remove old role associations
        await db.execute(delete(UserRole).where(UserRole.user_id == user.id))
        await db.flush()
        # Add new ones
        for rname in payload.roles:
            role_q = await db.execute(select(Role).where(and_(Role.organization_id == organization_id, Role.name == rname)))
            role = role_q.scalar_one_or_none()
            if role:
                db.add(UserRole(user_id=user.id, role_id=role.id, granted_by=updated_by_id))

    await db.flush()

    after_state = {
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "status": user.status,
        "employee_id": user.employee_id,
        "phone_number": user.phone_number,
        "department": user.department,
        "designation": user.designation,
        "profile_picture": user.profile_picture,
        "roles": payload.roles if payload.roles is not None else await _get_user_role_names(db, user.id)
    }

    # Write audit log
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_type="user",
        actor_user_id=updated_by_id,
        action="user.update",
        resource_type="users",
        resource_id=user.id,
        before_state=before_state,
        after_state=after_state
    )

    await db.commit()
    return await get_user_detail(db, organization_id, user.id)


async def delete_user(db: AsyncSession, organization_id: uuid.UUID, user_id: uuid.UUID, deleted_by_id: uuid.UUID) -> None:
    user_q = await db.execute(select(User).where(and_(User.organization_id == organization_id, User.id == user_id, User.deleted_at.is_(None))))
    user = user_q.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.deleted_at = datetime.utcnow()
    user.updated_by_id = deleted_by_id

    # Write audit log
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_type="user",
        actor_user_id=deleted_by_id,
        action="user.delete",
        resource_type="users",
        resource_id=user.id,
        before_state={"email": user.email, "username": user.username}
    )

    await db.commit()


async def bulk_action(
    db: AsyncSession,
    organization_id: uuid.UUID,
    user_ids: list[uuid.UUID],
    action: str,
    actor_id: uuid.UUID
) -> dict[str, Any]:
    count = 0
    for uid in user_ids:
        user_q = await db.execute(select(User).where(and_(User.organization_id == organization_id, User.id == uid, User.deleted_at.is_(None))))
        user = user_q.scalar_one_or_none()
        if not user:
            continue
        
        if action == "delete":
            user.deleted_at = datetime.utcnow()
            user.updated_by_id = actor_id
            await write_audit_log(db, organization_id=organization_id, actor_type="user", actor_user_id=actor_id, action="user.delete", resource_type="users", resource_id=user.id)
            count += 1
        elif action == "activate":
            user.status = "active"
            user.updated_by_id = actor_id
            await write_audit_log(db, organization_id=organization_id, actor_type="user", actor_user_id=actor_id, action="user.update", resource_type="users", resource_id=user.id, after_state={"status": "active"})
            count += 1
        elif action == "deactivate":
            user.status = "disabled"
            user.updated_by_id = actor_id
            await write_audit_log(db, organization_id=organization_id, actor_type="user", actor_user_id=actor_id, action="user.update", resource_type="users", resource_id=user.id, after_state={"status": "disabled"})
            count += 1
            
    await db.commit()
    return {"success": True, "count": count}


async def import_users_csv(
    db: AsyncSession,
    organization_id: uuid.UUID,
    csv_bytes: bytes,
    actor_id: uuid.UUID
) -> dict[str, Any]:
    content = csv_bytes.decode("utf-8")
    f = io.StringIO(content)
    reader = csv.DictReader(f)
    
    success_count = 0
    errors = []
    
    for idx, row in enumerate(reader):
        try:
            email = row.get("email")
            username = row.get("username")
            full_name = row.get("full_name")
            password = row.get("password") or "TempPass123!" # default temp password
            
            if not email or not username or not full_name:
                errors.append(f"Row {idx+1}: Missing required fields (email, username, full_name)")
                continue
                
            payload = UserCreate(
                email=email,
                username=username,
                full_name=full_name,
                password=password,
                employee_id=row.get("employee_id"),
                phone_number=row.get("phone_number"),
                department=row.get("department"),
                designation=row.get("designation"),
                status=row.get("status") or "active",
                roles=[r.strip() for r in row.get("roles", "").split(",")] if row.get("roles") else ["Read Only User"]
            )
            
            await create_user(db, organization_id, payload, actor_id)
            success_count += 1
        except Exception as e:
            # Rollback flush but keep going
            await db.rollback()
            errors.append(f"Row {idx+1}: {str(e)}")
            
    return {"success_count": success_count, "errors": errors}


async def export_users_csv(db: AsyncSession, organization_id: uuid.UUID) -> str:
    # Retrieve all users
    query = select(User).where(and_(User.organization_id == organization_id, User.deleted_at.is_(None))).order_by(User.full_name.asc())
    result = await db.execute(query)
    users = result.scalars().all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        "id", "email", "username", "full_name", "status", "employee_id", 
        "phone_number", "department", "designation", "mfa_enabled", "roles", 
        "created_at", "last_login_at"
    ])
    
    for user in users:
        roles = await _get_user_role_names(db, user.id)
        writer.writerow([
            str(user.id),
            user.email,
            user.username or "",
            user.full_name,
            user.status,
            user.employee_id or "",
            user.phone_number or "",
            user.department or "",
            user.designation or "",
            str(user.mfa_enabled),
            ",".join(roles),
            user.created_at.isoformat() if user.created_at else "",
            user.last_login_at.isoformat() if user.last_login_at else "",
        ])
        
    return output.getvalue()


# Helper function to get role names for a user
async def _get_user_role_names(db: AsyncSession, user_id: uuid.UUID) -> list[str]:
    result = await db.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user_id)
    )
    return [row[0] for row in result.all()]
