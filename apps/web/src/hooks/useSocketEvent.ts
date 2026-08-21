import { useEffect } from "react";
import type { ServerToClientEvents } from "@ai-infra-copilot/shared-types";
import { useSocketContext } from "@/providers/socket-provider";

/**
 * Subscribes to a single Socket.IO server event for the lifetime of the
 * calling component. Generic over ServerToClientEvents so payloads are
 * typed at the call site — reusable by any future feature consuming the
 * app's socket connection (e.g. approval.requested/resolved), not just
 * Network Discovery.
 */
export function useSocketEvent<E extends keyof ServerToClientEvents>(
  event: E,
  handler: (payload: ServerToClientEvents[E]) => void
): void {
  const { socket } = useSocketContext();

  useEffect(() => {
    socket.on(event, handler as any);
    return () => {
      socket.off(event, handler as any);
    };
  }, [socket, event, handler]);
}
