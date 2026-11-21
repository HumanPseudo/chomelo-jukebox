import { useEffect, useRef, useState } from "react";
import { refreshTokens, wsUrl } from "./api";
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
      ws.onclose = (event) => {
        setStatus("offline");
        if (closedByUs || event.code === 4403) return;
        retryTimer = setTimeout(async () => {
          if (event.code === 4401 && !(await refreshTokens())) return;
          connect();
        }, event.code === 4401 ? 200 : 3000);
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
