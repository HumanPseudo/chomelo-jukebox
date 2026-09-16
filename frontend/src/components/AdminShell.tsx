import { Link, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { SignalDot } from "./ui";

export function AdminShell() {
  const { user, logout } = useAuth();

  return (
    <div className="shell">
      <aside className="shell__rail">
        <Link to="/" className="shell__brand" style={{ textDecoration: "none" }}>
          <span className="shell__brand-mark" style={{ color: "var(--alert)" }}>
            ⌁
          </span>
          CHOMELO ADMIN
        </Link>
        <div className="shell__user" style={{ marginTop: "auto" }}>
          <SignalDot state="live" />
          <span className="mono">{user?.display_name ?? user?.email}</span>
          <button className="shell__logout" onClick={logout}>
            salir
          </button>
        </div>
      </aside>
      <main className="shell__main">
        <Outlet />
      </main>
    </div>
  );
}
