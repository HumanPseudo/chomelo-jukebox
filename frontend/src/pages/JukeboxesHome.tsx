import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { jukeboxes } from "../lib/endpoints";
import { ApiError } from "../lib/api";
import type { JukeboxOut } from "../lib/types";
import { Button, Empty, Field, Input, Panel, Tag } from "../components/ui";

export function JukeboxesHome() {
  const navigate = useNavigate();
  const [list, setList] = useState<JukeboxOut[] | null>(null);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function reload() {
    setList(await jukeboxes.list());
  }

  useEffect(() => {
    reload();
  }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError("");
    try {
      const jb = await jukeboxes.create(name.trim());
      navigate(`/jukeboxes/${jb.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "no se pudo crear");
    } finally {
      setBusy(false);
    }
  }

  async function onJoin(e: FormEvent) {
    e.preventDefault();
    if (!code.trim()) return;
    setBusy(true);
    setError("");
    try {
      const jb = await jukeboxes.join(code.trim().toUpperCase());
      navigate(`/jukeboxes/${jb.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "código inválido");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>Frecuencias</h1>
      <p style={{ color: "var(--dim)" }}>tus jukebox activas y las que puedes sintonizar</p>

      <div style={{ display: "grid", gap: "12px", marginBottom: "32px" }}>
        {list === null && <Empty>cargando…</Empty>}
        {list?.length === 0 && <Empty>todavía no perteneces a ninguna frecuencia</Empty>}
        {list?.map((jb) => (
          <Panel
            key={jb.id}
            className="jb-row"
            onClick={() => navigate(`/jukeboxes/${jb.id}`)}
          >
            <div className="jb-row__main">
              <h2 style={{ margin: 0 }}>{jb.name}</h2>
              <span className="mono" style={{ color: "var(--dim)", fontSize: 12 }}>
                {jb.member_count} en la señal · código {jb.invite_code}
              </span>
            </div>
            <Tag live={jb.role === "ADMIN"}>{jb.role}</Tag>
          </Panel>
        ))}
      </div>

      <div className="jb-create-grid">
        <Panel accent>
          <h3>abrir frecuencia nueva</h3>
          <form onSubmit={onCreate}>
            <Field label="nombre">
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </Field>
            <Button type="submit" disabled={busy}>
              transmitir
            </Button>
          </form>
        </Panel>
        <Panel>
          <h3>unirse con código</h3>
          <form onSubmit={onJoin}>
            <Field label="código de invitación" error={error}>
              <Input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="mono"
                maxLength={8}
              />
            </Field>
            <Button type="submit" variant="ghost" disabled={busy}>
              sintonizar
            </Button>
          </form>
        </Panel>
      </div>
    </div>
  );
}
