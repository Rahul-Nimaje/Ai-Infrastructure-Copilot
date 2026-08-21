"use client";

import { useDashboardData } from "@/features/dashboard/hooks/useDashboardData";
import { buildHealthDistribution, buildOsDistribution, buildStatCards } from "@/features/dashboard/utils/dashboard.utils";
import { StatCards } from "@/features/dashboard/components/StatCards";
import { DistributionChart } from "@/features/dashboard/components/DistributionChart";
import { RecentAutomationRuns } from "@/features/dashboard/components/RecentAutomationRuns";
import { RecentAiConversations } from "@/features/dashboard/components/RecentAiConversations";

const HEALTH_COLOR: Record<string, string> = {
  Healthy: "bg-emerald-500",
  Warning: "bg-amber-500",
  Critical: "bg-red-500",
  Unknown: "bg-slate-400",
};

const OS_COLOR: Record<string, string> = {
  Windows: "bg-primary",
  Linux: "bg-emerald-500",
};

export function DashboardPage() {
  const { servers, isServersLoading, tasks, isTasksLoading, isTasksError, conversations, isConversationsLoading, isConversationsError } =
    useDashboardData();

  if (isServersLoading) {
    return <p className="text-sm text-muted-foreground">Loading...</p>;
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-lg font-semibold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Fleet-wide health across {servers.length} monitored servers</p>
      </div>

      <StatCards cards={buildStatCards(servers)} />

      <div className="grid grid-cols-1 gap-3.5 lg:grid-cols-2">
        <DistributionChart title="Server Health Distribution" rows={buildHealthDistribution(servers)} barColor={(l) => HEALTH_COLOR[l] ?? "bg-primary"} />
        <DistributionChart title="Operating Systems" rows={buildOsDistribution(servers)} barColor={(l) => OS_COLOR[l] ?? "bg-primary"} />
      </div>

      <div className="grid grid-cols-1 gap-3.5 lg:grid-cols-2">
        <RecentAutomationRuns tasks={tasks} isLoading={isTasksLoading} isError={isTasksError} />
        <RecentAiConversations conversations={conversations} isLoading={isConversationsLoading} isError={isConversationsError} />
      </div>
    </div>
  );
}
