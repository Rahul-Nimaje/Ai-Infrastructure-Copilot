import { apiSlice } from "@/store/api-slice";
import type { AiConversation, Task } from "@ai-infra-copilot/shared-types";

export const dashboardApi = apiSlice.injectEndpoints({
  endpoints: (builder) => ({
    getTasks: builder.query<{ data: Task[] }, void>({
      query: () => "/api/v1/tasks",
      providesTags: ["Tasks"],
    }),
    getConversations: builder.query<{ data: AiConversation[] }, void>({
      query: () => "/api/v1/ai/conversations",
      providesTags: ["Conversations"],
    }),
  }),
});

export const { useGetTasksQuery, useGetConversationsQuery } = dashboardApi;
