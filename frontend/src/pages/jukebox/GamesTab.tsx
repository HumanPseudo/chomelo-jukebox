import { useCallback, useEffect, useState } from "react";
import { games } from "../../lib/endpoints";
import { useJukebox } from "../../lib/jukeboxContext";
import { ApiError } from "../../lib/api";
import type { RoundOut } from "../../lib/types";
import { Button, Empty, Panel, Tag } from "../../components/ui";

const GAME_KEY = "guess_the_song";

export function GamesTab() {
  const { jukebox, lastEvent } = useJukebox();
  const [rounds, setRounds] = useState<RoundOut[] | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    setRounds(await games.list(jukebox.id, GAME_KEY));
  }, [jukebox.id]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    if (lastEvent?.event === "game.updated") reload();
  }, [lastEvent, reload]);

  async function start() {
    setError("");
    setBusy(true);
    try {
      await games.start(jukebox.id, GAME_KEY);
      reload();
    } catch (err) {
      setError(
        err instanceof ApiError && err.code === "not_enough_songs"
          ? "faltan canciones reproducidas en esta frecuencia para armar una ronda"
          : "no se pudo iniciar la ronda",
      );
    } finally {
      setBusy(false);
    }
  }

  async function answer(roundId: number, title: string) {
    await games.answer(jukebox.id, GAME_KEY, roundId, title);
    reload();
  }

  if (!rounds) return <Empty>cargando…</Empty>;

  const open = rounds.find((r) => r.status === "OPEN");
  const finished = rounds.filter((r) => r.status === "FINISHED").slice(0, 5);

  return (
    <div>
      <Panel accent style={{ marginBottom: 24 }}>
        <h3>adivina la canción</h3>
        <p style={{ color: "var(--dim)", fontSize: 13 }}>
          se elige al azar una canción ya reproducida en esta frecuencia. el primero en acertar
          gana puntos y créditos.
        </p>
        {!open && (
          <Button onClick={start} disabled={busy}>
            iniciar ronda
          </Button>
        )}
        {error && <p className="error-text">{error}</p>}
      </Panel>

      {open && (
        <Panel live style={{ marginBottom: 24 }}>
          <Tag live>ronda abierta</Tag>
          <p style={{ marginTop: 8 }}>¿qué canción sonó?</p>
          <div className="guess-options">
            {open.options.map((opt) => (
              <button
                key={opt}
                className="search-result"
                disabled={!!open.my_attempt}
                onClick={() => answer(open.id, opt)}
              >
                {opt}
              </button>
            ))}
          </div>
          {open.my_attempt && (
            <p style={{ marginTop: 12 }} className="mono">
              {open.my_attempt.correct
                ? `acertaste · +${open.my_attempt.points} pts`
                : "respuesta registrada, esperando al resto"}
            </p>
          )}
        </Panel>
      )}

      {finished.length > 0 && (
        <>
          <h3>últimas rondas</h3>
          <Panel style={{ padding: 0 }}>
            {finished.map((r) => (
              <div key={r.id} className="queue-item" style={{ gridTemplateColumns: "1fr auto" }}>
                <div className="queue-item__meta">
                  <div className="queue-item__title">{r.correct_title}</div>
                  <div className="queue-item__artist">{r.artist}</div>
                </div>
                <span className="mono" style={{ fontSize: 12, color: "var(--dim)" }}>
                  {r.my_attempt?.correct ? `+${r.my_attempt.points} pts` : "—"}
                </span>
              </div>
            ))}
          </Panel>
        </>
      )}
    </div>
  );
}
