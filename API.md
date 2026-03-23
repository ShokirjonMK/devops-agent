# REST API

Asosiy prefiks: `/api`. JSON format.

## Umumiy

| Endpoint | Metod | Tavsif |
|----------|--------|--------|
| `/health` | GET | Minimal: `{"status":"ok"}` |
| `/api/health` | GET | DB + Redis: `status`, `components` |
| `/docs` | GET | OpenAPI (Swagger UI) |
| `/openapi.json` | GET | SXema |

## Auth (v2)

| Endpoint | Metod | Tavsif |
|----------|--------|--------|
| `/api/auth/telegram` | POST | Telegram Login Widget body (JSON) → JWT |

`JWT_SECRET` va `TELEGRAM_BOT_TOKEN` sozlangan bo‘lishi kerak.

## Credentials (shifrlangan vault)

| Endpoint | Metod | Tavsif |
|----------|--------|--------|
| `/api/credentials` | GET | Bearer JWT — ro‘yxat (secret qaytarilmaydi) |
| `/api/credentials` | POST | Bearer JWT + `name`, `credential_type`, `secret` |

`ENCRYPTION_MASTER_KEY_B64` (32 bayt base64) majburiy.

## WebSocket

`WS /api/ws/tasks/{task_id}/stream` — agent Redis orqali yuborgan hodisalar (JSON qatorlar).

## Servers

### `GET /api/servers`

Barcha serverlar (alias + ulanish ma’lumotlari).

### `POST /api/servers`

Yaratish. Tana:

```json
{
  "name": "sarbon",
  "host": "10.0.0.5",
  "user": "ubuntu",
  "auth_type": "ssh_key",
  "key_path": "/ssh-keys/id_rsa"
}
```

**201** — yaratilgan obyekt.

### `GET /api/servers/{id}`

Bitta server.

### `PUT /api/servers/{id}`

Qisman yangilash. Maydonlar ixtiyoriy.

### `DELETE /api/servers/{id}`

**204** — muvaffaqiyatli o‘chirish.

### Task step (timeline)

Har bir qadam:

- `step_order`, `command`, `output`, `status`, `created_at`
- `explanation` — nima uchun bu buyruq bajarilgani
- `phase` — `diagnose` | `execute` | `verify`

## Tasks

### `GET /api/tasks`

So‘rov parametrlari:

- `skip` (default 0)
- `limit` (default 50, max 200)

Ro‘yxat: vazifalar, `created_at` bo‘yicha teskari.

### `GET /api/tasks/{id}`

Batafsil: `steps` (timeline), `logs` (audit).

### `POST /api/tasks`

Web UI uchun. **202 Accepted**.

```json
{
  "command_text": "sarbon serverida nginx tekshir",
  "server_id": null
}
```

`server_id` berilsa, server tanlash LLM dan oldin majburiy bog‘lanadi.

Javob: vazifa qisqa obyekti (`id`, `status`: `pending`, …). Bajarish **Celery worker** da.

### `POST /api/tasks/submit`

Telegram / tashqi mijozlar.

```json
{
  "command_text": "…",
  "server_id": null,
  "user_id": "123456",
  "source": "telegram"
}
```

`source`: `web` yoki `telegram` (boshqa qiymat `web` ga tushadi).

## Status kodlar

| Kod | Mazmun |
|-----|--------|
| 200 | OK |
| 201 | Server yaratildi |
| 202 | Vazifa navbatga qo‘yildi |
| 204 | O‘chirildi |
| 404 | Topilmadi |
| 422 | Validatsiya xatosi (`detail`: xatolar ro‘yxati) |

## CORS

`API_CORS_ORIGINS` (vergul bilan ajratilgan) orqali sozlanadi.

## Ichki oqim

1. `POST /api/tasks` yoki `/submit` → DB da `tasks` qator, status `pending`.
2. Celery `run_agent_task` → SSH + LLM → `task_steps` va `logs` to‘ldiriladi, status `done` / `error`.
