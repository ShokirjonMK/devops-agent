# DevOps AI Agent

`tz.md` va `tz1.md` bo‘yicha **avtonom DevOps / SysAdmin / NetAdmin AI agent**: tabiiy til buyrug‘i → serverni aniqlash → SSH diagnostika → AI qaror → bajarish → timeline va audit.

## Arxitektura

- **Backend:** FastAPI, PostgreSQL, Redis + Celery worker, Paramiko (SSH)
- **AI:** OpenAI yoki `OPENAI_BASE_URL` orqali mos keluvchi API (Ollama va hokazo) yoki Anthropic (`AI_PROVIDER=anthropic`)
- **Frontend:** React + Vite + Tailwind (dashboard, serverlar CRUD, vazifa timeline)
- **Telegram:** alohida servis (`--profile telegram`)

## Tez deploy (Docker)

1. Nusxa oling: `cp .env.example .env` va `OPENAI_API_KEY` (yoki Anthropic / mahalliy LLM) ni to‘ldiring.

2. SSH kalit:
   - **Variant A:** `ssh-keys/` papkasiga kalit qo‘ying va Web UI da server `key_path` ni masalan `/ssh-keys/id_rsa` qiling (worker konteynerida shu mount).
   - **Variant B:** kalitni base64 qilib `.env` da `SSH_PRIVATE_KEY_B64` ga qo‘ying.

3. Ishga tushiring:

```bash
docker compose up -d --build
```

4. Brauzer: **http://localhost** (nginx orqali UI + `/api` proksi). To‘g‘ridan-to‘g‘ri API: **http://localhost:8000/docs**

5. Telegram:

```bash
docker compose --profile telegram up -d --build
```

(`TELEGRAM_BOT_TOKEN` `.env` da bo‘lishi kerak.)

## Mahalliy ishlab chiqish

**Backend**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
set DATABASE_URL=postgresql://devops:devops@localhost:5432/devops_agent
alembic upgrade head
uvicorn app.main:app --reload
```

Alohida terminalda Redis va Celery worker:

```bash
celery -A app.celery_app worker -l info
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Vite `/api` ni `http://127.0.0.1:8000` ga proksi qiladi.

## API qisqacha

| Metod | Yo‘l | Tavsif |
|--------|------|--------|
| GET | `/api/servers` | Serverlar |
| POST | `/api/servers` | Yangi server |
| PUT/DELETE | `/api/servers/{id}` | Tahrirlash / o‘chirish |
| GET | `/api/tasks` | Vazifalar |
| POST | `/api/tasks` | Web buyruq |
| POST | `/api/tasks/submit` | Telegram / tashqi |
| GET | `/api/tasks/{id}` | Timeline + loglar |

## Xavfsizlik

- Xavfli buyruqlar filtri (`rm -rf /`, `shutdown`, `dd`, va hokazo).
- Barcha SSH buyruqlari va audit yozuvlari DB da saqlanadi.

## Qabul qilish (TZ)

- Chat (Web + Telegram) orqali buyruq
- Server nomi / alias bilan aniqlash
- SSH, diagnostika, AI qaror, bajarish, timeline
