# Agent va Worker (Celery)

## Celery

| Fayl | Mazmun |
|------|--------|
| `app/celery_app.py` | Broker, backend, serializer, **beat_schedule**, task importlari |
| `app/worker_tasks.py` | `run_agent_task` — vazifa ID bo‘yicha agentni ishga tushiradi |
| `app/beat_tasks.py` | `beat_heartbeat` — Beat jadvali bo‘yicha chaqiriladi |

Worker buyrug‘i (Docker):

`celery -A app.celery_app worker -l info`

Beat:

`celery -A app.celery_app beat -l info`

## DevOpsAgent

**Fayl:** `app/services/agent.py`  
**Klass:** `DevOpsAgent`

### Umumiy oqim

1. Vazifani `running` qiladi, serverlar ro‘yxatini oladi.
2. **Intent** — LLM dan JSON: `server_name`, `problem_summary`, `diagnostic_plan[{command, explanation}]`.
3. Serverni topish (alias, bitta server fallback).
4. **SSH** ulanishi (`SSHExecutor`), diagnostika bosqichi (`phase=diagnose`).
5. **Sikl** — `_decide_loop`: tahlil, `next_steps`, `step_phase` (`execute` / `verify`), buyruqlarni bajarish.
6. Takrorlanuvchi reja, iteratsiya limiti — cheksiz sikl oldini olish.
7. `done` / `error`, `summary`, audit va Redis hodisalari.

### Bog‘langan servislar

| Modul | Vazifa |
|--------|--------|
| `llm.py` | OpenAI / Anthropic JSON completion |
| `ssh_client.py` | Paramiko, retry, timeout |
| `command_filter.py` | Xavfli buyruqlarni bloklash |
| `task_events.py` | Redis pub/sub hodisalari |

### Qadam yozuvi

Har bajarilgan qadam `task_steps` jadvaliga: `command`, `output`, `status`, `explanation`, `phase`.

## Muhit o‘zgaruvchilari (agent uchun)

Worker konteynerida LLM va SSH uchun: `OPENAI_*`, `ANTHROPIC_*`, `AI_PROVIDER`, `SSH_PRIVATE_KEY_B64`, `SSH_KEYS_DIR` mount, va hokazo. Ro‘yxat: [../sozlamalar-env/README.md](../sozlamalar-env/README.md).
