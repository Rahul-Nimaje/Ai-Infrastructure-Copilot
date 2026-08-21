"use client";

import { createContext, useContext, useEffect, useState } from "react";
import type { Socket } from "socket.io-client";
import type { ServerToClientEvents } from "@ai-infra-copilot/shared-types";
import { getSocket } from "@/lib/socket-client";
import { useAuthStore } from "@/lib/auth-store";

interface SocketContextValue {
  socket: Socket<ServerToClientEvents, any>;
  connected: boolean;
}

const SocketContext = createContext<SocketContextValue | null>(null);

/**
 * Connects the shared Socket.IO client only while the user is authenticated,
 * joins the org room on (re)connect. Scoped inside the dashboard layout (not
 * root layout) since unauthenticated routes have no org to join.
 */
export function SocketProvider({ children }: { children: React.ReactNode }) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const organizationId = useAuthStore((s) => s.user?.organization_id);
  const [connected, setConnected] = useState(false);
  const socket = getSocket();

  useEffect(() => {
    if (!accessToken || !organizationId) {
      socket.disconnect();
      setConnected(false);
      return;
    }

    const onConnect = () => {
      setConnected(true);
      socket.emit("join", { organization_id: organizationId });
    };
    const onDisconnect = () => setConnected(false);

    socket.on("connect", onConnect);
    socket.on("disconnect", onDisconnect);
    socket.on("connect_error", onDisconnect);
    socket.connect();

    return () => {
      socket.off("connect", onConnect);
      socket.off("disconnect", onDisconnect);
      socket.off("connect_error", onDisconnect);
    };
  }, [accessToken, organizationId, socket]);

  return <SocketContext.Provider value={{ socket, connected }}>{children}</SocketContext.Provider>;
}

export function useSocketContext(): SocketContextValue {
  const ctx = useContext(SocketContext);
  if (!ctx) {
    throw new Error("useSocketContext must be used within a SocketProvider");
  }
  return ctx;
}
