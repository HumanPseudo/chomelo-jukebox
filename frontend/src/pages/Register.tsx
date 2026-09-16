import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { ApiError } from "../lib/api";
import { Button, Field, Input, Panel } from "../components/ui";

export function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await register(email, password, displayName || undefined);
      navigate("/jukeboxes", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "no se pudo conectar con el servidor");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <div className="auth__panel">
        <div className="auth__brand">
          <span className="mark">⌁</span>
          <h1>Nueva identidad</h1>
          <p className="auth__tagline">alta en la red · sin datos de más</p>
        </div>
        <Panel accent>
          <form onSubmit={onSubmit}>
            <Field label="correo">
              <Input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoFocus
              />
            </Field>
            <Field label="nombre visible (opcional)">
              <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
            </Field>
            <Field label="contraseña · mínimo 8 caracteres" error={error}>
              <Input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Field>
            <Button type="submit" disabled={busy} style={{ width: "100%" }}>
              {busy ? "creando…" : "unirse a la red"}
            </Button>
          </form>
        </Panel>
        <p className="auth__switch">
          ¿ya tienes acceso? <Link to="/login">sintonizar</Link>
        </p>
      </div>
    </div>
  );
}
