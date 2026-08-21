"use client";

import { useDocumentChunks, useDocumentDetail } from "@/hooks";
import { DocumentStatusBadge } from "./DocumentStatusBadge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { FileText, Layers, Hash, Calendar, ShieldAlert } from "lucide-react";
import { useState } from "react";

interface Props {
  documentId: string | null;
  onClose: () => void;
}

export function DocumentDetailDrawer({ documentId, onClose }: Props) {
  const [activeTab, setActiveTab] = useState<"overview" | "chunks">("overview");

  const { data: detailData, isLoading: detailLoading } = useDocumentDetail(documentId);
  const { data: chunksData, isLoading: chunksLoading } = useDocumentChunks(activeTab === "chunks" ? documentId : null);

  const doc = detailData?.data;
  const chunks = chunksData?.data || [];

  return (
    <Dialog open={!!documentId} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[700px] max-h-[85vh] flex flex-col p-0 overflow-hidden">
        <DialogHeader className="p-6 pb-3 border-b border-border">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            <DialogTitle className="text-lg font-bold truncate max-w-[500px]">
              {doc?.title || "Document Details"}
            </DialogTitle>
          </div>
          <div className="flex items-center gap-3 mt-2">
            {doc && <DocumentStatusBadge status={doc.status} errorMessage={doc.error_message} />}
            <span className="text-xs text-muted-foreground font-mono">{doc?.file_name}</span>
          </div>
        </DialogHeader>

        {/* Tab navigation */}
        <div className="flex border-b border-border bg-muted/40 px-6">
          <button
            onClick={() => setActiveTab("overview")}
            className={`px-4 py-2.5 text-xs font-bold border-b-2 transition-colors ${
              activeTab === "overview"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Overview &amp; Metadata
          </button>
          <button
            onClick={() => setActiveTab("chunks")}
            className={`px-4 py-2.5 text-xs font-bold border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === "chunks"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <Layers className="h-3.5 w-3.5" />
            Extracted Chunks ({doc?.chunk_count ?? 0})
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {detailLoading ? (
            <div className="p-8 text-center text-xs text-muted-foreground animate-pulse">
              Loading document metadata...
            </div>
          ) : activeTab === "overview" && doc ? (
            <div className="space-y-6">
              {doc.error_message && (
                <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-xs flex gap-2 items-start">
                  <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-bold">Ingestion Failure Error</p>
                    <p className="mt-0.5">{doc.error_message}</p>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 rounded-xl border border-border bg-card/60 space-y-1">
                  <span className="text-[11px] font-semibold text-muted-foreground">File Size</span>
                  <p className="text-sm font-bold">{(doc.file_size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
                <div className="p-3 rounded-xl border border-border bg-card/60 space-y-1">
                  <span className="text-[11px] font-semibold text-muted-foreground">Chunk Count</span>
                  <p className="text-sm font-bold">{doc.chunk_count} chunks</p>
                </div>
                <div className="p-3 rounded-xl border border-border bg-card/60 space-y-1">
                  <span className="text-[11px] font-semibold text-muted-foreground">File Format</span>
                  <p className="text-sm font-bold uppercase">{doc.file_type}</p>
                </div>
                <div className="p-3 rounded-xl border border-border bg-card/60 space-y-1">
                  <span className="text-[11px] font-semibold text-muted-foreground">Department</span>
                  <p className="text-sm font-bold">{doc.department || "N/A"}</p>
                </div>
              </div>

              {doc.tags && doc.tags.length > 0 && (
                <div className="space-y-1.5">
                  <span className="text-xs font-semibold text-muted-foreground">Tags</span>
                  <div className="flex flex-wrap gap-1.5">
                    {doc.tags.map((tag: string) => (
                      <Badge key={tag} variant="muted" className="text-[11px]">
                        #{tag}
                      </Badge>
                    ))}

                  </div>
                </div>
              )}

              <div className="space-y-2 border-t border-border pt-4 text-xs text-muted-foreground font-mono space-y-1">
                <div className="flex justify-between">
                  <span>SHA-256 Hash:</span>
                  <span className="truncate max-w-[300px]" title={doc.file_hash || ""}>
                    {doc.file_hash || "N/A"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Uploaded:</span>
                  <span>{new Date(doc.created_at).toLocaleString()}</span>
                </div>
                {doc.processing_completed_at && (
                  <div className="flex justify-between">
                    <span>Processing Completed:</span>
                    <span>{new Date(doc.processing_completed_at).toLocaleString()}</span>
                  </div>
                )}
              </div>
            </div>
          ) : activeTab === "chunks" ? (
            <div className="space-y-3">
              {chunksLoading ? (
                <div className="p-8 text-center text-xs text-muted-foreground animate-pulse">
                  Loading vector chunks...
                </div>
              ) : chunks.length === 0 ? (
                <div className="p-8 text-center text-xs text-muted-foreground">
                  No chunks extracted yet.
                </div>
              ) : (
                chunks.map((chunk) => (
                  <div key={chunk.id} className="p-3 border border-border rounded-xl bg-card space-y-2 text-xs">
                    <div className="flex items-center justify-between text-[11px] text-muted-foreground font-mono border-b border-border/40 pb-1.5">
                      <span className="font-bold text-primary">Chunk #{chunk.chunk_index + 1}</span>
                      {chunk.page_number && <span>Page {chunk.page_number}</span>}
                      {chunk.section && <span className="truncate max-w-[200px]">{chunk.section}</span>}
                      {chunk.token_count && <span>~{chunk.token_count} tokens</span>}
                    </div>
                    <p className="whitespace-pre-wrap font-sans text-foreground/90 leading-relaxed">
                      {chunk.content}
                    </p>
                  </div>
                ))
              )}
            </div>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}
