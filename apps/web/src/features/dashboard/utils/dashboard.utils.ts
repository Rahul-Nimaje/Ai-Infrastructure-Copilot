import type { Server } from "@ai-infra-copilot/shared-types";

import type { DistributionRow, StatCard } from "@/features/dashboard/types";

function avg(values: number[]): number {
  if (!values.length) return 0;
  return Math.round(values.reduce((sum, v) => sum + v, 0) / values.length);
}

export function buildStatCards(servers: Server[]): StatCard[] {
  const healthy = servers.filter((s) => s.health_status === "healthy").length;
  const critical = servers.filter((s) => s.health_status === "critical").length;
  const cpuAvg = avg(servers.map((s) => s.cpu_usage_pct).filter((v): v is number => v !== null));
  const ramAvg = avg(servers.map((s) => s.memory_usage_pct).filter((v): v is number => v !== null));
  const diskAvg = avg(servers.map((s) => s.disk_usage_pct).filter((v): v is number => v !== null));

  return [
    { label: "Total Servers", value: String(servers.length), delta: "across all environments" },
    {
      label: "Healthy Servers",
      value: String(healthy),
      delta: servers.length ? `${Math.round((healthy / servers.length) * 100)}% of fleet` : "no servers yet",
    },
    { label: "Critical Servers", value: String(critical), delta: critical > 0 ? "needs attention" : "all clear" },
    { label: "CPU Usage (avg)", value: `${cpuAvg}%`, delta: "fleet average" },
    { label: "RAM Usage (avg)", value: `${ramAvg}%`, delta: "fleet average" },
    { label: "Disk Usage (avg)", value: `${diskAvg}%`, delta: "fleet average" },
  ];
}

export function buildHealthDistribution(servers: Server[]): DistributionRow[] {
  const total = servers.length || 1;
  const statuses: Server["health_status"][] = ["healthy", "warning", "critical", "unknown"];
  return statuses.map((status) => {
    const count = servers.filter((s) => s.health_status === status).length;
    return { label: status[0].toUpperCase() + status.slice(1), count, pct: (count / total) * 100 };
  });
}

export function buildOsDistribution(servers: Server[]): DistributionRow[] {
  const total = servers.length || 1;
  const windows = servers.filter((s) => s.os_type === "windows").length;
  const linux = servers.filter((s) => s.os_type === "linux").length;
  return [
    { label: "Windows", count: windows, pct: (windows / total) * 100 },
    { label: "Linux", count: linux, pct: (linux / total) * 100 },
  ];
}
