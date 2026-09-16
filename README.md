# Chomelo Jukebox

Jukebox social por internet: colas compartidas, votos, minijuegos, créditos.

## Quickstart

```bash
docker compose up -d
```

- Web: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Worker: http://localhost:9000/health

## Estructura

- `backend/` — FastAPI + WebSockets + SQLAlchemy async
- `worker/` — Worker yt-dlp (resolver URLs)
- `frontend/` — React + Vite + TS
- `docker-compose.yml` — Postgres + Redis + backend + worker
