import { createContext, useContext } from "react";
import type { QueueOut } from "./types";

export interface AdminQueueCtx {
  data: QueueOut | null;
  reload: () => Promise<void>;
}

const Ctx = createContext<AdminQueueCtx | null>(null);

export const AdminQueueProvider = Ctx.Provider;

/**
 * Cola + estado del player, cargados una sola vez en AdminJukeboxLayout
 * (que sigue montado sin importar en qué pestaña estés) para que el
 * <audio> real no se destruya al cambiar de "Consola" a "Encuestas" etc.
 */
export function useAdminQueue(): AdminQueueCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAdminQueue debe usarse dentro de AdminJukeboxLayout");
  return ctx;
}
