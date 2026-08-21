import {
  Info,
  Server,
  Monitor,
  Cpu,
  Layers,
  HardDrive,
  Network,
  Package,
  Settings,
  Eye,
  Clock,
  RefreshCw,
  History,
  Activity,
  ShieldCheck,
  Zap,
  Radar,
  type LucideIcon,
} from "lucide-react";

// ─── Device detail drawer tabs ────────────────────────────────
// Order matches the full-inventory-scan spec's required tab list exactly.
export interface DeviceTab {
  id: string;
  label: string;
  icon: LucideIcon;
}

export const DEVICE_DETAIL_TABS: DeviceTab[] = [
  { id: "overview", label: "Overview", icon: Info },
  { id: "hardware", label: "Hardware", icon: Server },
  { id: "cpu", label: "CPU", icon: Cpu },
  { id: "memory", label: "Memory", icon: Layers },
  { id: "storage", label: "Storage", icon: HardDrive },
  { id: "os", label: "Operating System", icon: Monitor },
  { id: "network", label: "Network", icon: Network },
  { id: "software", label: "Software", icon: Package },
  { id: "services", label: "Services", icon: Settings },
  { id: "processes", label: "Processes", icon: Activity },
  { id: "ports", label: "Ports", icon: Eye },
  { id: "security", label: "Security", icon: ShieldCheck },
  { id: "scan_history", label: "Scan History", icon: Clock },
  { id: "ip_history", label: "IP History", icon: RefreshCw },
  { id: "inventory_history", label: "Inventory History", icon: History },
];

// ─── Device type filter options ───────────────────────────────
export const DEVICE_TYPE_OPTIONS = [
  { value: "", label: "All Types" },
  { value: "Server", label: "Server" },
  { value: "Switch", label: "Switch" },
  { value: "Router", label: "Router" },
  { value: "Firewall", label: "Firewall" },
  { value: "Workstation", label: "Workstation" },
  { value: "Printer", label: "Printer" },
] as const;

// ─── Scan mode buttons (section 12) — wire value matches backend ScanMode ──
export interface ScanModeOption {
  value: "quick" | "standard" | "full";
  label: string;
  description: string;
  icon: LucideIcon;
}

export const SCAN_MODE_OPTIONS: ScanModeOption[] = [
  { value: "quick", label: "Quick Scan", description: "IP, hostname, MAC, vendor, status only", icon: Zap },
  { value: "standard", label: "Standard Scan", description: "+ OS, open ports, services", icon: Radar },
  { value: "full", label: "Full Scan", description: "+ hardware, software, security, processes", icon: ShieldCheck },
];

// ─── Scan status filter options (device.scan_status) ──────────
export const SCAN_STATUS_FILTER_OPTIONS = [
  { value: "", label: "All Scan Statuses" },
  { value: "discovered", label: "Discovered" },
  { value: "identifying", label: "Identifying" },
  { value: "scanning", label: "Scanning" },
  { value: "completed", label: "Completed" },
  { value: "partial", label: "Partial" },
  { value: "failed", label: "Failed" },
  { value: "credentials_required", label: "Credentials Required" },
  { value: "offline", label: "Offline" },
] as const;

// ─── Port labels ──────────────────────────────────────────────
export const PORT_LABELS: Record<number, string> = {
  21: "FTP",
  22: "SSH",
  23: "Telnet",
  25: "SMTP",
  53: "DNS",
  80: "HTTP",
  110: "POP3",
  139: "NetBIOS",
  143: "IMAP",
  443: "HTTPS",
  445: "SMB",
  3389: "RDP",
  5985: "WinRM HTTP",
  5986: "WinRM HTTPS",
  8080: "Proxy",
};

// ─── Dangerous ports (shown in red) ───────────────────────────
export const DANGEROUS_PORTS = new Set([23, 139, 445]);

// ─── Device icon class map (device_type → tailwind color) ─────
export const DEVICE_ICON_COLOR: Record<string, string> = {
  server: "text-indigo-500",
  printer: "text-emerald-500",
  switch: "text-amber-500",
  router: "text-amber-500",
  firewall: "text-amber-500",
  workstation: "text-blue-500",
};

// ─── Default subnet / scan mode ───────────────────────────────
export const DEFAULT_TARGET_RANGE = "10.20.4.0/24";
export const DEFAULT_SCAN_MODE = "standard" as const;
