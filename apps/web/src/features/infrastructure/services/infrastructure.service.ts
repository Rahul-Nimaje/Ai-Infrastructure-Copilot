import type { Server } from "@ai-infra-copilot/shared-types";

import { apiFetch } from "@/lib/api-client";

export function listServers() {
  return apiFetch<{ data: Server[] }>("/api/v1/servers");
}
