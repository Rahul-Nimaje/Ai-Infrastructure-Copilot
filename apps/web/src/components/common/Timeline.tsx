import { Badge } from "@/components/ui/badge";
import type { BadgeProps } from "@/components/ui/badge";

interface TimelineEvent {
  id: string;
  content: React.ReactNode;
  timestamp: string | Date;
  badge?: {
    label: string;
    variant?: BadgeProps["variant"];
  };
}

interface TimelineProps {
  events: TimelineEvent[];
  emptyMessage?: string;
  loading?: boolean;
  loadingMessage?: string;
}

export function Timeline({
  events,
  emptyMessage = "No events recorded.",
  loading = false,
  loadingMessage = "Loading timeline...",
}: TimelineProps) {
  if (loading) {
    return (
      <p className="text-xs text-muted-foreground animate-pulse">{loadingMessage}</p>
    );
  }

  if (events.length === 0) {
    return (
      <div className="p-8 rounded-lg border border-border bg-muted/20 text-center text-xs text-muted-foreground">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="relative pl-4 border-l border-border space-y-4">
      {events.map((event) => {
        const dateStr =
          typeof event.timestamp === "string"
            ? new Date(event.timestamp).toLocaleString()
            : event.timestamp.toLocaleString();

        return (
          <div key={event.id} className="relative text-xs space-y-1">
            <span className="absolute -left-[21px] top-1.5 flex h-2 w-2 rounded-full bg-primary" />
            <div className="flex items-center justify-between">
              {event.badge ? (
                <Badge
                  variant={event.badge.variant ?? "muted"}
                  className="text-[9px] py-0 px-1 font-mono uppercase tracking-wide border border-border"
                >
                  {event.badge.label}
                </Badge>
              ) : (
                <div />
              )}
              <span className="text-[10px] text-muted-foreground">{dateStr}</span>
            </div>
            <div className="text-foreground">{event.content}</div>
          </div>
        );
      })}
    </div>
  );
}
