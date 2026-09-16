import { createContext, useContext } from "react";
import type { JukeboxOut, WsEvent } from "./types";
import type { SocketStatus } from "./useJukeboxSocket";

export interface JukeboxCtx {
  jukebox: JukeboxOut;
  wsStatus: SocketStatus;
  lastEvent: WsEvent | null;
  reloadJukebox: () => Promise<void>;
}

const Ctx = createContext<JukeboxCtx | null>(null);

export const JukeboxProvider = Ctx.Provider;

export function useJukebox(): JukeboxCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useJukebox debe usarse dentro de una frecuencia activa");
  return ctx;
}
