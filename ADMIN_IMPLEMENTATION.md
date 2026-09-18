# ADMIN_IMPLEMENTATION.md — Consola de operaciones

Implementación del rediseño del panel de administración descrito en
`ADMIN_AUDIT.md`. Resumen de decisiones, cambios y cómo verificarlo.

## Objetivo
Convertir `/jukeboxes/:id/admin` en una consola real de operaciones (resumen,
reproductor, moderación de cola, miembros, actividad, auditoría) sin romper los
contratos existentes ni la identidad visual "Señal Pirata".

## Decisiones
- **Roles**: el código manda. Solo existen `ADMIN` y `MEMBER`; el prompt original
  mencionaba OWNER/MODERATOR/GUEST y ya no existen. La autorización se valida
  siempre en el backend; la UI solo oculta/deshabilita.
- **Sin React Query**: se mantiene el patrón del proyecto (`useEffect` + refetch
  disparado por eventos WebSocket). El WS solo avisa (`queue.updated`,
  `player.updated`); los datos se re-sincronizan por REST. Volumen bajo, sin
  sobre-ingeniería.
- **El `<audio>` real no se mueve**: sigue viviendo en `AdminJukeboxLayout`, que
  permanece montado al navegar entre pestañas, para no cortar la música.
- **Actividad sin sistema de eventos nuevo**: la actividad es una consulta
  agregada de tablas existentes (`queue_items`, `votes`, `polls`, `poll_votes`,
  `game_rounds`, `game_attempts`, `jukebox_members`). No se creó un bus de
  eventos ni una tabla `activity`.
- **`/admin/audit` sigue siendo superusuario-only**. La pestaña Auditoría solo se
  muestra si `user.is_superuser`; el backend devuelve 403 en caso contrario.
- **Sin métricas inventadas**: no hay "online members" ni economía por jukebox en
  la API, así que no se muestran.

## Backend
- `app/api/schemas/auth.py`: `UserOut.is_superuser: bool = False`.
- `app/api/routes/users.py`: `/users/me` expone `is_superuser`.
- `app/api/schemas/activity.py` (nuevo): `ActivityOut{id, kind, user_id,
  display_name, title, subtitle, created_at}`.
- `app/services/activity_service.py` (nuevo): `recent_activity(db, jukebox_id,
  *, limit=30)`, mezcla fuentes por fecha desc y resuelve `display_name` desde
  `profiles`. Nunca revela el título secreto de una ronda abierta.
- `app/api/routes/jukeboxes.py`: `GET /{jukebox_id}/activity?limit=` (default 30,
  `ge=1 le=100`) con `require_role(Role.ADMIN)`.
- `tests/test_activity.py` (nuevo): 401, 403, 422 (límites), agregación de kinds,
  orden desc, `display_name`, y no-fuga del secreto de ronda.

`kind`s emitidos: `queue.add`, `track.played`, `vote`, `poll.created`,
`poll.vote`, `game.round`, `game.won`, `member.joined`.

## Frontend
Rutas admin (`src/AdminApp.tsx`) y navegación por pestañas en
`src/pages/admin/AdminJukeboxLayout.tsx`:
Resumen · Transmisor · Cola · Encuestas · Adivina la canción · Miembros ·
Actividad · Auditoría (solo superusuario).

- `src/components/AdminShell.tsx`: rail con navegación ("Consolas") y marca de
  superusuario.
- `src/pages/admin/AdminOverview.tsx`: ahora suena, tiles (en cola, votos,
  miembros, encuestas abiertas), siguiente/más votadas, estado de ronda,
  comunidad y feed de movimientos.
- `src/pages/admin/AdminPlayerTab.tsx`: controles (anterior/pausar-reanudar-
  iniciar/siguiente) + slider de seek.
- `src/pages/admin/AdminQueueTab.tsx`: `AddTrackPanel` + moderación (subir,
  bajar, al tope, al fondo, quitar) con autor de cada canción.
- `src/pages/admin/AdminActivityTab.tsx` + `ActivityFeed.tsx`: feed con "ver
  más".
- `src/pages/admin/AdminAuditTab.tsx`: tabla de auditoría con filtro por acción
  y paginación.
- `src/pages/admin/AdminJukeboxList.tsx`: estado de error + reintentar; copy
  corregido (ya no dice "owner").
- `src/pages/jukebox/AdminTab.tsx`: **eliminado** (reemplazado por Overview +
  Player + Queue).
- `src/lib/types.ts` / `endpoints.ts`: `is_superuser`, `ActivityOut`, `AuditOut`,
  `jukeboxes.activity`, `admin.audit`.
- `src/styles/admin.css` (nuevo, importado en `admin-main.tsx`).

## Verificación
- Backend: `cd backend && uv run ruff check app tests && uv run pytest`
  → **166 passed**.
- Frontend: `cd frontend && npx tsc -b && npm run lint && npm run build`
  → sin errores.
- Smoke test contra `docker compose` en marcha:
  - `GET /api/v1/jukeboxes/{id}/activity`: 200 con ADMIN, 401 sin token, 403 con
    MEMBER, 422 con `limit` fuera de rango.
  - `/users/me` devuelve `is_superuser`; `/admin/audit` 403 no-superusuario /
    200 superusuario, con campos que coinciden con `AuditOut`.
  - Admin dev server (`:5174`) sirve `admin.html`, módulos y `admin.css` (200).

## Ajuste: sincronía del temporizador
Bug: el contador de la canción se descuadraba entre oyente y admin, y saltaba
al cambiar de pestaña. Causa: `players.position_ms` es una foto fija que solo se
actualiza en play/pausa/seek; cada cliente la extrapolaba desde su propio
momento de montaje/refetch, así que los relojes divergían.

- Backend: `queue_service.live_position_ms()` adelanta la posición hasta el
  instante de la respuesta mientras `is_playing` (anclada en `players.updated_at`)
  y la recorta a la duración; `GET /queue` la usa. El servidor es la referencia.
- Frontend: `PlayerReadout` extrapola desde `positionAt` (epoch ms local en que
  se recibió la posición del servidor), no desde el montaje del componente. Los
  contextos/`QueueTab` guardan ese `fetchedAt` al hacer fetch, así que cambiar
  de pestaña no reinicia el contador.
- Tests: unitarios de `live_position_ms` (avanza, congelado en pausa, ancla
  naive, recorte por duración) + integración del endpoint con ancla retrasada.

## Fuera de alcance
- E2E de frontend (no hay infraestructura de tests de UI en el repo; se decidió
  no introducir Playwright).
- Economía/micropagos por jukebox y presencia "en línea" (no existen en la API).
