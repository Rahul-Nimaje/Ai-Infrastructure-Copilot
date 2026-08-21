import { useQuery } from "@tanstack/react-query";
import { API_BASE_URL, apiFetch, getAccessToken } from "@/lib/api-client";
import { useToastMutation } from "./useToastMutation";
import type { DocumentChunk, DocumentDetail, KnowledgeDocument } from "@/features/knowledge-base/types";

interface ListParams {
  status?: string;
  file_type?: string;
  department?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export function useKnowledgeBase(params?: ListParams) {
  const documentsQuery = useQuery({
    queryKey: ["knowledge-documents", params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params?.status) searchParams.set("status", params.status);
      if (params?.file_type) searchParams.set("file_type", params.file_type);
      if (params?.department) searchParams.set("department", params.department);
      if (params?.search) searchParams.set("search", params.search);
      if (params?.page) searchParams.set("page", String(params.page));
      if (params?.page_size) searchParams.set("page_size", String(params.page_size));

      const queryStr = searchParams.toString();
      const url = `/api/v1/knowledge/documents${queryStr ? `?${queryStr}` : ""}`;
      return apiFetch<{ data: KnowledgeDocument[]; pagination: { page: number; page_size: number; total: number } }>(url);
    },
    refetchInterval: (query) => {
      // Auto-refetch every 3s if any document is processing or pending
      const docs = query.state.data?.data;
      const hasPending = docs?.some((d) => d.status === "pending" || d.status === "processing");
      return hasPending ? 3000 : false;
    },
  });

  const uploadDocument = useToastMutation<any, any, { file: File; title?: string; department?: string; tags?: string }>({
    mutationFn: async ({ file, title, department, tags }) => {
      const formData = new FormData();
      formData.append("file", file);
      if (title) formData.append("title", title);
      if (department) formData.append("department", department);
      if (tags) formData.append("tags", tags);

      const response = await fetch(`${API_BASE_URL}/api/v1/knowledge/documents`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getAccessToken()}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error?.detail?.message || error?.message || "Failed to upload document");
      }
      return response.json();
    },
    invalidateKeys: [["knowledge-documents"]],
    successTitle: "Document Uploaded",
    successDescription: "Document submitted for ingestion and indexing.",
    errorTitle: "Upload Failed",
  });

  const deleteDocument = useToastMutation<any, any, string>({
    mutationFn: (documentId: string) =>
      apiFetch(`/api/v1/knowledge/documents/${documentId}`, { method: "DELETE" }),
    invalidateKeys: [["knowledge-documents"]],
    successTitle: "Document Deleted",
    successDescription: "Document and its embeddings removed successfully.",
    errorTitle: "Delete Failed",
  });

  const reindexDocument = useToastMutation<any, any, string>({
    mutationFn: (documentId: string) =>
      apiFetch(`/api/v1/knowledge/documents/${documentId}/reindex`, { method: "POST" }),
    invalidateKeys: [["knowledge-documents"]],
    successTitle: "Re-indexing Triggered",
    successDescription: "Document is being re-parsed and re-embedded.",
    errorTitle: "Re-index Failed",
  });

  return {
    documents: documentsQuery.data?.data || [],
    pagination: documentsQuery.data?.pagination,
    isLoading: documentsQuery.isLoading,
    refetch: documentsQuery.refetch,
    uploadDocument,
    deleteDocument,
    reindexDocument,
  };
}

export function useDocumentDetail(documentId: string | null) {
  return useQuery({
    queryKey: ["knowledge-document", documentId],
    queryFn: () => apiFetch<{ data: DocumentDetail }>(`/api/v1/knowledge/documents/${documentId}`),
    enabled: !!documentId,
  });
}

export function useDocumentChunks(documentId: string | null) {
  return useQuery({
    queryKey: ["knowledge-document-chunks", documentId],
    queryFn: () => apiFetch<{ data: DocumentChunk[] }>(`/api/v1/knowledge/documents/${documentId}/chunks`),
    enabled: !!documentId,
  });
}
