export const STATUS_VARIANTS: Record<string, { label: string; variant: "default" | "muted" | "destructive" | "success" | "warning" }> = {
  pending: { label: "Pending", variant: "muted" },
  processing: { label: "Processing", variant: "warning" },
  indexed: { label: "Indexed", variant: "success" },
  failed: { label: "Failed", variant: "destructive" },
  deleting: { label: "Deleting", variant: "muted" },
};


export const FILE_TYPE_BADGES: Record<string, { label: string; color: string }> = {
  pdf: { label: "PDF", color: "bg-red-500/10 text-red-600 border-red-500/20" },
  docx: { label: "DOCX", color: "bg-blue-500/10 text-blue-600 border-blue-500/20" },
  txt: { label: "TXT", color: "bg-gray-500/10 text-gray-600 border-gray-500/20" },
  md: { label: "MD", color: "bg-purple-500/10 text-purple-600 border-purple-500/20" },
  csv: { label: "CSV", color: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20" },
  html: { label: "HTML", color: "bg-orange-500/10 text-orange-600 border-orange-500/20" },
  ps1: { label: "PS1", color: "bg-cyan-500/10 text-cyan-600 border-cyan-500/20" },
  sh: { label: "SH", color: "bg-green-500/10 text-green-600 border-green-500/20" },
};
