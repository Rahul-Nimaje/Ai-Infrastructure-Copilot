import { create } from "zustand";
import { store } from "@/store";
import { setSession as setReduxSession, clear as clearRedux } from "@/store/auth-slice";
import type { User } from "@ai-infra-copilot/shared-types";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  setSession: (session: { accessToken: string; refreshToken: string; user: User }) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>((set) => {
  const getInitial = () => {
    const authState = store.getState().auth;
    return {
      accessToken: authState.accessToken,
      refreshToken: authState.refreshToken,
      user: authState.user,
    };
  };

  store.subscribe(() => {
    const authState = store.getState().auth;
    set({
      accessToken: authState.accessToken,
      refreshToken: authState.refreshToken,
      user: authState.user,
    });
  });

  return {
    ...getInitial(),
    setSession: (session) => {
      store.dispatch(setReduxSession(session));
    },
    clear: () => {
      store.dispatch(clearRedux());
    },
  };
});
export type { AuthState };
