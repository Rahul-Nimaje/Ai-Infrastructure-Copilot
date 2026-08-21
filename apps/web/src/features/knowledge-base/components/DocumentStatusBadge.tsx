"use client";

import { Badge } from "@/components/ui/badge";
import { Loader2, CheckCircle2, XCircle, Clock, Trash2 } from "lucide-react";
import type { DocumentStatus } from "../types";
import { STATUS_VARIANTS } from "../utils/constants";

interface Props {
  status: DocumentStatus;
  errorMessage?: string | null;
}

export function DocumentStatusBadge({ status, errorMessage }: Props) {
  const config = STATUS_VARIANTS[status] || { label: status, variant: "secondary" };

  return (
    <div className="flex items-center gap-1.5" title={errorMessage || undefined}>
      <Badge variant={config.variant as any} className="capitalize text-xs font-semibold gap-1 py-0.5 px-2">
        {status === "processing" && <Loader2 className="h-3 w-3 animate-spin" />}
        {status === "indexed" && <CheckCircle2 className="h-3 w-3 text-emerald-500" />}
        {status === "failed" && <XCircle className="h-3 w-3 text-destructive" />}
        {status === "pending" && <Clock className="h-3 w-3" />}
        {status === "deleting" && <Trash2 className="h-3 w-3" />}
        <span>{config.label}</span>
      </Badge>
    </div>
  );
}
