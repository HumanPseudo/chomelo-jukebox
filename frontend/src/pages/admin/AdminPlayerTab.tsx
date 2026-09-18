import { useState } from "react";
import { queue } from "../../lib/endpoints";
import { useJukebox } from "../../lib/jukeboxContext";
import { useAdminQueue } from "../../lib/adminQueueContext";
import { ApiError } from "../../lib/api";
import { Button, Empty, Panel, Tag } from "../../components/ui";
import { PlayerReadout } from "../jukebox/PlayerReadout";
import { formatDuration } from "../jukebox/QueueTab";

function friendly(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.code === "no_previous_track") return "no hay ninguna canción anterior en el historial";
    if (err.code === "queue_empty") return "no hay nada en la cola para iniciar";
    if (err.code === "nothing_playing") return "no hay nada sonando ahora mismo";
  }
  return "no se pudo completar la acción";
}

export function AdminPlayerTab() {
  const { jukebox } = useJukebox();
  const { data, fetchedAt, reload } = useAdminQueue();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState<number | null>(null);

  async function act(fn: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await fn();
      await reload();
    } catch (err) {
      setError(friendly(err));
    } finally {
      setBusy(false);
    }
  }

  async function commitSeek() {
    if (draft === null) return;
    await act(() => queue.player.seek(jukebox.id, draft * 1000));
    setDraft(null);
  }

  if (!data) return <Empty>cargando consola…</Empty>;

  const playing = data.items.find((i) => i.id === data.player.current_item_id);
  const pending = data.items.filter((i) => i.status === "QUEUED");
  const next = pending[0];
  const duration = playing?.duration_seconds ?? 0;
  const liveSeconds = Math.floor(data.player.position_ms / 1000);
  const sliderValue = draft ?? (duration > 0 ? Math.min(liveSeconds, duration) : liveSeconds);

  return (
    <div>
      <Panel live style={{ marginBottom: 24, borderLeftColor: "var(--alert)" }}>
        <PlayerReadout
          item={playing}
          player={data.player}
          positionAt={fetchedAt}
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
                <Button
                  size="sm"
                  disabled={busy}
                  onClick={() => act(() => queue.player.pause(jukebox.id))}
                >
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
        {playing && duration > 0 && (
          <div className="seek">
            <input
              type="range"
              min={0}
              max={duration}
              value={sliderValue}
              disabled={busy}
              aria-label="posición de la canción"
              onChange={(e) => setDraft(Number(e.target.value))}
              onPointerUp={commitSeek}
              onKeyUp={(e) => {
                if (e.key === "Enter") commitSeek();
              }}
            />
            <span className="mono seek__time">
              {formatDuration(sliderValue)} / {formatDuration(duration)}
            </span>
          </div>
        )}
        {error && (
          <p className="error-text" style={{ marginTop: 8 }} role="alert">
            {error}
          </p>
        )}
      </Panel>

      <div className="ov-cols">
        <Panel>
          <h3 style={{ marginTop: 0 }}>a continuación</h3>
          {next ? (
            <div className="ov-next">
              <div className="ov-next__title">{next.title}</div>
              <div className="queue-item__artist">
                {next.artist || "desconocido"} ·{" "}
                {next.duration_seconds ? formatDuration(next.duration_seconds) : "--:--"}
              </div>
            </div>
          ) : (
            <Empty>no queda nada en la cola</Empty>
          )}
          <p style={{ color: "var(--dim)", fontSize: 12, marginTop: 12 }}>
            el reproductor es autoritativo en el servidor: aquí solo lo controlas.
          </p>
        </Panel>

        <Panel>
          <h3 style={{ marginTop: 0 }}>estado de la señal</h3>
          <p className="mono" style={{ fontSize: 13 }}>
            {data.player.is_playing ? (
              <Tag live>transmitiendo</Tag>
            ) : playing ? (
              <Tag>en pausa</Tag>
            ) : (
              <Tag>detenido</Tag>
            )}
          </p>
          <p className="mono" style={{ fontSize: 13, color: "var(--dim)" }}>
            {pending.length} en espera · posición {formatDuration(liveSeconds)}
          </p>
        </Panel>
      </div>
    </div>
  );
}
