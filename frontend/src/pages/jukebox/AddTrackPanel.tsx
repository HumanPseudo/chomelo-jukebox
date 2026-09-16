import { useState, type FormEvent } from "react";
import { music, queue } from "../../lib/endpoints";
import type { TrackInfo } from "../../lib/types";
import { Button, Input, Panel } from "../../components/ui";
import { formatDuration } from "./QueueTab";

/** Buscar y añadir una canción a la cola. Lo usan tanto la vista de
 * oyente (QueueTab) como la consola de admin (AdminTab) — el admin
 * también necesita poder meter canciones, no solo saltar por la cola
 * que ya está. */
export function AddTrackPanel({
  jukeboxId,
  onAdded,
}: {
  jukeboxId: number;
  onAdded: () => void;
}) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<TrackInfo[]>([]);
  const [searching, setSearching] = useState(false);

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
    await queue.add(jukeboxId, trackId);
    setResults([]);
    setQ("");
    onAdded();
  }

  return (
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
  );
}
