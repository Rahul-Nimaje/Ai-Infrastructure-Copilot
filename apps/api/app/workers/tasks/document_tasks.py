"""Celery tasks for document processing.

Each task runs in the worker process with its own async event loop and DB session.
Tasks support retry, failure handling, and progress tracking via DB status updates.
"""
from __future__ import annotations

import asyncio
import logging
import uuid

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async function in a new event loop (Celery workers are sync)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    name="app.workers.tasks.document_tasks.process_document_task",
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def process_document_task(self, document_id: str, organization_id: str):
    """Process a document through the full ingestion pipeline.

    Called after upload — parses, chunks, embeds, and stores vectors.
    Retries up to 3 times on failure with 30-second delays.
    """
    logger.info("Processing document %s for org %s", document_id, organization_id)

    async def _process():
        from app.core.db import SessionLocal
        from app.modules.knowledge.service import process_document

        async with SessionLocal() as db:
            await process_document(
                db,
                document_id=uuid.UUID(document_id),
                organization_id=uuid.UUID(organization_id),
            )

    try:
        _run_async(_process())
        logger.info("Document %s processed successfully", document_id)
    except Exception as exc:
        logger.exception("Document %s processing failed (attempt %d)", document_id, self.request.retries + 1)
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.workers.tasks.document_tasks.delete_document_task",
    max_retries=3,
    default_retry_delay=10,
)
def delete_document_task(self, document_id: str, organization_id: str):
    """Clean up chunks and stored files for a deleted document."""
    logger.info("Cleaning up document %s", document_id)

    async def _delete():
        from app.core.db import SessionLocal
        from app.modules.knowledge.service import delete_document

        async with SessionLocal() as db:
            await delete_document(
                db,
                organization_id=uuid.UUID(organization_id),
                document_id=uuid.UUID(document_id),
            )

    try:
        _run_async(_delete())
        logger.info("Document %s cleanup complete", document_id)
    except Exception as exc:
        logger.exception("Document %s cleanup failed", document_id)
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    name="app.workers.tasks.document_tasks.reindex_document_task",
    max_retries=3,
    default_retry_delay=30,
)
def reindex_document_task(self, document_id: str, organization_id: str):
    """Drop existing chunks and re-process a document."""
    logger.info("Re-indexing document %s", document_id)

    async def _reindex():
        from app.core.db import SessionLocal
        from app.modules.knowledge import repository as repo
        from app.modules.knowledge.service import process_document

        async with SessionLocal() as db:
            # Delete existing chunks
            await repo.delete_chunks_by_document(db, document_id=uuid.UUID(document_id))
            await repo.update_document_status(
                db, document_id=uuid.UUID(document_id), status="pending", chunk_count=0,
            )
            await db.commit()

            # Re-process
            await process_document(
                db,
                document_id=uuid.UUID(document_id),
                organization_id=uuid.UUID(organization_id),
            )

    try:
        _run_async(_reindex())
        logger.info("Document %s re-indexed successfully", document_id)
    except Exception as exc:
        logger.exception("Document %s re-indexing failed", document_id)
        raise self.retry(exc=exc)
