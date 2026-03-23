# DevOps Agent v2 — qamrov va chegaralar

`devopsagent_tz_md.md` dagi **to‘liq** super-prompt (async SQLAlchemy, 8+ LLM provayder, DeployHandler, analytics UI, metrics jadvallari, va hokazo) — bu **katta mahsulot**; bitta iteratsiyada 100% bajarish realistik emas.

Ushbu commitda **ishlaydigan v2 asos** qo‘shildi va mavjud agent bilan integratsiya qilindi.

## Amalga oshirilgan

| Talab (prompt) | Holat |
|----------------|--------|
| Docker: tarmoq, healthcheck, `depends_on: service_healthy`, beat | `docker-compose.yml` yangilandi; `beat` servisi; `app-network` |
| `docker-compose.override.yml` (dev) | Hot reload + `app` volume |
| Makefile | `up`, `down`, `migrate`, `test`, `logs`, … |
| Multi-stage `backend/Dockerfile` | Builder + runtime |
| AES-256-GCM + AAD kontekst | `app/services/encryption_service.py` |
| Secretlar DB da shifrlangan | `credential_vault` + `POST /api/credentials` (plaintext faqat HTTP orqali, DB da binary) |
| Telegram Login HMAC | `POST /api/auth/telegram` + `telegram_auth.py` |
| JWT | `PyJWT`, `dependencies.get_current_user` |
| Redis pub/sub + WebSocket | `task_events.py` + agent `publish_*` + `GET WS /api/ws/tasks/{id}/stream` |
| Celery Beat | `beat_heartbeat` har 5 daqiqa |
| structlog | `main.py` lifespan |
| `/api/health` | DB + Redis tekshiruvi |
| `bot/` papkasi | `telegram_bot` o‘rniga compose `bot` |
| pytest | `tests/test_encryption.py`, `tests/test_command_filter.py` |
| Frontend WS | `useTaskStream` + TaskDetail |

## Hali prompt bo‘yicha kengaytirish kerak

- To‘liq UUID migratsiyasi barcha jadvallar uchun (hozir `tasks/servers` int PK saqlangan).
- `users`, `credential_vault` tashqari: `server_metrics`, `alert_rules`, `notifications`, `user_sessions`, …
- Async SQLAlchemy butun API bo‘ylab.
- `LLMRouter` + 8 ta provayder adapterlari.
- `DeployHandler`, `SafetyFilter` alohida klass (hozir `command_filter` + agent ichida sikl).
- Analytics sahifasi + `AnalyticsService` to‘liq.
- Bot: middleware auth, inline keyboard, webhook rejimi.
- Frontend: Telegram Widget login, Zustand, React Query, Credentials/Tokens sahifalari.

## Ishga tushirish

```bash
cp .env.example .env
# JWT_SECRET, ENCRYPTION_MASTER_KEY_B64 (openssl rand -base64 32) to‘ldiring
docker compose up -d --build
make migrate
make test
```

Telegram login va `credential_vault` ishlashi uchun **JWT_SECRET**, **ENCRYPTION_MASTER_KEY_B64**, **TELEGRAM_BOT_TOKEN** majburiy (auth va shifrlash).
