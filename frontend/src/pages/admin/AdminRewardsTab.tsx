import { useCallback, useEffect, useState } from "react";
import { jukeboxes, rewards } from "../../lib/endpoints";
import { useJukebox } from "../../lib/jukeboxContext";
import { ApiError } from "../../lib/api";
import type { MemberOut, WalletOut } from "../../lib/types";
import { Button, Empty, Field, Input, Panel, Tag } from "../../components/ui";

function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `adm-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function AdminRewardsTab() {
  const { jukebox } = useJukebox();
  const [members, setMembers] = useState<MemberOut[] | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [wallet, setWallet] = useState<WalletOut | null>(null);
  const [amount, setAmount] = useState(10);
  const [reason, setReason] = useState("");
  const [idempotencyKey, setIdempotencyKey] = useState(newIdempotencyKey);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadMembers = useCallback(async () => {
    const list = await jukeboxes.members(jukebox.id);
    setMembers(list);
    setSelected((current) =>
      current !== null && list.some((m) => m.user_id === current)
        ? current
        : (list[0]?.user_id ?? null),
    );
  }, [jukebox.id]);

  const loadWallet = useCallback(
    async (userId: number) => {
      setWallet(null);
      try {
        setWallet(await rewards.wallet(jukebox.id, userId));
        setError("");
      } catch {
        setError("no se pudo leer el saldo de este miembro");
      }
    },
    [jukebox.id],
  );

  useEffect(() => {
    loadMembers().catch(() => setError("no se pudo cargar la lista de miembros"));
  }, [loadMembers]);

  useEffect(() => {
    if (selected !== null) loadWallet(selected);
  }, [selected, loadWallet]);

  async function apply(sign: 1 | -1) {
    if (selected === null) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await rewards.adjust(jukebox.id, selected, {
        amount: sign * amount,
        reason: reason.trim(),
        idempotency_key: idempotencyKey,
      });
      setIdempotencyKey(newIdempotencyKey());
      setNotice(`saldo actual: ${result.credits} créditos`);
      setReason("");
      await loadWallet(selected);
    } catch (err) {
      if (err instanceof ApiError && err.code === "insufficient_balance") {
        setError("el miembro no tiene créditos suficientes");
      } else if (err instanceof ApiError && err.code === "member_not_found") {
        setError("ese usuario ya no es miembro");
      } else {
        setError(err instanceof ApiError ? err.message : "no se pudo aplicar el ajuste");
      }
    } finally {
      setBusy(false);
    }
  }

  const canApply =
    selected !== null &&
    Number.isInteger(amount) &&
    amount >= 1 &&
    amount <= 10000 &&
    reason.trim().length >= 3 &&
    !busy;

  if (members === null) return <Empty>cargando recompensas…</Empty>;

  return (
    <div>
      {error && (
        <p className="error-text" style={{ marginBottom: 12 }} role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="mono" style={{ color: "var(--frequency)", fontSize: 13, marginTop: 0 }}>
          {notice}
        </p>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "minmax(180px, 1fr) 2fr", gap: 16 }}>
        <Panel>
          <h3 style={{ marginTop: 0 }}>miembros</h3>
          {members.length === 0 ? (
            <Empty>sin miembros</Empty>
          ) : (
            <div style={{ display: "grid", gap: 6 }}>
              {members.map((m) => (
                <button
                  key={m.user_id}
                  type="button"
                  className={`btn ${selected === m.user_id ? "btn--primary" : "btn--ghost"}`}
                  onClick={() => setSelected(m.user_id)}
                >
                  {m.display_name || `usuario #${m.user_id}`}
                </button>
              ))}
            </div>
          )}
        </Panel>

        <div>
          <Panel>
            <h3 style={{ marginTop: 0 }}>ajustar puntos</h3>
            <p style={{ color: "var(--dim)", fontSize: 13, marginTop: 0 }}>
              los puntos son créditos de la wallet. cada ajuste queda registrado en el ledger y en la
              auditoría.
            </p>
            <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 12 }}>
              <span className="mono" style={{ fontSize: 32 }}>
                {wallet ? wallet.credits : "—"}
              </span>
              <span style={{ color: "var(--dim)", fontSize: 13 }}>créditos disponibles</span>
              {selected !== null && (
                <Tag>{members.find((m) => m.user_id === selected)?.role}</Tag>
              )}
            </div>
            <Field label="cantidad">
              <Input
                type="number"
                min={1}
                max={10000}
                value={amount}
                onChange={(e) => setAmount(Number(e.target.value))}
              />
            </Field>
            <Field label="motivo">
              <Input
                value={reason}
                maxLength={200}
                placeholder="ej: premio del sorteo"
                onChange={(e) => setReason(e.target.value)}
              />
            </Field>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <Button disabled={!canApply} onClick={() => apply(1)}>
                asignar puntos
              </Button>
              <Button variant="danger" disabled={!canApply} onClick={() => apply(-1)}>
                quitar puntos
              </Button>
            </div>
          </Panel>

          <h3>movimientos</h3>
          <Panel style={{ padding: 0 }}>
            {!wallet ? (
              <Empty>cargando movimientos…</Empty>
            ) : wallet.transactions.length === 0 ? (
              <Empty>sin movimientos todavía</Empty>
            ) : (
              wallet.transactions.map((tx) => (
                <div
                  key={tx.id}
                  className="queue-item"
                  style={{ gridTemplateColumns: "1fr auto", padding: "12px 16px" }}
                >
                  <div className="queue-item__meta">
                    <div className="queue-item__title">
                      {tx.kind === "admin_adjust" ? "ajuste del admin" : tx.kind}
                      {tx.description ? ` · ${tx.description}` : ""}
                    </div>
                    <div className="queue-item__artist mono">
                      {new Date(tx.created_at).toLocaleString()}
                    </div>
                  </div>
                  <span
                    className="mono"
                    style={{
                      color: tx.amount >= 0 ? "var(--frequency)" : "var(--alert)",
                      fontWeight: 700,
                    }}
                  >
                    {tx.amount >= 0 ? "+" : ""}
                    {tx.amount}
                  </span>
                </div>
              ))
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}
