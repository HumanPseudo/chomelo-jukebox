import { useCallback, useEffect, useState } from "react";
import { Link, NavLink, Navigate, Outlet, useParams } from "react-router-dom";
import { jukeboxes, queue } from "../../lib/endpoints";
import { useAuth } from "../../lib/auth";
import { JukeboxProvider } from "../../lib/jukeboxContext";
import { AdminQueueProvider } from "../../lib/adminQueueContext";
import { useJukeboxSocket } from "../../lib/useJukeboxSocket";
import { useAudioSync } from "../jukebox/useAudioSync";
import { useWakeLock } from "../jukebox/useWakeLock";
import { useMediaSession } from "../jukebox/useMediaSession";
import type { JukeboxOut, QueueOut, WsEvent } from "../../lib/types";
import { Button, Empty, Panel, SignalDot } from "../../components/ui";

const REFRESH_MS = 30000;

function tabClass({ isActive }: { isActive: boolean }) {
  return `jb-tab ${isActive ? "is-active" : ""}`;
}

export function AdminJukeboxLayout() {
  const { id } = useParams();
  const jukeboxId = Number(id);
  const { user } = useAuth();
  const [jukebox, setJukebox] = useState<JukeboxOut | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [lastEvent, setLastEvent] = useState<WsEvent | null>(null);
  const [queueData, setQueueData] = useState<QueueOut | null>(null);
  const [queueFetchedAt, setQueueFetchedAt] = useState(0);
  const [queueError, setQueueError] = useState("");

  const loadJukebox = useCallback(async () => {
    if (!Number.isFinite(jukeboxId)) return;
    setStatus("loading");
    try {
      setJukebox(await jukeboxes.get(jukeboxId));
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }, [jukeboxId]);

  const reloadQueue = useCallback(async () => {
    if (!Number.isFinite(jukeboxId)) return;
    try {
      setQueueData(await queue.get(jukeboxId));
      setQueueFetchedAt(Date.now());
      setQueueError("");
    } catch {
      setQueueError("no se pudo sincronizar la transmisión");
    }
  }, [jukeboxId]);

  useEffect(() => {
    setJukebox(null);
    setQueueData(null);
    loadJukebox();
    reloadQueue();
  }, [loadJukebox, reloadQueue]);

  // El WS avisa; el REST es la fuente de verdad. Si el socket se cae,
  // este latido lento evita que la consola se quede con datos rancios.
  useEffect(() => {
    const timer = setInterval(reloadQueue, REFRESH_MS);
    return () => clearInterval(timer);
  }, [reloadQueue]);

  useEffect(() => {
    if (lastEvent?.event === "queue.updated" || lastEvent?.event === "player.updated") {
      reloadQueue();
    }
  }, [lastEvent, reloadQueue]);

  const wsStatus = useJukeboxSocket(Number.isFinite(jukeboxId) ? jukeboxId : null, setLastEvent);

  // El <audio> real vive aquí, no en una pestaña: este layout sigue
  // montado sin importar a dónde navegues, así no se corta la música.
  const playing = queueData?.items.find((i) => i.id === queueData.player.current_item_id);
  const player = queueData?.player ?? { is_playing: false, position_ms: 0, current_item_id: null };
  const { audioRef, locked, unlock } = useAudioSync(playing, player, true);

  useWakeLock(player.is_playing);
  const onMediaPlay = useCallback(() => {
    const action = playing ? queue.player.resume : queue.player.play;
    action(jukeboxId).then(reloadQueue).catch(() => {});
  }, [jukeboxId, playing, reloadQueue]);
  const onMediaPause = useCallback(() => {
    queue.player.pause(jukeboxId).then(reloadQueue).catch(() => {});
  }, [jukeboxId, reloadQueue]);
  const onMediaNext = useCallback(() => {
    queue.player.next(jukeboxId).then(reloadQueue).catch(() => {});
  }, [jukeboxId, reloadQueue]);
  const onMediaPrevious = useCallback(() => {
    queue.player.previous(jukeboxId).then(reloadQueue).catch(() => {});
  }, [jukeboxId, reloadQueue]);
  useMediaSession(playing, player, {
    onPlay: onMediaPlay,
    onPause: onMediaPause,
    onNext: onMediaNext,
    onPrevious: onMediaPrevious,
  });

  if (!Number.isFinite(jukeboxId)) return <Navigate to="/" replace />;

  if (status === "error") {
    return (
      <Panel style={{ borderLeftColor: "var(--alert)" }}>
        <h2 style={{ marginTop: 0 }}>consola fuera de alcance</h2>
        <p style={{ color: "var(--dim)" }}>
          no pudimos abrir esta frecuencia: puede que no exista, que ya no estés en ella o que el
          servidor no responda.
        </p>
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <Button onClick={loadJukebox}>reintentar</Button>
          <Link to="/" className="btn btn--ghost">
            volver a consolas
          </Link>
        </div>
      </Panel>
    );
  }

  if (!jukebox) return <Empty>sintonizando…</Empty>;

  if (jukebox.role !== "ADMIN") {
    return <Navigate to="/" replace />;
  }

  return (
    <JukeboxProvider value={{ jukebox, wsStatus, lastEvent, reloadJukebox: loadJukebox }}>
      <AdminQueueProvider value={{ data: queueData, fetchedAt: queueFetchedAt, reload: reloadQueue }}>
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
              <span className="mono">{wsStatus === "online" ? "en vivo" : "reintentando…"}</span>
            </span>
          </div>
        </div>

        {queueError && (
          <p className="error-text" style={{ marginBottom: 12 }} role="alert">
            {queueError} ·{" "}
            <button className="linkish" onClick={reloadQueue}>
              reintentar
            </button>
          </p>
        )}

        <nav className="jb-tabs">
          <NavLink to="" end className={tabClass}>
            Resumen
          </NavLink>
          <NavLink to="player" className={tabClass}>
            Transmisor
          </NavLink>
          <NavLink to="queue" className={tabClass}>
            Cola
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
          <NavLink to="activity" className={tabClass}>
            Actividad
          </NavLink>
          {user?.is_superuser && (
            <NavLink to="audit" className={tabClass}>
              Auditoría
            </NavLink>
          )}
        </nav>

        <div className="jb-content">
          <Outlet />
        </div>
      </AdminQueueProvider>
    </JukeboxProvider>
  );
}
