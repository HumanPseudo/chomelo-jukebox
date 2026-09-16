import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { ApiError } from "../lib/api";
import { Button, Field, Input, Panel } from "../components/ui";

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email, password);
      const from = (location.state as { from?: string })?.from ?? "/jukeboxes";
      navigate(from, { replace: true });
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
          <h1>Sintonizar señal</h1>
          <p className="auth__tagline">acceso a la red de jukebox clandestinas</p>
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
            <Field label="contraseña" error={error}>
              <Input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Field>
            <Button type="submit" disabled={busy} style={{ width: "100%" }}>
              {busy ? "conectando…" : "entrar"}
            </Button>
          </form>
        </Panel>
        <p className="auth__switch">
          ¿primera transmisión? <Link to="/register">crear identidad</Link>
        </p>
      </div>
    </div>
  );
}
