// Action categories to display in the matrix
export const ACTIONS = [
  { key: "read", label: "Read" },
  { key: "create", label: "Create" },
  { key: "update", label: "Update" },
  { key: "delete", label: "Delete" },
  { key: "execute", label: "Execute" },
  { key: "export", label: "Export" },
  { key: "import", label: "Import" },
  { key: "approve", label: "Approve" },
  { key: "manage", label: "Settings" },
] as const;

// Modules list
export const MODULES = [
  { key: "dashboard", label: "Dashboard" },
  { key: "users", label: "User Management" },
  { key: "roles", label: "RBAC (Roles)" },
  { key: "servers", label: "Infrastructure Inventory" },
  { key: "windows", label: "Active Directory & GPO" },
  { key: "linux", label: "Linux & SSH" },
  { key: "discovery", label: "Network Discovery" },
  { key: "vmware", label: "VMware Virtualization" },
  { key: "hyperv", label: "Hyper-V Virtualization" },
  { key: "automation", label: "Workflows & Automation" },
  { key: "scripts", label: "PowerShell Generator" },
  { key: "alerts", label: "Alerts & Events" },
  { key: "reports", label: "Reports" },
  { key: "settings", label: "System Settings" },
] as const;
