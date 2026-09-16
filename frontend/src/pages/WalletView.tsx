import { useEffect, useState } from "react";
import { users } from "../lib/endpoints";
import type { WalletOut } from "../lib/types";
import { Empty, Panel } from "../components/ui";

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
};

export function WalletView() {
  const [wallet, setWallet] = useState<WalletOut | null>(null);

  useEffect(() => {
    users.wallet().then(setWallet);
  }, []);

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
