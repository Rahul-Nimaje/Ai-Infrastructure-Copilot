"use client";

import { useState } from "react";
import { UploadCloud } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { FileUpload } from "@/components/common";
import { useKnowledgeBase } from "@/hooks";

export function DocumentUploadDialog() {
  const [open, setOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [tags, setTags] = useState("");

  const { uploadDocument } = useKnowledgeBase();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    uploadDocument.mutate(
      { file: selectedFile, title, department, tags },
      {
        onSuccess: () => {
          setOpen(false);
          setSelectedFile(null);
          setTitle("");
          setDepartment("");
          setTags("");
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="font-bold bg-primary hover:bg-primary/95 text-primary-foreground gap-2">
          <UploadCloud className="h-4 w-4" />
          Upload Document
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle className="text-lg font-bold">Upload Infrastructure Knowledge Document</DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            Upload SOPs, architecture guidelines, configuration guides, or troubleshooting runbooks (PDF, DOCX, TXT, MD, CSV, HTML, PS1, SH).
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          <FileUpload
            file={selectedFile}
            onFileSelect={(file) => {
              setSelectedFile(file);
              if (file && !title) {
                setTitle(file.name.replace(/\.[^/.]+$/, ""));
              }
            }}
            accept=".pdf,.docx,.txt,.md,.csv,.html,.ps1,.sh"
            maxSizeMB={50}
            helperText="Supports PDF, DOCX, Markdown, Text, CSV, HTML, PowerShell (.ps1), Bash (.sh) up to 50MB"
          />

          <div className="space-y-1.5">
            <Label className="text-xs font-semibold">Document Title</Label>
            <Input
              placeholder="e.g. IIS Troubleshooting SOP"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="text-xs h-9"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Department (Optional)</Label>
              <Input
                placeholder="e.g. IT Operations"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="text-xs h-9"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Tags (Comma-separated)</Label>
              <Input
                placeholder="e.g. windows, iis, runbook"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                className="text-xs h-9"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-border">
            <Button type="button" variant="outline" size="sm" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={!selectedFile || uploadDocument.isPending}
              className="font-bold bg-primary hover:bg-primary/95 text-primary-foreground"
            >
              {uploadDocument.isPending ? "Uploading..." : "Start Ingestion"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
