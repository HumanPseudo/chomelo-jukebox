import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { music, queue } from "../../lib/endpoints";
import { ApiError } from "../../lib/api";
import type { TrackInfo } from "../../lib/types";
import { Button, Input, Panel } from "../../components/ui";
import { formatDuration } from "./QueueTab";

/** Buscar y añadir una canción a la cola. Lo usan tanto la vista de
 * oyente (QueueTab) como la consola de admin (AdminQueueTab) — el admin
 * también necesita poder meter canciones, no solo saltar por la cola
 * que ya está. */
export function AddTrackPanel({
  jukeboxId,
  onAdded,
  buyHref = "/wallet",
  cooldownEndsAt = null,
  costCredits = 5,
}: {
  jukeboxId: number;
  onAdded: () => void;
  buyHref?: string;
  cooldownEndsAt?: Date | null;
  costCredits?: number;
}) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<TrackInfo[]>([]);
  const [searching, setSearching] = useState(false);
  const [addError, setAddError] = useState("");
  const [now, setNow] = useState(Date.now());
  const remainingMs = cooldownEndsAt ? Math.max(0, cooldownEndsAt.getTime() - now) : 0;
  const inCooldown = remainingMs > 0;
  const remainingLabel = `${Math.floor(remainingMs / 60000)}:${String(
    Math.floor((remainingMs % 60000) / 1000),
  ).padStart(2, "0")}`;

  useEffect(() => {
    if (!cooldownEndsAt) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [cooldownEndsAt]);

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
    setAddError("");
    try {
      await queue.add(jukeboxId, trackId);
      setResults([]);
      setQ("");
      onAdded();
    } catch (err) {
      if (err instanceof ApiError && err.code === "add_track_cooldown") {
        setAddError("⏳ espera para añadir gratis o usa créditos");
      } else {
        setAddError("no se pudo añadir");
      }
    }
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
      {inCooldown && (
        <div className="cooldown-timer">
          <span className="hourglass">⏳</span>
          <span className="mono">próxima canción gratis en {remainingLabel}</span>
          <span className="mono" style={{ color: "var(--dim)", fontSize: 12 }}>
            o añade ahora por {costCredits} créditos
          </span>
        </div>
      )}
      {addError && (
        <p className="error-text" style={{ marginTop: 8 }}>
          {addError}
          {buyHref && (
            <>
              {" · "}
              <Link to={buyHref}>comprar créditos</Link>
            </>
          )}
        </p>
      )}
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
