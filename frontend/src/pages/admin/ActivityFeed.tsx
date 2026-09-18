import type { ActivityOut } from "../../lib/types";
import { Empty } from "../../components/ui";

export function activityLabel(e: ActivityOut): string {
  const who = e.display_name || (e.user_id != null ? `usuario #${e.user_id}` : "alguien");
  switch (e.kind) {
    case "queue.add":
      return `${who} añadió «${e.title ?? "una canción"}»`;
    case "track.played":
      return `sonó «${e.title ?? "una canción"}»`;
    case "vote":
      return `${who} votó «${e.title ?? "una canción"}»`;
    case "poll.created":
      return `${who} creó la encuesta «${e.title ?? ""}»`;
    case "poll.vote":
      return `${who} votó «${e.subtitle ?? "una opción"}» en «${e.title ?? ""}»`;
    case "game.round":
      return `${who} inició ${e.title ?? "una ronda"}`;
    case "game.won":
      return `${who} ganó ${e.title ?? "la ronda"}`;
    case "member.joined":
      return `${e.display_name || "alguien"} entró a la señal`;
    default:
      return `${who}: ${e.kind}`;
  }
}

export function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const seconds = Math.max(0, Math.floor(diff / 1000));
  if (seconds < 60) return "hace instantes";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `hace ${hours} h`;
  return new Date(iso).toLocaleDateString();
}

export function ActivityFeed({
  items,
  loading,
  error,
  onRetry,
}: {
  items: ActivityOut[] | null;
  loading?: boolean;
  error?: string;
  onRetry?: () => void;
}) {
  if (error) {
    return (
      <p className="error-text" role="alert">
        {error}
        {onRetry && (
          <>
            {" · "}
            <button className="linkish" onClick={onRetry}>
              reintentar
            </button>
          </>
        )}
      </p>
    );
  }
  if (!items) return <Empty>{loading ? "cargando movimientos…" : "sin movimientos"}</Empty>;
  if (items.length === 0) return <Empty>todavía no pasó nada en esta frecuencia</Empty>;

  return (
    <div className="activity">
      {items.map((e) => (
        <div className="activity__row" key={`${e.kind}-${e.id}-${e.created_at}`}>
          <span className={`activity__mark activity__mark--${e.kind.split(".")[0]}`} />
          <span className="activity__text">{activityLabel(e)}</span>
          <time className="mono activity__time">{timeAgo(e.created_at)}</time>
        </div>
      ))}
    </div>
  );
}
