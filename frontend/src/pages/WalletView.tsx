import { useEffect, useState } from "react";
import { payments, users } from "../lib/endpoints";
import { ApiError } from "../lib/api";
import type { PaymentOut, WalletOut } from "../lib/types";
import { Button, Empty, Panel, Tag } from "../components/ui";

const KIND_LABEL: Record<string, string> = {
  add_track: "canción añadida",
  track_played: "tu canción sonó",
  vote: "voto en la cola",
  poll_created: "encuesta creada",
  poll_vote: "voto en encuesta",
  game_win: "ronda ganada",
  payment: "compra de créditos",
  bonus: "bono",
  spend: "gasto",
  boost: "impulsaste una canción",
};

const PRESETS = [100, 500, 1000];

const PAYMENT_STATUS_LABEL: Record<PaymentOut["status"], string> = {
  PENDING: "pendiente",
  PROCESSED: "procesado",
  CREDITS_GRANTED: "acreditado",
  FAILED: "falló",
};

export function WalletView() {
  const [wallet, setWallet] = useState<WalletOut | null>(null);
  const [purchases, setPurchases] = useState<PaymentOut[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    users.wallet().then(setWallet);
    payments.list().then(setPurchases);
  }, []);

  async function buy(credits: number) {
    setError("");
    setBusy(true);
    try {
      const { checkout_url } = await payments.checkout(credits);
      window.location.href = checkout_url;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "no se pudo iniciar la compra");
      setBusy(false);
    }
  }

  if (!wallet) return <Empty>cargando saldo…</Empty>;

  return (
    <div>
      <h1>Créditos</h1>
      <Panel accent style={{ marginBottom: 24 }}>
        <span className="mono" style={{ fontSize: 12, color: "var(--dim)" }}>
          saldo disponible
        </span>
        <div className="mono" style={{ fontSize: 40, fontWeight: 700, color: "var(--signal)" }}>
          {wallet.credits}
        </div>
      </Panel>

      <Panel style={{ marginBottom: 24 }}>
        <h3>comprar créditos</h3>
        <p style={{ color: "var(--dim)", fontSize: 13 }}>
          te lleva a la pasarela de pago; los créditos se acreditan al confirmarse.
        </p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {PRESETS.map((amount) => (
            <Button key={amount} size="sm" disabled={busy} onClick={() => buy(amount)}>
              {amount} créditos
            </Button>
          ))}
        </div>
        {error && (
          <p className="error-text" style={{ marginTop: 8 }}>
            {error}
          </p>
        )}
      </Panel>

      {purchases !== null && purchases.length > 0 && (
        <>
          <h3>compras</h3>
          <Panel style={{ padding: 0, marginBottom: 24 }}>
            {purchases.map((p) => (
              <div
                key={p.id}
                className="queue-item"
                style={{ gridTemplateColumns: "1fr auto", padding: "12px 16px" }}
              >
                <div className="queue-item__meta">
                  <div className="queue-item__title">{p.credits} créditos</div>
                  <div className="queue-item__artist mono">
                    {new Date(p.created_at).toLocaleString()}
                  </div>
                </div>
                <Tag live={p.status === "CREDITS_GRANTED"}>{PAYMENT_STATUS_LABEL[p.status]}</Tag>
              </div>
            ))}
          </Panel>
        </>
      )}

      <h3>movimientos</h3>
      <Panel style={{ padding: 0 }}>
        {wallet.transactions.length === 0 && <Empty>sin movimientos todavía</Empty>}
        {wallet.transactions.map((tx) => (
          <div
            key={tx.id}
            className="queue-item"
            style={{ gridTemplateColumns: "1fr auto", padding: "12px 16px" }}
          >
            <div className="queue-item__meta">
              <div className="queue-item__title">{KIND_LABEL[tx.kind] ?? tx.kind}</div>
              <div className="queue-item__artist mono">
                {new Date(tx.created_at).toLocaleString()}
              </div>
            </div>
            <span
              className="mono"
              style={{ color: tx.amount >= 0 ? "var(--frequency)" : "var(--alert)", fontWeight: 700 }}
            >
              {tx.amount >= 0 ? "+" : ""}
              {tx.amount}
            </span>
          </div>
        ))}
      </Panel>
    </div>
  );
}
