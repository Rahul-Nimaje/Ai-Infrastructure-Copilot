import type { AiConversation, Server, Task } from "@ai-infra-copilot/shared-types";

import { apiFetch } from "@/lib/api-client";

export function listServers() {
  return apiFetch<{ data: Server[] }>("/api/v1/servers");
}

export function listTasks() {
  return apiFetch<{ data: Task[] }>("/api/v1/tasks");
}

export function listConversations() {
  return apiFetch<{ data: AiConversation[] }>("/api/v1/ai/conversations");
}
