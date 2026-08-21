import { apiSlice } from "@/store/api-slice";
import type { Server } from "@ai-infra-copilot/shared-types";

export const infrastructureApi = apiSlice.injectEndpoints({
  endpoints: (builder) => ({
    getServers: builder.query<{ data: Server[] }, void>({
      query: () => "/api/v1/servers",
      providesTags: ["Servers"],
    }),
  }),
});

export const { useGetServersQuery } = infrastructureApi;
