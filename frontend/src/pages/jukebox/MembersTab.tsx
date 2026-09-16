import { useCallback, useEffect, useState } from "react";
import { jukeboxes } from "../../lib/endpoints";
import { useJukebox } from "../../lib/jukeboxContext";
import { ApiError } from "../../lib/api";
import type { MemberOut, Role } from "../../lib/types";
import { Button, Empty, Panel, Tag } from "../../components/ui";

const ASSIGNABLE: Role[] = ["ADMIN", "MEMBER"];

export function MembersTab() {
  const { jukebox } = useJukebox();
  const [members, setMembers] = useState<MemberOut[] | null>(null);
  const [error, setError] = useState("");
  const canManage = jukebox.role === "ADMIN";

  const reload = useCallback(async () => {
    setMembers(await jukeboxes.members(jukebox.id));
  }, [jukebox.id]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function changeRole(userId: number, role: Role) {
    setError("");
    try {
      await jukeboxes.setRole(jukebox.id, userId, role);
      reload();
    } catch (err) {
      setError(
        err instanceof ApiError && err.code === "last_admin"
          ? "la jukebox se quedaría sin ningún admin"
          : "no se pudo cambiar el rol",
      );
    }
  }

  async function remove(userId: number) {
    setError("");
    try {
      await jukeboxes.removeMember(jukebox.id, userId);
      reload();
    } catch (err) {
      setError(
        err instanceof ApiError && err.code === "last_admin"
          ? "la jukebox se quedaría sin ningún admin"
          : "no se pudo expulsar",
      );
    }
  }

  if (!members) return <Empty>cargando miembros…</Empty>;

  return (
    <div>
      {error && (
        <p className="error-text" style={{ marginBottom: 12 }}>
          {error}
        </p>
      )}
      <Panel style={{ padding: 0 }}>
        {members.map((m) => (
          <div
            key={m.user_id}
            className="queue-item"
            style={{ gridTemplateColumns: "1fr auto auto" }}
          >
            <div className="queue-item__meta">
              <div className="queue-item__title">{m.display_name || `usuario #${m.user_id}`}</div>
            </div>
            <Tag live={m.role === "ADMIN"}>{m.role}</Tag>
            {canManage && (
              <div style={{ display: "flex", gap: 6 }}>
                <select
                  className="mono"
                  value={m.role}
                  onChange={(e) => changeRole(m.user_id, e.target.value as Role)}
                  style={{
                    background: "var(--void)",
                    border: "1px solid var(--line)",
                    color: "var(--ink)",
                  }}
                >
                  {ASSIGNABLE.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
                <Button size="sm" variant="danger" onClick={() => remove(m.user_id)}>
                  expulsar
                </Button>
              </div>
            )}
          </div>
        ))}
      </Panel>
    </div>
  );
}
