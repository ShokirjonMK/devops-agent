# CHANGELOG

## [Unreleased]

### Added

- Docker Compose: `x-backend-env` anchor, Redis `requirepass` + healthcheck, `postgres_data` / `redis_data` / `ssh_keys` volumes, `API_PORT`, bot uchun `API_BASE_URL`.
- `.env.example`: TZ bilan mos kengaytirilgan o‘zgaruvchilar (DB, Redis, JWT, `API_INTERNAL_SECRET`, AI, agent).
- `Makefile`: `generate-keys`, `test-cov`, `clean`, `shell-api` / `shell-db` (TZ namunasiga yaqin).
- `POST /api/auth/bot-login`: `telegram_id` + `API_INTERNAL_SECRET` bilan JWT (bot uchun 7 kun).
- `MASTER_ENCRYPTION_KEY` (64 hex) qo‘llab-quvvatlash; `ENCRYPTION_MASTER_KEY_B64` bilan orqaga moslik.
- `/api/health`: Celery worker soni (`inspect.stats`), `components.workers`.

### Changed

- API healthcheck: `curl` orqali `GET /api/health`.
- `JWT` algoritm env: `JWT_ALGORITHM`; token muddatlari: `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` (refresh keyingi bosqichda cookie bilan kengayadi).
- `DATABASE_URL` da `postgresql+asyncpg://` berilsa, sync SQLAlchemy uchun avtomatik `postgresql://` ga almashtiriladi (Alembic ham).

### Migration notes

- Eski `pgdata` volume o‘rniga `postgres_data` ishlatiladi: yangi tom yoki `docker compose down -v` dan keyin bazani qayta yaratish kerak bo‘lishi mumkin.

### Docker Compose defaults (mahalliy ishlab chiqish)

- `POSTGRES_*`, `REDIS_PASSWORD`, `DATABASE_URL`, `REDIS_URL`, `CELERY_*`, `JWT_SECRET`, `API_INTERNAL_SECRET` uchun `${VAR:-...}` defaultlari qo‘yilgan; **production** da `.env` da aniq kuchli qiymatlar ishlating.
