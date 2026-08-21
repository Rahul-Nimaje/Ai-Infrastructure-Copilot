// Centralised route path constants.
// Import these instead of hardcoding "/dashboard" etc. in components.

export const ROUTES = {
  LOGIN: "/login",
  DASHBOARD: "/dashboard",

  // Infrastructure
  INFRASTRUCTURE: "/infrastructure",
  INVENTORY: "/inventory",
  DISCOVERY: "/discovery",
  ACTIVE_DIRECTORY: "/active-directory",
  GROUP_POLICY: "/group-policy",
  DNS: "/dns",
  DHCP: "/dhcp",

  // Identity & Access
  USERS: "/users",
  DEPARTMENTS: "/departments",
  DESIGNATIONS: "/designations",
  ROLES: "/roles",

  // Virtualization
  VMWARE: "/vmware",
  HYPER_V: "/hyper-v",

  // Cloud
  AWS: "/aws",
  AZURE: "/azure",
  GCP: "/gcp",

  // Tools
  EVENT_LOG_ANALYZER: "/event-log-analyzer",
  POWERSHELL_GENERATOR: "/powershell-generator",
  AUTOMATION: "/automation",
  ALERTS: "/alerts",
  REPORTS: "/reports",
  SETTINGS: "/settings",
  AI_CHAT: "/ai-chat",
} as const;

export type AppRoute = (typeof ROUTES)[keyof typeof ROUTES];
