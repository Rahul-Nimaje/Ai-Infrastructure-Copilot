"use client";

import { useState } from "react";
import { Search, FileText, Trash2, RefreshCw, Layers, BookOpen, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ConfirmationDialog } from "@/components/ui/confirmation-dialog";
import { PageHeader, EmptyState, Pagination } from "@/components/common";
import { useKnowledgeBase } from "@/hooks";
import { DocumentStatusBadge } from "./DocumentStatusBadge";
import { DocumentUploadDialog } from "./DocumentUploadDialog";
import { DocumentDetailDrawer } from "./DocumentDetailDrawer";
import { FILE_TYPE_BADGES } from "../utils/constants";
import type { KnowledgeDocument } from "../types";

export function KnowledgeBasePage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [docToDelete, setDocToDelete] = useState<KnowledgeDocument | null>(null);

  const { documents, pagination, isLoading, refetch, deleteDocument, reindexDocument } = useKnowledgeBase({
    search: search || undefined,
    status: statusFilter || undefined,
    page,
    page_size: pageSize,
  });

  return (
    <div className="flex h-[calc(100vh-6rem)] flex-col gap-4">
      <PageHeader
        title="Knowledge Base &amp; RAG Documents"
        description="Upload and manage infrastructure documentation, SOPs, script libraries, and runbooks used by the AI Copilot for grounded retrieval."
      >
        <DocumentUploadDialog />
      </PageHeader>


      {/* Filter and Search Bar */}
      <div className="flex items-center gap-3 bg-card border border-border/60 rounded-xl p-3 shadow-sm">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search documents by title or file name..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="pl-9 text-xs h-9 bg-background/50 border-border/50"
          />
        </div>

        <div className="flex items-center gap-1.5 border-l border-border/60 pl-3">
          <Filter className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <span className="text-xs font-semibold text-muted-foreground">Status:</span>
          {["", "indexed", "processing", "pending", "failed"].map((st) => (
            <Button
              key={st}
              variant={statusFilter === st ? "default" : "ghost"}
              size="sm"
              onClick={() => {
                setStatusFilter(st);
                setPage(1);
              }}
              className="text-xs h-7 px-2.5 capitalize font-medium"
            >

              {st || "All"}
            </Button>
          ))}
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          className="h-9 px-3 text-xs gap-1.5"
          title="Refresh list"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {/* Document List Table / Grid */}
      <div className="flex-1 overflow-y-auto rounded-xl border border-border/60 bg-card/40 backdrop-blur-md shadow-sm p-4">
        {isLoading ? (
          <div className="flex h-full items-center justify-center p-8 text-xs text-muted-foreground animate-pulse">
            Loading knowledge base documents...
          </div>
        ) : documents.length === 0 ? (
          <EmptyState
            icon={BookOpen}
            title="No Documents Found"
            description={
              search || statusFilter
                ? "No documents match the active filters."
                : "Upload infrastructure runbooks, SOPs, or script documentation to give the AI Copilot access to organization knowledge."
            }
          />
        ) : (
          <div className="space-y-2">
            {documents.map((doc: KnowledgeDocument) => {
              const fileConfig = FILE_TYPE_BADGES[doc.file_type] || {
                label: doc.file_type.toUpperCase(),
                color: "bg-gray-500/10 text-gray-600 border-gray-500/20",
              };

              return (
                <div
                  key={doc.id}
                  className="flex items-center justify-between p-3.5 rounded-xl border border-border/60 bg-card hover:border-primary/40 transition-colors group cursor-pointer"
                  onClick={() => setSelectedDocId(doc.id)}
                >
                  <div className="flex items-center gap-3.5 min-w-0">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <FileText className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="text-xs font-bold text-foreground truncate max-w-[350px]">
                          {doc.title}
                        </h4>
                        <Badge variant="muted" className={`text-[10px] py-0 px-1.5 font-bold ${fileConfig.color}`}>
                          {fileConfig.label}
                        </Badge>

                      </div>
                      <div className="flex items-center gap-3 text-[11px] text-muted-foreground mt-0.5">
                        <span className="font-mono">{doc.file_name}</span>
                        <span>•</span>
                        <span>{(doc.file_size / 1024 / 1024).toFixed(2)} MB</span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <Layers className="h-3 w-3" />
                          {doc.chunk_count} chunks
                        </span>
                        {doc.department && (
                          <>
                            <span>•</span>
                            <span className="font-semibold text-foreground/80">{doc.department}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3" onClick={(e) => e.stopPropagation()}>
                    <DocumentStatusBadge status={doc.status} />

                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                        title="Re-index document"
                        onClick={() => reindexDocument.mutate(doc.id)}
                        disabled={reindexDocument.isPending || doc.status === "processing"}
                      >
                        <RefreshCw className="h-3.5 w-3.5" />
                      </Button>

                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                        title="Delete document"
                        onClick={() => setDocToDelete(doc)}
                        disabled={deleteDocument.isPending}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {pagination && pagination.total > 0 && (
        <div className="rounded-xl border border-border/60 bg-card/40">
          <Pagination
            page={page}
            pageSize={pageSize}
            total={pagination.total}
            onPageChange={setPage}
            onPageSizeChange={(size) => {
              setPageSize(size);
              setPage(1);
            }}
            summaryLabel="documents"
          />
        </div>
      )}

      {/* Detail Modal / Drawer */}
      <DocumentDetailDrawer documentId={selectedDocId} onClose={() => setSelectedDocId(null)} />

      <ConfirmationDialog
        isOpen={!!docToDelete}
        onClose={() => setDocToDelete(null)}
        onConfirm={() => {
          if (docToDelete) deleteDocument.mutate(docToDelete.id);
        }}
        title="Delete Document"
        description={`Are you sure you want to delete "${docToDelete?.title}"? This will permanently remove the document and its embeddings. This action cannot be undone.`}
        confirmText="Delete"
        variant="destructive"
        isLoading={deleteDocument.isPending}
      />
    </div>
  );
}
