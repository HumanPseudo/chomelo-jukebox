import { useEffect, useState, type FormEvent } from "react";
import { users } from "../lib/endpoints";
import type { ListenHistoryItem, ProfileOut } from "../lib/types";
import { Button, Empty, Field, Input, Panel } from "../components/ui";

export function ProfileView() {
  const [profile, setProfile] = useState<ProfileOut | null>(null);
  const [history, setHistory] = useState<ListenHistoryItem[] | null>(null);
  const [bio, setBio] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    users.profile().then((p) => {
      setProfile(p);
      setBio(p.bio);
    });
    users.history().then(setHistory);
  }, []);

  async function onSave(e: FormEvent) {
    e.preventDefault();
    const updated = await users.updateProfile({ bio });
    setProfile(updated);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  if (!profile) return <Empty>cargando perfil…</Empty>;

  const xpIntoLevel = profile.xp % 100;

  return (
    <div>
      <h1>{profile.display_name}</h1>

      <Panel accent style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
          <span className="mono">nivel {profile.level}</span>
          <span className="mono" style={{ color: "var(--dim)" }}>
            {xpIntoLevel} / 100 xp
          </span>
        </div>
        <div className="player__progress">
          <div className="player__progress-fill" style={{ width: `${xpIntoLevel}%` }} />
        </div>

        <div className="profile-stats mono">
          <div>
            <strong>{profile.tracks_added}</strong>
            <span>añadidas</span>
          </div>
          <div>
            <strong>{profile.tracks_played}</strong>
            <span>reproducidas</span>
          </div>
          <div>
            <strong>{profile.votes_cast}</strong>
            <span>votos</span>
          </div>
          <div>
            <strong>{profile.polls_created}</strong>
            <span>encuestas</span>
          </div>
        </div>
      </Panel>

      <Panel style={{ marginBottom: 24 }}>
        <h3>biografía</h3>
        <form onSubmit={onSave}>
          <Field label="visible para el resto de la señal">
            <Input value={bio} onChange={(e) => setBio(e.target.value)} maxLength={500} />
          </Field>
          <Button size="sm" type="submit">
            {saved ? "guardado ✓" : "guardar"}
          </Button>
        </form>
      </Panel>

      <h3>historial de escucha</h3>
      <Panel style={{ padding: 0 }}>
        {history?.length === 0 && <Empty>todavía nada en el historial</Empty>}
        {history?.map((h, i) => (
          <div key={i} className="queue-item" style={{ gridTemplateColumns: "1fr auto" }}>
            <div className="queue-item__meta">
              <div className="queue-item__title">{h.title}</div>
              <div className="queue-item__artist">
                {h.artist} · {h.jukebox_name}
              </div>
            </div>
            <span className="mono" style={{ fontSize: 12, color: "var(--dim)" }}>
              {new Date(h.played_at).toLocaleDateString()}
            </span>
          </div>
        ))}
      </Panel>
    </div>
  );
}
