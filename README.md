# DevOps AI Agent

`tz.md` / `tz1.md` bo‘yicha **AI DevOps operator** platformasi: tabiiy til → serverni aniqlash → SSH diagnostika → LLM qaror → filtrlangan bajarish → **timeline** va **audit**.

## Hujjatlar

| Fayl | Mazmun |
|------|--------|
| [INSTALL.md](INSTALL.md) | Docker va mahalliy o‘rnatish, ishga tushirish |
| [USAGE.md](USAGE.md) | Real buyruqlar, nginx/docker/port/disk/SSH ssenariylari |
| [API.md](API.md) | REST endpointlar va JSON shakllar |

## Stack

- **Backend:** FastAPI, PostgreSQL, **Redis + Celery**, Paramiko (SSH)
- **AI:** OpenAI / `OPENAI_BASE_URL` (mos API) yoki Anthropic
- **Frontend:** React + Vite + Tailwind
- **Telegram:** **aiogram 3** (`telegram_bot/`)

## Tez start (Docker)

```bash
cp .env.example .env
# OPENAI_API_KEY yoki mahalliy LLM URL; SSH kalit — ssh-keys/ yoki SSH_PRIVATE_KEY_B64
docker compose up -d --build
```

- **UI:** http://localhost  
- **Swagger:** http://localhost:8000/docs  

**Telegram:**

```bash
docker compose --profile telegram up -d --build
```

## Xavfsizlik

- Xavfli buyruqlar filtri (`backend/app/services/command_filter.py`)
- SSH ulanish **qayta urinish** + loglar (`ssh_client.py`)
- API validatsiya xatolari — JSON `detail` (422)

## Production eslatma

SSH `AutoAddPolicy` qulay, lekin productionda host kalitini qat’iy tekshirish yaxshiroq. LLM chiqishi har doim to‘g‘ri bo‘lmasligi mumkin — muhim muhitda inson tasdiqlash qatlami qo‘shing.
