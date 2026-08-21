import Link from "next/link";
import type { Task } from "@ai-infra-copilot/shared-types";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const RESULT_DOT: Record<string, string> = {
  completed: "bg-emerald-500",
  failed: "bg-red-500",
  cancelled: "bg-slate-400",
};

export function RecentAutomationRuns({ tasks, isLoading, isError }: { tasks: Task[]; isLoading: boolean; isError: boolean }) {
  const recent = tasks.slice(0, 4);
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Recent Automation Runs</CardTitle>
        <Link href="/automation" className="text-xs font-semibold text-primary">
          View all →
        </Link>
      </CardHeader>
      <CardContent className="flex flex-col gap-2.5">
        {isLoading && <p className="text-sm text-muted-foreground">Loading...</p>}
        {isError && <p className="text-sm text-muted-foreground">Automation runs aren&apos;t available.</p>}
        {!isLoading && !isError && recent.length === 0 && (
          <p className="text-sm text-muted-foreground">No automation runs yet.</p>
        )}
        {recent.map((task) => (
          <div key={task.id} className="flex items-start gap-2.5 border-t border-border pt-2 first:border-t-0 first:pt-0">
            <span className={`mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full ${RESULT_DOT[task.status] ?? "bg-primary"}`} />
            <div className="min-w-0 flex-1">
              <div className="truncate text-xs font-semibold">{task.type}</div>
              <div className="text-[11px] text-muted-foreground">{task.status}</div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
