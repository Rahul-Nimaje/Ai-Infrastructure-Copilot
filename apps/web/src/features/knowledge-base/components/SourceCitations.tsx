"use client";

import { BookOpen, FileText, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { SourceCitation } from "../types";

interface Props {
  sources: SourceCitation[];
}

export function SourceCitations({ sources }: Props) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3 border-t border-border/40 pt-2 space-y-1.5">
      <div className="flex items-center gap-1.5 text-xs font-bold text-muted-foreground uppercase tracking-wider">
        <BookOpen className="h-3.5 w-3.5 text-primary" />
        Retrieved Knowledge Sources ({sources.length})
      </div>
      <div className="flex flex-wrap gap-2 pt-1">
        {sources.map((src, i) => (
          <div
            key={src.chunk_id || i}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-primary/20 bg-primary/5 hover:bg-primary/10 transition-colors text-xs cursor-pointer group"
            title={src.snippet || src.file_name}
          >
            <FileText className="h-3 w-3 text-primary shrink-0" />
            <span className="font-semibold text-foreground truncate max-w-[200px]">
              {src.document_title || src.file_name}
            </span>
            {src.page_number && (
              <span className="text-[10px] text-muted-foreground font-mono">
                p.{src.page_number}
              </span>
            )}
            {src.relevance_score && (
              <Badge variant="muted" className="text-[9px] py-0 px-1 font-mono">
                {Math.round(src.relevance_score * 100)}% match
              </Badge>
            )}

          </div>
        ))}
      </div>
    </div>
  );
}
