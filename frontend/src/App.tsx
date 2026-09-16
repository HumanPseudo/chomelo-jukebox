import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./lib/auth";
import { RequireAuth } from "./components/RequireAuth";
import { AppShell } from "./components/AppShell";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { JukeboxesHome } from "./pages/JukeboxesHome";
import { WalletView } from "./pages/WalletView";
import { ProfileView } from "./pages/ProfileView";
import { JukeboxLayout } from "./pages/jukebox/JukeboxLayout";
import { QueueTab } from "./pages/jukebox/QueueTab";
import { PollsTab } from "./pages/jukebox/PollsTab";
import { GamesTab } from "./pages/jukebox/GamesTab";
import { MembersTab } from "./pages/jukebox/MembersTab";
import { AdminTab } from "./pages/jukebox/AdminTab";

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route
            element={
              <RequireAuth>
                <AppShell />
              </RequireAuth>
            }
          >
            <Route path="/" element={<Navigate to="/jukeboxes" replace />} />
            <Route path="/jukeboxes" element={<JukeboxesHome />} />
            <Route path="/wallet" element={<WalletView />} />
            <Route path="/profile" element={<ProfileView />} />

            <Route path="/jukeboxes/:id" element={<JukeboxLayout />}>
              <Route index element={<QueueTab />} />
              <Route path="polls" element={<PollsTab />} />
              <Route path="games" element={<GamesTab />} />
              <Route path="members" element={<MembersTab />} />
              <Route path="admin" element={<AdminTab />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
