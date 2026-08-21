import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import type { User } from "@ai-infra-copilot/shared-types";

export interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
}

const STORAGE_KEY = "copilot.auth";

function loadInitial(): AuthState {
  if (typeof window === "undefined") {
    return { accessToken: null, refreshToken: null, user: null };
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { accessToken: null, refreshToken: null, user: null };
    return JSON.parse(raw);
  } catch {
    return { accessToken: null, refreshToken: null, user: null };
  }
}

const initialState: AuthState = loadInitial();

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setSession: (
      state,
      action: PayloadAction<{ accessToken: string; refreshToken: string; user: User }>
    ) => {
      state.accessToken = action.payload.accessToken;
      state.refreshToken = action.payload.refreshToken;
      state.user = action.payload.user;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(action.payload));
      }
    },
    clear: (state) => {
      state.accessToken = null;
      state.refreshToken = null;
      state.user = null;
      if (typeof window !== "undefined") {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    },
  },
});

export const { setSession, clear } = authSlice.actions;
export default authSlice.reducer;
