import { useCallback, useEffect, useState } from "react";
import { jukeboxes } from "../../lib/endpoints";
import { useJukebox } from "../../lib/jukeboxContext";
import type { ActivityOut } from "../../lib/types";
import { Button, Panel } from "../../components/ui";
import { ActivityFeed } from "./ActivityFeed";

const LIMIT = 50;

export function AdminActivityTab() {
  const { jukebox, lastEvent } = useJukebox();
  const [items, setItems] = useState<ActivityOut[] | null>(null);
  const [limit, setLimit] = useState(LIMIT);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(
    async (nextLimit: number) => {
      setLoading(true);
      setError("");
      try {
        setItems(await jukeboxes.activity(jukebox.id, nextLimit));
      } catch {
        setError("no se pudo cargar la actividad");
      } finally {
        setLoading(false);
      }
    },
    [jukebox.id],
  );

  useEffect(() => {
    load(limit);
  }, [load, limit]);

  useEffect(() => {
    if (lastEvent) load(limit);
  }, [lastEvent, load, limit]);

  return (
    <Panel>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div>
          <h2 style={{ margin: 0 }}>actividad</h2>
          <span className="mono" style={{ fontSize: 12, color: "var(--dim)" }}>
            lo que pasó en esta frecuencia
          </span>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Button size="sm" variant="ghost" disabled={loading} onClick={() => load(limit)}>
            actualizar
          </Button>
          {items && items.length >= limit && (
            <Button size="sm" variant="ghost" disabled={loading} onClick={() => setLimit(limit + LIMIT)}>
              ver más
            </Button>
          )}
        </div>
      </div>
      <div style={{ marginTop: 16 }}>
        <ActivityFeed items={items} loading={loading} error={error} onRetry={() => load(limit)} />
      </div>
    </Panel>
  );
}
