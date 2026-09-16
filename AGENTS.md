# AGENTS.md — Chomelo Jukebox

Contexto para agentes de codificación (opencode, etc.).

## Proyecto
Chomelo Jukebox: plataforma de jukebox social por internet.
Cola compartida de música, votos, minijuegos, economía virtual, micropagos.

## Stack
- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0 async, PostgreSQL 16, Redis 7, Alembic, WebSockets
- **Worker música**: FastAPI + yt-dlp + ffmpeg (proceso separado)
- **Frontend**: React + Vite + TypeScript (Fase 1 puede ser mínimo)
- **Infra**: Docker Compose (postgres, redis, backend, worker, frontend)
- **Tests**: pytest, pytest-asyncio, Testcontainers

## Arquitectura: Modular Monolith
Módulos con límites claros bajo `backend/app/`:
`api/` (routers), `domain/` (modelos SQLAlchemy), `services/` (lógica),
`providers/` (MusicProvider, PaymentProvider — interfaces intercambiables),
`infra/` (redis, ws manager, rate limit), `core/` (config, security, logging).

## Reglas duras
1. Nunca confiar en el cliente para dinero/puntos/XP. Todo se valida en servidor.
2. Wallet: ledger append-only (`wallet_transactions`), balance con lock (FOR UPDATE).
   PROHIBIDO `balance = balance + x` sin transacción + ledger + idempotency_key.
3. Pagos: verificar firma de webhook + idempotencia (payment_events.provider_event_id UNIQUE).
4. Música: yt-dlp vive SOLO en el worker. El backend habla con él por HTTP.
   `MusicProvider` es una interfaz; `YtDlpMusicProvider` es una implementación.
5. No almacenar audio. Solo metadata + stream URLs efímeras.
6. API versionada: todo bajo `/api/v1`.
7. Autorización por rol de jukebox: OWNER > ADMIN > MODERATOR > MEMBER > GUEST.
8. Un voto por usuario por item: UNIQUE(queue_item_id, user_id).
9. Errors: respuestas JSON consistentes {detail, code}. HTTP codes correctos.
10. Cada fase debe dejar el sistema funcionando y con tests.

## Estilo
- Código limpio, sin sobre-ingeniería (filosofía ponytail/YAGNI).
- Type hints completos. Pydantic para DTOs. Ruff para lint.
- Logging estructurado JSON con request id.
- Commits en español, mensajes claros.

## Estructura de carpetas raíz
```
chomelo/
├── AGENTS.md
├── PLAN.md
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic/
│   ├── app/
│   └── tests/
├── worker/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── main.py
└── frontend/
```

## Cómo correr
```bash
docker compose up -d
# API: http://localhost:8000  (docs: /docs)
# Worker: http://localhost:9000/health
# Frontend: http://localhost:5173
```

## Frontend
React + Vite + TypeScript, sin librería de UI (design system propio).
Tema "Señal Pirata": consola de transmisión clandestina, sin degradados
decorativos — cada color tiene un solo trabajo (ámbar = acción, cian =
en vivo, rojo = alarma), esquinas cortadas en diagonal (`clip-path`) en
vez de `border-radius`. Tipografías autohospedadas (`@fontsource`):
Chakra Petch (UI) + JetBrains Mono (datos/números). Ver
`frontend/src/styles/tokens.css`.
- El WebSocket solo avisa (`queue.updated`, `player.updated`, etc.); los
  datos siempre se re-sincronizan por REST — nunca confiar en el payload
  del evento.
- Panel `/jukeboxes/:id/admin` (reproductor + moderación de cola) solo
  visible para MODERATOR+; el resto de miembros ve la cola en solo lectura.
- Jukebox física real: solo el dispositivo del admin (conectado a las
  bocinas) reproduce audio de verdad (`useAudioSync`, `withAudio` en
  `PlayerReadout`); los oyentes normales solo ven el estado sincronizado,
  nunca intentan transmitir sonido por su propio navegador.

## Modelo de datos: ver PLAN.md sección "Modelo de datos".
## Roadmap por fases: ver PLAN.md.
