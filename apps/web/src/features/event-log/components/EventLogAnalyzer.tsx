"use client";

import { useSearchParams } from "next/navigation";
import type { EventLogEntry } from "@ai-infra-copilot/shared-types";
import { RefreshCw, FileText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/common";
import { useEventLog } from "@/hooks";
import type { EventLevel } from "../types";
import { LOG_LEVEL_VARIANTS } from "../utils/constants";

function levelVariant(level: string): EventLevel {
  const norm = level.toLowerCase();
  return (LOG_LEVEL_VARIANTS as any)[norm] || "default";
}

export function EventLogAnalyzer() {
  const params = useSearchParams();
  const serverId = params.get("serverId");
  const hostname = params.get("hostname");

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={hostname ? `Event Logs — ${hostname}` : "Event Log Analyzer"}
        description="Inspect operating system event diagnostics, service alerts, and audit logs."
      />

      {!serverId ? (
        <Card className="border border-dashed border-border/80 p-8 flex flex-col items-center justify-center text-center">
          <FileText className="h-8 w-8 text-muted-foreground/60 mb-2" />
          <h3 className="text-sm font-bold">No host selected</h3>
          <p className="text-xs text-muted-foreground max-w-xs mt-1">
            Pick a server host from your Infrastructure Inventory page to review its real-time event logs.
          </p>
        </Card>
      ) : (
        <EventList serverId={serverId} />
      )}
    </div>
  );
}

function EventList({ serverId }: { serverId: string }) {
  const { events, isEventsLoading, isEventsFetching, syncEvents } = useEventLog(serverId);

  const handleSync = () => {
    syncEvents.mutate();
  };

  const syncResponse = syncEvents.data;
  const syncNotice = syncResponse && !syncResponse.data.synced ? syncResponse.data.reason ?? "Sync skipped." : null;

  return (
    <Card className="border border-border/60 shadow-sm bg-card/60 backdrop-blur-md">
      <CardHeader className="pb-3 border-b border-border/40">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
            <FileText className="h-4 w-4 text-primary" />
            Recent Windows System Events
          </CardTitle>
          <Button
            size="sm"
            variant="outline"
            className="h-8 text-xs font-bold gap-1.5"
            disabled={syncEvents.isPending || isEventsFetching}
            onClick={handleSync}
          >
            <RefreshCw className={`h-3 w-3 ${syncEvents.isPending || isEventsFetching ? "animate-spin" : ""}`} />
            {syncEvents.isPending ? "Refreshing..." : "Refresh Logs"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="pt-6 flex flex-col gap-4">
        {syncNotice && (
          <div className="rounded-lg border border-border bg-muted/60 p-3 text-xs font-medium text-muted-foreground">
            {syncNotice}
          </div>
        )}

        {isEventsLoading ? (
          <p className="text-sm text-muted-foreground animate-pulse py-8 text-center">Loading system logs...</p>
        ) : events.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">No event log entries found for this server.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {events.map((entry: EventLogEntry) => (
              <li
                key={entry.id}
                className="rounded-lg border border-border/60 bg-background/50 hover:bg-background/80 transition-colors p-4 flex flex-col gap-2"
              >
                <div className="flex items-start justify-between gap-4">
                  <span className="text-sm font-semibold text-foreground">
                    {entry.log_channel} #{entry.event_id} — {entry.source_provider}
                  </span>
                  <Badge variant={levelVariant(entry.level)} className="capitalize shrink-0">
                    {entry.level}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground font-mono leading-relaxed bg-muted/30 rounded border border-border/20 p-2 overflow-x-auto whitespace-pre-wrap">
                  {entry.message}
                </p>
                <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
                  {new Date(entry.occurred_at).toLocaleString()}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
