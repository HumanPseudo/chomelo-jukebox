# Chomelo Jukebox — Frontend

React + Vite + TypeScript. Sin librería de UI: sistema de diseño propio
("Señal Pirata", tema cyberpunk) en `src/styles/`.

Son **dos apps en un solo proyecto** (Vite multi-página), pensadas para
correr en **puertos distintos** para que sus sesiones (`localStorage`)
nunca se pisen en el mismo navegador:

- `index.html` / `App.tsx` — app de **oyentes**: cola, votar, encuestas,
  minijuego, créditos, perfil. Sin ninguna ruta de administración.
- `admin.html` / `AdminApp.tsx` — **consola de admin**: reproductor real
  (conectado a las bocinas), moderar la cola, lanzar encuestas/rondas,
  gestionar miembros. Solo entra quien tenga rol MODERATOR+ en la jukebox.

Comparten `src/lib/`, `src/components/` y las pestañas de
`src/pages/jukebox/` (`PollsTab`, `GamesTab`, `MembersTab`, `AdminTab`).

## Correr en desarrollo

```bash
npm install
npm run dev                              # oyentes, :5173
VITE_ENTRY=admin npm run dev -- --port 5174   # admin, :5174
```

O con el resto del stack: `docker compose up -d` desde la raíz del repo
(servicios `frontend` y `admin`, puertos 5173/5174).

## Estructura

- `src/lib/` — cliente API (`api.ts`), tipos que reflejan los schemas del
  backend (`types.ts`), auth (`auth.tsx`), WebSocket por jukebox
  (`useJukeboxSocket.ts`)
- `src/components/` — piezas de UI reutilizables (`Panel`, `Button`, …) y
  los shells de cada app (`AppShell`, `AdminShell`)
- `src/pages/` — vistas de la app de oyentes; `src/pages/jukebox/` son
  las pestañas compartidas dentro de una frecuencia
- `src/pages/admin/` — vistas exclusivas de la consola de admin
- `src/styles/tokens.css` — la paleta y tipografías; punto de partida
  para cualquier cambio visual

Ver `AGENTS.md` en la raíz para las convenciones del proyecto.
