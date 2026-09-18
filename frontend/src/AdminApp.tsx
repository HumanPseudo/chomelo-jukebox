import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./lib/auth";
import { RequireAuth } from "./components/RequireAuth";
import { AdminShell } from "./components/AdminShell";
import { Login } from "./pages/Login";
import { AdminJukeboxList } from "./pages/admin/AdminJukeboxList";
import { AdminJukeboxLayout } from "./pages/admin/AdminJukeboxLayout";
import { AdminOverview } from "./pages/admin/AdminOverview";
import { AdminPlayerTab } from "./pages/admin/AdminPlayerTab";
import { AdminQueueTab } from "./pages/admin/AdminQueueTab";
import { AdminActivityTab } from "./pages/admin/AdminActivityTab";
import { AdminAuditTab } from "./pages/admin/AdminAuditTab";
import { PollsTab } from "./pages/jukebox/PollsTab";
import { GamesTab } from "./pages/jukebox/GamesTab";
import { MembersTab } from "./pages/jukebox/MembersTab";

export function AdminApp() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route
            path="/login"
            element={
              <Login
                homePath="/"
                showRegister={false}
                title="Consola de admin"
                tagline="control de transmisión · solo para quien administra"
              />
            }
          />

          <Route
            element={
              <RequireAuth>
                <AdminShell />
              </RequireAuth>
            }
          >
            <Route path="/" element={<AdminJukeboxList />} />

            <Route path="/:id" element={<AdminJukeboxLayout />}>
              <Route index element={<AdminOverview />} />
              <Route path="player" element={<AdminPlayerTab />} />
              <Route path="queue" element={<AdminQueueTab />} />
              <Route path="polls" element={<PollsTab />} />
              <Route path="games" element={<GamesTab />} />
              <Route path="members" element={<MembersTab />} />
              <Route path="activity" element={<AdminActivityTab />} />
              <Route path="audit" element={<AdminAuditTab />} />
            </Route>
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
