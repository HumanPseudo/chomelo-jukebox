import { useCallback, useEffect, useState } from "react";
import { queue } from "../../lib/endpoints";
import { useJukebox } from "../../lib/jukeboxContext";
import { ApiError } from "../../lib/api";
import type { QueueOut } from "../../lib/types";
import { Empty, Panel } from "../../components/ui";
import { PlayerReadout } from "./PlayerReadout";
import { AddTrackPanel } from "./AddTrackPanel";

const BOOST_COST = 10;

export function QueueTab() {
  const { jukebox, lastEvent } = useJukebox();
  const [data, setData] = useState<QueueOut | null>(null);
  const [fetchedAt, setFetchedAt] = useState(0);
  const [boostError, setBoostError] = useState<{ itemId: number; message: string } | null>(null);

  const reload = useCallback(async () => {
    setData(await queue.get(jukebox.id));
    setFetchedAt(Date.now());
  }, [jukebox.id]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    if (lastEvent?.event === "queue.updated" || lastEvent?.event === "player.updated") reload();
  }, [lastEvent, reload]);

  async function toggleVote(itemId: number, voted: boolean) {
    if (voted) await queue.unvote(jukebox.id, itemId);
    else await queue.vote(jukebox.id, itemId);
    reload();
  }

  async function boost(itemId: number) {
    setBoostError(null);
    try {
      await queue.boost(jukebox.id, itemId, BOOST_COST);
      reload();
    } catch (err) {
      setBoostError({
        itemId,
        message:
          err instanceof ApiError && err.code === "insufficient_balance"
            ? "no te alcanzan los créditos"
            : "no se pudo impulsar",
      });
    }
  }

  if (!data) return <Empty>cargando cola…</Empty>;

  const pending = data.items.filter((i) => i.status === "QUEUED");
  const playing = data.items.find((i) => i.id === data.player.current_item_id);

  return (
    <div>
      <Panel live style={{ marginBottom: "24px" }}>
        <PlayerReadout item={playing} player={data.player} positionAt={fetchedAt} />
      </Panel>

      <AddTrackPanel jukeboxId={jukebox.id} onAdded={reload} />

      <Panel style={{ padding: 0 }}>
        {pending.length === 0 && <Empty>la cola está vacía · agrega la primera canción</Empty>}
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
                {item.artist || "desconocido"}
                {item.boost > 0 && <span className="boost-badge"> ⚡ +{item.boost}</span>}
              </div>
              {boostError?.itemId === item.id && (
                <div className="error-text" style={{ fontSize: 11 }}>
                  {boostError.message}
                </div>
              )}
            </div>
            <span className="queue-item__dur mono" style={{ color: "var(--dim)", fontSize: 12 }}>
              {item.duration_seconds ? formatDuration(item.duration_seconds) : ""}
            </span>
            <button
              className="boost-btn"
              onClick={() => boost(item.id)}
              title="gastar créditos para priorizar"
            >
              ⚡ {BOOST_COST}
            </button>
            <button
              className={`vote-btn ${item.voted_by_me ? "is-voted" : ""}`}
              onClick={() => toggleVote(item.id, item.voted_by_me)}
            >
              ▲ {item.score}
            </button>
          </div>
        ))}
      </Panel>
    </div>
  );
}

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${s}`;
}
