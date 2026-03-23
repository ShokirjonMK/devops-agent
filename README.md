# DevOps AI Agent

Production-style **avtonom DevOps / SysAdmin / NetAdmin AI operator**: tabiiy til → server (alias) → **diagnose → decide → execute → verify** sikli (LLM) → SSH → **timeline** (har qadamda *nima uchun*) + audit.

## Loyiha tahlili (qisqa)

| Bo‘lim | Mazmun |
|--------|--------|
| **Arxitektura** | Web/Telegram → FastAPI → PostgreSQL + Celery (Redis) → worker → Paramiko → maqsadli server |
| **Agent** | Intent JSON (`diagnostic_plan` + `problem_summary`) → diagnostika qadamlari → sikl: `analysis` + `next_steps[{command, explanation}]` + `step_phase` (execute/verify) |
| **Timeline** | `task_steps`: `step_order`, `command`, `output`, `status`, `timestamp`, **`explanation`**, **`phase`** |
| **Xavfsizlik** | Buyruq qora ro‘yxati, SSH timeout/retry, buyruq uzunligi cheklovi, audit `logs` |

## Aniqlangan muammolar va yechimlar (joriy versiya)

| Muammo | Yechim |
|--------|--------|
| Qadam sababi ko‘rinmas edi | `task_steps.explanation` + `phase`; LLM har buyruq uchun WHY |
| Verify alohida ifodalanmagan | `step_phase: verify` + promptda verify bosqichi |
| Server nomi noaniq | Alias normalizatsiya; **bitta server** bo‘lsa avtomatik fallback + audit |
| Cheksiz sikl xavfi | `agent_max_iterations` + **takrorlanuvchi reja** 2 marta — to‘xtatish |
| Telegram “bir martalik” natija | Poll `2s`, yangi `steps` soni o‘zgarganda progress matni yangilanadi |
| Kiritma abuse | `command_text` max **8000** belgi (Pydantic) |

## Qo‘shilgan / kuchaytirilgan komponentlar

- Alembic **`002_task_step_meta`**: `explanation`, `phase`
- Agent: diagnostika rejalashtirish, `_decide_loop`, chiqishdan **hint** audit (`permission denied`, disk, port)
- Telegram: bosqichma-bosqich progress matni
- Frontend: timeline da phase + explanation

## Hujjatlar

| Fayl | Mazmun |
|------|--------|
| [INSTALL.md](INSTALL.md) | Docker va mahalliy o‘rnatish |
| [USAGE.md](USAGE.md) | Misollar va test ssenariylari |
| [API.md](API.md) | REST |
| [V2_QAMROV.md](V2_QAMROV.md) | v2 super-prompt qamrovi (nima qo‘shildi / nima qoldi) |
| [TIZIM-MAQSAD-VA-HOLAT.md](TIZIM-MAQSAD-VA-HOLAT.md) | Maqsad va holat |

## Arxitektura (diagram)

```text
[React UI] ──► nginx /api ──► [FastAPI] ──► PostgreSQL
                                │ delay
                                ▼
                         [Redis] ◄──► [Celery worker]
                                │
                         DevOpsAgent (LLM + loop)
                                │
                                ▼
                         [Paramiko SSH] ──► Linux serverlar

[Telegram aiogram] ──HTTP──► FastAPI (/api/tasks/submit, GET task)
```

## Stack

- **Backend:** FastAPI, PostgreSQL, Redis + Celery, Paramiko  
- **AI:** OpenAI yoki `OPENAI_BASE_URL`; yoki Anthropic (`AI_PROVIDER`)  
- **Frontend:** React + Vite + Tailwind  
- **Telegram:** aiogram 3  

## Tez start

```bash
cp .env.example .env
docker compose up -d --build
```

- UI: http://localhost  
- Swagger: http://localhost:8000/docs  

Telegram: `docker compose --profile telegram up -d --build`

## Xavfsizlik

- `backend/app/services/command_filter.py`  
- SSH: timeout, **retry/backoff** (`ssh_client.py`, env orqali)  
- API: 422 validatsiya JSON  

Production: `known_hosts` / SSH siyosati, API auth, rate limit — keyingi iteratsiya.
