import { useEffect, useRef, useState, type ReactNode } from "react";
import type { PlayerStateOut, QueueItemOut } from "../../lib/types";
import { SignalDot, Tag } from "../../components/ui";
import { formatDuration } from "./QueueTab";

/**
 * Puramente visual (progreso, título, tag en vivo/pausa). El <audio> real
 * vive aparte, en AdminJukeboxLayout — que sigue montado sin importar en
 * qué pestaña estés — para que no se corte la música al navegar entre
 * Consola/Encuestas/Miembros. Ver useAudioSync.
 *
 * `player.position_ms` es la posición autoritativa del servidor *en el
 * momento en que se recibió* (`positionAt`, epoch ms local). Extrapolamos
 * desde esa ancla con el reloj local, no desde el montaje del componente:
 * así el contador no salta al cambiar de pestaña ni se descuadra respecto
 * a otros oyentes. Sin `positionAt` cae al tiempo de montaje.
 */
export function PlayerReadout({
  item,
  player,
  controls,
  positionAt,
}: {
  item: QueueItemOut | undefined;
  player: PlayerStateOut;
  controls?: ReactNode;
  positionAt?: number;
}) {
  const fallbackAnchor = useRef(Date.now());
  const [, tick] = useState(0);

  useEffect(() => {
    if (!player.is_playing) return;
    const timer = setInterval(() => tick((n) => n + 1), 500);
    return () => clearInterval(timer);
  }, [player.is_playing]);

  const anchor = positionAt && positionAt > 0 ? positionAt : fallbackAnchor.current;
  const positionMs = player.is_playing
    ? player.position_ms + Math.max(0, Date.now() - anchor)
    : player.position_ms;

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
  const shownMs = durationMs > 0 ? Math.min(positionMs, durationMs) : positionMs;
  const pct = durationMs > 0 ? Math.min(100, (shownMs / durationMs) * 100) : 0;

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
          <span>{formatDuration(Math.floor(shownMs / 1000))}</span>
          <span>{item.duration_seconds ? formatDuration(item.duration_seconds) : "--:--"}</span>
        </div>
      </div>
      {controls}
      <SignalDot state={player.is_playing ? "rec" : "idle"} />
    </div>
  );
}
