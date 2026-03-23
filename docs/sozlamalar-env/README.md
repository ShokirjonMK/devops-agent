# Sozlamalar (environment)

Namuna: [../../.env.example](../../.env.example)

## AI

| O‘zgaruvchi | Tavsif |
|-------------|--------|
| `OPENAI_API_KEY` | OpenAI |
| `OPENAI_BASE_URL` | Mos keluvchi API (masalan Ollama bridge) |
| `OPENAI_MODEL` | Model nomi |
| `ANTHROPIC_API_KEY` | Claude |
| `AI_PROVIDER` | `openai` yoki `anthropic` |

## Auth va shifrlash (v2)

| O‘zgaruvchi | Tavsif |
|-------------|--------|
| `JWT_SECRET` | JWT imzo kaliti |
| `JWT_EXPIRE_MINUTES` | Ixtiyoriy (config default bor) |
| `ENCRYPTION_MASTER_KEY_B64` | **32 bayt** base64 (`openssl rand -base64 32`) |
| `TELEGRAM_BOT_TOKEN` | Widget tekshiruvi + bot |

## Ma’lumotlar va navbat

| O‘zgaruvchi | Tavsif |
|-------------|--------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis (bir qatorli ulanish) |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Odatda Redis |

## SSH (worker)

| O‘zgaruvchi | Tavsif |
|-------------|--------|
| `SSH_PRIVATE_KEY_B64` | Kalit base64 |
| `SSH_KEYS_DIR` | Hostdan mount (`/ssh-keys` ichida kalitlar) |
| `SSH_CONNECT_RETRIES`, `SSH_RETRY_BACKOFF_SECONDS` | Ulanish qayta urinish |

## API

| O‘zgaruvchi | Tavsif |
|-------------|--------|
| `API_CORS_ORIGINS` | Vergul bilan ajratilgan originlar |

## Bot (polling)

| O‘zgaruvchi | Tavsif |
|-------------|--------|
| `HTTP_RETRIES`, `POLL_INTERVAL_SEC`, `POLL_MAX_ROUNDS` | Bot HTTP va poll |

## Xavfsizlik qoidalari

- Secretlarni repoga qo‘shmang.
- Productionda har muhit uchun alohida kalitlar.
- `ENCRYPTION_MASTER_KEY_B64` o‘zgartirilsa, **eski vault yozuvlarini** yangi kalit bilan o‘qib bo‘lmaydi.
