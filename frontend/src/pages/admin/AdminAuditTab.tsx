import { useCallback, useEffect, useState, type FormEvent } from "react";
import { admin } from "../../lib/endpoints";
import { useAuth } from "../../lib/auth";
import type { AuditOut } from "../../lib/types";
import { Button, Empty, Input, Panel, Tag } from "../../components/ui";

const PAGE = 50;

export function AdminAuditTab() {
  const { user } = useAuth();
  const [entries, setEntries] = useState<AuditOut[] | null>(null);
  const [offset, setOffset] = useState(0);
  const [filter, setFilter] = useState("");
  const [applied, setApplied] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(
    async (nextOffset: number, action: string, append: boolean) => {
      setLoading(true);
      setError("");
      try {
        const page = await admin.audit({
          limit: PAGE,
          offset: nextOffset,
          action: action || undefined,
        });
        setEntries((prev) => (append && prev ? [...prev, ...page] : page));
        setOffset(nextOffset + page.length);
      } catch {
        setError("no se pudo leer el registro de auditoría");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    load(0, applied, false);
  }, [load, applied]);

  if (!user?.is_superuser) {
    return (
      <Panel style={{ borderLeftColor: "var(--alert)" }}>
        <h2 style={{ marginTop: 0 }}>acceso restringido</h2>
        <p style={{ color: "var(--dim)" }}>la auditoría de la plataforma es solo para superusuarios.</p>
      </Panel>
    );
  }

  function applyFilter(e: FormEvent) {
    e.preventDefault();
    setApplied(filter.trim());
  }

  return (
    <Panel>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <div>
          <h2 style={{ margin: 0 }}>auditoría</h2>
          <span className="mono" style={{ fontSize: 12, color: "var(--dim)" }}>
            registro de acciones de la plataforma · solo superusuario
          </span>
        </div>
        <form onSubmit={applyFilter} style={{ display: "flex", gap: 8 }}>
          <Input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="filtrar por acción…"
            aria-label="filtrar por acción"
          />
          <Button size="sm" type="submit" disabled={loading}>
            filtrar
          </Button>
          {applied && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setFilter("");
                setApplied("");
              }}
            >
              limpiar
            </Button>
          )}
        </form>
      </div>

      <div style={{ marginTop: 16 }}>
        {error && (
          <p className="error-text" role="alert">
            {error} ·{" "}
            <button className="linkish" onClick={() => load(0, applied, false)}>
              reintentar
            </button>
          </p>
        )}
        {!entries && !error && <Empty>cargando auditoría…</Empty>}
        {entries && entries.length === 0 && <Empty>sin registros{applied && ` para «${applied}»`}</Empty>}

        {entries && entries.length > 0 && (
          <div className="audit">
            <div className="audit__row audit__row--head mono">
              <span>cuándo</span>
              <span>acción</span>
              <span>actor</span>
              <span>recurso</span>
              <span>detalle</span>
            </div>
            {entries.map((e) => (
              <div className="audit__row" key={e.id}>
                <span className="mono audit__time">{new Date(e.created_at).toLocaleString()}</span>
                <span>
                  <Tag>{e.action}</Tag>
                </span>
                <span className="mono">{e.user_id != null ? `#${e.user_id}` : "—"}</span>
                <span className="mono">
                  {e.resource_type ? `${e.resource_type}:${e.resource_id ?? "?"}` : "—"}
                </span>
                <span className="audit__detail mono" title={e.ip ?? undefined}>
                  {e.detail ? JSON.stringify(e.detail) : e.ip || "—"}
                </span>
              </div>
            ))}
          </div>
        )}

        {entries && entries.length > 0 && entries.length % PAGE === 0 && (
          <div style={{ marginTop: 12, textAlign: "center" }}>
            <Button
              size="sm"
              variant="ghost"
              disabled={loading}
              onClick={() => load(offset, applied, true)}
            >
              {loading ? "cargando…" : "cargar más"}
            </Button>
          </div>
        )}
      </div>
    </Panel>
  );
}
