import { useEffect, useState } from "react";
import { jukeboxes } from "../../lib/endpoints";
import { useJukebox } from "../../lib/jukeboxContext";
import { ApiError } from "../../lib/api";
import { Button, Field, Input, Panel } from "../../components/ui";

export function AdminPaymentsTab() {
  const { jukebox, reloadJukebox } = useJukebox();
  const [cooldown, setCooldown] = useState(jukebox.add_track_cooldown_seconds);
  const [cost, setCost] = useState(jukebox.add_track_cost_credits);
  const [boostCost, setBoostCost] = useState(jukebox.boost_cost_credits);
  const [creditPrice, setCreditPrice] = useState(jukebox.credit_price_cents);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setCooldown(jukebox.add_track_cooldown_seconds);
    setCost(jukebox.add_track_cost_credits);
    setBoostCost(jukebox.boost_cost_credits);
    setCreditPrice(jukebox.credit_price_cents);
  }, [
    jukebox.add_track_cooldown_seconds,
    jukebox.add_track_cost_credits,
    jukebox.boost_cost_credits,
    jukebox.credit_price_cents,
  ]);

  async function save() {
    setSaving(true);
    setError("");
    try {
      await jukeboxes.update(jukebox.id, {
        add_track_cooldown_seconds: cooldown,
        add_track_cost_credits: cost,
        boost_cost_credits: boostCost,
        credit_price_cents: creditPrice,
      });
      await reloadJukebox();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "no se pudo guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <Panel>
        <h3 style={{ marginTop: 0 }}>pagos y precios</h3>
        <p style={{ color: "var(--dim)", fontSize: 13, marginTop: 0 }}>
          control total de la economía de esta frecuencia: precio del crédito en
          COP y créditos cobrados por cada evento de pago.
        </p>
        <Field label="precio de 1 crédito en céntimos (COP)">
          <Input
            type="number"
            value={creditPrice}
            onChange={(e) => setCreditPrice(Number(e.target.value))}
          />
        </Field>
        <Field label="cooldown para canción gratis (segundos)">
          <Input
            type="number"
            value={cooldown}
            onChange={(e) => setCooldown(Number(e.target.value))}
          />
        </Field>
        <Field label="créditos por añadir canción durante cooldown">
          <Input
            type="number"
            value={cost}
            onChange={(e) => setCost(Number(e.target.value))}
          />
        </Field>
        <Field label="créditos por impulsar (boost)">
          <Input
            type="number"
            value={boostCost}
            onChange={(e) => setBoostCost(Number(e.target.value))}
          />
        </Field>
        {error && <p className="error-text">{error}</p>}
        <Button size="sm" disabled={saving} onClick={save}>
          {saving ? "guardando…" : "guardar"}
        </Button>
      </Panel>
    </div>
  );
}
