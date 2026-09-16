import { useCallback, useEffect, useState } from "react";
import { jukeboxes } from "../../lib/endpoints";
import { useJukebox } from "../../lib/jukeboxContext";
import { roleAtLeast, type MemberOut, type Role } from "../../lib/types";
import { Button, Empty, Panel, Tag } from "../../components/ui";

const ASSIGNABLE: Role[] = ["ADMIN", "MODERATOR", "MEMBER", "GUEST"];

export function MembersTab() {
  const { jukebox } = useJukebox();
  const [members, setMembers] = useState<MemberOut[] | null>(null);
  const canManage = roleAtLeast(jukebox.role, "ADMIN");

  const reload = useCallback(async () => {
    setMembers(await jukeboxes.members(jukebox.id));
  }, [jukebox.id]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function changeRole(userId: number, role: Role) {
    await jukeboxes.setRole(jukebox.id, userId, role);
    reload();
  }

  async function remove(userId: number) {
    await jukeboxes.removeMember(jukebox.id, userId);
    reload();
  }

  if (!members) return <Empty>cargando miembros…</Empty>;

  return (
    <Panel style={{ padding: 0 }}>
      {members.map((m) => (
        <div key={m.user_id} className="queue-item" style={{ gridTemplateColumns: "1fr auto auto" }}>
          <div className="queue-item__meta">
            <div className="queue-item__title">{m.display_name || `usuario #${m.user_id}`}</div>
          </div>
          <Tag live={m.role === "OWNER" || m.role === "ADMIN"}>{m.role}</Tag>
          {canManage && m.role !== "OWNER" && (
            <div style={{ display: "flex", gap: 6 }}>
              <select
                className="mono"
                value={m.role}
                onChange={(e) => changeRole(m.user_id, e.target.value as Role)}
                style={{ background: "var(--void)", border: "1px solid var(--line)", color: "var(--ink)" }}
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
  );
}
