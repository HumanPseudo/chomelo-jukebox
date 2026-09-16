import { useCallback, useEffect, useState, type FormEvent } from "react";
import { music, queue } from "../../lib/endpoints";
import { useJukebox } from "../../lib/jukeboxContext";
import type { QueueOut, TrackInfo } from "../../lib/types";
import { Button, Empty, Input, Panel } from "../../components/ui";
import { PlayerReadout } from "./PlayerReadout";

export function QueueTab() {
  const { jukebox, lastEvent } = useJukebox();
  const [data, setData] = useState<QueueOut | null>(null);
  const [q, setQ] = useState("");
  const [results, setResults] = useState<TrackInfo[]>([]);
  const [searching, setSearching] = useState(false);

  const reload = useCallback(async () => {
    setData(await queue.get(jukebox.id));
  }, [jukebox.id]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    if (lastEvent?.event === "queue.updated" || lastEvent?.event === "player.updated") reload();
  }, [lastEvent, reload]);

  async function onSearch(e: FormEvent) {
    e.preventDefault();
    if (!q.trim()) return;
    setSearching(true);
    try {
      setResults(await music.search(q.trim()));
    } finally {
      setSearching(false);
    }
  }

  async function addTrack(trackId: string) {
    await queue.add(jukebox.id, trackId);
    setResults([]);
    setQ("");
    reload();
  }

  async function toggleVote(itemId: number, voted: boolean) {
    if (voted) await queue.unvote(jukebox.id, itemId);
    else await queue.vote(jukebox.id, itemId);
    reload();
  }

  if (!data) return <Empty>cargando cola…</Empty>;

  const pending = data.items.filter((i) => i.status === "QUEUED");
  const playing = data.items.find((i) => i.id === data.player.current_item_id);

  return (
    <div>
      <Panel live style={{ marginBottom: "24px" }}>
        <PlayerReadout item={playing} player={data.player} />
      </Panel>

      <Panel accent style={{ marginBottom: "24px" }}>
        <h3>añadir a la transmisión</h3>
        <form onSubmit={onSearch} style={{ display: "flex", gap: 8 }}>
          <Input
            placeholder="buscar canción o artista…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <Button type="submit" size="sm" disabled={searching}>
            buscar
          </Button>
        </form>
        {results.length > 0 && (
          <div className="search-results">
            {results.map((t) => (
              <button key={t.track_id} className="search-result" onClick={() => addTrack(t.track_id)}>
                {t.thumbnail_url && <img src={t.thumbnail_url} alt="" />}
                <span className="search-result__title">
                  {t.title} {t.artist && `— ${t.artist}`}
                </span>
                {t.duration_seconds && (
                  <span className="search-result__dur">{formatDuration(t.duration_seconds)}</span>
                )}
              </button>
            ))}
          </div>
        )}
      </Panel>

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
              <div className="queue-item__artist">{item.artist || "desconocido"}</div>
            </div>
            <span className="mono" style={{ color: "var(--dim)", fontSize: 12 }}>
              {item.duration_seconds ? formatDuration(item.duration_seconds) : ""}
            </span>
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
