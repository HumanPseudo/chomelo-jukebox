# ADMIN_AUDIT.md — Auditoría del panel Admin

Fecha: 2026-09-17. Fuente de verdad: el código actual (no PLAN.md).

## Estado actual

- Dos apps en un solo proyecto Vite, orígenes separados a propósito
  (listener `:5173` / admin `:5174`, `localStorage` independiente).
- App de admin: `admin.html` → `AdminApp.tsx` → `AdminShell` (rail sin
  navegación) → `/` lista de jukeboxes donde soy ADMIN → `/:id`
  (`AdminJukeboxLayout`) con 4 pestañas.
- `AdminJukeboxLayout` es el corazón: monta el `<audio>` real
  (`useAudioSync(enabled=true)`), Wake Lock, Media Session, carga la cola
  una sola vez (`AdminQueueProvider`) y la refresca al recibir
  `queue.updated` / `player.updated`. Roles reales: **solo ADMIN y MEMBER**
  (migración `0012_two_roles`; ya no existen OWNER/MODERATOR/GUEST).
- Pestaña índice (Consola) = `AdminTab`: reproductor con
  anterior/pausa/reanudar/iniciar/siguiente + panel "añadir a la
  transmisión" + moderación de cola (subir / bajar / quitar).
- `Encuestas`, `Adivina la canción` y `Miembros` son componentes
  **compartidos** con la app de oyente (`PollsTab`, `GamesTab`, `MembersTab`).
- No existe Overview, ni Activity, ni vista de Auditoría en la UI.
  El backend tiene `GET /admin/audit` (superuser) pero el frontend no lo
  consume y **ni siquiera sabe si el usuario es superuser**
  (`UserOut` no expone `is_superuser`).

## Funcionalidades existentes (utilizables desde el Admin)

- Player autoritativo: play/pause/resume/next/previous/seek (ADMIN).
- Cola: añadir (MEMBER+), moderar (ADMIN: quitar cualquiera, mover),
  votos, boosts, scores por ítem, historial reproducción.
- Encuestas: crear/votar/cerrar/borrar; resultados y estado OPEN/CLOSED.
- Juego "adivina la canción": iniciar ronda, estado, intentos, puntos.
- Miembros: listar, cambiar rol, expulsar (con salvaguarda `last_admin`).
- Jukebox: nombre/descripción, regenerar código de invitación.
- WebSocket: `queue.updated`, `player.updated`, `poll.updated`,
  `game.updated` (solo avisan; los datos se re-sincronizan por REST).

## Endpoints utilizados hoy por el Admin

| Endpoint | Auth | Uso |
|---|---|---|
| `GET /jukeboxes` | AUTH | lista para elegir consola |
| `GET /jukeboxes/{id}` | MEMBER | metadata + rol + member_count |
| `GET /jukeboxes/{id}/queue` | MEMBER | cola + player (fuente de verdad) |
| `POST/DELETE .../queue/{item}` | ADMIN/MEMBER | quitar ítem |
| `PATCH .../queue/{item}/move` | ADMIN | reordenar |
| `POST .../player/{play,pause,resume,next,previous,seek}` | ADMIN | control |
| `GET .../members`, `PATCH/DELETE .../members/{user}` | MEMBER/ADMIN | gestión |
| `GET/POST .../polls`, `POST .../polls/{id}/close` | MEMBER/ADMIN | encuestas |
| `GET/POST .../games/{key}/rounds` | MEMBER/ADMIN | juego |
| `POST .../invite` | ADMIN | regenerar código |
| `GET /admin/audit` | SUPERUSER | auditoría (NO usada por el UI) |

## Permisos actuales

- Jerarquía real: `ADMIN (100) > MEMBER (50)`.
- `require_role(Role.ADMIN)` en player, move, polls create/close, games
  start, invite, members set/remove. El resto: cualquier miembro.
- `GET /admin/audit` exige `is_superuser` (403 `admin_required` si no).
- Regla `last_admin`: no se puede deshacer al último admin (409).
- La UI solo oculta/deshabilita; la autorización es del backend. Debe
  seguir siendo así.

## Problemas encontrados

1. Sin Overview: el admin no ve de un vistazo qué suena, qué viene,
   quiénes hay, qué encuestas/juegos están abiertos.
2. `AdminTab` mezcla dos jobs distintos (operar el reproductor y moderar la
   cola) en una sola pestaña con un único `busy` compartido.
3. Estados de loading/error pobres: `AdminJukeboxLayout` se queda en
   "sintonizando…" para siempre si falla el fetch (404 `not_member`,
   red caída); `AdminJukeboxList` igual. Promesas sin `.catch` → rejection
   no manejada.
4. Sin vista de Auditoría, y el frontend no puede saber si hay que
   mostrarla (`is_superuser` ausente de `UserOut`).
5. Sin actividad reciente: no existe ningún endpoint que agregue qué pasó
   (quién añadió, votó, qué sonó, rondas, altas de miembros).
6. La moderación de cola no muestra votos/boost/añadido por quién; el
   estado PLAYING no se distingue de QUEUED en la cola del admin.
7. El rail del `AdminShell` no tiene navegación (ni "Consolas" para volver).
8. Sin confirmación para acciones destructivas (expulsar miembro) y sin
   seek; la cola no tiene "mover al top/bottom".
9. Sin refresh periódico si el WebSocket está caído (cola puede quedar
   obsoleta mientras dura la reconexión).

## Funcionalidades reutilizables

- `PlayerReadout` (visual), `AddTrackPanel` (buscar/añadir),
  `PollsTab`, `GamesTab`, `MembersTab` (compartidos), `ui.tsx`
  (Panel/Button/Tag/Empty/SignalDot), tokens de color y cortes en diagonal.
- `useJukeboxSocket` + contexto `AdminQueueProvider` (datos ya alzados al
  layout; no hay que volver a cargar la cola en cada pestaña).

## Gaps

- No hay endpoint de actividad por jukebox (los datos existen en tablas:
  queue_items, votes, poll_votes, game_rounds/game_attempts,
  jukebox_members; falta una consulta agregada).
- `is_superuser` no viaja en `GET /users/me` → el Admin no puede
  decidir si mostrar Auditoría.
- No hay "online/active" (WSManager conoce conexiones pero no se expone
  por API) → **no inventar métricas**; el resumen mostrará solo datos
  reales disponibles.
- No hay economía por jukebox (wallet es global) → el resumen no mostrará
  créditos del jukebox salvo boosts (ya visibles por ítem en la cola).

## Propuesta de arquitectura

Nada de React Query en esta iteración: el frontend ya tiene un patrón
`useEffect + refetch-on-event` homogéneo y el volumen de datos es bajo.
Se mantiene ese patrón (justificado en ADMIN_IMPLEMENTATION.md).

**Navegación del Admin** (`AdminJukeboxLayout`, una pestaña por job):

```
Resumen   → AdminOverview     (qué pasa ahora: player, cola, comunidad,
                               encuestas abiertas, ronda activa, movimientos)
Transmisor → AdminPlayerTab   (control del reproductor + seek)
Cola       → AdminQueueTab    (moderación: estado, votos, boost, mover/poner
                               al tope/fondo, quitar, añadir)
Encuestas  → PollsTab         (compartido, ya integrado)
Juegos     → GamesTab         (compartido, ya integrado)
Miembros   → MembersTab       (compartido, mejorado: código de invitación +
                               confirmación al expulsar)
Actividad  → AdminActivityTab (feed reciente del jukebox)
Auditoría  → AdminAuditTab    (solo si user.is_superuser; log global
                               paginado + filtro por acción)
```

**Backend (mínimo y justificado):**
1. `UserOut.is_superuser: bool` — solo informativo; no cambia
   autorización. Permite al Admin decidir si mostrar "Auditoría".
2. `GET /api/v1/jukeboxes/{id}/activity?limit=` (ADMIN) — agrega datos ya
   existentes (sin sistema de eventos nuevo): añadir canción, canción que
   sonó, voto, encuesta creada, voto de encuesta, ronda iniciada, ronda
   ganada, miembro unido. No filtra internos; respeta estado secret de la
   ronda (no revela la canción correcta en ronda abierta).

**No se toca:** roles, `last_admin`, `GET /admin/audit` (sigue siendo
superuser), contrato de endpoints existentes, WebSocket como aviso puro.