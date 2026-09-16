import { useCallback, useEffect, useState } from "react";
import { Link, NavLink, Navigate, Outlet, useParams } from "react-router-dom";
import { jukeboxes, queue } from "../../lib/endpoints";
import { JukeboxProvider } from "../../lib/jukeboxContext";
import { AdminQueueProvider } from "../../lib/adminQueueContext";
import { useJukeboxSocket } from "../../lib/useJukeboxSocket";
import { useAudioSync } from "../jukebox/useAudioSync";
import type { JukeboxOut, QueueOut, WsEvent } from "../../lib/types";
import { Button, Empty, SignalDot } from "../../components/ui";

function tabClass({ isActive }: { isActive: boolean }) {
  return `jb-tab ${isActive ? "is-active" : ""}`;
}

export function AdminJukeboxLayout() {
  const { id } = useParams();
  const jukeboxId = Number(id);
  const [jukebox, setJukebox] = useState<JukeboxOut | null>(null);
  const [lastEvent, setLastEvent] = useState<WsEvent | null>(null);
  const [queueData, setQueueData] = useState<QueueOut | null>(null);

  const reloadJukebox = useCallback(async () => {
    setJukebox(await jukeboxes.get(jukeboxId));
  }, [jukeboxId]);

  const reloadQueue = useCallback(async () => {
    setQueueData(await queue.get(jukeboxId));
  }, [jukeboxId]);

  useEffect(() => {
    setJukebox(null);
    setQueueData(null);
    reloadJukebox();
    reloadQueue();
  }, [reloadJukebox, reloadQueue]);

  useEffect(() => {
    if (lastEvent?.event === "queue.updated" || lastEvent?.event === "player.updated") {
      reloadQueue();
    }
  }, [lastEvent, reloadQueue]);

  const wsStatus = useJukeboxSocket(Number.isFinite(jukeboxId) ? jukeboxId : null, setLastEvent);

  // El <audio> real vive aquí, no en la pestaña "Consola": este layout
  // sigue montado sin importar a qué pestaña navegues, así que la
  // música no se corta al ir a Encuestas/Miembros/etc.
  const playing = queueData?.items.find((i) => i.id === queueData.player.current_item_id);
  const player = queueData?.player ?? { is_playing: false, position_ms: 0, current_item_id: null };
  const { audioRef, locked, unlock } = useAudioSync(playing, player, true);

  if (!jukebox) return <Empty>sintonizando…</Empty>;

  if (jukebox.role !== "ADMIN") {
    return <Navigate to="/" replace />;
  }

  return (
    <JukeboxProvider value={{ jukebox, wsStatus, lastEvent, reloadJukebox }}>
      <AdminQueueProvider value={{ data: queueData, reload: reloadQueue }}>
        <audio ref={audioRef} preload="auto" />

        <div className="jb-header">
          <div>
            <Link to="/" className="mono" style={{ fontSize: 11, color: "var(--dim)" }}>
              ← consolas
            </Link>
            <h1 style={{ margin: "4px 0" }}>{jukebox.name}</h1>
            <span className="mono" style={{ fontSize: 12, color: "var(--dim)" }}>
              código {jukebox.invite_code} · {jukebox.member_count} en la señal
            </span>
          </div>
          <div className="jb-header__status" style={{ gap: 12 }}>
            {player.is_playing && locked && (
              <Button size="sm" onClick={unlock}>
                🔇 activar sonido
              </Button>
            )}
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <SignalDot state={wsStatus === "online" ? "live" : "idle"} />
              <span className="mono">{wsStatus === "online" ? "en vivo" : "reconectando…"}</span>
            </span>
          </div>
        </div>

        <nav className="jb-tabs">
          <NavLink to="" end className={tabClass}>
            Consola
          </NavLink>
          <NavLink to="polls" className={tabClass}>
            Encuestas
          </NavLink>
          <NavLink to="games" className={tabClass}>
            Adivina la canción
          </NavLink>
          <NavLink to="members" className={tabClass}>
            Miembros
          </NavLink>
        </nav>

        <div className="jb-content">
          <Outlet />
        </div>
      </AdminQueueProvider>
    </JukeboxProvider>
  );
}
