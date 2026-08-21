import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { useToastMutation } from "./useToastMutation";

export function useAiChat() {
  const queryClient = useQueryClient();

  const createConversation = useMutation({
    mutationFn: () =>
      apiFetch<{ data: { id: string } }>("/api/v1/ai/conversations", {
        method: "POST",
        body: {},
      }),
  });

  const approveTask = useToastMutation<any, any, string>({
    mutationFn: (taskId: string) =>
      apiFetch(`/api/v1/tasks/${taskId}/approve`, {
        method: "POST",
        body: {},
      }),
    invalidateKeys: [["tasks"]],
    successTitle: "Task Approved",
    successDescription: "Task approved and scheduled for background execution.",
    errorTitle: "Approval Failed",
  });

  const rejectTask = useToastMutation<any, any, string>({
    mutationFn: (taskId: string) =>
      apiFetch(`/api/v1/tasks/${taskId}/reject`, {
        method: "POST",
        body: { reason: "Rejected from AI Chat" },
      }),
    successTitle: "Task Rejected",
    successDescription: "Task has been rejected.",
    errorTitle: "Rejection Failed",
  });

  return {
    createConversation,
    approveTask,
    rejectTask,
  };
}
