"use client";

import { useRef, useState } from "react";
import { UploadCloud, File as FileIcon, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface FileUploadProps {
  file: File | null;
  onFileSelect: (file: File | null) => void;
  accept?: string;
  maxSizeMB?: number;
  disabled?: boolean;
  helperText?: string;
  className?: string;
}

export function FileUpload({
  file,
  onFileSelect,
  accept,
  maxSizeMB,
  disabled = false,
  helperText,
  className = "",
}: FileUploadProps) {
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndSelect = (candidate: File | undefined | null) => {
    if (!candidate) return;
    if (maxSizeMB && candidate.size > maxSizeMB * 1024 * 1024) {
      setError(`File exceeds the ${maxSizeMB}MB size limit.`);
      return;
    }
    setError(null);
    onFileSelect(candidate);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;
    validateAndSelect(e.dataTransfer.files?.[0]);
  };

  if (file) {
    return (
      <div className={cn("flex items-center justify-between rounded-xl border border-border/60 bg-card p-3", className)}>
        <div className="flex items-center gap-3 min-w-0">
          <FileIcon className="h-5 w-5 text-primary shrink-0" />
          <div className="min-w-0">
            <p className="text-xs font-bold truncate max-w-[280px]">{file.name}</p>
            <p className="text-[11px] text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
          </div>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0 rounded-full shrink-0"
          disabled={disabled}
          onClick={() => onFileSelect(null)}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    );
  }

  return (
    <div className={className}>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        className={cn(
          "relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition-colors cursor-pointer bg-card/40",
          isDragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50",
          disabled && "cursor-not-allowed opacity-50"
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          disabled={disabled}
          onChange={(e) => validateAndSelect(e.target.files?.[0])}
          className="absolute inset-0 opacity-0 cursor-pointer disabled:cursor-not-allowed"
        />
        <UploadCloud className="h-10 w-10 text-primary mb-2" />
        <p className="text-sm font-semibold">Click or drag &amp; drop file to upload</p>
        {helperText && <p className="text-xs text-muted-foreground mt-1">{helperText}</p>}
      </div>
      {error && <p className="mt-1.5 text-xs font-medium text-destructive">{error}</p>}
    </div>
  );
}
