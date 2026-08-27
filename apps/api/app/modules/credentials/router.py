import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_permission
from app.dependencies import get_org_db
from app.modules.credentials import service
from app.modules.credentials.schemas import CreateCredentialRequest, CredentialOut

router = APIRouter(prefix="/api/v1/credentials", tags=["credentials"])


@router.get("", response_model=None)
async def list_credentials(
    user=Depends(require_permission("servers.write")),
    db: AsyncSession = Depends(get_org_db),
):
    credentials = await service.list_credentials(db, organization_id=uuid.UUID(user.organization_id))
    return {
        "data": [
            CredentialOut(
                id=c.id, name=c.name, credential_type=c.credential_type,
                username=c.encrypted_metadata.get("username"),
            )
            for c in credentials
        ]
    }


@router.post("", status_code=status.HTTP_201_CREATED, response_model=None)
async def create_credential(
    payload: CreateCredentialRequest,
    user=Depends(require_permission("servers.write")),
    db: AsyncSession = Depends(get_org_db),
):
    credential = await service.create_credential(
        db,
        organization_id=uuid.UUID(user.organization_id),
        created_by_user_id=uuid.UUID(user.user_id),
        name=payload.name,
        credential_type=payload.credential_type,
        username=payload.username,
        secret=payload.secret,
    )
    return {
        "data": CredentialOut(
            id=credential.id, name=credential.name, credential_type=credential.credential_type,
            username=payload.username,
        )
    }


@router.delete("/{credential_id}", status_code=status.HTTP_200_OK)
async def delete_credential(
    credential_id: uuid.UUID,
    user=Depends(require_permission("servers.write")),
    db: AsyncSession = Depends(get_org_db),
):
    success = await service.delete_credential(
        db, organization_id=uuid.UUID(user.organization_id), credential_id=credential_id
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")
    return {"message": "Credential deleted successfully"}

