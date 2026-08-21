import { useAuthStore } from "@/lib/auth-store";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export class ApiClientError extends Error {
  code: string;
  status: number;

  constructor(message: string, code: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const { refreshToken, user, setSession, clear } = useAuthStore.getState();
  if (!refreshToken || !user) return null;
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) {
    clear();
    return null;
  }
  const body = await response.json();
  setSession({ accessToken: body.data.access_token, refreshToken: body.data.refresh_token, user });
  return body.data.access_token as string;
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  skipAuthRetry?: boolean;
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, skipAuthRetry, headers, ...rest } = options;
  const accessToken = useAuthStore.getState().accessToken;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (response.status === 401 && !skipAuthRetry) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      return apiFetch<T>(path, { ...options, skipAuthRetry: true });
    }
  }

  if (!response.ok) {
    let code = "INTERNAL_ERROR";
    let message = response.statusText;
    try {
      const errorBody = await response.json();
      code = errorBody?.error?.code ?? errorBody?.detail?.code ?? code;
      message = errorBody?.error?.message ?? errorBody?.detail?.message ?? message;
    } catch {
      // response had no JSON body
    }
    throw new ApiClientError(message, code, response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function apiStreamUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

export function getAccessToken(): string | null {
  return useAuthStore.getState().accessToken;
}

export { API_BASE_URL };
