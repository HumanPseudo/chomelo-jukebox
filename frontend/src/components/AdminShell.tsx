import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { SignalDot } from "./ui";

function navClass({ isActive }: { isActive: boolean }) {
  return `shell__nav-item ${isActive ? "is-active" : ""}`;
}

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
        <nav className="shell__nav">
          <NavLink to="/" end className={navClass}>
            Consolas
          </NavLink>
          {user?.is_superuser && (
            <span className="shell__nav-item" style={{ cursor: "default" }}>
              superusuario
            </span>
          )}
        </nav>
        <div className="shell__user">
          <SignalDot state="live" />
          <span className="mono">{user?.display_name || user?.email}</span>
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
