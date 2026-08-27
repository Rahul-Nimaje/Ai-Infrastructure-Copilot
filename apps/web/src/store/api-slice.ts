import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import type { BaseQueryFn, FetchArgs, FetchBaseQueryError } from "@reduxjs/toolkit/query";
import { setSession, clear } from "./auth-slice";
import type { RootState } from "./index";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

const baseQuery = fetchBaseQuery({
  baseUrl: API_BASE_URL,
  prepareHeaders: (headers, { getState }) => {
    const token = (getState() as RootState).auth.accessToken;
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    return headers;
  },
});

const baseQueryWithReauth: BaseQueryFn<
  string | FetchArgs,
  unknown,
  FetchBaseQueryError
> = async (args, api, extraOptions) => {
  let result = await baseQuery(args, api, extraOptions);

  if (result.error && result.error.status === 401) {
    const state = api.getState() as RootState;
    const refreshToken = state.auth.refreshToken;
    const user = state.auth.user;

    if (refreshToken && user) {
      const refreshResult = await baseQuery(
        {
          url: "/api/v1/auth/refresh",
          method: "POST",
          body: { refresh_token: refreshToken },
        },
        api,
        extraOptions
      );

      if (refreshResult.data) {
        const data = (refreshResult.data as any).data;
        api.dispatch(
          setSession({
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
            user,
          })
        );
        result = await baseQuery(args, api, extraOptions);
      } else {
        api.dispatch(clear());
      }
    } else {
      api.dispatch(clear());
    }
  }

  return result;
};

export const apiSlice = createApi({
  reducerPath: "api",
  baseQuery: baseQueryWithReauth,
  tagTypes: [
    "Servers",
    "Tasks",
    "Conversations",
    "Devices",
    "Scans",
    "Roles",
    "Permissions",
    "Users",
    "Departments",
    "Designations",
    "Credentials"
  ],
  endpoints: () => ({}),
});
export { API_BASE_URL };
