import { useCallback, useEffect, useState } from "react";
import { jukeboxes, queue } from "../../lib/endpoints";
import { useJukebox } from "../../lib/jukeboxContext";
import { useAdminQueue } from "../../lib/adminQueueContext";
import { ApiError } from "../../lib/api";
import type { MemberOut } from "../../lib/types";
import { Empty, Panel, Tag } from "../../components/ui";
import { AddTrackPanel } from "../jukebox/AddTrackPanel";
import { PlayerReadout } from "../jukebox/PlayerReadout";
import { formatDuration } from "../jukebox/QueueTab";

export function AdminQueueTab() {
  const { jukebox } = useJukebox();
  const { data, fetchedAt, reload } = useAdminQueue();
  const [members, setMembers] = useState<MemberOut[]>([]);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState("");

  const loadMembers = useCallback(async () => {
    try {
      setMembers(await jukeboxes.members(jukebox.id));
    } catch {
      // los nombres son un lujo, no un requisito para moderar
    }
  }, [jukebox.id]);

  useEffect(() => {
    loadMembers();
  }, [loadMembers]);

  async function act(itemId: number, fn: () => Promise<unknown>) {
    setBusyId(itemId);
    setError("");
    try {
      await fn();
      await reload();
    } catch (err) {
      setError(
        err instanceof ApiError && err.code === "item_not_found"
          ? "esa canción ya no está en la cola"
          : "no se pudo moderar la cola",
      );
    } finally {
      setBusyId(null);
    }
  }

  if (!data) return <Empty>cargando cola…</Empty>;

  const playing = data.items.find((i) => i.id === data.player.current_item_id);
  const pending = data.items.filter((i) => i.status === "QUEUED");
  const nameOf = (userId: number) =>
    members.find((m) => m.user_id === userId)?.display_name || `usuario #${userId}`;

  return (
    <div>
      <Panel live style={{ marginBottom: 24 }}>
        <PlayerReadout item={playing} player={data.player} positionAt={fetchedAt} />
      </Panel>

      <AddTrackPanel jukeboxId={jukebox.id} onAdded={reload} />

      {error && (
        <p className="error-text" style={{ marginBottom: 12 }} role="alert">
          {error}
        </p>
      )}

      <Panel style={{ padding: 0 }}>
        {pending.length === 0 && <Empty>la cola está vacía · agrega la primera canción</Empty>}
        {pending.map((item, idx) => (
          <div className="queue-item queue-item--admin" key={item.id}>
            <span className="queue-item__pos mono">{idx + 1}</span>
            {item.thumbnail_url ? (
              <img className="queue-item__art" src={item.thumbnail_url} alt="" />
            ) : (
              <div className="queue-item__art" />
            )}
            <div className="queue-item__meta">
              <div className="queue-item__title">{item.title}</div>
              <div className="queue-item__artist">
                {item.artist || "desconocido"} · la puso {nameOf(item.added_by)}
                {item.boost > 0 && <span className="boost-badge"> ⚡ +{item.boost}</span>}
              </div>
            </div>
            <span className="queue-item__dur mono" style={{ color: "var(--dim)", fontSize: 12 }}>
              {item.duration_seconds ? formatDuration(item.duration_seconds) : ""}
            </span>
            <span className="queue-item__score mono" style={{ color: "var(--signal)" }}>
              ▲ {item.score}
            </span>
            <div className="queue-item__actions">
              <button
                className="icon-btn"
                title="subir"
                disabled={busyId === item.id || idx === 0}
                onClick={() => act(item.id, () => queue.move(jukebox.id, item.id, idx - 1))}
              >
                ↑
              </button>
              <button
                className="icon-btn"
                title="bajar"
                disabled={busyId === item.id || idx === pending.length - 1}
                onClick={() => act(item.id, () => queue.move(jukebox.id, item.id, idx + 1))}
              >
                ↓
              </button>
              <button
                className="icon-btn"
                title="al tope"
                disabled={busyId === item.id || idx === 0}
                onClick={() => act(item.id, () => queue.move(jukebox.id, item.id, 0))}
              >
                ⇈
              </button>
              <button
                className="icon-btn"
                title="al fondo"
                disabled={busyId === item.id || idx === pending.length - 1}
                onClick={() =>
                  act(item.id, () => queue.move(jukebox.id, item.id, pending.length - 1))
                }
              >
                ⇊
              </button>
              <button
                className="icon-btn icon-btn--danger"
                title="quitar"
                disabled={busyId === item.id}
                onClick={() => act(item.id, () => queue.remove(jukebox.id, item.id))}
              >
                ✕
              </button>
            </div>
          </div>
        ))}
      </Panel>

      {playing && (
        <Panel style={{ marginTop: 24 }}>
          <h3 style={{ marginTop: 0 }}>sonando ahora</h3>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Tag live>en vivo</Tag>
            <div>
              <div className="queue-item__title">{playing.title}</div>
              <div className="queue-item__artist">la puso {nameOf(playing.added_by)}</div>
            </div>
          </div>
        </Panel>
      )}
    </div>
  );
}
