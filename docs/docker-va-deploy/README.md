# Docker va deploy

## Fayllar

| Fayl | Mazmun |
|------|--------|
| `docker-compose.yml` | Production-style: `postgres`, `redis`, `api`, `worker`, `beat`, `web`, `bot` (profil) |
| `docker-compose.override.yml` | Dev: kod mount, `uvicorn --reload` |
| `backend/Dockerfile` | Multi-stage: builder + runtime, `tests/` kopiya |
| `backend/docker-entrypoint.sh` | `alembic upgrade head`, keyin asosiy process |
| `frontend/Dockerfile` | Node build + nginx |
| `bot/Dockerfile` | Python + aiogram |
| `Makefile` | `up`, `down`, `migrate`, `test`, `logs`, … |

## Tarmoq

Barcha servislar **`app-network`** bridge tarmog‘ida.

## Healthcheck

- **postgres:** `pg_isready`
- **redis:** `redis-cli ping`
- **api:** Python orqali `GET http://127.0.0.1:8000/health`
- **web** `depends_on` api **healthy**

## Portlar

| Xizmat | Tashqi port |
|--------|-------------|
| web | 80 |
| api | 8000 |

## Tezkor buyruqlar

```bash
docker compose up -d --build
make migrate
make test
docker compose logs -f api worker
```

## Production eslatmalari

- `docker-compose.override.yml` ni production serverda olib tashlang yoki `COMPOSE_FILE` bilan boshqaring.
- `JWT_SECRET`, `ENCRYPTION_MASTER_KEY_B64`, AI kalitlari — faqat xavfsiz muhitda.
- TLS (HTTPS/WSS) — tashqi reverse proxy (Caddy, Traefik, nginx) orqali.

Batafsil qadamlar: [../../INSTALL.md](../../INSTALL.md).
