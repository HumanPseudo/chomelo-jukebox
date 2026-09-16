# PLAN.md — Chomelo Jukebox: Roadmap por fases

Estado del proyecto y plan de trabajo. Actualizar el checkbox al completar cada fase.
**No avanzar a la siguiente fase sin que la actual esté funcionando y verificada.**

## Estado actual

**FASE 18 — MVP COMPLETADO ✅.** Frontend React + Vite + TS, tema cyberpunk
propio ("Señal Pirata": consola de transmisión clandestina, sin degradados
tipo IA — colores con un solo trabajo cada uno, cortes en diagonal en vez
de `border-radius`, tipografías autohospedadas Chakra Petch + JetBrains
Mono). Login/registro, lista de jukeboxes (crear/unirse por código), vista
de jukebox con cola en vivo (buscar/añadir/votar), reproductor de solo
lectura para miembros, panel de Admin separado (`/jukeboxes/:id/admin`,
MODERATOR+) con controles del reproductor (play/pause/next) y moderación
de cola, encuestas, minijuego "adivina la canción", créditos (wallet) y
perfil con XP/historial. WebSocket conectado (el evento solo avisa, los
datos se re-sincronizan por REST). Verificado con Playwright real
(capturas de cada vista, sin errores de consola) y en Docker (`docker
compose up -d` levanta también el frontend en :5173).

**FASE 14 — COMPLETADA ✅.** Tests de concurrencia contra Postgres real
(Testcontainers) con `asyncio.gather` y sesiones/conexiones independientes
simulando requests concurrentes: votos simultáneos, créditos/débitos de
wallet simultáneos, webhook duplicado en paralelo, dos respuestas correctas
a la vez en un minijuego. Los tests destaparon **tres carreras reales** que
se corrigieron: creación de wallet sin `ON CONFLICT`, un evento de pago
duplicado que podía reventar con `IntegrityError` sin manejar, dos
jugadores ganando la misma ronda a la vez, y — la más sutil — un
`SELECT ... FOR UPDATE` que bloqueaba correctamente en Postgres pero
devolvía datos obsoletos por el identity map de SQLAlchemy (sin
`populate_existing=True`). 152 tests verdes (147 + 5 de concurrencia).

**FASE 13 — COMPLETADA ✅.** Seguridad avanzada: cabeceras de seguridad
(`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
`Permissions-Policy`, `Cache-Control: no-store`, HSTS+CSP solo en
producción), CORS con origen explícito (nunca `*` + credenciales), rate
limit global por IP (Redis, fail-open) además del de login existente,
audit log append-only de acciones sensibles (`audit_logs` + `is_superuser`
en `users`, endpoint `GET /admin/audit`), handler genérico de excepciones
que nunca filtra internals, saneo de `X-Request-ID`. Verificado en Docker
real con Postgres. 147 tests verdes.

**FASE 12 — COMPLETADA ✅.** WebSockets: canal por jukebox con auth por token
(query JWT), `WSManager` con fan-out local + Redis Pub/Sub (`instance_id` para
evitar duplicados), eventos `queue/ player/poll/game.updated` emitidos desde
services tras commit, suscriptor en lifespan (fail-open). Verificado en Docker
real con dos clientes. 136 tests verdes.

**FASE 11 — COMPLETADA ✅.** Micropagos: `PaymentProvider` (ABC, Stripe +
mock de desarrollo), checkout, webhook con verificación de firma e idempotencia
(evento UNIQUE `provider_event_id`), flujo PENDING→PROCESSED→CREDITS_GRANTED y
abono a la wallet con idempotency key. Verificado con Postgres real.
130 tests verdes. Migración `0009_payments`.

**FASE 10 — COMPLETADA ✅.** Wallet + ledger append-only: `credit`/`debit` con
FOR UPDATE + idempotency keys deterministas, recompensas por acciones (añadir,
reproducir, votos, encuestas, ganar ronda) abonadas vía wallet, endpoints de
consulta. 122 tests verdes. Migración `0008_wallet` aplicada.

**FASE 9 — COMPLETADA ✅.** Motor de minijuegos (interfaz `Game`, Guess the Song
primero): rondas con respuesta secreta, un intento por jugador, cierre automático
por expiración (reloj inyectable), puntos 100-2·elapsed (mín. 10) y XP == puntos.
Verificado con Postgres real + worker. 111 tests verdes, migración `0007_games`.

**FASE 8 — COMPLETADA ✅.** Perfiles con bio + XP y nivel (xp//100 + 1), XP solo
del servidor, `played_at` en reproducción, estadísticas e historial de escucha.
100 tests verdes, migración `0006_profile_xp`.

**FASE 7 — COMPLETADA ✅.** Encuestas con conteos en vivo, cierre automático por
fecha (reloj inyectable) y un voto por usuario. 90 tests verdes, migración
`0005_polls`.

**FASE 5 — COMPLETADA ✅.** Player + cola: modelo QueueItem/Player, agregar/quitar/
reordenar, player autoritativo en servidor, endpoints REST de control, historial.

**FASE 6 — COMPLETADA ✅.** Voto único por usuario (UNIQUE), voto mueve al votar otro
ítem, reordenamiento por score, rate limit Redis.

**FASE 4 — COMPLETADA ✅.** MusicProvider (interfaz) + YtDlpProvider (HTTP→worker),
worker con búsqueda/metadata/stream reales con yt-dlp, caché de metadata en Redis con
TTL, manejo de expiración de stream URLs (6h). Verificado con YouTube real.
53 tests verdes (backend 44 + worker 9).

**FASE 3 — COMPLETADA ✅.** Sesiones de jukebox: CRUD, roles OWNER/ADMIN/MODERATOR/MEMBER/GUEST,
permisos por jerarquía, invitaciones por código (unirse = MEMBER), transferencia de propiedad,
33 tests verdes y migración `0002_jukeboxes` aplicada a Postgres.

**FASE 2 — COMPLETADA ✅.** Registro/login/refresh con JWT (access 15min + refresh 7d),
bcrypt, `GET /users/me` protegido, rate limit en login con Redis (resiliente a caída de Redis),
16 tests verdes y migración Alembic aplicada a Postgres en Docker.

**FASE 1 — COMPLETADA ✅.** Verificada: `docker compose up -d` levanta
backend + db + redis + worker con healthchecks, tests verdes y Alembic conectando a Postgres.

---

## FASE 0 — Arquitectura ✅
Completada en conversación: modular monolith Python/FastAPI + worker yt-dlp separado,
PostgreSQL + Redis, WebSocket, JWT, ledger auditable, roadmap de 18 fases.

## FASE 1 — Proyecto base + Docker ✅ (COMPLETADA)

**Objetivo:** `docker compose up -d` levanta backend + db + redis + worker,
con healthchecks y tests básicos pasando.

**Entregables (todos completados):**
- [x] `backend/app/api/router.py` — agrega routers bajo `/api/v1`
- [x] `backend/app/core/config.py` — pydantic-settings (CHOMELO_*, DATABASE_URL, REDIS_URL,
      JWT_SECRET, JWT_EXPIRE_MINUTES, WORKER_URL)
- [x] `backend/app/db/session.py` — engine async + `get_db` dependency
- [x] `backend/app/db/base.py` — Base declarativo + naming convention + TimestampMixin
- [x] `backend/app/core/logging.py` — logging JSON + middleware request-id
- [x] `backend/app/core/exceptions.py` — AppError + handler global
- [x] `backend/.env.example`
- [x] `worker/` — FastAPI mínima: `GET /health`, stub `POST /resolve`
      (acepta `{url}`, devuelve 501 Not Implemented; yt-dlp llega en Fase 4)
- [x] `docker-compose.yml` — servicios: `db` (postgres:16), `redis` (7),
      `backend` (uvicorn --reload, puerto 8000), `worker` (puerto 9000).
      Healthchecks en db, redis, backend y worker. Volúmenes para hot-reload en dev.
      (db en `127.0.0.1:5433` y redis en `127.0.0.1:6379` para evitar conflictos locales)
- [x] `backend/tests/test_health.py` — 5 tests (health v1, root, 404, 405, AppError)
- [x] Alembic inicializado con env.py async (sin migraciones de modelos aún — Fase 2)

**Verificación (ejecutada):**
```bash
docker compose up -d --build          # ✓ todos healthy
curl localhost:8000/health            # ✓ {"status":"ok","service":"chomelo-backend"}
curl localhost:9000/health            # ✓ {"status":"ok","service":"chomelo-worker"}
docker compose exec backend alembic upgrade head   # ✓ conecta a Postgres
cd backend && uv run pytest -v        # ✓ 5 passed
cd backend && uv run ruff check .     # ✓ All checks passed
```

**Conceptos que se aprenden:** estructura de app FastAPI, dependency injection,
settings por entorno, Docker Compose con healthchecks, separación app/worker.

---

## FASE 2 — Usuarios + Auth ✅ (COMPLETADA)

**Objetivo:** modelos User/Profile, register/login, JWT access+refresh, bcrypt,
`GET /users/me` protegido, rate limit básico en login.

**Entregables (todos completados):**
- [x] `backend/app/domain/user.py` — `User` (email único, password_hash, is_active)
      y `Profile` (display_name, avatar_url), relationship `lazy="selectin"`
- [x] `backend/app/core/security.py` — bcrypt (hash/verify, sin passlib),
      JWT access 15min + refresh 7d (payload `type`), `get_current_user` dependency
- [x] `backend/app/infra/rate_limit.py` — rate limiter async Redis
      (resiliente: si Redis cae, permite la request)
- [x] `backend/app/api/schemas/auth.py` — RegisterRequest, LoginRequest,
      RefreshRequest, TokenResponse, UserOut
- [x] `backend/app/services/auth_service.py` — register, authenticate, refresh, issue_tokens
- [x] `backend/app/api/routes/auth.py` — `POST /auth/register`, `/auth/login`, `/auth/refresh`
- [x] `backend/app/api/routes/users.py` — `GET /users/me` (requiere Bearer token)
- [x] `backend/app/api/router.py` — incluye routers auth + users bajo `/api/v1`
- [x] `backend/pyproject.toml` — reemplaza `passlib[bcrypt]` por `bcrypt>=4.0`,
      añade `python-jose[cryptography]` y `email-validator`; ruff ignora B008
- [x] `backend/alembic/versions/0001_users_profiles.py` — tablas `users` + `profiles`
- [x] `backend/tests/conftest.py` — engine SQLite in-memory (aiosqlite + StaticPool),
      override de `get_db`
- [x] `backend/tests/test_auth.py` — 11 tests (register, login, me, refresh, errores 401/409/422)

**Verificación (ejecutada):**
```bash
docker compose build backend && docker compose up -d backend   # ✓ healthy
docker compose exec backend alembic upgrade head               # ✓ Running upgrade 0001_users_profiles
curl -X POST localhost:8000/api/v1/auth/register -d '{"email":"demo@chomelo.app","password":"demo1234"}'   # ✓ 201
curl -X POST localhost:8000/api/v1/auth/login -d '{...}'       # ✓ 200 devuelve tokens
curl localhost:8000/api/v1/users/me -H "Authorization: Bearer $TOKEN"   # ✓ 200 {id, email, display_name, ...}
curl localhost:8000/api/v1/users/me (sin token)                # ✓ 401
curl -X POST localhost:8000/api/v1/auth/register (email duplicado)      # ✓ 409 code=email_taken
cd backend && uv run pytest -v                                # ✓ 16 passed (5 health + 11 auth)
cd backend && uv run ruff check . && ruff format --check .     # ✓ All checks passed
```

**Nota:** el refresh emite un JWT nuevo; si ocurre en el mismo segundo que el anterior,
el token puede ser byte-idéntico (payload sub/iat/exp iguales) — comportamiento normal
de JWT sin estado, no es un bug de rotación.

**Conceptos que se aprenden:** auth JWT stateless, hash de contraseñas con bcrypt,
dependencias FastAPI con roles, rate limiting con Redis, mocks de DB en tests async.

## FASE 3 — Jukebox (sesiones) ✅ (COMPLETADA)

**Objetivo:** CRUD jukebox, miembros, roles OWNER/ADMIN/MODERATOR/MEMBER/GUEST,
permisos por rol, invitaciones por código.

**Entregables (todos completados):**
- [x] `backend/app/domain/jukebox.py` — `Role` (StrEnum + ranking), `Jukebox` (name,
      description, owner_id, invite_code único 6-char, is_active), `JukeboxMember`
      (UNIQUE(jukebox_id, user_id), role)
- [x] `backend/app/api/deps.py` — `get_membership` (carga membresía + jukebox,
      404 si no es miembro o inactivo), `require_role(min_role)` factory
- [x] `backend/app/api/schemas/jukebox.py` — JukeboxCreate/Update/Join/Out, MemberOut, RoleUpdate
- [x] `backend/app/services/jukebox_service.py` — create/list/get/update/delete,
      join por código, regenerar código, listar miembros, set_role con reglas de
      jerarquía, remove_member, transferencia de propiedad (owner → nuevo owner)
- [x] `backend/app/api/routes/jukeboxes.py` — `POST/GET /jukeboxes`, `POST /join`,
      `GET/PATCH/DELETE /{id}`, `POST /{id}/invite`, `GET /{id}/members`,
      `PATCH/DELETE /{id}/members/{user_id}`
- [x] `backend/alembic/versions/0002_jukeboxes.py` — tablas `jukeboxes` + `jukebox_members`
      (FK ondelete CASCADE, invitación no ambigua sin O/0/I/1)
- [x] `backend/tests/test_jukebox.py` — 17 tests (crear/listar, join + 404/409,
      permisos crear/actualizar/borrar por rol, lista de miembros, jerarquía de roles,
      transferencia de propiedad, remover miembro)

**Reglas de permisos implementadas:**
- Crear jukebox → requiere auth, autor pasa a OWNER
- Ver/editar nombre/listar miembros → cualquier miembro (GUEST ve)
- Cambiar rol → solo se puede afectar a miembros de rango **menor** que el tuyo,
  y no se puede asignar un rol superior al tuyo; solo OWNER transfiere propiedad
- Borrar jukebox / remover miembro → OWNER (remover: rango menor que el tuyo)
- JOIN por código → default MEMBER, rate limit 10/min por IP, código case-insensitive

**Verificación (ejecutada):**
```bash
docker compose exec backend alembic upgrade head   # ✓ Running upgrade 0001 -> 0002_jukeboxes
POST /api/v1/jukeboxes (with token)                # ✓ 201 {id, name, role: OWNER, invite_code: "JWBYTU", member_count: 1}
POST /api/v1/jukeboxes/join {invite_code}          # ✓ 201 rol MEMBER
GET  /api/v1/jukeboxes/{id}/members                # ✓ [{OWNER dueno}, {MEMBER invitado}]
DELETE /api/v1/jukeboxes/{id} por miembro          # ✓ 403 insufficient_role
cd backend && uv run pytest -v                     # ✓ 33 passed (5 health + 11 auth + 17 jukebox)
cd backend && uv run ruff check . && format --check# ✓ All checks passed
```

**Conceptos que se aprenden:** jerarquía de roles y chequeo de permisos como
dependencias FastAPI, códigos de invitación, transferencia de propiedad, cascade de FKs.

## FASE 4 — Music Provider + yt-dlp ✅ (COMPLETADA)

**Objetivo:** `MusicProvider` (ABC), `YtDlpProvider` HTTP→worker, worker con
búsqueda/metadata/stream reales (yt-dlp), caché de metadata en Redis con TTL,
manejo de expiración de stream URLs.

**Entregables (todos completados):**
- [x] `backend/app/providers/music.py` — `TrackInfo`, `ResolvedTrack` (añade stream_url
      + expires_at), `MusicProviderError` (502), `MusicProvider` (ABC: search/get_track/resolve)
- [x] `backend/app/providers/ytdlp.py` — `YtDlpProvider` implementa la interfaz
      llamando al worker por HTTP (httpx, timeouts, 502 si el worker cae)
- [x] `backend/app/infra/music_cache.py` — caché Redis de TrackInfo con TTL
      (`music_cache_ttl_seconds`, default 1h), resiliente a caída de Redis
- [x] `backend/app/services/music_service.py` — search (directo), get_track (caché+worker),
      resolve_stream (fresco, URLs efímeras)
- [x] `backend/app/api/routes/music.py` — `GET /api/v1/music/search`, `/tracks/{id}`,
      `/tracks/{id}/stream` (requieren auth)
- [x] `backend/app/core/config.py` — `music_cache_ttl_seconds`
- [x] `worker/main.py` — reimplementado: `WorkerError` + handler JSON {detail,code},
      `GET /search`, `GET /tracks/{track_id}`, `GET /tracks/{track_id}/stream`
      con yt-dlp (`bestaudio/best`, noplaylist); stream_url + expires_at (+6h)
- [x] `worker/tests/test_worker.py` — 9 tests (mapping de campos, endpoints, errores)
- [x] `backend/tests/test_music.py` — 11 tests (auth, search, track, stream, 404,
      502 worker caído, unidad de YtDlpProvider con transport mock)

**Verificación (ejecutada, YouTube real):**
```bash
curl localhost:9000/search?q=never+gonna+give+you+up&limit=2   # ✓ {track_id, title, artist, duration, thumbnail}
curl localhost:9000/tracks/dQw4w9WgXcQ                          # ✓ metadata completa
curl localhost:9000/tracks/dQw4w9WgXcQ/stream                   # ✓ stream_url (googlevideo) + expires_at (+6h)
curl localhost:8000/api/v1/music/search?q=neon+trees+animals (Bearer)   # ✓ items reales
curl localhost:8000/api/v1/music/tracks/dQw4w9WgXcQ             # ✓ 200 + Redis TTL ~3600s (track:dQw4w9WgXcQ)
curl localhost:8000/api/v1/music/tracks/dQw4w9WgXcQ/stream      # ✓ 200
curl .../music/search (sin token)                              # ✓ 401
cd backend && uv run pytest -v                                  # ✓ 44 passed
cd worker && uv run pytest -v                                   # ✓ 9 passed
cd backend && worker && uv run ruff check .                     # ✓ All checks passed
```

**Conceptos que se aprenden:** interfaz provider desacoplada del worker, resiliencia
a fallos del worker (502 + caché), URLs de stream efímeras con expiración, `extract_flat`
para búsquedas rápidas y extracción completa bajo demanda.

## FASE 5 — Player + Queue ✅ (COMPLETADA)

Modelo Queue/QueueItem, agregar/quitar/reordenar, estado del player autoritativo
en servidor, endpoints REST de control. Historial.

**Entregables (todos completados):**
- [x] `backend/app/domain/queue.py` — `QueueStatus` (QUEUED/PLAYING/PLAYED/SKIPPED),
      `QueueItem` (metadata desnormalizada + added_by + posición), `Player`
      (current_item FK SET NULL, is_playing, position_ms)
- [x] `backend/app/api/schemas/queue.py` — QueueAdd, ItemMove, SeekRequest,
      QueueItemOut, PlayerStateOut, QueueOut
- [x] `backend/app/services/queue_service.py` — add_to_queue (resuelve metadata vía
      MusicProvider), get_queue (PLAYING primero + QUEUED), get_history (PLAYED),
      remove_item (moderador cualquiera / dueño propio), move_item (clamp + reorden),
      player_play/pause/resume/skip/seek (estado autoritativo en servidor)
- [x] `backend/app/api/routes/queue.py` — `GET/POST .../{id}/queue` (add MEMBER+),
      `DELETE .../queue/{item_id}`, `PATCH .../queue/{item_id}/move` (MODERATOR+),
      `GET .../history`, `POST .../player/{play,pause,resume,next,seek}` (MODERATOR+)
- [x] `backend/alembic/versions/0003_queue.py` — tablas `queue_items` + `players`
      (aplicada: 0002_jukeboxes → 0003_queue)
- [x] `backend/tests/test_queue.py` — 16 tests (permisos MEMBER/GUEST/MODERATOR,
      flujo play/pause/resume/skip, history, seek clamp, quitar propio/ajeno,
      mover/reordenar, 409 item no removible)

**Verificación (ejecutada, con worker real en Docker):**
```bash
docker compose exec backend alembic upgrade head   # ✓ 0002 -> 0003_queue
# jukebox nuevo "Fase5" con demo@chomelo.app:
POST /api/v1/jukeboxes/2/queue {"track_id":"dQw4w9WgXcQ"}  # ✓ 201 "Rick Astley..." 213s QUEUED
POST /api/v1/jukeboxes/2/queue {"track_id":"9bZkp7q19f0"}  # ✓ 201 "GANGNAM STYLE" QUEUED
POST .../player/play   # ✓ 204
GET  .../queue         # ✓ player{playing,current=1} + [PLAYING, QUEUED] con posiciones
POST .../player/next   # ✓ 204
GET  .../history       # ✓ [dQw4w9WgXcQ PLAYED]
POST .../player/seek {"position_ms":42000}  # ✓ 204; player.position_ms=42000, current=2
DELETE .../queue/{current}                  # ✓ 409 item_not_removable
cd backend && uv run pytest -v               # ✓ 60 passed (16 queue nuevos)
cd backend && uv run ruff check .            # ✓ All checks passed
```

**Conceptos que se aprenden:** estado del player autoritativo en servidor (el cliente
solo consulta/controla, nunca define posición), filas de cola con metadata
desnormalizada (sin joins a worker en lectura), transición QUEUED→PLAYING→PLAYED con
timestamps, filtrado de jugadas fuera de la cola activa, permisos diferenciados por
rol (MEMBERS añaden, MODERATORS controlan).

## FASE 6 — Voting ✅ (COMPLETADA)

Voto único por usuario, cooldown, rate limit Redis, reordenamiento por score,
eventos internos. Reglas configurables por jukebox.

**Entregables (todos completados):**
- [x] `backend/app/domain/vote.py` — `Vote` (jukebox_id, queue_item_id, user_id) con
      UNIQUE(queue_item_id, user_id) (regla dura #8) + UNIQUE(jukebox_id, user_id)
      para "un voto por usuario" por jukebox; FK CASCADE
- [x] `backend/alembic/versions/0004_votes.py` — tabla `votes` (aplicada)
- [x] `backend/app/services/vote_service.py` — `cast_vote` (voto único: votar otro ítem
      **mueve** el voto), `remove_vote` (idempotente), rate limit Redis
      `vote:{user}:{jukebox}` 30/min (429 rate_limited), 404 ítem no encontrado,
      409 `item_not_votable` si no está QUEUED
- [x] `backend/app/services/queue_service.py` — `_item_scores` (GROUP BY), `_my_voted_item_ids`,
      `reorder_queue_by_score` (score DESC + posición ASC, solo QUEUED), `get_queue`
      ahora devuelve scores + votos del usuario
- [x] `backend/app/api/schemas/queue.py` — `QueueItemOut` con `score` y `voted_by_me`
- [x] `backend/app/api/routes/queue.py` — `POST/DELETE /{jb}/queue/{item}/vote` (MEMBER+),
      `GET /{jb}/queue` incluye score y voted_by_me
- [x] `backend/tests/helpers.py` — proveedor fake + helpers compartidos (refactor
      futuro para test_queue/test_music)
- [x] `backend/tests/test_vote.py` — 13 tests (401/403 GUEST/404 no miembro/404 ítem,
      voto único que se mueve, idempotencia, reorden por score, empate conserva orden,
      quitar voto + idempotente, 409 en PLAYING/PLAYED)

**Verificación (ejecutada, con worker real en Docker):**
```bash
docker compose exec backend alembic upgrade head   # ✓ 0003_queue -> 0004_votes
POST /api/v1/jukeboxes/2/queue {track} x3          # ✓ 201
GET  /queue  # ✓ voto al último pasa al frente con score=1, voted_by_me=true
POST .../queue/{item}/vote (otro ítem)             # ✓ 204; el voto se movió
DELETE .../queue/{item}/vote                        # ✓ 204 idempotente
POST .../queue/{playing}/vote                       # ✓ 409 item_not_votable
cd backend && uv run pytest -v                      # ✓ 73 passed (13 votes nuevos)
cd backend && uv run ruff check .                   # ✓ All checks passed
```

**Pendiente (diferido a fases posteriores):** eventos internos de votos → se
emitirán con WebSockets (Fase 12); reglas configurables por jukebox (toggles) → se
suman con los ajustes de jukebox de Fase 7.

**Conceptos que se aprenden:** voto único mediante reemplazo (borrar+insertar) con
restricciones UNIQUE en DB como red de seguridad ante concurrencia, orden de cola
derivado del score (nunca almacenado por el cliente), estabilidad del reordenamiento
en empates, score agregado con GROUP BY y votado-por-mí filtrado por usuario autenticado.

## FASE 7 — Polls ✅ (COMPLETADA)

CRUD encuestas, opciones, voto único, cierre automático, resultados.

**Entregables (todos completados):**
- [x] `backend/app/domain/poll.py` — `Poll` (question, created_by, status OPEN/CLOSED,
      closes_at opcional), `PollOption` (cascade delete-orphan), `PollVote`
      (UNIQUE(poll_id, user_id) voto único + UNIQUE(poll_id, option_id, user_id))
- [x] `backend/alembic/versions/0005_polls.py` — tablas `polls`, `poll_options`,
      `poll_votes` (aplicada)
- [x] `backend/app/api/schemas/poll.py` — PollCreate (opciones 2..20, dedupe por
      texto/whitespace), PollVoteRequest, PollOptionOut (votes), PollOut (results,
      my_option_id, total_votes)
- [x] `backend/app/services/poll_service.py` — create/list/get/vote/close/delete;
      **cierre automático** por `closes_at` (comparación naive/aware robusta),
      conteo de resultados con GROUP BY, rate limit Redis 30/min en votos;
      permisos: crear/votar MEMBER+, cerrar/borrar MODERATOR+
- [x] `backend/app/api/routes/polls.py` — `POST/GET /{jb}/polls`, `GET /{jb}/polls/{id}`,
      `POST /{jb}/polls/{id}/vote`, `POST /{jb}/polls/{id}/close`,
      `DELETE /{jb}/polls/{id}`; filtro `?status=OPEN|CLOSED`
- [x] `backend/app/api/router.py` — incluye polls router
- [x] `backend/tests/test_polls.py` — 17 tests (auth/403 GUEST/404 no miembro,
      creación + dedupe de opciones, voto modifica resultados, segundo voto 409,
      opción inválida 404, voto en cerrada 409, cierre automático por fecha,
      cierre manual + resultados, filtro status, borrar 204 + 404 tras borrar)

**Verificación (ejecutada, con Postgres real en Docker):**
```bash
docker compose exec backend alembic upgrade head   # ✓ 0004_votes -> 0005_polls
POST /api/v1/jukeboxes/2/polls {3 opciones, closes_at>now}  # ✓ 201 OPEN
POST .../polls/1/vote {option_id}                  # ✓ 204; resultado total=1, my=2, Pop=1
POST .../polls/1/vote (de nuevo)                   # ✓ 409 poll_already_voted
POST .../polls/1/close                              # ✓ CLOSED total=1
POST .../polls/1/vote (cerrada)                    # ✓ 409 poll_closed
DELETE .../polls/1                                 # ✓ 204
cd backend && uv run pytest -v                      # ✓ 90 passed (17 polls nuevos)
cd backend && uv run ruff check .                   # ✓ All checks passed
```

**Pendiente (diferido):** eventos internos de polls/votos → con WebSockets (Fase 12);
reglas configurables por jukebox (toggles de voting/polls) → quedan para el ajuste
de jukebox de las fases 7+.

**Conceptos que se aprenden:** voto único con restricciones UNIQUE en DB, estado de
encuesta que pasa a CLOSED de forma perezosa (al leer/votar, sin job en background),
resultados agregados con GROUP BY + voto propio filtrado por usuario, comparación de
timestamps robusta entre SQLite (naive) y Postgres (aware) para tests y prod.

## FASE 8 — Profiles + XP ✅ (COMPLETADA)

Perfil completo, XP/niveles, estadísticas, historial de escucha, achievements básicos.

**Entregables (todos completados):**
- [x] `Profile` ampliado: `bio` + `xp` (servidor-default 0) + función `level_for_xp`
      (nivel = xp // 100 + 1)
- [x] `backend/alembic/versions/0006_profile_xp.py` — columnas `bio` y `xp` (aplicada)
- [x] `backend/app/services/xp_service.py` — `grant_xp(db, user_id, amount)`;
      **solo el servidor otorga XP** (el payload XP del cliente se ignora):
      ADD_TRACK=10, TRACK_PLAYED=20 (al empezar a sonar tu canción),
      CAST_VOTE=5, CREATE_POLL=10, POLL_VOTE=5
- [x] XP integrado como mismo commit en los servicios: `queue_service`
      (add_to_queue, player_play, player_skip), `vote_service.cast_vote`,
      `poll_service` (create_poll, cast_vote)
- [x] `backend/app/api/schemas/profile.py` — ProfileUpdate, ProfileOut
      (xp, level, stats), ListenHistoryItem
- [x] `backend/app/services/profile_service.py` — perfil + estadísticas
      (tracks_added, tracks_played, votes_cast, polls_created, poll_votes_cast),
      historial de escucha (tracks propias que ya sonaron, con jukebox)
- [x] `backend/app/api/routes/profile.py` — `GET/PATCH /users/me/profile`,
      `GET /users/me/listen-history?limit=`; registro en router
- [x] `played_at` ahora se marca al **iniciar** la reproducción (estado PLAYING),
      no solo al saltar; `tracks_played` y el historial cuentan lo que ya sonó
- [x] `backend/tests/test_profile.py` — 10 tests (auth 401, perfil por defecto,
      XP por add/play/vote/poll, XP nunca viene del cliente, PATCH de perfil,
      historial de escucha, límites de nivel)

**Verificación (ejecutada, con Postgres real + worker en Docker):**
```bash
docker compose exec backend alembic upgrade head   # ✓ 0005_polls -> 0006_profile_xp
POST /jukeboxes/3/queue fJ9rUzIMcZQ y vbvyNnw8Qjg   # ✓ 2 items
GET /users/me/profile                               # ✓ xp=20, tracks_added=2
POST /player/play                                    # ✓ 204 -> xp=40, tracks_played=1
POST /queue/{id}/vote                                # ✓ 204 (+5)
POST /polls + POST /polls/{id}/vote                  # ✓ 201/204 (+10/+5)
GET /users/me/profile                                # ✓ xp=60, votes=1, polls=1, poll_votes=1
GET /users/me/listen-history                         # ✓ 1 entrada (canción sonando)
cd backend && uv run pytest -q                       # ✓ 100 passed (10 nuevos)
cd backend && uv run ruff check .                    # ✓ All checks passed
```

**Pendiente (diferido):** achievements básicos (medallas automáticas); eventos de
XP/listen para otros miembros → con WebSockets (Fase 12); backfill de XP de acciones
previas a esta fase (no se otorgó XP retroactivo).

**Conceptos que se aprenden:** XP como **lado del servidor** (incremento en el mismo
commit que la acción, jamás aceptado del cliente), nivel derivado (no almacenado),
estadísticas calculadas con GROUP BY agregados, historial de escucha como "lo que
empezó a sonar" con `played_at` al iniciar, coherencia entre evento (start) y métrica.

## FASE 9 — Minijuegos ✅ (COMPLETADA)

Motor extensible de juegos (interfaz Game), Guess the Song primero.
Recompensas vía wallet (nunca directas) — el crédito se conectará en Fase 10.

**Entregables (todos completados):**
- [x] `backend/app/games/base.py` — interfaz `Game` (ABC) + `RoundData`: `build()`
      construye la ronda (respuesta secreta + opciones) y `grade()` califica;
      motor extensible: añadir un juego = registrar una clase
- [x] `backend/app/games/guess_the_song.py` — Guess the Song: elige al azar una
      canción reproducida en el jukebox como respuesta y 3 distracciones
      (opciones en orden aleatorio, la respuesta nunca se revela en OPEN)
- [x] `backend/app/games/__init__.py` — registro `GAMES` por clave
- [x] `backend/app/domain/game.py` — `GameRound` (track una respuesta, options
      JSON, status OPEN/FINISHED, starts_at/expires_at) y `GameAttempt`
      (UNIQUE(round_id, user_id): un intento por jugador)
- [x] `backend/alembic/versions/0007_games.py` — tablas `game_rounds`,
      `game_attempts` (aplicada)
- [x] `backend/app/services/game_service.py` — iniciar ronda (rate limit Redis,
      no permite duplicada OPEN), listar/detalle con **cierre automático** por
      `expires_at` (reloj inyectable `get_clock`), responder: gana el primer
      acierto (cierra la ronda), puntos 100-2·seg (mín. 10), XP == puntos
      (solo servidor), errores 404/409/422
- [x] `backend/app/api/deps.py` — `get_clock` (fuente de tiempo inyectable para
      probar expiración)
- [x] `backend/app/api/routes/games.py` — `POST/GET /{jb}/games/{game}/rounds`,
      `GET .../rounds/{id}`, `POST .../rounds/{id}/answer`; MEMBER+ para
      iniciar/responder; registro en router
- [x] `backend/tests/test_games.py` — 11 tests (auth 401, juego 404, sin
      repertorio 409, crear + duplicada 409, acierto cierra la ronda + XP,
      fallo 0 puntos sin filtrar respuesta, 409 al terminar, un intento por
      jugador, opción inválida 422, expiración automática con reloj fake,
      GUEST 403)

**Verificación (ejecutada, con Postgres real + worker en Docker):**
```bash
docker compose exec backend alembic upgrade head   # ✓ 0006_profile_xp -> 0007_games
POST /jukeboxes/{jb}/games/guess_the_song/rounds   # ✓ 201 OPEN, 4 opciones, secret=None
POST (de nuevo)                                       # ✓ 409 round_in_progress
POST rounds/{id}/answer {opci[fn]}                    # ✓ correct=False, points=0, OPEN
POST answer (mismo jugador)                           # ✓ 409 already_answered
POST answer (otro jugador, acierta)                   # ✓ correct=True, points=10, FINISHED, +10 XP
GET round                                             # ✓ FINISHED; correct_title visible solo terminada
GET rounds?status=FINISHED                            # ✓ [1]
cd backend && uv run pytest -q                        # ✓ 111 passed (11 nuevos)
cd backend && uv run ruff check . && ruff format      # ✓ limpio
```

**Nota de diseño:** `.distinct() + order_by(func.random())` falla en Postgres
(ORDER BY debe ir en la select-list); se resuelve con subquery.

**Pendiente (diferido):** recompensas en créditos vía wallet → Fase 10; ranking de
jugadores por puntos acumulados; más juegos sobre el mismo motor; eventos de
rondas/intentos → WebSockets (Fase 12).

**Conceptos que se aprenden:** motor de juegos con interfaz y registro extensible
(no un switch de casos), respuesta oculta que solo se revela al terminar, "primer
acierto gana" como condición de cierre natural, expiración perezosa con reloj
inyectable para tests, un intento por jugador con UNIQUE, puntos con decaimiento
por velocidad (100 - 2·elapsed) y XP == puntos otorgado solo por el servidor.

## FASE 10 — Wallet + Ledger ✅ (COMPLETADA)
wallet + wallet_transactions (append-only), FOR UPDATE, idempotency keys,
endpoints de consulta. Sin pagos aún.

**Entregables (todos completados):**
- [x] `backend/app/domain/wallet.py` — `Wallet` (1:1 con user, saldo credits) y
      `WalletTransaction` (ledger **append-only**: nunca se actualiza ni borra),
      UNIQUE(wallet_id, idempotency_key)
- [x] `backend/alembic/versions/0008_wallet.py` — tablas `wallets` y
      `wallet_transactions` (aplicada)
- [x] `backend/app/services/wallet_service.py` — `credit` (solo el servidor) y
      `debit` con **SELECT ... FOR UPDATE** + ledger + idempotencia por clave
      (`INSERT ... ON CONFLICT DO NOTHING` portable SQLite/Postgres); saldo
      insuficiente = 409; `balance` y `list_transactions`
- [x] `backend/app/api/schemas/wallet.py` + `routes/wallet.py` —
      `GET /users/me/wallet` (saldo + últimos 20 movs) y
      `GET /users/me/wallet/transactions` (paginado)
- [x] Recompensas conectadas (regla dura: vía wallet, nunca directas):
      añadir canción +1 (`add_track`), canción reproducida +1 para quien la
      añadió (`track_played`), voto en cola +1 (`vote`), crear encuesta +2
      (`poll_created`), votar encuesta +1 (`poll_vote`), ganar ronda = puntos
      (`game_win`). **Idempotency keys deterministas** por evento
      (p. ej. `game_win:{user}:{round}`) → reintentos duplicados = no-op
- [x] `backend/tests/test_wallet.py` — 11 tests (auth 401, wallet a demanda,
      crédito idempotente, importe inválido 422, débito ok/saldo 409/débito
      idempotente, recompensa por add/play/vote/poll/game-win == puntos)

**Verificación (ejecutada, Postgres real):**
```bash
docker compose exec backend alembic upgrade head   # ✓ 0007_games -> 0008_wallet
GET /users/me/wallet                               # ✓ credits 0
+ canción + voto + play + encuesta(+2) + voto poll  # ✓ credits 6
GET /users/me/wallet                               # ✓ ledger con kinds/amounts/desc
GET /users/me/wallet/transactions?limit=2&offset=3 # ✓ paginación [vote, add_track]
cd backend && uv run pytest -q                     # ✓ 122 passed (11 nuevos)
cd backend && uv run ruff check .                  # ✓ All checks passed
```

**Pendiente (diferido):** comprar créditos → Fase 11 (Micropagos); gastar
créditos en ventajas aún no definidas; gateway de débito con `PaymentProvider`.

**Conceptos que se aprenden:** ledger append-only con balance como proyección
(no = alfa de movimientos), lock pessimista FOR UPDATE para el balance, clave de
idempotencia determinista por evento (el reintento es un no-op seguro), `ON
CONFLICT DO NOTHING` portátil entre SQLite y Postgres, "el servidor abona, el
cliente nunca" como principio de economía segura.

## FASE 11 — Micropagos ✅ (COMPLETADA)
`PaymentProvider` (ABC) + implementación (Stripe), checkout, webhook con
verificación de firma, idempotencia de eventos, flujo
PENDING→PROCESSED→CREDITS_GRANTED.

**Entregables (todos completados):**
- [x] `backend/app/providers/payments.py` — `PaymentProvider` (ABC) con
      `create_checkout` y `verify_event` (normaliza a `ProviderEvent`
      independiente del vendor): `StripePaymentProvider` (SDK Stripe, verifica
      firma con `Webhook.construct_event`) y `MockPaymentProvider` SOLO dev
      (sin credenciales, para desarrollo/verificación)
- [x] `backend/app/core/config.py` — `payment_provider` (mock/stripe),
      `stripe_secret_key`, `stripe_webhook_secret`, `cents_per_credit` (10)
- [x] `backend/app/domain/payment.py` — `Payment` (PENDING/PROCESSED/
      CREDITS_GRANTED/FAILED) y `PaymentEvent` con `provider_event_id` UNIQUE
      (regla dura #3); migración `0009_payments`
- [x] `backend/app/services/payment_service.py` — `create_checkout` (créditos
      5-10000, precio cents), `consume_webhook` (firma → idempotencia por evento
      → crédito de wallet con idempotency clave `payment:{provider}:{session}` →
      CREDITS_GRANTED; evento desconocido = seguro, sin crédito), `list_payments`
- [x] `backend/app/api/routes/payments.py` — `POST /payments/webhook` (público),
      `POST /users/me/payments/checkout` (201) y `GET /users/me/payments`;
      `get_payment_provider` como dependency inyectable en tests
- [x] `backend/tests/test_payments.py` — 8 tests (auth 401, firma inválida 400,
      checkout PENDING + precio, importe fuera de rango 422, webhook concede una
      vez, evento duplicado no duplica crédito, evento nuevo misma sesión no
      duplica, sesión desconocida segura)

**Verificación (ejecutada, Postgres real + proveedor mock):**
```bash
docker compose exec backend alembic upgrade head   # ✓ 0008_wallet -> 0009_payments
POST /users/me/payments/checkout {credits:500}    # ✓ 201 PENDING, cents 5000
POST /payments/webhook (firma test)                # ✓ {"received":true}
POST webhook mismo evento                          # ✓ {"duplicate":true}
POST webhook con firma mala                        # ✓ 400 invalid_signature
GET /users/me/payments                             # ✓ CREDITS_GRANTED
GET /users/me/wallet                               # ✓ 6 -> 506, ledger "payment" +500
cd backend && uv run pytest -q                     # ✓ 130 passed (8 nuevos)
cd backend && uv run ruff check . && ruff format   # ✓ limpio
```

**Pendiente (diferido):** claves/modo real de Stripe en `.env` de producción;
URL de éxito/cancelación reales del frontend; reembolsos; avisos al usuario por
WebSockets (Fase 12); gastar créditos en ítems/ventajas.

**Conceptos que se aprenden:** proveedor de pagos tras una interfaz intercambiable
(migrar Stripe por otro proveedor no toca el dominio), webhook como la ÚNICA fuente
de verdad del pago (el cliente nunca dice "pagué"), verificación de firma con el
payload crudo (nunca re-serializar antes de verificar), doble capa de idempotencia
(evento UNIQUE + wallet idempotency key), los 200 idempotentes evitan reintentos
sin fin del proveedor.

## FASE 12 — WebSockets ✅ (COMPLETADA)
Canales por jukebox `/ws/jukebox/{id}`, broadcast de cola/player/votos/polls/juegos,
Redis Pub/Sub para escalar. Reconexión y auth por token.

**Entregables (todos completados):**
- [x] `backend/app/infra/ws_manager.py` — `WSManager` con conexiones agrupadas por
      jukebox, `broadcast_local` (envío directo) + publicación en Redis Pub/Sub
      (channel `chomelo:ws`, mensaje con `instance_id` que el suscriptor ignora para
      no duplicar) y suscriptor por instancia (fail-open: sin Redis sigue el
      broadcast local)
- [x] `backend/app/infra/events.py` — `notify_jukebox(jukebox_id, type, **data)`:
      emisor único usado por los services
- [x] `backend/app/api/routes/ws.py` — `WS /ws/jukebox/{id}` con auth por
      `?token=` (JWT, solo tipo access), membresía obligatoria (no-GUEST) y
      handshake: `connected` + bucle keepalive (`ping`→`pong`); cierra 4401
      (auth) / 4403 (sin membresía)
- [x] Integración en services (eventos tras commit): `queue.updated` (añadir/
      quitar/mover/votar), `player.updated` (play/pause/resume/next/seek),
      `poll.updated` (crear/votar/cerrar/borrar/auto-cierre), `game.updated`
      (ronda iniciada / respondida / auto-fin)
- [x] Lifespan en `main.py`: arranca/para el suscriptor; `settings.ws_pubsub_enabled`
      (false en tests)
- [x] `backend/tests/test_ws.py` — 6 tests (token inválido 4401, no miembro 4403,
      hello, broadcast de cola/player/poll/game, aislamiento por jukebox)
      verificado con `starlette.TestClient`

**Verificación (ejecutada, Postgres real + Redis Docker):**
```bash
WS /ws/jukebox/4?token=…                       # ✓ {"event":"connected",...}
POST /jukeboxes/4/queue                        # ✓ {"event":"queue.updated","data":{"item_id":14}}
POST /jukeboxes/4/queue/14/vote                # ✓ {"event":"queue.updated",...}
POST /jukeboxes/4/player/{pause,resume,next}   # ✓ {"event":"player.updated",...}
cd backend && uv run pytest -q                 # ✓ 136 passed (6 nuevos)
cd backend && uv run ruff check . && format    # ✓ limpio
```

**Pendiente (diferido):** reconexión con backoff en el cliente + "last known
state" (el cliente re-sincroniza con REST al reconectar); suscripción a eventos
de wallet/usuario (canales `/ws/me`); `subscribe` por suscripción selectiva.

**Conceptos que se aprenden:** WebSocket como canal push (los datos viajan por
REST, el WS avisa para refetch), auth por query con JWT (los navegadores no
envían headers en WS), agrupación por sala (jukebox_id) con fan-out solo a la
sala, Redis Pub/Sub como bus horizontal entre instancias detrás del balanceador,
guarda `instance_id` para no duplicar el envío local, evento mínimo (aviso, no
payload completo) = YAGNI.

## FASE 13 — Seguridad avanzada ✅ (COMPLETADA)

Hardening: headers, CORS estricto, rate limits globales, audit log de acciones
sensibles, revisión de superficie de ataque.

**Entregables (todos completados):**
- [x] `backend/app/core/security_headers.py` — middleware que añade
      `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`,
      `Permissions-Policy`, `Cache-Control: no-store` a toda respuesta HTTP;
      `Strict-Transport-Security` y `Content-Security-Policy` solo si
      `environment == "production"` (no rompen `/docs` en desarrollo);
      suprime la cabecera `Server`
- [x] `backend/app/core/cors.py` — `CORSMiddleware` con `cors_origins`
      explícitos por config; `allow_credentials=False` si se usa `*`
      (nunca origen comodín + credenciales)
- [x] `backend/app/core/rate_limit_middleware.py` — `GlobalRateLimitMiddleware`
      (Redis, fail-open) por IP, excluye `/health`, `/docs`, `/redoc`,
      `/openapi.json`, `/payments/webhook` y `OPTIONS`
- [x] `backend/app/services/auth_service.py` — segundo rate limit de login
      por IP (`login_ip:{ip}`) además del existente por email
- [x] `backend/app/domain/audit.py` + `backend/app/services/audit_service.py`
      — `AuditLog` (append-only: quién, qué, cuándo, desde dónde), saneo de
      IP/user-agent contra log injection, `log_action()` usado tras commit
      en acciones sensibles (auth register/login/refresh, crear/borrar
      jukebox, cambio de rol, remover miembro, checkout/webhook de pagos,
      cerrar/borrar encuesta, quitar ítem de cola)
- [x] `backend/app/api/routes/admin.py` — `GET /admin/audit` protegido por
      `is_superuser` (403 `admin_required` si no lo es)
- [x] `backend/app/domain/user.py` — columna `is_superuser` (default false)
- [x] `backend/alembic/versions/0010_audit_logs_superuser.py` — tabla
      `audit_logs` + columna `users.is_superuser` (aplicada)
- [x] `backend/app/core/exceptions.py` — handler genérico de `Exception` que
      loguea el traceback pero responde siempre `{"detail","code":"internal_error"}`
      sin filtrar internos (ni con `debug=True`)
- [x] `backend/app/core/logging.py` — saneo de `X-Request-ID` entrante
      (whitelist de caracteres + longitud máxima) contra spoofing/log injection
- [x] `backend/app/main.py` — `docs_url`/`redoc_url`/`openapi_url`
      deshabilitados en producción; orden de middlewares explícito
- [x] `docker-compose.yml` — `uvicorn --no-server-header`
- [x] `backend/tests/test_security.py` — 11 tests (headers presentes,
      HSTS/CSP solo en producción, CORS origen permitido/rechazado, rate
      limit global bloquea y excluye health/OPTIONS, brute-force de login
      por IP, 500 genérico oculta el error real, saneo de request id,
      audit log con permisos de superusuario, resource_id correcto en
      audit de checkout, docs habilitado en dev)

**Verificación (ejecutada, Postgres real + Redis en Docker):**
```bash
docker compose up -d --build                        # ✓ todos healthy
docker compose exec backend alembic upgrade head     # ✓ 0009_payments -> 0010_audit
curl -sD - localhost:8000/health                     # ✓ headers de seguridad, sin "Server"
curl -sD - -H "Origin: http://localhost:3000" .../jukeboxes  # ✓ access-control-allow-origin ecoado
curl -sD - -H "Origin: http://evil.example" .../jukeboxes    # ✓ sin access-control-allow-origin
POST /auth/register + /auth/login (fase13@chomelo.app)       # ✓ 201/200
UPDATE users SET is_superuser=true (psql directo)             # ✓
GET /admin/audit (Bearer token del mismo user)                 # ✓ 200, incluye auth.register/auth.login
cd backend && uv run pytest -q                        # ✓ 147 passed (11 nuevos)
cd backend && uv run ruff check . && ruff format --check .    # ✓ limpio
```

**Pendiente (diferido):** revocación de tokens (blacklist en Redis);
métricas de seguridad (intentos bloqueados, 4xx/5xx) → Fase 15
(Observabilidad); tests de concurrencia (webhooks/votos duplicados) →
Fase 14; panel de administración más allá de la consulta del audit log.

**Conceptos que se aprenden:** defensa en profundidad con middlewares en
capas (rate limit → headers → CORS, del más interno al más externo),
CSP/HSTS solo tienen sentido detrás de TLS real (por eso solo en
producción), un audit log append-only es la fuente de verdad para
"quién hizo qué" y debe sanear entradas controladas por el cliente
(IP, user-agent, request-id) antes de persistirlas, un handler de
excepciones "catch-all" es la última red para no filtrar tracebacks,
y `is_superuser` como bandera simple es suficiente antes de necesitar
un sistema de roles global (YAGNI).

## FASE 14 — Tests de concurrencia ✅ (COMPLETADA)

Votos simultáneos, transacciones de wallet simultáneas, webhooks duplicados,
recompensas duplicadas. asyncio.gather + Testcontainers.

**Entregables (todos completados):**
- [x] `backend/tests/test_concurrency.py` — 5 tests contra Postgres real
      (Testcontainers, no el SQLite en memoria del resto de la suite, porque
      solo Postgres tiene semántica real de `FOR UPDATE` y de bloqueo en
      `INSERT ... ON CONFLICT`); cada test lanza tareas `asyncio.gather` con
      **sesiones/conexiones independientes** (como requests HTTP distintos)
      y verifica el estado final en la base de datos, no el interleaving
      exacto (para no ser un test frágil):
      - voto simultáneo del mismo usuario a dos ítems: nunca terminan
        sobreviviendo dos votos (UNIQUE(jukebox_id, user_id))
      - 8 créditos concurrentes con la misma `idempotency_key`: se aplica
        una sola vez
      - 5 débitos concurrentes que exceden el saldo: nunca hay sobregiro,
        el número de éxitos es determinista (`saldo // importe`)
      - misma entrega de webhook duplicada dos veces en paralelo: nunca
        avienta una excepción sin manejar y solo abona una vez
      - dos jugadores acertando la misma ronda al mismo tiempo: "primer
        acierto gana" se mantiene, solo un `GameAttempt.correct=True` y
        una recompensa
- [x] `backend/app/infra/db_utils.py` — `dialect_insert()` compartido
      (Postgres/SQLite) para `INSERT ... ON CONFLICT DO NOTHING`, extraído
      de `wallet_service` para reusarlo también en `payment_service`
- [x] `backend/app/services/wallet_service.py` — **tres correcciones**
      encontradas por los tests de concurrencia:
      1. `get_wallet(..., create=True)` creaba la wallet con un `INSERT`
         plano: dos requests concurrentes del mismo usuario por primera vez
         violaban el UNIQUE(user_id). Ahora usa `ON CONFLICT DO NOTHING` +
         re-select.
      2. `_locked_wallet` hacía un `SELECT` sin lock (en `get_wallet`) y
         luego un `SELECT ... FOR UPDATE` del mismo objeto en la misma
         sesión: el lock de Postgres se adquiría correctamente, pero
         SQLAlchemy no refrescaba los atributos del objeto ya presente en
         el identity map, así que `wallet.credits` seguía con el valor
         previo al bloqueo. Con saldo suficiente esto permitía sobregiro
         bajo concurrencia real. Se corrigió añadiendo
         `.execution_options(populate_existing=True)` al `SELECT FOR UPDATE`.
      3. Refactor menor: `_insert()` (privado) pasó a ser
         `dialect_insert()` en `app/infra/db_utils.py`.
- [x] `backend/app/services/payment_service.py` — `consume_webhook` hacía
      "check-then-insert" (`SELECT` de duplicado, luego `INSERT` del
      evento): dos entregas concurrentes del mismo evento (reintento del
      proveedor) podían hacer que la segunda reventara con
      `IntegrityError` sin manejar en el UNIQUE de `provider_event_id`.
      Ahora el `INSERT ... ON CONFLICT DO NOTHING` es la única fuente de
      verdad atómica: si no insertó ninguna fila, es un duplicado seguro.
- [x] `backend/app/services/game_service.py` — `guess()` leía la
      `GameRound` sin lock antes de decidir si cerraba la ronda: dos
      jugadores acertando "a la vez" podían cerrar la ronda y cobrar la
      recompensa los dos. Nuevo helper `_get_round_locked()` con
      `SELECT ... FOR UPDATE` (+ `populate_existing=True`) serializa las
      respuestas por ronda.
- [x] `backend/pyproject.toml` — `testcontainers[postgres]` como
      dependencia de desarrollo (solo se usa en `test_concurrency.py`)

**Verificación (ejecutada, Postgres real vía Testcontainers):**
```bash
cd backend && uv run pytest tests/test_concurrency.py -v   # ✓ 5 passed
cd backend && uv run pytest -q                              # ✓ 152 passed (147 + 5 nuevos)
cd backend && uv run ruff check . && ruff format --check .  # ✓ limpio
```

**Nota de diseño:** el hallazgo más importante fue el del punto 2 de
wallet: `SELECT ... FOR UPDATE` bloquea correctamente en Postgres incluso
si el objeto ya fue leído sin lock antes en la misma sesión — pero
SQLAlchemy, por diseño, no sobreescribe los atributos de un objeto ya
presente en el identity map salvo que se pida explícitamente con
`populate_existing=True`. El resultado sin ese flag es un lock "real" a
nivel de base de datos que protege el orden de escritura, pero con datos
en memoria obsoletos en el momento de decidir — silencioso y sin ningún
error, solo visible con concurrencia real (nunca con SQLite en memoria de
un solo hilo). Se aplicó el mismo flag por consistencia a `game_service`
aunque ahí no había una lectura previa que lo disparara.

**Pendiente (diferido):** tests de concurrencia para `queue_service`
(mover/reordenar ítems simultáneamente) y `poll_service` (cierre
automático concurrente); los tests de esta fase corren contra un
Postgres efímero de Testcontainers y no contra el Postgres de
`docker-compose.yml`, así que no se ejecutan en el flujo normal de
`pytest` sin Docker disponible.

## FASE 15 — Observabilidad
Métricas Prometheus, dashboards Grafana, tracing (OpenTelemetry) si aporta.

## FASE 16 — CI/CD
GitHub Actions: lint → unit → integration → build → security scan → image.

## FASE 17 — Deployment
Deploy a VPS/servidor del usuario, dominios, TLS, backups de Postgres.

## FASE 18 — Frontend ✅ (MVP COMPLETADO)

SPA (React/Vite): Home, Login, Jukebox, Player, Queue, Search, Profile,
Polls, Games, Wallet. Conexión WS en vivo.

**Dirección visual — "Señal Pirata":** una consola de transmisión
clandestina en una ciudad controlada por corporaciones. Referencia
investigada (no un look genérico de IA): identidad ámbar/negro tipo
señalética de peligro (evitando el cliché de degradado morado/verde-ácido
sobre negro), vocabulario del propio dominio (frecuencia, transmisión,
señal) en vez de copy genérico.

**Entregables (todos completados):**
- [x] `frontend/` — Vite + React 19 + TypeScript, sin librería de UI
- [x] `src/styles/tokens.css` — 8 tokens de color con un solo trabajo cada
      uno (ámbar=acción, cian=en vivo, rojo=alarma, sin degradados
      decorativos); dos tipografías autohospedadas (`@fontsource`):
      Chakra Petch (UI) + JetBrains Mono (datos/números)
- [x] `src/styles/global.css` — sistema de componentes propio: `.panel`
      (esquinas cortadas con `clip-path`, nunca `border-radius`), `.btn`
      (hexágono achatado), campos, indicadores de señal con pulso
      (`prefers-reduced-motion` respetado)
- [x] `src/lib/api.ts` — cliente fetch con JWT (access+refresh), reintento
      automático de un 401 tras refrescar el token, `ApiError` tipado
- [x] `src/lib/endpoints.ts` + `types.ts` — funciones y tipos que reflejan
      1:1 los schemas Pydantic del backend
- [x] `src/lib/auth.tsx` — `AuthProvider`/`useAuth`, `RequireAuth` para
      rutas protegidas
- [x] `src/lib/useJukeboxSocket.ts` — WS con reconexión automática
      (backoff fijo 3s); **el evento solo dispara un refetch por REST**,
      nunca se confía en su payload como estado (mismo principio que el
      backend de Fase 12)
- [x] `src/pages/` — Login, Register, JukeboxesHome (crear/unirse por
      código), y bajo `/jukeboxes/:id`: Cola (buscar/añadir/votar +
      reproductor de solo lectura), Encuestas, Adivina la canción,
      Miembros (gestión de roles para ADMIN+), y **Admin** (solo
      MODERATOR+: reproductor con play/pausa/siguiente + moderar cola)
- [x] `src/pages/WalletView.tsx` y `ProfileView.tsx` — saldo/ledger y
      perfil con XP/nivel/estadísticas/historial
- [x] `frontend/Dockerfile` + servicio `frontend` en `docker-compose.yml`
      (bind mount + volumen anónimo para `node_modules`, evita el choque
      glibc/musl entre host y contenedor Alpine)
- [x] Verificado con Playwright real (Chromium): registro → crear
      frecuencia → cola → juego → encuestas → miembros → admin → créditos
      → perfil → vista móvil, sin errores de consola

**Verificación (ejecutada):**
```bash
docker compose up -d --build          # ✓ 5 servicios healthy (+ frontend)
curl localhost:5173                    # ✓ 200
# Playwright: registro real vía /api/v1/auth/register, navegación por
# las 8 vistas, captura de pantalla de cada una (incluida móvil 390px)
# sin CONSOLE ERROR ni PAGE ERROR.
cd frontend && npx tsc -b              # ✓ sin errores de tipos
cd frontend && npm run lint            # ✓ solo warnings de estilo (React
                                        #   fast-refresh / set-state-in-effect,
                                        #   esperables sin librería de fetching)
```

**Pendiente (diferido):** librería de fetching (react-query) si el MVP
crece y el patrón `useEffect` + `useState` empieza a doler; página de
detalle de pago/checkout (Fase 11 ya tiene el backend, falta el botón de
compra); reconexión del WS con "último estado conocido" más agresiva;
tests de componentes (Vitest/Testing Library) — no había suite de frontend
previa que mantener, se puede sumar cuando el UI se estabilice.

**Conceptos que se aprenden:** un sistema de diseño con tokens con
significado (no "azul porque sí") evita el look genérico; WebSocket como
aviso puro y REST como única fuente de verdad también aplica en el
cliente, no solo en el servidor; separar el panel de control (Admin) de
la vista de miembro no es solo un `if` de permisos — es una ruta y una
experiencia distintas; `clip-path` como alternativa consistente a
`border-radius` para una identidad visual que no se parece a un kit SaaS.

---

## Riesgos documentados (Fase 0)

- yt-dlp/YouTube: solo para uso privado/aprendizaje; `MusicProvider` permite migrar.
- Stream URLs expiran (~6h): re-resolver con backoff.
- Minijuegos: economía ganada ≠ economía comprada (evitar mecánicas de apuesta).
- Pagos reales: regulación; MVP usa modo test del proveedor.
