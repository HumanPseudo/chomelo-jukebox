import { useCallback, useEffect, useState } from "react";
import { offers, users } from "../../lib/endpoints";
import { useJukebox } from "../../lib/jukeboxContext";
import { ApiError } from "../../lib/api";
import type { OfferOut, RedemptionOut, WalletOut } from "../../lib/types";
import { Button, Empty, Panel, Tag } from "../../components/ui";

const REDEMPTION_LABEL: Record<RedemptionOut["status"], string> = {
  PENDING: "esperando aprobación",
  APPROVED: "listo para entregar",
  REDEEMED: "entregado",
  CANCELLED: "cancelado",
  EXPIRED: "vencido",
};

export function PrizesTab() {
  const { jukebox, lastEvent } = useJukebox();
  const [list, setList] = useState<OfferOut[] | null>(null);
  const [mine, setMine] = useState<RedemptionOut[]>([]);
  const [wallet, setWallet] = useState<WalletOut | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    const [nextOffers, nextMine, nextWallet] = await Promise.all([
      offers.list(jukebox.id),
      offers.myRedemptions(),
      users.wallet(),
    ]);
    setList(nextOffers);
    setMine(nextMine);
    setWallet(nextWallet);
  }, [jukebox.id]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    if (
      lastEvent?.event === "offer.updated" ||
      lastEvent?.event === "redemption.updated"
    ) {
      reload();
    }
  }, [lastEvent, reload]);

  useEffect(() => {
    const timer = setInterval(reload, 30000);
    return () => clearInterval(timer);
  }, [reload]);

  async function claim(offerId: number) {
    setBusyId(offerId);
    setError("");
    try {
      await offers.claim(jukebox.id, offerId);
      await reload();
    } catch (err) {
      setError(
        err instanceof ApiError && err.code === "insufficient_balance"
          ? "no te alcanzan los créditos"
          : "no se pudo canjear",
      );
    } finally {
      setBusyId(null);
    }
  }

  if (!list) return <Empty>conectando con las ofertas…</Empty>;

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "end",
          gap: 16,
          marginBottom: 16,
        }}
      >
        <div>
          <h1 style={{ marginBottom: 4 }}> Premios</h1>
          <span className="mono" style={{ fontSize: 12, color: "var(--dim)" }}>
            canjea créditos por ofertas de la frecuencia
          </span>
        </div>
        <span className="mono" style={{ color: "var(--signal)", fontSize: 20, fontWeight: 700 }}>
          {wallet?.credits ?? "—"} CR
        </span>
      </div>

      {error && (
        <p className="error-text" style={{ marginBottom: 12 }} role="alert">
          {error}
        </p>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 24, alignItems: "start" }}>
        <div>
          {list.length === 0 && <Empty>no hay ofertas publicadas todavía</Empty>}
          {list.map((offer) => {
            const soldOut = offer.stock_remaining === 0 || offer.status !== "ACTIVE";
            return (
              <Panel key={offer.id} style={{ marginBottom: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                  <div>
                    <span
                      className="mono"
                      style={{ fontSize: 11, color: "var(--dim)", letterSpacing: 1 }}
                    >
                      {offer.merchant}
                    </span>
                    <h3 style={{ margin: "4px 0 8px" }}>{offer.title}</h3>
                  </div>
                  <Tag live={offer.status === "ACTIVE"}>
                    {offer.status === "ACTIVE" ? `${offer.stock_remaining} cupos` : offer.status}
                  </Tag>
                </div>
                <p style={{ fontSize: 13, color: "var(--dim)", marginTop: 0 }}>{offer.description}</p>
                {offer.terms && (
                  <p className="mono" style={{ fontSize: 11, color: "var(--dim)" }}>
                    {offer.terms}
                  </p>
                )}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: 12,
                    marginTop: 16,
                  }}
                >
                  <span className="mono" style={{ color: "var(--signal)", fontSize: 18 }}>
                    {offer.cost_credits} CR
                  </span>
                  {offer.my_redemption_status ? (
                    <Tag>{REDEMPTION_LABEL[offer.my_redemption_status as RedemptionOut["status"]]}</Tag>
                  ) : (
                    <Button
                      size="sm"
                      disabled={soldOut || busyId === offer.id}
                      onClick={() => claim(offer.id)}
                    >
                      {soldOut ? "sin cupos" : busyId === offer.id ? "canjeando…" : "canjear"}
                    </Button>
                  )}
                </div>
                {offer.my_code && (
                  <p className="mono" style={{ marginTop: 12, color: "var(--ink)" }}>
                    código {offer.my_code}
                  </p>
                )}
              </Panel>
            );
          })}
        </div>

        <Panel style={{ padding: 16 }}>
          <h3 style={{ marginTop: 0 }}>mis canjes</h3>
          {mine.length === 0 && <Empty>todavía no canjeaste nada</Empty>}
          {mine.map((redemption) => (
            <div key={redemption.id} style={{ marginBottom: 16, paddingBottom: 12, borderBottom: "1px solid var(--line)" }}>
              <div className="queue-item__title">{redemption.offer_title}</div>
              <div className="mono" style={{ fontSize: 11, color: "var(--dim)" }}>
                {REDEMPTION_LABEL[redemption.status]} · {redemption.credits_spent} CR
              </div>
              {redemption.code && (
                <div className="mono" style={{ marginTop: 6, color: "var(--signal)" }}>
                  {redemption.code}
                </div>
              )}
            </div>
          ))}
        </Panel>
      </div>
    </div>
  );
}
