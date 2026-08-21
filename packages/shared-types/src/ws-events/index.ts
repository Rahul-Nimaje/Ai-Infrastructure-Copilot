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

// Network Discovery / Full Inventory Scan — live progress (section 11).
// Payloads are deliberately minimal (ids, counts, name) — full device detail
// is fetched via the REST API, these are just progress pings.

export interface ScanProgressEvent {
  scan_id: string;
  phase: "discovering" | "identifying" | "scanning" | string;
  devices_total: number;
  devices_processed: number;
}

export interface ScanCompletedEvent {
  scan_id: string;
  status: string;
}

export interface DeviceProgressEvent {
  scan_id: string | null;
  device_id: string;
  device_name?: string | null;
  status: string;
}

export type ServerToClientEvents = {
  "task.progress": TaskProgressEvent;
  "approval.requested": ApprovalRequestedEvent;
  "approval.resolved": ApprovalResolvedEvent;
  "discovery.scan.progress": ScanProgressEvent;
  "discovery.scan.completed": ScanCompletedEvent;
  "discovery.device.progress": DeviceProgressEvent;
};
