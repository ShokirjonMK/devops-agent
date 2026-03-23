# O‘rnatish va ishga tushirish

Production uchun tavsiya: **Docker Compose**. Mahalliy ishlab chiqish: pastdagi bo‘lim.

## Talablar

- Docker Engine 24+ va Docker Compose v2
- Yoki: Python 3.12, Node 20, PostgreSQL 16, Redis 7

## 1. Docker Compose (production-style)

### 1.1 Muhit

```bash
cp .env.example .env
```

To‘ldiring:

| O‘zgaruvchi | Tavsif |
|-------------|--------|
| `OPENAI_API_KEY` | OpenAI kaliti (yoki `OPENAI_BASE_URL` + mahalliy model) |
| `AI_PROVIDER` | `openai` yoki `anthropic` |
| `ANTHROPIC_API_KEY` | Claude uchun (agar `anthropic`) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot (faqat bot profili bilan) |

### 1.2 SSH

**Variant A — volume:** `ssh-keys/` ga private key qo‘ying, Web UI da server `key_path`: `/ssh-keys/id_rsa`.

**Variant B — base64:** `.env` da `SSH_PRIVATE_KEY_B64` (worker konteynerida).

### 1.3 Ishga tushirish

```bash
docker compose up -d --build
```

- Web UI: http://localhost (nginx → static + `/api` → API)
- Swagger: http://localhost:8000/docs

### 1.4 Telegram bot (aiogram)

```bash
docker compose --profile telegram up -d --build
```

## 2. Mahalliy ishlab chiqish

### 2.1 PostgreSQL va Redis

O‘zingizning portlar bilan ishga tushiring yoki Docker:

```bash
docker run -d --name pg -e POSTGRES_USER=devops -e POSTGRES_PASSWORD=devops -e POSTGRES_DB=devops_agent -p 5432:5432 postgres:16-alpine
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### 2.2 Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
set DATABASE_URL=postgresql://devops:devops@localhost:5432/devops_agent
set PYTHONPATH=%CD%
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2.3 Celery worker

```bash
cd backend
set PYTHONPATH=%CD%
set DATABASE_URL=postgresql://devops:devops@localhost:5432/devops_agent
set CELERY_BROKER_URL=redis://localhost:6379/0
set CELERY_RESULT_BACKEND=redis://localhost:6379/0
celery -A app.celery_app worker -l info
```

### 2.4 Frontend

```bash
cd frontend
npm ci
npm run dev
```

Brauzer: http://localhost:5173 — Vite `/api` ni `127.0.0.1:8000` ga proksi qiladi.

### 2.5 Telegram bot (mahalliy)

```bash
cd telegram_bot
pip install -r requirements.txt
set API_URL=http://127.0.0.1:8000
set TELEGRAM_BOT_TOKEN=...
python main.py
```

## 3. Tekshiruv

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/servers
```

## 4. Yangilash

```bash
git pull
docker compose build --no-cache
docker compose up -d
```

Ma’lumotlar bazasi migratsiyasi API/worker `docker-entrypoint.sh` orqali `alembic upgrade head` bilan avtomatik bajariladi (jumladan `002_task_step_meta`: `explanation`, `phase` ustunlari).
