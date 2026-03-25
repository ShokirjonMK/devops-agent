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
| `JWT_SECRET` | JWT uchun maxfiy kalit (Docker stack uchun **majburiy**) |
| `ENCRYPTION_MASTER_KEY_B64` | Vault shifrlash: `openssl rand -base64 32` (**majburiy**) |
| `OPENAI_API_KEY` | OpenAI kaliti (yoki `OPENAI_BASE_URL` + mahalliy model) |
| `AI_PROVIDER` | `openai` yoki `anthropic` |
| `ANTHROPIC_API_KEY` | Claude uchun (agar `anthropic`) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot (`--profile telegram` bilan) |

**Eslatma:** `docker/postgres/init-01-extensions.sql` faqat **birinchi** `pgdata` yaratilganda ishlaydi. Eski volume bilan muammo bo‘lsa, `docker compose down -v` (ma’lumot yo‘qoladi) yoki qo‘lda `CREATE EXTENSION pgcrypto`.

### 1.2 SSH

**Variant A — volume:** `ssh-keys/` ga private key qo‘ying, Web UI da server `key_path`: `/ssh-keys/id_rsa`.

**Variant B — base64:** `.env` da `SSH_PRIVATE_KEY_B64` (worker konteynerida).

### 1.3 Ishga tushirish

Barcha servislar (Postgres, Redis, API + migratsiya, worker, beat, nginx web):

```bash
docker compose up -d --build
```

Migratsiya `api` konteyneri `docker-entrypoint.sh` orqali har safar `alembic upgrade head` bilan bajariladi.

- Web UI: http://localhost:8080/ (standart `WEB_PORT`; `.env` da `WEB_PORT=80` qilsangiz http://localhost/)
- API to‘g‘ridan-to‘g‘ri: http://localhost:8000/docs

### 1.3.1 To‘liq stack + Telegram bot

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
cd bot
pip install -r requirements.txt
set API_URL=http://127.0.0.1:8000
set TELEGRAM_BOT_TOKEN=...
python main.py
```

Docker Compose da bot konteksti: `./bot` (`--profile telegram`).

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
