import type { Server } from "@ai-infra-copilot/shared-types";

import type { InfrastructureCategory } from "@/features/infrastructure/types";

function avg(values: number[]): number {
  if (!values.length) return 0;
  return Math.round(values.reduce((sum, v) => sum + v, 0) / values.length);
}

function buildRealCategory(key: string, name: string, servers: Server[]): InfrastructureCategory {
  const numeric = (pick: (s: Server) => number | null) => servers.map(pick).filter((v): v is number => v !== null);
  return {
    kind: "real",
    key,
    name,
    count: servers.length,
    cpu: avg(numeric((s) => s.cpu_usage_pct)),
    mem: avg(numeric((s) => s.memory_usage_pct)),
    disk: avg(numeric((s) => s.disk_usage_pct)),
    healthy: servers.filter((s) => s.health_status === "healthy").length,
    warning: servers.filter((s) => s.health_status === "warning").length,
    critical: servers.filter((s) => s.health_status === "critical").length,
    href: "/inventory",
  };
}

const UNBACKED_CATEGORIES: { key: string; name: string }[] = [
  { key: "cloud", name: "Cloud (AWS / Azure / GCP)" },
  { key: "vmware", name: "VMware vSphere" },
  { key: "hyperv", name: "Hyper-V Hosts" },
  { key: "network", name: "Network Devices" },
  { key: "storage", name: "Storage Arrays" },
];

export function buildInfrastructureCategories(servers: Server[]): InfrastructureCategory[] {
  const windows = servers.filter((s) => s.os_type === "windows");
  const linux = servers.filter((s) => s.os_type === "linux");

  return [
    buildRealCategory("windows", "Windows Servers", windows),
    buildRealCategory("linux", "Linux Servers", linux),
    ...UNBACKED_CATEGORIES.map(({ key, name }): InfrastructureCategory => ({ kind: "placeholder", key, name })),
  ];
}
