import { useGetServersQuery } from "@/features/infrastructure/services/infrastructure-api";
import { useGetTasksQuery, useGetConversationsQuery } from "@/features/dashboard/services/dashboard-api";

export function useDashboardData() {
  const { data: serversData, isLoading: isServersLoading } = useGetServersQuery();
  const { data: tasksData, isLoading: isTasksLoading, isError: isTasksError } = useGetTasksQuery();
  const { data: conversationsData, isLoading: isConversationsLoading, isError: isConversationsError } = useGetConversationsQuery();

  return {
    servers: serversData?.data ?? [],
    isServersLoading,
    tasks: tasksData?.data ?? [],
    isTasksLoading,
    isTasksError,
    conversations: conversationsData?.data ?? [],
    isConversationsLoading,
    isConversationsError,
  };
}
