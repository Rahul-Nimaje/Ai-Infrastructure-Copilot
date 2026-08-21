import { apiSlice } from "@/store/api-slice";

export const authApi = apiSlice.injectEndpoints({
  endpoints: (builder) => ({
    login: builder.mutation<any, any>({
      query: (credentials) => ({
        url: "/api/v1/auth/login",
        method: "POST",
        body: credentials,
      }),
    }),
    verifyMfa: builder.mutation<any, any>({
      query: (data) => ({
        url: "/api/v1/auth/mfa/verify",
        method: "POST",
        body: data,
      }),
    }),
  }),
});

export const { useLoginMutation, useVerifyMfaMutation } = authApi;
