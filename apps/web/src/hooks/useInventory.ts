import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { useToastMutation } from "./useToastMutation";

export function useInventory() {
  const serversQuery = useQuery({
    queryKey: ["servers"],
    queryFn: () => apiFetch<{ data: any[] }>("/api/v1/servers"),
  });

  const registerServer = useToastMutation<any, any, any>({
    mutationFn: async (form: {
      hostname: string;
      ipAddress?: string;
      osVersion?: string;
      username: string;
      secret: string;
      winrmUseSsl: boolean;
      winrmPort: string | number;
    }) => {
      const credential = await apiFetch<{ data: { id: string } }>("/api/v1/credentials", {
        method: "POST",
        body: {
          name: `${form.hostname}-winrm`,
          credential_type: "winrm",
          username: form.username,
          secret: form.secret,
        },
      });
      return apiFetch("/api/v1/servers", {
        method: "POST",
        body: {
          hostname: form.hostname,
          ip_address: form.ipAddress || null,
          os_type: "windows",
          os_version: form.osVersion || null,
          environment: "production",
          credential_id: credential.data.id,
          winrm_port: Number(form.winrmPort),
          winrm_use_ssl: form.winrmUseSsl,
        },
      });
    },
    invalidateKeys: [["servers"]],
    successTitle: "Server Registered",
    successDescription: "Successfully registered new Windows server.",
    errorTitle: "Error Registering Server",
  });

  const detachServer = useToastMutation<any, any, string>({
    mutationFn: (serverId: string) => apiFetch(`/api/v1/servers/${serverId}`, { method: "DELETE" }),
    invalidateKeys: [["servers"]],
    successTitle: "Server Detached",
    successDescription: "Successfully detached server from inventory.",
    errorTitle: "Error Detaching Server",
  });

  const scanNetwork = useToastMutation<any, any, string>({
    mutationFn: (cidr: string) =>
      apiFetch<{ data: any[] }>("/api/v1/inventory/scan", {
        method: "POST",
        body: { cidr },
      }),
    successTitle: "Scan Completed",
    successDescription: "Network discovery scan finished successfully.",
    errorTitle: "Scan Failed",
  });

  return {
    servers: serversQuery.data?.data || [],
    isServersLoading: serversQuery.isLoading,
    registerServer,
    detachServer,
    scanNetwork,
  };
}
