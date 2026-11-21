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
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setCooldown(jukebox.add_track_cooldown_seconds);
    setCost(jukebox.add_track_cost_credits);
    setBoostCost(jukebox.boost_cost_credits);
  }, [
    jukebox.add_track_cooldown_seconds,
    jukebox.add_track_cost_credits,
    jukebox.boost_cost_credits,
  ]);

  async function save() {
    setSaving(true);
    setError("");
    try {
      await jukeboxes.update(jukebox.id, {
        add_track_cooldown_seconds: cooldown,
        add_track_cost_credits: cost,
        boost_cost_credits: boostCost,
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
        <h3 style={{ marginTop: 0 }}>economía de la frecuencia</h3>
        <p style={{ color: "var(--dim)", fontSize: 13, marginTop: 0 }}>
          el precio de compra de créditos se toma del servidor; aquí solo controlas los
          costes internos de esta jukebox.
        </p>
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
        <Button size="sm" disabled={saving} onClick={save}>
          {saving ? "guardando…" : "guardar"}
        </Button>
      </Panel>
    </div>
  );
}
