import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { Script } from "@ai-infra-copilot/shared-types";
import { useToastMutation } from "./useToastMutation";

export function usePowerShell() {
  const scriptsQuery = useQuery({
    queryKey: ["scripts"],
    queryFn: () => apiFetch<{ data: Script[] }>("/api/v1/scripts"),
  });

  const generateScript = useToastMutation<{ data: Script }, any, { description: string }>({
    mutationFn: ({ description }) =>
      apiFetch<{ data: Script }>("/api/v1/scripts/generate", {
        method: "POST",
        body: { description, language: "powershell" },
      }),
    invalidateKeys: [["scripts"]],
    successTitle: "Script Generated",
    successDescription: "PowerShell script generated successfully.",
    errorTitle: "Generation Failed",
  });

  const executeScript = useToastMutation<
    { data: { task_id: string; status: string } },
    any,
    { scriptId: string; targetServerId: string }
  >({
    mutationFn: ({ scriptId, targetServerId }) =>
      apiFetch<{ data: { task_id: string; status: string } }>(`/api/v1/scripts/${scriptId}/execute`, {
        method: "POST",
        body: { target_server_id: targetServerId },
      }),
    successTitle: "Execution Requested",
    successDescription: "Script execution task created successfully.",
    errorTitle: "Execution Failed",
  });

  return {
    scripts: scriptsQuery.data?.data || [],
    isScriptsLoading: scriptsQuery.isLoading,
    generateScript,
    executeScript,
  };
}
