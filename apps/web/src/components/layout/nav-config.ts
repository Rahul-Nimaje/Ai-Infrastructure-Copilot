export interface NavLeaf {
  href: string;
  label: string;
}

export interface NavGroup {
  key: string;
  label: string;
  defaultOpen: boolean;
  items: NavLeaf[];
}

export const TOP_NAV: NavLeaf[] = [{ href: "/dashboard", label: "Dashboard" }];

export const NAV_GROUPS: NavGroup[] = [
  {
    key: "infrastructure",
    label: "Infrastructure",
    defaultOpen: true,
    items: [
      { href: "/infrastructure", label: "Overview" },
      { href: "/inventory", label: "Servers" },
      { href: "/discovery", label: "Network Discovery" },
      { href: "/active-directory", label: "Active Directory" },
      { href: "/group-policy", label: "Group Policy" },
      { href: "/dns", label: "DNS" },
      { href: "/dhcp", label: "DHCP" },
    ],
  },
  {
    key: "identity",
    label: "Identity & Access",
    defaultOpen: true,
    items: [
      { href: "/users", label: "User Management" },
      { href: "/departments", label: "Departments" },
      { href: "/designations", label: "Designations" },
      { href: "/roles", label: "Roles & Permissions" },
    ],
  },
  {
    key: "virtualization",
    label: "Virtualization",
    defaultOpen: false,
    items: [
      { href: "/vmware", label: "VMware" },
      { href: "/hyper-v", label: "Hyper-V" },
    ],
  },
  {
    key: "cloud",
    label: "Cloud",
    defaultOpen: false,
    items: [
      { href: "/aws", label: "AWS" },
      { href: "/azure", label: "Azure" },
      { href: "/gcp", label: "GCP" },
    ],
  },
];

export const BOTTOM_NAV: NavLeaf[] = [
  { href: "/knowledge-base", label: "Knowledge Base" },
  { href: "/event-log-analyzer", label: "Event Log Analyzer" },
  { href: "/powershell-generator", label: "PowerShell Generator" },
  { href: "/automation", label: "Automation" },
  { href: "/alerts", label: "Alerts" },

  { href: "/reports", label: "Reports" },
  { href: "/settings", label: "Settings" },
];


export const AI_CHAT_NAV: NavLeaf = { href: "/ai-chat", label: "AI Chat" };

const ALL_NAV_LEAVES: NavLeaf[] = [
  ...TOP_NAV,
  ...NAV_GROUPS.flatMap((g) => g.items),
  ...BOTTOM_NAV,
  AI_CHAT_NAV,
];

export function navLabelFor(href: string): string | undefined {
  return ALL_NAV_LEAVES.find((leaf) => leaf.href === href)?.label;
}
