import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { SignalDot } from "./ui";

const NAV = [
  { to: "/jukeboxes", label: "Frecuencias" },
  { to: "/wallet", label: "Créditos" },
  { to: "/profile", label: "Perfil" },
];

export function AppShell() {
  const { user, logout } = useAuth();

  return (
    <div className="shell">
      <aside className="shell__rail">
        <div className="shell__brand">
          <span className="shell__brand-mark">⌁</span>
          CHOMELO
        </div>
        <nav className="shell__nav">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `shell__nav-item ${isActive ? "is-active" : ""}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="shell__user">
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
