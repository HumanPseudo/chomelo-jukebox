import { useEffect, useState, type ReactNode } from "react";
import type { PlayerStateOut, QueueItemOut } from "../../lib/types";
import { SignalDot, Tag } from "../../components/ui";
import { formatDuration } from "./QueueTab";

/**
 * Puramente visual (progreso, título, tag en vivo/pausa). El <audio> real
 * vive aparte, en AdminJukeboxLayout — que sigue montado sin importar en
 * qué pestaña estés — para que no se corte la música al navegar entre
 * Consola/Encuestas/Miembros. Ver useAudioSync.
 */
export function PlayerReadout({
  item,
  player,
  controls,
}: {
  item: QueueItemOut | undefined;
  player: PlayerStateOut;
  controls?: ReactNode;
}) {
  const [positionMs, setPositionMs] = useState(player.position_ms);

  useEffect(() => {
    setPositionMs(player.position_ms);
    if (!player.is_playing) return;
    const start = Date.now();
    const base = player.position_ms;
    const timer = setInterval(() => setPositionMs(base + (Date.now() - start)), 500);
    return () => clearInterval(timer);
  }, [player.position_ms, player.is_playing]);

  if (!item) {
    return (
      <div className="player">
        <div className="player__art" />
        <div className="player__meta">
          <Tag>sin transmisión</Tag>
          <p style={{ margin: "6px 0 0", color: "var(--dim)", fontSize: 13 }}>
            agrega una canción a la cola para empezar
          </p>
        </div>
        {controls}
      </div>
    );
  }

  const durationMs = (item.duration_seconds ?? 0) * 1000;
  const pct = durationMs > 0 ? Math.min(100, (positionMs / durationMs) * 100) : 0;

  return (
    <div className="player">
      {item.thumbnail_url ? (
        <img className="player__art" src={item.thumbnail_url} alt="" />
      ) : (
        <div className="player__art" />
      )}
      <div className="player__meta">
        <Tag live={player.is_playing}>{player.is_playing ? "en vivo" : "en pausa"}</Tag>
        <h2 style={{ margin: "6px 0 2px" }}>{item.title}</h2>
        <span style={{ color: "var(--dim)", fontSize: 13 }}>{item.artist || "desconocido"}</span>
        <div className="player__progress">
          <div className="player__progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <div
          className="mono"
          style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginTop: 4 }}
        >
          <span>{formatDuration(Math.floor(positionMs / 1000))}</span>
          <span>{item.duration_seconds ? formatDuration(item.duration_seconds) : "--:--"}</span>
        </div>
      </div>
      {controls}
      <SignalDot state={player.is_playing ? "rec" : "idle"} />
    </div>
  );
}
