import { useCallback, useEffect, useState } from "react";
import { jukeboxes, payments } from "../../lib/endpoints";
import { useJukebox } from "../../lib/jukeboxContext";
import { ApiError } from "../../lib/api";
import type { PricingOut } from "../../lib/types";
import { Button, Field, Input, Panel } from "../../components/ui";

export function AdminPaymentsTab() {
  const { jukebox, reloadJukebox } = useJukebox();
  const [cooldown, setCooldown] = useState(jukebox.add_track_cooldown_seconds);
  const [cost, setCost] = useState(jukebox.add_track_cost_credits);
  const [boostCost, setBoostCost] = useState(jukebox.boost_cost_credits);
  const [pricing, setPricing] = useState<PricingOut | null>(null);
  const [price, setPrice] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const reloadPricing = useCallback(async () => {
    const next = await payments.pricing();
    setPricing(next);
    setPrice(next.cents_per_credit);
  }, []);

  useEffect(() => {
    setCooldown(jukebox.add_track_cooldown_seconds);
    setCost(jukebox.add_track_cost_credits);
    setBoostCost(jukebox.boost_cost_credits);
    reloadPricing();
  }, [
    jukebox.add_track_cooldown_seconds,
    jukebox.add_track_cost_credits,
    jukebox.boost_cost_credits,
    reloadPricing,
  ]);

  async function save() {
    setSaving(true);
    setError("");
    try {
      await Promise.all([
        jukeboxes.update(jukebox.id, {
          add_track_cooldown_seconds: cooldown,
          add_track_cost_credits: cost,
          boost_cost_credits: boostCost,
        }),
        payments.updatePricing(jukebox.id, {
          cents_per_credit: price,
          currency: pricing?.currency ?? "cop",
        }),
      ]);
      await Promise.all([reloadJukebox(), reloadPricing()]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "no se pudo guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <Panel>
        <h3 style={{ marginTop: 0 }}>economía de la frecuencia</h3>
        <p style={{ color: "var(--dim)", fontSize: 13, marginTop: 0 }}>
          el precio de compra es global; los costes internos son de esta jukebox.
        </p>
        <Field label={`precio de 1 crédito en céntimos (${pricing?.currency.toUpperCase() ?? "COP"})`}>
          <Input
            type="number"
            value={price}
            onChange={(e) => setPrice(Number(e.target.value))}
          />
        </Field>
        <Field label="cooldown para canción gratis (segundos)">
          <Input
            type="number"
            value={cooldown}
            onChange={(e) => setCooldown(Number(e.target.value))}
          />
        </Field>
        <Field label="costo en créditos para añadir durante cooldown">
          <Input
            type="number"
            value={cost}
            onChange={(e) => setCost(Number(e.target.value))}
          />
        </Field>
        <Field label="costo en créditos para impulsar (boost)">
          <Input
            type="number"
            value={boostCost}
            onChange={(e) => setBoostCost(Number(e.target.value))}
          />
        </Field>
        {error && <p className="error-text">{error}</p>}
        <Button size="sm" disabled={saving || !pricing} onClick={save}>
          {saving ? "guardando…" : "guardar"}
        </Button>
      </Panel>
    </div>
  );
}
