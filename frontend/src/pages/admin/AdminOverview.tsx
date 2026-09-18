import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { games, jukeboxes, polls } from "../../lib/endpoints";
import { useJukebox } from "../../lib/jukeboxContext";
import { useAdminQueue } from "../../lib/adminQueueContext";
import type { ActivityOut, MemberOut, PollOut, RoundOut } from "../../lib/types";
import { Empty, Panel, Tag } from "../../components/ui";
import { PlayerReadout } from "../jukebox/PlayerReadout";
import { formatDuration } from "../jukebox/QueueTab";
import { ActivityFeed } from "./ActivityFeed";

const GAME_KEY = "guess_the_song";

export function AdminOverview() {
  const { jukebox, lastEvent } = useJukebox();
  const { data, fetchedAt } = useAdminQueue();
  const [members, setMembers] = useState<MemberOut[] | null>(null);
  const [openPolls, setOpenPolls] = useState<PollOut[] | null>(null);
  const [rounds, setRounds] = useState<RoundOut[] | null>(null);
  const [activity, setActivity] = useState<ActivityOut[] | null>(null);

  const reload = useCallback(async () => {
    const [m, p, r, a] = await Promise.allSettled([
      jukeboxes.members(jukebox.id),
      polls.list(jukebox.id, "OPEN"),
      games.list(jukebox.id, GAME_KEY, "OPEN"),
      jukeboxes.activity(jukebox.id, 10),
    ]);
    if (m.status === "fulfilled") setMembers(m.value);
    if (p.status === "fulfilled") setOpenPolls(p.value);
    if (r.status === "fulfilled") setRounds(r.value);
    if (a.status === "fulfilled") setActivity(a.value);
  }, [jukebox.id]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    if (lastEvent) reload();
  }, [lastEvent, reload]);

  const playing = data?.items.find((i) => i.id === data.player.current_item_id);
  const pending = data?.items.filter((i) => i.status === "QUEUED") ?? [];
  const next = pending[0];
  const topVoted = [...pending].sort((a, b) => b.score + b.boost - (a.score + a.boost)).slice(0, 3);
  const totalVotes = pending.reduce((sum, i) => sum + i.score, 0);
  const adminCount = members?.filter((m) => m.role === "ADMIN").length ?? 0;
  const openRound = rounds?.[0];

  return (
    <div>
      <Panel live style={{ marginBottom: 24 }}>
        <PlayerReadout
          item={playing}
          player={
            data?.player ?? { is_playing: false, position_ms: 0, current_item_id: null }
          }
          positionAt={fetchedAt}
        />
      </Panel>

      <div className="ov-grid">
        <div className="stat-tile">
          <span className="stat-tile__value mono">{pending.length}</span>
          <span className="stat-tile__label">en cola</span>
        </div>
        <div className="stat-tile">
          <span className="stat-tile__value mono">{totalVotes}</span>
          <span className="stat-tile__label">votos en la cola</span>
        </div>
        <div className="stat-tile">
          <span className="stat-tile__value mono">{members?.length ?? "—"}</span>
          <span className="stat-tile__label">en la señal</span>
        </div>
        <div className="stat-tile">
          <span className="stat-tile__value mono">{openPolls?.length ?? "—"}</span>
          <span className="stat-tile__label">encuestas abiertas</span>
        </div>
      </div>

      <div className="ov-cols">
        <Panel>
          <h3 style={{ marginTop: 0 }}>transmisión</h3>
          {next ? (
            <div className="ov-next">
              <span className="mono" style={{ color: "var(--dim)", fontSize: 11 }}>
                siguiente
              </span>
              <div className="ov-next__title">{next.title}</div>
              <div className="queue-item__artist">
                {next.artist || "desconocido"} ·{" "}
                {next.duration_seconds ? formatDuration(next.duration_seconds) : "--:--"}
              </div>
            </div>
          ) : (
            <Empty>la cola está vacía</Empty>
          )}

          {topVoted.length > 0 && (
            <>
              <h3>más votadas</h3>
              <div>
                {topVoted.map((item, i) => (
                  <div className="ov-rank" key={item.id}>
                    <span className="mono" style={{ color: "var(--dim)" }}>
                      {i + 1}
                    </span>
                    <span className="ov-rank__title">{item.title}</span>
                    <span className="mono" style={{ color: "var(--signal)" }}>
                      ▲ {item.score}
                      {item.boost > 0 && <span className="boost-badge"> ⚡{item.boost}</span>}
                    </span>
                  </div>
                ))}
              </div>
              <Link to="queue" className="ov-link">
                moderar la cola →
              </Link>
            </>
          )}

          <h3>juego</h3>
          {openRound ? (
            <p className="mono" style={{ fontSize: 13 }}>
              <Tag live>ronda abierta</Tag> termina{" "}
              {new Date(openRound.expires_at).toLocaleTimeString()}
            </p>
          ) : (
            <p style={{ color: "var(--dim)", fontSize: 13 }}>sin ronda activa</p>
          )}
          <Link to="games" className="ov-link">
            ir a adivina la canción →
          </Link>

          <h3>comunidad</h3>
          <p className="mono" style={{ fontSize: 13, color: "var(--dim)", margin: 0 }}>
            {members?.length ?? "—"} miembros · {adminCount} admin{adminCount === 1 ? "" : "s"}
          </p>
          <Link to="members" className="ov-link">
            gestionar miembros →
          </Link>
        </Panel>

        <Panel>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <h3 style={{ marginTop: 0 }}>movimientos recientes</h3>
            <Link to="activity" className="ov-link">
              ver todo →
            </Link>
          </div>
          <ActivityFeed items={activity} />
        </Panel>
      </div>
    </div>
  );
}
