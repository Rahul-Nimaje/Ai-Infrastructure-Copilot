// Mirrors the Phase 1 subset of docs/04-database-design.md Section 5.
// Field names match the API responses in docs/05-api-design.md exactly.

export type OrgPlanTier = "starter" | "professional" | "enterprise";
export type OrgStatus = "trial" | "active" | "suspended" | "cancelled";

export interface Organization {
  id: string;
  name: string;
  slug: string;
  plan_tier: OrgPlanTier;
  status: OrgStatus;
  created_at: string;
}

export type UserStatus = "invited" | "active" | "disabled";

export interface User {
  id: string;
  organization_id: string;
  email: string;
  username: string | null;
  full_name: string;
  status: UserStatus;
  employee_id: string | null;
  phone_number: string | null;
  department: string | null;
  designation: string | null;
  profile_picture: string | null;
  mfa_enabled: boolean;
  roles: string[];
  created_by_id: string | null;
  updated_by_id: string | null;
  last_login_at: string | null;
  created_at: string;
}

export interface Role {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  is_system_role: boolean;
}

export interface Permission {
  id: string;
  code: string;
  module: string;
  description: string | null;
}

export type OsType = "windows" | "linux";
export type ServerEnvironment = "production" | "staging" | "development";
export type HealthStatus = "healthy" | "warning" | "critical" | "unknown";

export interface Server {
  id: string;
  organization_id: string;
  hostname: string;
  ip_address: string | null;
  os_type: OsType;
  os_version: string | null;
  environment: ServerEnvironment;
  credential_id: string | null;
  winrm_port: number;
  winrm_use_ssl: boolean;
  health_status: HealthStatus;
  cpu_usage_pct: number | null;
  memory_usage_pct: number | null;
  disk_usage_pct: number | null;
  open_alerts_count: number;
  last_seen_at: string | null;
  tags: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export type CredentialType = "winrm" | "ssh_password" | "ssh_key" | "api_key" | "cloud_iam";

export interface Credential {
  id: string;
  organization_id: string;
  name: string;
  credential_type: CredentialType;
  created_at: string;
}

export type ScriptLanguage = "powershell" | "bash" | "python";
export type RiskLevel = "low" | "medium" | "high";

export interface Script {
  id: string;
  organization_id: string;
  name: string;
  language: ScriptLanguage;
  category: string | null;
  content: string;
  version: number;
  risk_level: RiskLevel;
  is_ai_generated: boolean;
  is_approved_template: boolean;
  created_at: string;
  updated_at: string;
}

export type TaskType = "script_execution" | "workflow_step" | "remediation";
export type TaskStatus =
  | "pending_approval"
  | "approved"
  | "rejected"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "execution_skipped_flagged_off";
export type ExecutionMethod = "winrm" | "ssh";

export interface Task {
  id: string;
  organization_id: string;
  type: TaskType;
  status: TaskStatus;
  target_server_id: string | null;
  script_id: string | null;
  execution_method: ExecutionMethod | null;
  payload: Record<string, unknown>;
  result: Record<string, unknown> | null;
  requires_approval: boolean;
  requested_by_user_id: string | null;
  requested_by_ai: boolean;
  approved_by_user_id: string | null;
  approved_at: string | null;
  rejected_reason: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export type EventLogChannel = "Application" | "System" | "Security";
export type EventLogLevel = "Information" | "Warning" | "Error" | "Critical";

export interface EventLogEntry {
  id: number;
  organization_id: string;
  server_id: string;
  log_channel: EventLogChannel;
  event_id: number;
  level: EventLogLevel;
  source_provider: string | null;
  message: string | null;
  occurred_at: string;
}

export type ConversationStatus = "active" | "archived";

export interface AiConversation {
  id: string;
  organization_id: string;
  user_id: string;
  title: string | null;
  module_context: string | null;
  status: ConversationStatus;
  last_message_at: string | null;
  created_at: string;
}

export type MessageRole = "user" | "assistant" | "system" | "tool";

export interface AiMessage {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  referenced_task_id: string | null;
  model_used: string | null;
  created_at: string;
}

export interface Device {
  id: string;
  organization_id: string;
  device_type: string;
  name: string;
  ip_address: string | null;
  mac_address: string | null;
  vendor: string | null;
  model: string | null;
  operating_system: string | null;
  status: string;
  last_seen_at: string | null;
  first_seen_at: string;
  scan_timestamp: string | null;
  response_time: number | null;
  open_ports: { ports: number[] } | null;
  network_interface: string | null;
  created_at: string;
  updated_at: string;
}

export interface DeviceScan {
  id: string;
  organization_id: string;
  status: "pending" | "running" | "completed" | "failed";
  scan_type: string;
  target_range: string | null;
  started_at: string | null;
  completed_at: string | null;
  devices_found: number;
  created_by_id: string | null;
  error_message: string | null;
  created_at: string;
}

export interface DeviceHistory {
  id: string;
  organization_id: string;
  device_id: string;
  event_type: string;
  description: string | null;
  before_state: Record<string, any> | null;
  after_state: Record<string, any> | null;
  created_at: string;
}
