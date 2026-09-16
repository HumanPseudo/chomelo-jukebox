import { useEffect, useRef, useState } from "react";
import { wsUrl } from "./api";
import type { WsEvent } from "./types";

export type SocketStatus = "connecting" | "online" | "offline";

/**
 * El WebSocket solo avisa que algo cambió; los datos siempre se
 * re-sincronizan por REST (ver Fase 12 del backend). `onEvent` dispara el
 * refetch correspondiente según el tipo de evento.
 */
export function useJukeboxSocket(jukeboxId: number | null, onEvent: (ev: WsEvent) => void) {
  const [status, setStatus] = useState<SocketStatus>("connecting");
  const onEventRef = useRef(onEvent);

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    if (jukeboxId === null) return;
    let closedByUs = false;
    let retryTimer: ReturnType<typeof setTimeout>;
    let ws: WebSocket;

    function connect() {
      setStatus("connecting");
      ws = new WebSocket(wsUrl(jukeboxId!));
      ws.onopen = () => setStatus("online");
      ws.onmessage = (msg) => {
        try {
          onEventRef.current(JSON.parse(msg.data));
        } catch {
          // ignorar mensajes no-JSON (p.ej. pong crudo)
        }
      };
      ws.onclose = () => {
        setStatus("offline");
        if (!closedByUs) retryTimer = setTimeout(connect, 3000);
      };
      ws.onerror = () => ws.close();
    }

    connect();
    return () => {
      closedByUs = true;
      clearTimeout(retryTimer);
      ws?.close();
    };
  }, [jukeboxId]);

  return status;
}
