import { apiSlice } from "@/store/api-slice";

export interface CredentialItem {
  id: string;
  name: string;
  credential_type: "ssh_password" | "ssh_key" | "winrm" | "snmp_v2c" | "snmp_v3" | string;
  username: string | null;
}

export interface CreateCredentialPayload {
  name: string;
  credential_type: string;
  username: string;
  secret: string;
}

export const credentialsApi = apiSlice.injectEndpoints({
  endpoints: (builder) => ({
    getCredentials: builder.query<CredentialItem[], void>({
      query: () => "/api/v1/credentials",
      transformResponse: (response: { data: CredentialItem[] }) => response.data || [],
      providesTags: ["Credentials"],
    }),
    createCredential: builder.mutation<CredentialItem, CreateCredentialPayload>({
      query: (payload) => ({
        url: "/api/v1/credentials",
        method: "POST",
        body: payload,
      }),
      transformResponse: (response: { data: CredentialItem }) => response.data,
      invalidatesTags: ["Credentials"],
    }),
    deleteCredential: builder.mutation<void, string>({
      query: (credentialId) => ({
        url: `/api/v1/credentials/${credentialId}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Credentials"],
    }),
  }),
});

export const {
  useGetCredentialsQuery,
  useCreateCredentialMutation,
  useDeleteCredentialMutation,
} = credentialsApi;
