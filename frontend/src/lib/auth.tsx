import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { tokens } from "./api";
import { auth as authApi, users } from "./endpoints";
import type { UserOut } from "./types";

interface AuthState {
  user: UserOut | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);

  async function refreshUser() {
    if (!tokens.access) {
      setUser(null);
      return;
    }
    try {
      setUser(await users.me());
    } catch {
      tokens.clear();
      setUser(null);
    }
  }

  useEffect(() => {
    refreshUser().finally(() => setLoading(false));
  }, []);

  async function login(email: string, password: string) {
    const res = await authApi.login(email, password);
    tokens.set(res.access_token, res.refresh_token);
    await refreshUser();
  }

  async function register(email: string, password: string, displayName?: string) {
    const res = await authApi.register(email, password, displayName);
    tokens.set(res.access_token, res.refresh_token);
    await refreshUser();
  }

  function logout() {
    authApi.logout();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
