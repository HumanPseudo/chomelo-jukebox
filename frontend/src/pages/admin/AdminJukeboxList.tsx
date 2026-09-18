import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { jukeboxes } from "../../lib/endpoints";
import type { JukeboxOut } from "../../lib/types";
import { Button, Empty, Panel, Tag } from "../../components/ui";

export function AdminJukeboxList() {
  const navigate = useNavigate();
  const [list, setList] = useState<JukeboxOut[] | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      setList(await jukeboxes.list());
    } catch {
      setError("no se pudieron cargar tus consolas");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const consoles = list?.filter((jb) => jb.role === "ADMIN");

  return (
    <div>
      <h1>Consolas</h1>
      <p style={{ color: "var(--dim)" }}>frecuencias que administras</p>

      {error && (
        <p className="error-text" role="alert">
          {error} ·{" "}
          <button className="linkish" onClick={load}>
            reintentar
          </button>
        </p>
      )}

      <div style={{ display: "grid", gap: "12px" }}>
        {!list && !error && <Empty>cargando…</Empty>}
        {consoles?.length === 0 && (
          <Empty>
            no administras ninguna frecuencia todavía · pídele a alguien con rango de admin que te
            ascienda desde la app de oyente
          </Empty>
        )}
        {consoles?.map((jb) => (
          <Panel key={jb.id} className="jb-row" onClick={() => navigate(`/${jb.id}`)}>
            <div className="jb-row__main">
              <h2 style={{ margin: 0 }}>{jb.name}</h2>
              <span className="mono" style={{ color: "var(--dim)", fontSize: 12 }}>
                {jb.member_count} en la señal · código {jb.invite_code}
              </span>
            </div>
            <Tag live>{jb.role}</Tag>
          </Panel>
        ))}
      </div>

      {consoles && consoles.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Button variant="ghost" size="sm" onClick={load}>
            actualizar
          </Button>
        </div>
      )}
    </div>
  );
}
