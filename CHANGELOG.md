# CHANGELOG

## [2.0.0] - 2026-03-25

### Added

- Alembic **005**: `ai_token_configs`, `server_metrics`, `alert_rules`, `admin_settings`, `notifications`, `platform_audit_logs` (server/task FK lar integer ID ga mos).
- Alembic **006**: `users.role`, `users.settings`, `users.last_seen_at`; `servers` monitoring va `metadata`; `tasks.telegram_message_id`; tizim foydalanuvchisi (`telegram_id = -1`) va `admin_settings` seed.
- RBAC: `Role`, `require_role`; serverlarni yozish faqat **admin**; `POST /api/tasks` uchun **operator**; yangi foydalanuvchilar odatda **operator**, `ADMIN_TELEGRAM_IDS` → **owner**.
- `/api/ai-tokens` (CRUD, `GET /providers`, `POST .../test`), `LLMRouter` (`app/services/llm_router.py`).
- `/api/admin/*`: foydalanuvchilar, sozlamalar, `stats/overview`, `system-ai` (vault + `SYSTEM_USER_ID`), audit loglar + CSV export.
- `platform_audit` yordamchi servisi; shifrlash: yangi yozuvlar **32 bayt salt + 600k** PBKDF2, eski **16 bayt + 390k** o‘qish bilan mos.
- Celery: `collect_all_server_metrics`, `check_alert_rules`, `cleanup_old_metrics`, `reset_monthly_ai_usage` + beat jadvali.
- WebSocket `/api/ws/tasks/{id}/stream`: ixtiyoriy `?token=` (JWT tekshiruvi).
- Frontend: `recharts`, sahifalar `AITokens`, `Analytics`, `AdminUsers`; `useTaskStream` token + qayta ulanish.
- `docs/SSH-SETUP.md`, `docs/AI-PROVIDERS.md`; bot: `handlers/extra_commands.py` (`/settings`, `/help`).
- `ADMIN_TELEGRAM_IDS` muhit o‘zgaruvchisi (config).

### Changed

- `encryption_service.py`: `to_db_row` / `from_db_row`, structlog xato logi.
- `tz.md`: versiya 2.0.0 va §15 kengaytirildi.

### Fixed

- Windows da `TZ.md`/`tz.md` nomi to‘qnashuvi: yagona `tz.md` ishlatiladi; versiya u yerga yoziladi.

## [Unreleased]

### Added (oldingi infra)

- Docker Compose: `x-backend-env` anchor, Redis `requirepass` + healthcheck, `postgres_data` / `redis_data` / `ssh_keys` volumes, `API_PORT`, bot uchun `API_BASE_URL`.
- `.env.example`: kengaytirilgan o‘zgaruvchilar.
- `Makefile`: `generate-keys`, `test-cov`, `clean`, `shell-api` / `shell-db`.
- `POST /api/auth/bot-login`.
- `MASTER_ENCRYPTION_KEY` (64 hex) qo‘llab-quvvatlash.
- `/api/health`: worker soni.

### Changed

- API healthcheck: `curl` + `GET /api/health`.
- JWT maydonlari: `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`.
- `DATABASE_URL` `+asyncpg` tozalash.

### Migration notes

- Eski `pgdata` o‘rniga `postgres_data` ishlatilishi mumkin.

### Docker Compose defaults

- `${VAR:-...}` mahalliy ishga tushirish uchun; productionda `.env` ni mustahkamlang.
