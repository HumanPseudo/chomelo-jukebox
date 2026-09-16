import { useCallback, useEffect, useState, type FormEvent } from "react";
import { polls } from "../../lib/endpoints";
import { useJukebox } from "../../lib/jukeboxContext";
import { roleAtLeast, type PollOut } from "../../lib/types";
import { Button, Empty, Field, Input, Panel, Tag } from "../../components/ui";

export function PollsTab() {
  const { jukebox, lastEvent } = useJukebox();
  const [list, setList] = useState<PollOut[] | null>(null);
  const [question, setQuestion] = useState("");
  const [options, setOptions] = useState(["", ""]);
  const canModerate = roleAtLeast(jukebox.role, "MODERATOR");

  const reload = useCallback(async () => {
    setList(await polls.list(jukebox.id));
  }, [jukebox.id]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    if (lastEvent?.event === "poll.updated") reload();
  }, [lastEvent, reload]);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    const clean = options.map((o) => o.trim()).filter(Boolean);
    if (!question.trim() || clean.length < 2) return;
    await polls.create(jukebox.id, question.trim(), clean);
    setQuestion("");
    setOptions(["", ""]);
    reload();
  }

  async function vote(pollId: number, optionId: number) {
    await polls.vote(jukebox.id, pollId, optionId);
    reload();
  }

  async function close(pollId: number) {
    await polls.close(jukebox.id, pollId);
    reload();
  }

  if (!list) return <Empty>cargando encuestas…</Empty>;

  return (
    <div>
      <Panel accent style={{ marginBottom: 24 }}>
        <h3>lanzar encuesta</h3>
        <form onSubmit={onCreate}>
          <Field label="pregunta">
            <Input value={question} onChange={(e) => setQuestion(e.target.value)} />
          </Field>
          {options.map((opt, i) => (
            <Field key={i} label={`opción ${i + 1}`}>
              <Input
                value={opt}
                onChange={(e) => {
                  const next = [...options];
                  next[i] = e.target.value;
                  setOptions(next);
                }}
              />
            </Field>
          ))}
          <div style={{ display: "flex", gap: 8 }}>
            <Button type="button" variant="ghost" size="sm" onClick={() => setOptions([...options, ""])}>
              + opción
            </Button>
            <Button type="submit" size="sm">
              publicar
            </Button>
          </div>
        </form>
      </Panel>

      {list.length === 0 && <Empty>no hay encuestas todavía</Empty>}
      {list.map((poll) => {
        const total = poll.total_votes || 1;
        return (
          <Panel key={poll.id} style={{ marginBottom: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <h3 style={{ color: "var(--ink)" }}>{poll.question}</h3>
              <Tag live={poll.status === "OPEN"}>{poll.status === "OPEN" ? "abierta" : "cerrada"}</Tag>
            </div>
            {poll.options.map((opt) => {
              const pct = Math.round((opt.votes / total) * 100);
              const mine = poll.my_option_id === opt.id;
              return (
                <div
                  key={opt.id}
                  className={`poll-option ${mine ? "is-mine" : ""}`}
                  onClick={() => poll.status === "OPEN" && vote(poll.id, opt.id)}
                >
                  <div className="poll-option__fill" style={{ width: `${pct}%` }} />
                  <div className="poll-option__row">
                    <span>{opt.text}</span>
                    <span>
                      {opt.votes} · {pct}%
                    </span>
                  </div>
                </div>
              );
            })}
            {canModerate && poll.status === "OPEN" && (
              <Button size="sm" variant="ghost" onClick={() => close(poll.id)}>
                cerrar encuesta
              </Button>
            )}
          </Panel>
        );
      })}
    </div>
  );
}
