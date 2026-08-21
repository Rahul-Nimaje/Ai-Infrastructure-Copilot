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

// Section 9/12 of the full-inventory-scan feature — device inventory
// lifecycle and scan depth, distinct from Device.status (online/offline
// reachability).
export type DeviceScanStatus =
  | "discovered"
  | "identifying"
  | "scanning"
  | "completed"
  | "partial"
  | "failed"
  | "credentials_required"
  | "offline";

export type ScanMode = "quick" | "standard" | "full";

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
  auth_success: boolean;
  auth_error: string | null;
  scan_status: DeviceScanStatus | null;
  identification_confidence: "confirmed" | "unverified" | "unknown" | null;
  identification_method: string | null;
  needs_credentials: boolean;
  created_at: string;
  updated_at: string;
}

export interface DeviceScan {
  id: string;
  organization_id: string;
  status: "pending" | "discovering" | "identifying" | "scanning" | "completed" | "partial" | "failed" | "credentials_required" | "cancelled";
  scan_type: ScanMode | string;
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

// ─── Full inventory scan detail entities (device detail drawer tabs) ──────

export interface DeviceInventoryProfile {
  computer_name: string | null;
  manufacturer: string | null;
  model: string | null;
  serial_number: string | null;
  bios_version: string | null;
  motherboard: string | null;
  domain: string | null;
  workgroup: string | null;
  os_name: string | null;
  os_edition: string | null;
  os_build: string | null;
  os_version: string | null;
  os_install_date: string | null;
  os_last_boot: string | null;
  os_timezone: string | null;
  antivirus: string | null;
  bitlocker_status: string | null;
  firewall_status: string | null;
  uptime: string | null;
}

export interface DeviceProcessorInfo {
  id: string;
  processor_name: string | null;
  architecture: string | null;
  cores: number | null;
  logical_processors: number | null;
  current_speed_mhz: number | null;
  max_speed_mhz: number | null;
  socket_designation: string | null;
}

export interface DeviceMemoryInfo {
  id: string;
  total_ram_bytes: number | null;
  available_ram_bytes: number | null;
  memory_slots: number | null;
  ram_modules: { slot: string | null; manufacturer: string | null; capacity: string | number | null; speed_mhz: string | number | null }[] | null;
  configured_speed_mhz: number | null;
}

export interface DevicePartitionInfo {
  id: string;
  mount_point: string | null;
  device_node: string | null;
  filesystem_type: string | null;
  label: string | null;
  capacity_bytes: number | null;
  used_bytes: number | null;
  free_space_bytes: number | null;
}

export interface DeviceStorageInfo {
  id: string;
  disk_model: string | null;
  serial_number: string | null;
  capacity_bytes: number | null;
  free_space_bytes: number | null;
  partitions: { name: string; size_bytes: number }[] | null;
  interface_type: string | null;
  media_type: string | null;
  health_status: string | null;
}

export interface DeviceNetworkInterfaceInfo {
  id: string;
  interface_name: string;
  mac_address: string | null;
  ip_addresses: string[] | null;
  dns_servers: string[] | null;
  gateway: string | null;
  dhcp_enabled: boolean | null;
  status: string | null;
  speed_mbps: number | null;
  duplex: string | null;
  interface_type: string | null;
}

export interface DeviceHardwareProfile {
  inventory: DeviceInventoryProfile | null;
  processors: DeviceProcessorInfo[];
  memory: DeviceMemoryInfo[];
  storage: DeviceStorageInfo[];
  interfaces: DeviceNetworkInterfaceInfo[];
  partitions: DevicePartitionInfo[];
}

export interface DeviceInstalledSoftwareInfo {
  id: string;
  name: string;
  version: string | null;
  publisher: string | null;
  install_date: string | null;
}

export interface DeviceServiceInfo {
  id: string;
  name: string;
  display_name: string | null;
  status: string | null;
  start_type: string | null;
}

export interface DeviceSoftwareProfile {
  installed_software: DeviceInstalledSoftwareInfo[];
  services: DeviceServiceInfo[];
}

export interface DeviceProcess {
  id: string;
  pid: number;
  name: string;
  command_line: string | null;
  user_name: string | null;
  cpu_percent: number | null;
  memory_bytes: number | null;
  status: string | null;
  collected_at: string;
}

export interface DeviceSecurityPosture {
  id: string;
  defender_enabled: boolean | null;
  defender_signature_version: string | null;
  firewall_enabled: boolean | null;
  firewall_profiles: Record<string, boolean> | null;
  bitlocker_status: string | null;
  secure_boot_enabled: boolean | null;
  antivirus_product: string | null;
  antivirus_up_to_date: boolean | null;
  pending_updates_count: number | null;
  last_update_installed_at: string | null;
  selinux_status: string | null;
  apparmor_status: string | null;
  ufw_active: boolean | null;
  iptables_rule_count: number | null;
  ssh_root_login_enabled: boolean | null;
  ssh_password_auth_enabled: boolean | null;
  collected_at: string;
}

export interface DevicePortInfo {
  id: string;
  port_number: number;
  protocol: string;
  service_name: string | null;
  product: string | null;
  version: string | null;
  state: string;
  first_seen_at: string;
  last_seen_at: string;
}

export interface DeviceHistoryBundle {
  ip_history: { id: string; old_ip: string | null; new_ip: string; changed_at: string }[];
  scan_history: { id: string; status: string; response_time: number | null; created_at: string }[];
  inventory_history: { id: string; change_type: string; component: string; description: string; created_at: string }[];
}
