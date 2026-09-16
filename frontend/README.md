# Chomelo Jukebox — Frontend

React + Vite + TypeScript. Sin librería de UI: sistema de diseño propio
("Señal Pirata", tema cyberpunk) en `src/styles/`.

## Correr en desarrollo

```bash
npm install
npm run dev          # http://localhost:5173, requiere el backend en :8000
```

O con el resto del stack: `docker compose up -d` desde la raíz del repo.

## Estructura

- `src/lib/` — cliente API (`api.ts`), tipos que reflejan los schemas del
  backend (`types.ts`), auth (`auth.tsx`), WebSocket por jukebox
  (`useJukeboxSocket.ts`)
- `src/components/` — piezas de UI reutilizables (`Panel`, `Button`, …) y
  el shell de la app
- `src/pages/` — vistas; `src/pages/jukebox/` son las pestañas dentro de
  una frecuencia (cola, encuestas, juego, miembros, admin)
- `src/styles/tokens.css` — la paleta y tipografías; punto de partida
  para cualquier cambio visual

Ver `AGENTS.md` en la raíz para las convenciones del proyecto.
