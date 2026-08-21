import type { SourceCitation } from "@/features/knowledge-base/types";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "agent_step";
  content: string;
  sources?: SourceCitation[];
}


export interface ProposedAction {
  taskId: string;
  summary: string;
  riskLevel: string;
  explanation: string;
  status: "pending_approval" | "approved" | "rejected" | string;
}
