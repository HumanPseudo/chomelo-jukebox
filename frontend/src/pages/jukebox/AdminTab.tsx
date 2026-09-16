import { useState } from "react";
import { queue } from "../../lib/endpoints";
import { useJukebox } from "../../lib/jukeboxContext";
import { useAdminQueue } from "../../lib/adminQueueContext";
import { ApiError } from "../../lib/api";
import { Button, Empty, Panel } from "../../components/ui";
import { PlayerReadout } from "./PlayerReadout";
import { AddTrackPanel } from "./AddTrackPanel";
import { formatDuration } from "./QueueTab";

export function AdminTab() {
  const { jukebox } = useJukebox();
  const { data, reload } = useAdminQueue();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function act(fn: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await fn();
      await reload();
    } catch (err) {
      setError(
        err instanceof ApiError && err.code === "no_previous_track"
          ? "no hay ninguna canción anterior en el historial"
          : "no se pudo completar la acción",
      );
    } finally {
      setBusy(false);
    }
  }

  if (!data) return <Empty>cargando consola…</Empty>;

  const playing = data.items.find((i) => i.id === data.player.current_item_id);
  const pending = data.items.filter((i) => i.status === "QUEUED");

  return (
    <div>
      <Panel live style={{ marginBottom: "24px", borderLeftColor: "var(--alert)" }}>
        <PlayerReadout
          item={playing}
          player={data.player}
          controls={
            <div className="player__controls">
              <Button
                size="sm"
                variant="ghost"
                disabled={busy}
                onClick={() => act(() => queue.player.previous(jukebox.id))}
              >
                anterior
              </Button>
              {data.player.is_playing ? (
                <Button size="sm" disabled={busy} onClick={() => act(() => queue.player.pause(jukebox.id))}>
                  pausar
                </Button>
              ) : (
                <Button
                  size="sm"
                  disabled={busy}
                  onClick={() =>
                    act(() =>
                      playing ? queue.player.resume(jukebox.id) : queue.player.play(jukebox.id),
                    )
                  }
                >
                  {playing ? "reanudar" : "iniciar"}
                </Button>
              )}
              <Button
                size="sm"
                variant="ghost"
                disabled={busy || pending.length === 0}
                onClick={() => act(() => queue.player.next(jukebox.id))}
              >
                siguiente
              </Button>
            </div>
          }
        />
        {error && (
          <p className="error-text" style={{ marginTop: 8 }}>
            {error}
          </p>
        )}
      </Panel>

      <AddTrackPanel jukeboxId={jukebox.id} onAdded={reload} />

      <h3>moderar transmisión</h3>
      <Panel style={{ padding: 0 }}>
        {pending.length === 0 && <Empty>no hay nada en espera</Empty>}
        {pending.map((item, idx) => (
          <div className="queue-item" key={item.id}>
            <span className="queue-item__pos mono">{idx + 1}</span>
            {item.thumbnail_url ? (
              <img className="queue-item__art" src={item.thumbnail_url} alt="" />
            ) : (
              <div className="queue-item__art" />
            )}
            <div className="queue-item__meta">
              <div className="queue-item__title">{item.title}</div>
              <div className="queue-item__artist">
                {item.artist || "desconocido"} · {formatDuration(item.duration_seconds ?? 0)}
              </div>
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy || idx === 0}
                onClick={() => act(() => queue.move(jukebox.id, item.id, idx - 1))}
              >
                subir
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={busy || idx === pending.length - 1}
                onClick={() => act(() => queue.move(jukebox.id, item.id, idx + 1))}
              >
                bajar
              </Button>
              <Button
                size="sm"
                variant="danger"
                disabled={busy}
                onClick={() => act(() => queue.remove(jukebox.id, item.id))}
              >
                quitar
              </Button>
            </div>
          </div>
        ))}
      </Panel>
    </div>
  );
}
