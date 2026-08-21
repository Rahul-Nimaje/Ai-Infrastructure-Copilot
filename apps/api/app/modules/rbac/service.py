from datetime import datetime
import uuid
from typing import Any
from fastapi import HTTPException, status
from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import write_audit_log
from app.models.rbac import Role, Permission, RolePermission, UserRole
from app.models.user import User
from app.modules.rbac.schemas import RoleCreate, RoleUpdate


async def list_roles(db: AsyncSession, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    query = select(Role).where(and_(Role.organization_id == organization_id, Role.deleted_at.is_(None)))
    result = await db.execute(query)
    roles = result.scalars().all()

    roles_list = []
    for role in roles:
        permissions = await _get_role_permission_codes(db, role.id)
        roles_list.append({
            "id": role.id,
            "organization_id": role.organization_id,
            "name": role.name,
            "description": role.description,
            "is_system_role": role.is_system_role,
            "permissions": permissions,
        })
    return roles_list


async def get_role_detail(db: AsyncSession, organization_id: uuid.UUID, role_id: uuid.UUID) -> dict[str, Any]:
    query = select(Role).where(and_(Role.organization_id == organization_id, Role.id == role_id, Role.deleted_at.is_(None)))
    result = await db.execute(query)
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    permissions = await _get_role_permission_codes(db, role.id)
    return {
        "id": role.id,
        "organization_id": role.organization_id,
        "name": role.name,
        "description": role.description,
        "is_system_role": role.is_system_role,
        "permissions": permissions,
    }


async def create_role(
    db: AsyncSession,
    organization_id: uuid.UUID,
    payload: RoleCreate,
    actor_id: uuid.UUID
) -> dict[str, Any]:
    # Check if role name already exists
    name_check = await db.execute(
        select(Role).where(
            and_(
                Role.organization_id == organization_id,
                Role.name == payload.name,
                Role.deleted_at.is_(None)
            )
        )
    )
    if name_check.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role name already exists")

    role = Role(
        organization_id=organization_id,
        name=payload.name,
        description=payload.description,
        is_system_role=False,
    )
    db.add(role)
    await db.flush()

    # Assign permissions
    for perm_id in payload.permissions:
        perm_check = await db.execute(select(Permission).where(Permission.id == perm_id))
        if perm_check.scalar_one_or_none():
            db.add(RolePermission(role_id=role.id, permission_id=perm_id))

    await db.flush()

    # Write audit log
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_type="user",
        actor_user_id=actor_id,
        action="role.create",
        resource_type="roles",
        resource_id=role.id,
        after_state={"name": role.name, "description": role.description, "permissions": [str(p) for p in payload.permissions]}
    )

    await db.commit()
    return await get_role_detail(db, organization_id, role.id)


async def update_role(
    db: AsyncSession,
    organization_id: uuid.UUID,
    role_id: uuid.UUID,
    payload: RoleUpdate,
    actor_id: uuid.UUID
) -> dict[str, Any]:
    # Fetch role
    query = select(Role).where(and_(Role.organization_id == organization_id, Role.id == role_id, Role.deleted_at.is_(None)))
    result = await db.execute(query)
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    if role.is_system_role:
        # System roles cannot be renamed or deleted, but their permissions might be adjustable.
        # However, to avoid breaking core features, let's block modifications to system roles completely
        # or only block editing name. Let's block modification completely.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="System roles cannot be modified")

    before_state = {
        "name": role.name,
        "description": role.description,
        "permissions": await _get_role_permission_codes(db, role.id)
    }

    # Validate name uniqueness
    if payload.name and payload.name != role.name:
        name_check = await db.execute(
            select(Role).where(
                and_(
                    Role.organization_id == organization_id,
                    Role.name == payload.name,
                    Role.id != role_id,
                    Role.deleted_at.is_(None)
                )
            )
        )
        if name_check.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role name already exists")
        role.name = payload.name

    if payload.description is not None:
        role.description = payload.description

    # Update permissions if provided
    if payload.permissions is not None:
        await db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
        await db.flush()

        for perm_id in payload.permissions:
            perm_check = await db.execute(select(Permission).where(Permission.id == perm_id))
            if perm_check.scalar_one_or_none():
                db.add(RolePermission(role_id=role.id, permission_id=perm_id))

    await db.flush()

    after_state = {
        "name": role.name,
        "description": role.description,
        "permissions": await _get_role_permission_codes(db, role.id)
    }

    # Write audit log
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_type="user",
        actor_user_id=actor_id,
        action="role.update",
        resource_type="roles",
        resource_id=role.id,
        before_state=before_state,
        after_state=after_state
    )

    await db.commit()
    return await get_role_detail(db, organization_id, role.id)


async def delete_role(db: AsyncSession, organization_id: uuid.UUID, role_id: uuid.UUID, actor_id: uuid.UUID) -> None:
    query = select(Role).where(and_(Role.organization_id == organization_id, Role.id == role_id, Role.deleted_at.is_(None)))
    result = await db.execute(query)
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    if role.is_system_role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="System roles cannot be deleted")

    role.deleted_at = datetime.utcnow()

    # Write audit log
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_type="user",
        actor_user_id=actor_id,
        action="role.delete",
        resource_type="roles",
        resource_id=role.id,
        before_state={"name": role.name}
    )

    await db.commit()


async def list_permissions(db: AsyncSession) -> list[Permission]:
    result = await db.execute(select(Permission))
    return list(result.scalars().all())


async def assign_user_roles(
    db: AsyncSession,
    organization_id: uuid.UUID,
    target_user_id: uuid.UUID,
    role_ids: list[uuid.UUID],
    actor_id: uuid.UUID
) -> list[str]:
    # Check user existence
    user_q = await db.execute(select(User).where(and_(User.organization_id == organization_id, User.id == target_user_id, User.deleted_at.is_(None))))
    user = user_q.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Clear old roles
    await db.execute(delete(UserRole).where(UserRole.user_id == target_user_id))
    await db.flush()

    # Add new ones
    for rid in role_ids:
        role_q = await db.execute(select(Role).where(and_(Role.organization_id == organization_id, Role.id == rid, Role.deleted_at.is_(None))))
        role = role_q.scalar_one_or_none()
        if role:
            db.add(UserRole(user_id=target_user_id, role_id=role.id, granted_by=actor_id))

    await db.flush()

    role_names = await _get_user_role_names(db, target_user_id)

    # Write audit log
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_type="user",
        actor_user_id=actor_id,
        action="user.assign_roles",
        resource_type="users",
        resource_id=target_user_id,
        after_state={"roles": role_names}
    )

    await db.commit()
    return role_names


# Helper function to get role names for a user
async def _get_user_role_names(db: AsyncSession, user_id: uuid.UUID) -> list[str]:
    result = await db.execute(
        select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == user_id)
    )
    return [row[0] for row in result.all()]


# Helper function to get permission codes for a role
async def _get_role_permission_codes(db: AsyncSession, role_id: uuid.UUID) -> list[str]:
    result = await db.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
    )
    return [row[0] for row in result.all()]


async def list_role_permissions(db: AsyncSession, organization_id: uuid.UUID, role_id: uuid.UUID) -> list[Permission]:
    role_q = await db.execute(
        select(Role).where(and_(Role.organization_id == organization_id, Role.id == role_id, Role.deleted_at.is_(None)))
    )
    role = role_q.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    result = await db.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
    )
    return list(result.scalars().all())


async def update_role_permissions(
    db: AsyncSession,
    organization_id: uuid.UUID,
    role_id: uuid.UUID,
    permission_ids: list[uuid.UUID],
    actor_id: uuid.UUID
) -> list[Permission]:
    role_q = await db.execute(
        select(Role).where(and_(Role.organization_id == organization_id, Role.id == role_id, Role.deleted_at.is_(None)))
    )
    role = role_q.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    if role.is_system_role:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="System roles cannot be modified")

    before_state = {
        "permissions": await _get_role_permission_codes(db, role_id)
    }

    # Clear old permissions
    await db.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
    await db.flush()

    # Add new permissions
    for perm_id in permission_ids:
        perm_check = await db.execute(select(Permission).where(Permission.id == perm_id))
        if perm_check.scalar_one_or_none():
            db.add(RolePermission(role_id=role_id, permission_id=perm_id))

    await db.flush()

    # Get updated permissions
    result = await db.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
    )
    updated_perms = list(result.scalars().all())
    after_state = {
        "permissions": [p.code for p in updated_perms]
    }

    # Write audit log
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_type="user",
        actor_user_id=actor_id,
        action="role.update_permissions",
        resource_type="roles",
        resource_id=role_id,
        before_state=before_state,
        after_state=after_state
    )

    await db.commit()
    return updated_perms


async def list_role_users(db: AsyncSession, organization_id: uuid.UUID, role_id: uuid.UUID) -> list[User]:
    role_q = await db.execute(
        select(Role).where(and_(Role.organization_id == organization_id, Role.id == role_id, Role.deleted_at.is_(None)))
    )
    role = role_q.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    result = await db.execute(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .where(and_(UserRole.role_id == role_id, User.organization_id == organization_id, User.deleted_at.is_(None)))
    )
    return list(result.scalars().all())


async def unassign_user_role(
    db: AsyncSession,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    actor_id: uuid.UUID
) -> None:
    user_q = await db.execute(
        select(User).where(and_(User.organization_id == organization_id, User.id == user_id, User.deleted_at.is_(None)))
    )
    user = user_q.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    role_q = await db.execute(
        select(Role).where(and_(Role.organization_id == organization_id, Role.id == role_id, Role.deleted_at.is_(None)))
    )
    role = role_q.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Delete assignment
    await db.execute(delete(UserRole).where(and_(UserRole.user_id == user_id, UserRole.role_id == role_id)))
    await db.flush()

    role_names = await _get_user_role_names(db, user_id)

    # Write audit log
    await write_audit_log(
        db,
        organization_id=organization_id,
        actor_type="user",
        actor_user_id=actor_id,
        action="user.unassign_role",
        resource_type="users",
        resource_id=user_id,
        after_state={"roles": role_names}
    )

    await db.commit()
