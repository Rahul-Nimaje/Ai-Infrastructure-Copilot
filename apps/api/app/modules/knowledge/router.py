"""Knowledge Base API endpoints.

All routes enforce RBAC via require_permission() and scope every DB query
to the authenticated user's organization via get_org_db.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AccessTokenClaims, require_permission
from app.dependencies import get_org_db
from app.modules.knowledge import repository as repo
from app.modules.knowledge import service
from app.modules.knowledge.schemas import (
    DocumentChunkOut,
    DocumentDetailOut,
    DocumentListParams,
    DocumentOut,
    DocumentStatusOut,
    DocumentUploadResponse,
    RagEvaluationCreate,
    RagEvaluationOut,
    RagQueryLogOut,
    RagSearchRequest,
    RagSearchResponse,
    SourceCitationOut,
)

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge-base"])
rag_router = APIRouter(prefix="/api/v1/rag", tags=["rag-admin"])


# ── Document Upload ─────────────────────────────────────────────────────

@router.post("/documents", response_model=None)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    department: str | None = Form(default=None),
    tags: str | None = Form(default=None),  # comma-separated
    user: AccessTokenClaims = Depends(require_permission("knowledge.manage")),
    db: AsyncSession = Depends(get_org_db),
):
    """Upload a document to the knowledge base. Processing happens in the background."""
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail={"code": "EMPTY_FILE", "message": "Uploaded file is empty."})

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

    try:
        result = await service.upload_document(
            db,
            organization_id=uuid.UUID(user.organization_id),
            user_id=uuid.UUID(user.user_id),
            file_bytes=file_bytes,
            file_name=file.filename or "unnamed",
            title=title,
            department=department,
            tags=tag_list,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "UPLOAD_ERROR", "message": str(e)})

    return {"data": DocumentUploadResponse(**result)}


# ── Document List ───────────────────────────────────────────────────────

@router.get("/documents", response_model=None)
async def list_documents(
    status: str | None = Query(default=None),
    file_type: str | None = Query(default=None),
    department: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: AccessTokenClaims = Depends(require_permission("knowledge.read")),
    db: AsyncSession = Depends(get_org_db),
):
    """List documents with optional filtering and pagination."""
    offset = (page - 1) * page_size
    docs, total = await repo.list_documents(
        db,
        organization_id=uuid.UUID(user.organization_id),
        status=status, file_type=file_type, department=department, search=search,
        offset=offset, limit=page_size,
    )
    return {
        "data": [DocumentOut.model_validate(d) for d in docs],
        "pagination": {"page": page, "page_size": page_size, "total": total},
    }


# ── Document Detail ─────────────────────────────────────────────────────

@router.get("/documents/{document_id}", response_model=None)
async def get_document(
    document_id: uuid.UUID,
    user: AccessTokenClaims = Depends(require_permission("knowledge.read")),
    db: AsyncSession = Depends(get_org_db),
):
    doc = await repo.get_document(db, organization_id=uuid.UUID(user.organization_id), document_id=document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "Document not found."})
    return {"data": DocumentDetailOut.model_validate(doc)}


# ── Document Delete ─────────────────────────────────────────────────────

@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    user: AccessTokenClaims = Depends(require_permission("knowledge.manage")),
    db: AsyncSession = Depends(get_org_db),
):
    try:
        await service.delete_document(db, organization_id=uuid.UUID(user.organization_id), document_id=document_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": str(e)})


# ── Document Re-index ───────────────────────────────────────────────────

@router.post("/documents/{document_id}/reindex", response_model=None)
async def reindex_document(
    document_id: uuid.UUID,
    user: AccessTokenClaims = Depends(require_permission("knowledge.manage")),
    db: AsyncSession = Depends(get_org_db),
):
    try:
        await service.reindex_document(db, organization_id=uuid.UUID(user.organization_id), document_id=document_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": str(e)})
    return {"data": {"message": "Re-indexing started."}}


# ── Document Status ─────────────────────────────────────────────────────

@router.get("/documents/{document_id}/status", response_model=None)
async def get_document_status(
    document_id: uuid.UUID,
    user: AccessTokenClaims = Depends(require_permission("knowledge.read")),
    db: AsyncSession = Depends(get_org_db),
):
    doc = await repo.get_document(db, organization_id=uuid.UUID(user.organization_id), document_id=document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "Document not found."})
    return {"data": DocumentStatusOut.model_validate(doc)}


# ── Document Chunks ─────────────────────────────────────────────────────

@router.get("/documents/{document_id}/chunks", response_model=None)
async def get_document_chunks(
    document_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    user: AccessTokenClaims = Depends(require_permission("knowledge.read")),
    db: AsyncSession = Depends(get_org_db),
):
    # Verify document belongs to org
    doc = await repo.get_document(db, organization_id=uuid.UUID(user.organization_id), document_id=document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "Document not found."})

    offset = (page - 1) * page_size
    chunks = await repo.get_chunks_by_document(db, document_id=document_id, offset=offset, limit=page_size)
    return {"data": [DocumentChunkOut.model_validate(c) for c in chunks]}


# ── RAG Search ──────────────────────────────────────────────────────────

@router.post("/search", response_model=None)
async def rag_search(
    payload: RagSearchRequest,
    user: AccessTokenClaims = Depends(require_permission("knowledge.read")),
    db: AsyncSession = Depends(get_org_db),
):
    """Search the knowledge base using semantic + keyword search with re-ranking."""
    result = await service.search(
        db,
        organization_id=uuid.UUID(user.organization_id),
        query=payload.query,
        top_k=payload.top_k,
        final_top_k=payload.final_top_k,
        metadata_filters=payload.metadata_filters,
        user_id=uuid.UUID(user.user_id),
    )
    return {
        "data": RagSearchResponse(
            query=result["query"],
            chunks=result["chunks"],
            sources=[SourceCitationOut(**s) for s in result["sources"]],
            query_log_id=result["query_log_id"],
        )
    }


# ── RAG Debug (Admin) ──────────────────────────────────────────────────

@rag_router.get("/debug/{query_id}", response_model=None)
async def get_rag_debug(
    query_id: uuid.UUID,
    user: AccessTokenClaims = Depends(require_permission("rag.debug")),
    db: AsyncSession = Depends(get_org_db),
):
    """Get detailed debug info for a RAG query — admin only."""
    log = await repo.get_query_log(db, organization_id=uuid.UUID(user.organization_id), query_log_id=query_id)
    if log is None:
        raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND", "message": "Query log not found."})
    return {"data": RagQueryLogOut.model_validate(log)}


# ── RAG Evaluations (Admin) ────────────────────────────────────────────

@rag_router.get("/evaluations", response_model=None)
async def list_evaluations(
    user: AccessTokenClaims = Depends(require_permission("rag.evaluate")),
    db: AsyncSession = Depends(get_org_db),
):
    evals = await repo.list_evaluations(db, organization_id=uuid.UUID(user.organization_id))
    return {"data": [RagEvaluationOut.model_validate(e) for e in evals]}


@rag_router.post("/evaluations", response_model=None)
async def create_evaluation(
    payload: RagEvaluationCreate,
    user: AccessTokenClaims = Depends(require_permission("rag.evaluate")),
    db: AsyncSession = Depends(get_org_db),
):
    evaluation = await repo.create_evaluation(
        db,
        organization_id=uuid.UUID(user.organization_id),
        question=payload.question,
        expected_doc_id=payload.expected_doc_id,
        expected_doc_name=payload.expected_doc_name,
    )
    await db.commit()
    return {"data": RagEvaluationOut.model_validate(evaluation)}
