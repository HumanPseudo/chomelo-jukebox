import { useCallback, useEffect, useState, type FormEvent } from "react";
import { offers } from "../../lib/endpoints";
import { useJukebox } from "../../lib/jukeboxContext";
import { ApiError } from "../../lib/api";
import type { OfferCreate, OfferOut, OfferUpdate, RedemptionOut } from "../../lib/types";
import { Button, Empty, Field, Input, Panel, Tag } from "../../components/ui";

const EMPTY_FORM: OfferCreate = {
  merchant: "",
  title: "",
  description: "",
  terms: "",
  image_url: "",
  cost_credits: 100,
  stock_total: 10,
};

const REDEMPTION_LABEL: Record<RedemptionOut["status"], string> = {
  PENDING: "pendiente",
  APPROVED: "aprobado",
  REDEEMED: "entregado",
  CANCELLED: "cancelado",
  EXPIRED: "vencido",
};

export function AdminOffersTab() {
  const { jukebox, lastEvent } = useJukebox();
  const [list, setList] = useState<OfferOut[]>([]);
  const [redemptions, setRedemptions] = useState<RedemptionOut[]>([]);
  const [form, setForm] = useState<OfferCreate>(EMPTY_FORM);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    const [nextOffers, nextRedemptions] = await Promise.all([
      offers.list(jukebox.id),
      offers.redemptions(jukebox.id),
    ]);
    setList(nextOffers);
    setRedemptions(nextRedemptions);
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

  function setField<K extends keyof OfferCreate>(key: K, value: OfferCreate[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function create(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await offers.create(jukebox.id, form);
      setForm(EMPTY_FORM);
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "no se pudo crear la oferta");
    } finally {
      setSaving(false);
    }
  }

  async function changeOffer(offerId: number, payload: OfferUpdate) {
    setBusyId(offerId);
    setError("");
    try {
      await offers.update(jukebox.id, offerId, payload);
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "no se pudo actualizar la oferta");
    } finally {
      setBusyId(null);
    }
  }

  async function changeRedemption(redemptionId: number, status: RedemptionOut["status"]) {
    setBusyId(redemptionId);
    setError("");
    try {
      await offers.updateRedemption(jukebox.id, redemptionId, status);
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "no se pudo actualizar el canje");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      {error && (
        <p className="error-text" style={{ marginBottom: 12 }} role="alert">
          {error}
        </p>
      )}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 24, alignItems: "start" }}>
        <Panel>
          <h3 style={{ marginTop: 0 }}>publicar oferta</h3>
          <form onSubmit={create}>
            <Field label="comercio">
              <Input value={form.merchant} onChange={(e) => setField("merchant", e.target.value)} />
            </Field>
            <Field label="título">
              <Input value={form.title} onChange={(e) => setField("title", e.target.value)} />
            </Field>
            <Field label="descripción">
              <Input
                value={form.description}
                onChange={(e) => setField("description", e.target.value)}
              />
            </Field>
            <Field label="condiciones">
              <Input value={form.terms} onChange={(e) => setField("terms", e.target.value)} />
            </Field>
            <Field label="coste en créditos">
              <Input
                type="number"
                value={form.cost_credits}
                onChange={(e) => setField("cost_credits", Number(e.target.value))}
              />
            </Field>
            <Field label="cupos">
              <Input
                type="number"
                value={form.stock_total}
                onChange={(e) => setField("stock_total", Number(e.target.value))}
              />
            </Field>
            <Button type="submit" size="sm" disabled={saving}>
              {saving ? "publicando…" : "publicar"}
            </Button>
          </form>
        </Panel>

        <div>
          <h3>ofertas publicadas</h3>
          {list.length === 0 && <Empty>sin ofertas</Empty>}
          {list.map((offer) => (
            <Panel key={offer.id} style={{ marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <div>
                  <span className="mono" style={{ fontSize: 11, color: "var(--dim)" }}>
                    {offer.merchant}
                  </span>
                  <h3 style={{ margin: "4px 0 8px" }}>{offer.title}</h3>
                </div>
                <Tag live={offer.status === "ACTIVE"}>{offer.status}</Tag>
              </div>
              <div className="mono" style={{ fontSize: 12, color: "var(--dim)" }}>
                {offer.cost_credits} CR · {offer.stock_remaining}/{offer.stock_total} cupos
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busyId === offer.id}
                  onClick={() =>
                    changeOffer(offer.id, {
                      status: offer.status === "ACTIVE" ? "PAUSED" : "ACTIVE",
                    })
                  }
                >
                  {offer.status === "ACTIVE" ? "pausar" : "activar"}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busyId === offer.id}
                  onClick={() => changeOffer(offer.id, { stock_total: offer.stock_total + 10 })}
                >
                  +10 cupos
                </Button>
                <Button
                  size="sm"
                  variant="danger"
                  disabled={busyId === offer.id}
                  onClick={() => changeOffer(offer.id, { status: "CLOSED" })}
                >
                  cerrar
                </Button>
              </div>
            </Panel>
          ))}

          <h3>canjes</h3>
          {redemptions.length === 0 && <Empty>sin canjes</Empty>}
          {redemptions.map((redemption) => (
            <Panel key={redemption.id} style={{ marginBottom: 12, padding: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <div>
                  <div className="queue-item__title">{redemption.offer_title}</div>
                  <div className="mono" style={{ fontSize: 11, color: "var(--dim)" }}>
                    usuario #{redemption.user_id} · {redemption.credits_spent} CR
                  </div>
                </div>
                <Tag live={redemption.status === "APPROVED"}>
                  {REDEMPTION_LABEL[redemption.status]}
                </Tag>
              </div>
              {redemption.code && (
                <div className="mono" style={{ marginTop: 8, color: "var(--signal)" }}>
                  {redemption.code}
                </div>
              )}
              <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
                {redemption.status === "PENDING" && (
                  <Button
                    size="sm"
                    disabled={busyId === redemption.id}
                    onClick={() => changeRedemption(redemption.id, "APPROVED")}
                  >
                    aprobar
                  </Button>
                )}
                {redemption.status === "APPROVED" && (
                  <Button
                    size="sm"
                    disabled={busyId === redemption.id}
                    onClick={() => changeRedemption(redemption.id, "REDEEMED")}
                  >
                    marcar entregado
                  </Button>
                )}
                {(redemption.status === "PENDING" || redemption.status === "APPROVED") && (
                  <Button
                    size="sm"
                    variant="danger"
                    disabled={busyId === redemption.id}
                    onClick={() => changeRedemption(redemption.id, "CANCELLED")}
                  >
                    cancelar
                  </Button>
                )}
              </div>
            </Panel>
          ))}
        </div>
      </div>
    </div>
  );
}
