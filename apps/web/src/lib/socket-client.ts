import { io, type Socket } from "socket.io-client";
import type { ServerToClientEvents } from "@ai-infra-copilot/shared-types";
import { API_BASE_URL } from "@/lib/api-client";

type ClientToServerEvents = {
  join: (data: { organization_id: string }) => void;
};

let socket: Socket<ServerToClientEvents, ClientToServerEvents> | null = null;

/**
 * Singleton Socket.IO client — first real-time socket consumer in this app
 * (backend's app/socket_app.py already emits approval.* events; Network
 * Discovery's live scan progress is the first frontend feature to listen).
 * Does not auto-connect; SocketProvider drives connect/disconnect based on
 * auth state.
 */
export function getSocket() {
  if (!socket) {
    socket = io(API_BASE_URL, {
      path: "/socket.io",
      autoConnect: false,
      transports: ["websocket", "polling"],
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 10000,
    });
  }
  return socket;
}
