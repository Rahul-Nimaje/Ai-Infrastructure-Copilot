export type DocumentStatus = "pending" | "processing" | "indexed" | "failed" | "deleting";

export interface KnowledgeDocument {
  id: string;
  title: string;
  file_name: string;
  file_type: string;
  file_size: number;
  status: DocumentStatus;
  department?: string | null;
  tags?: string[] | null;
  chunk_count: number;
  uploaded_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetail extends KnowledgeDocument {
  file_hash?: string | null;
  error_message?: string | null;
  metadata_extra?: Record<string, any> | null;
  processing_started_at?: string | null;
  processing_completed_at?: string | null;
}

export interface DocumentChunk {
  id: string;
  chunk_index: number;
  content: string;

  token_count?: number | null;
  page_number?: number | null;
  section?: string | null;
  title?: string | null;
  source_type?: string | null;
  created_at: string;
}

export interface SourceCitation {
  document_id: string;
  document_title: string;
  file_name: string;
  chunk_id?: string | null;
  chunk_index?: number | null;
  page_number?: number | null;
  section?: string | null;
  relevance_score?: number | null;
  snippet?: string | null;
}

export interface RagSearchResponse {
  query: string;
  chunks: any[];
  sources: SourceCitation[];
  query_log_id?: string | null;
}
