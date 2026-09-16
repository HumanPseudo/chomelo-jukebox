import { useCallback, useEffect, useState } from "react";
import { queue } from "../../lib/endpoints";
import { useJukebox } from "../../lib/jukeboxContext";
import type { QueueOut } from "../../lib/types";
import { Button, Empty, Panel } from "../../components/ui";
import { PlayerReadout } from "./PlayerReadout";
import { formatDuration } from "./QueueTab";

export function AdminTab() {
  const { jukebox, lastEvent } = useJukebox();
  const [data, setData] = useState<QueueOut | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    setData(await queue.get(jukebox.id));
  }, [jukebox.id]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    if (lastEvent?.event === "queue.updated" || lastEvent?.event === "player.updated") reload();
  }, [lastEvent, reload]);

  async function act(fn: () => Promise<unknown>) {
    setBusy(true);
    try {
      await fn();
      await reload();
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
      </Panel>

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
