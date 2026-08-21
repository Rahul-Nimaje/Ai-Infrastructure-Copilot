// Socket.IO event payloads. Room/event names match docs/02-HLD.md Section 10
// so extracting this into a standalone notification-gateway later is a no-op for clients.

export interface TaskProgressEvent {
  task_id: string;
  status: string;
  detail?: string;
}

export interface ApprovalRequestedEvent {
  task_id: string;
  summary: string;
  risk_level: "low" | "medium" | "high";
  target_server_id: string | null;
}

export interface ApprovalResolvedEvent {
  task_id: string;
  decision: "approved" | "rejected";
  status: string;
}

export interface AgentStepEvent {
  stage: string;
  detail: string;
}

export interface TokenEvent {
  delta: string;
}

export type ServerToClientEvents = {
  "task.progress": TaskProgressEvent;
  "approval.requested": ApprovalRequestedEvent;
  "approval.resolved": ApprovalResolvedEvent;
};
