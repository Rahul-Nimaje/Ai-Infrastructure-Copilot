"""Knowledge Base tables — documents, chunks with pgvector embeddings,
RAG query logs, and evaluation test cases.

Revision ID: 0005_knowledge_base
Revises: 0004_departments_designations
Create Date: 2026-08-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005_knowledge_base"
down_revision = ("3838d8e1c37a", "0004")




branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure pgvector extension is available
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── documents ───────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(500), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("file_hash", sa.String(128), nullable=True),
        sa.Column("storage_path", sa.String(1000), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("department", sa.String(200), nullable=True),
        sa.Column("tags", JSONB(), server_default="[]"),
        sa.Column("metadata_extra", JSONB(), server_default="{}"),
        sa.Column("uploaded_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("chunk_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_documents_org", "documents", ["organization_id"],
                    postgresql_where=sa.text("deleted_at IS NULL"))

    # ── document_chunks ─────────────────────────────────────────────────
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", sa.Uuid(),
                  sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.Uuid(),
                  sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(500), nullable=True),
        sa.Column("title", sa.String(500), nullable=True),
        sa.Column("source_type", sa.String(50), nullable=True),
        sa.Column("metadata_extra", JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_chunks_doc", "document_chunks", ["document_id"])
    op.create_index("idx_chunks_org", "document_chunks", ["organization_id"])

    # Add the vector column (pgvector) — 1536 dimensions for text-embedding-3-small
    op.execute("ALTER TABLE document_chunks ADD COLUMN embedding vector(1536)")

    # HNSW index for fast approximate nearest neighbor search (cosine distance)
    op.execute("""
        CREATE INDEX idx_chunks_embedding ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # ── rag_query_logs ──────────────────────────────────────────────────
    op.create_table(
        "rag_query_logs",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.Uuid(),
                  sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("conversation_id", sa.Uuid(),
                  sa.ForeignKey("ai_conversations.id"), nullable=True),
        sa.Column("original_query", sa.Text(), nullable=False),
        sa.Column("transformed_query", sa.Text(), nullable=True),
        sa.Column("search_query", sa.Text(), nullable=True),
        sa.Column("metadata_filters", JSONB(), server_default="{}"),
        sa.Column("retrieved_chunks", JSONB(), server_default="[]"),
        sa.Column("final_context", sa.Text(), nullable=True),
        sa.Column("llm_response", sa.Text(), nullable=True),
        sa.Column("sources", JSONB(), server_default="[]"),
        sa.Column("retrieval_time_ms", sa.Integer(), nullable=True),
        sa.Column("total_time_ms", sa.Integer(), nullable=True),
        sa.Column("feedback", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_rag_logs_org", "rag_query_logs", ["organization_id"])

    # ── rag_evaluations ─────────────────────────────────────────────────
    op.create_table(
        "rag_evaluations",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.Uuid(),
                  sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("expected_doc_id", sa.Uuid(),
                  sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("expected_doc_name", sa.String(500), nullable=True),
        sa.Column("actual_doc_ids", JSONB(), server_default="[]"),
        sa.Column("retrieval_hit", sa.Boolean(), nullable=True),
        sa.Column("context_relevance", sa.Float(), nullable=True),
        sa.Column("answer_relevance", sa.Float(), nullable=True),
        sa.Column("citation_accuracy", sa.Float(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # ── Seed knowledge permissions ──────────────────────────────────────
    op.execute("""
        INSERT INTO permissions (id, code, module, description) VALUES
            (gen_random_uuid(), 'knowledge.manage', 'knowledge', 'Upload, delete, and re-index knowledge base documents'),
            (gen_random_uuid(), 'knowledge.read', 'knowledge', 'View and search knowledge base documents'),
            (gen_random_uuid(), 'rag.debug', 'rag', 'Access RAG debug interface'),
            (gen_random_uuid(), 'rag.evaluate', 'rag', 'Manage RAG evaluation test cases')
        ON CONFLICT (code) DO NOTHING
    """)

    # Grant knowledge permissions to the Admin role (first org's admin)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name = 'Admin'
          AND p.code IN ('knowledge.manage', 'knowledge.read', 'rag.debug', 'rag.evaluate')
          AND NOT EXISTS (
              SELECT 1 FROM role_permissions rp
              WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_chunks_embedding")
    op.drop_table("rag_evaluations")
    op.drop_table("rag_query_logs")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.execute("""
        DELETE FROM role_permissions WHERE permission_id IN (
            SELECT id FROM permissions WHERE code IN (
                'knowledge.manage', 'knowledge.read', 'rag.debug', 'rag.evaluate'
            )
        )
    """)
    op.execute("""
        DELETE FROM permissions WHERE code IN (
            'knowledge.manage', 'knowledge.read', 'rag.debug', 'rag.evaluate'
        )
    """)
