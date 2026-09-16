# PLAN.md — Chomelo Jukebox: Roadmap por fases

Estado del proyecto y plan de trabajo. Actualizar el checkbox al completar cada fase.
**No avanzar a la siguiente fase sin que la actual esté funcionando y verificada.**

## Estado actual

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

## FASE 10 — Wallet + Ledger
wallet + wallet_transactions (append-only), FOR UPDATE, idempotency keys,
endpoints de consulta. Sin pagos aún.

## FASE 11 — Micropagos
`PaymentProvider` (ABC) + implementación (Stripe o equivalente),
checkout, webhook con verificación de firma, idempotencia de eventos,
flujo PENDING→PROCESSED→CREDITS_GRANTED.

## FASE 12 — WebSockets
Canales por jukebox `/ws/jukebox/{id}`, broadcast de cola/player/votos/polls/juegos,
Redis Pub/Sub para escalar. Reconexión y auth por token.

## FASE 13 — Seguridad avanzada
Hardening: headers, CORS estricto, rate limits globales, audit log de acciones
sensibles, revisión de superficie de ataque.

## FASE 14 — Tests de concurrencia
Votos simultáneos, transacciones de wallet simultáneas, webhooks duplicados,
recompensas duplicadas. asyncio.gather + Testcontainers.

## FASE 15 — Observabilidad
Métricas Prometheus, dashboards Grafana, tracing (OpenTelemetry) si aporta.

## FASE 16 — CI/CD
GitHub Actions: lint → unit → integration → build → security scan → image.

## FASE 17 — Deployment
Deploy a VPS/servidor del usuario, dominios, TLS, backups de Postgres.

## FASE 18 — Frontend (transversal, empezar tras Fase 5)
SPA (React/Vite o Angular — decidir antes): Home, Login, Jukebox, Player, Queue,
Search, Profile, Polls, Games, Wallet. Conexión WS en vivo.

---

## Riesgos documentados (Fase 0)

- yt-dlp/YouTube: solo para uso privado/aprendizaje; `MusicProvider` permite migrar.
- Stream URLs expiran (~6h): re-resolver con backoff.
- Minijuegos: economía ganada ≠ economía comprada (evitar mecánicas de apuesta).
- Pagos reales: regulación; MVP usa modo test del proveedor.
