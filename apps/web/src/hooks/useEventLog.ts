import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { EventLogEntry } from "@ai-infra-copilot/shared-types";
import { useToastMutation } from "./useToastMutation";

export function useEventLog(serverId: string | null) {
  const query = useQuery({
    queryKey: ["events", serverId],
    queryFn: () => {
      if (!serverId) return { data: [] };
      return apiFetch<{ data: EventLogEntry[] }>(`/api/v1/servers/${serverId}/events`);
    },
    enabled: !!serverId,
  });

  const syncEvents = useToastMutation<{ data: { synced: boolean; reason?: string } }, any, void>({
    mutationFn: () => {
      if (!serverId) throw new Error("Server ID is required to sync events");
      return apiFetch<{ data: { synced: boolean; reason?: string } }>(
        `/api/v1/servers/${serverId}/events/sync`,
        { method: "POST" }
      );
    },
    invalidateKeys: [["events", serverId]],
    successTitle: "Logs Synchronized",
    successDescription: (res) => (res.data.synced ? "Event logs updated." : res.data.reason ?? "Sync skipped."),
    errorTitle: "Sync Failed",
  });

  return {
    events: query.data?.data || [],
    isEventsLoading: query.isLoading,
    isEventsFetching: query.isFetching,
    syncEvents,
  };
}
