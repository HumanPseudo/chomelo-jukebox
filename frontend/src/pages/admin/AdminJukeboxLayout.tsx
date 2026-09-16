import { useCallback, useEffect, useState } from "react";
import { Link, NavLink, Navigate, Outlet, useParams } from "react-router-dom";
import { jukeboxes } from "../../lib/endpoints";
import { JukeboxProvider } from "../../lib/jukeboxContext";
import { useJukeboxSocket } from "../../lib/useJukeboxSocket";
import type { JukeboxOut, WsEvent } from "../../lib/types";
import { Empty, SignalDot } from "../../components/ui";

function tabClass({ isActive }: { isActive: boolean }) {
  return `jb-tab ${isActive ? "is-active" : ""}`;
}

export function AdminJukeboxLayout() {
  const { id } = useParams();
  const jukeboxId = Number(id);
  const [jukebox, setJukebox] = useState<JukeboxOut | null>(null);
  const [lastEvent, setLastEvent] = useState<WsEvent | null>(null);

  const reloadJukebox = useCallback(async () => {
    setJukebox(await jukeboxes.get(jukeboxId));
  }, [jukeboxId]);

  useEffect(() => {
    setJukebox(null);
    reloadJukebox();
  }, [reloadJukebox]);

  const wsStatus = useJukeboxSocket(Number.isFinite(jukeboxId) ? jukeboxId : null, setLastEvent);

  if (!jukebox) return <Empty>sintonizando…</Empty>;

  if (jukebox.role !== "ADMIN") {
    return <Navigate to="/" replace />;
  }

  return (
    <JukeboxProvider value={{ jukebox, wsStatus, lastEvent, reloadJukebox }}>
      <div className="jb-header">
        <div>
          <Link to="/" className="mono" style={{ fontSize: 11, color: "var(--dim)" }}>
            ← consolas
          </Link>
          <h1 style={{ margin: "4px 0" }}>{jukebox.name}</h1>
          <span className="mono" style={{ fontSize: 12, color: "var(--dim)" }}>
            código {jukebox.invite_code} · {jukebox.member_count} en la señal
          </span>
        </div>
        <div className="jb-header__status">
          <SignalDot state={wsStatus === "online" ? "live" : "idle"} />
          <span className="mono">{wsStatus === "online" ? "en vivo" : "reconectando…"}</span>
        </div>
      </div>

      <nav className="jb-tabs">
        <NavLink to="" end className={tabClass}>
          Consola
        </NavLink>
        <NavLink to="polls" className={tabClass}>
          Encuestas
        </NavLink>
        <NavLink to="games" className={tabClass}>
          Adivina la canción
        </NavLink>
        <NavLink to="members" className={tabClass}>
          Miembros
        </NavLink>
      </nav>

      <div className="jb-content">
        <Outlet />
      </div>
    </JukeboxProvider>
  );
}
