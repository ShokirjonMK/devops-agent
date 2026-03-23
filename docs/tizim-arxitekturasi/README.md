# Tizim arxitekturasi

## Maqsad (qisqa)

Foydalanuvchi **tabiiy til** bilan buyruq beradi; tizim serverni **alias** bo‘yicha topadi, **SSH** orqali diagnostika va LLM yordamida xavfsiz buyruqlar zanjirini bajaradi; natija **timeline**, **audit** va ixtiyoriy **real-time** kanal orqali qaytariladi.

## Mantiqiy diagramma

```text
                    ┌─────────────┐     ┌─────────────┐
                    │  Web (React) │     │  Telegram   │
                    │  + nginx     │     │  bot        │
                    └──────┬──────┘     └──────┬──────┘
                           │ HTTP              │ HTTP
                           ▼                   ▼
                    ┌──────────────────────────────────┐
                    │         FastAPI (api)            │
                    │  REST + WebSocket (/api/ws/...)  │
                    └──────────┬───────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ┌──────────┐    ┌──────────┐   ┌──────────┐
        │PostgreSQL│    │  Redis   │   │ (tashqi) │
        │          │    │ broker   │   │ LLM API  │
        └──────────┘    └────┬─────┘   └────▲─────┘
                             │              │
                             ▼              │
                    ┌─────────────────┐     │
                    │ Celery worker   │─────┘
                    │ DevOpsAgent     │
                    │ Paramiko SSH    │──────────► Linux serverlar
                    └─────────────────┘
```

## Asosiy komponentlar

| Komponent | Vazifa |
|-----------|--------|
| **api** | HTTP API, migratsiya (entrypoint), WebSocket ulanishlari |
| **worker** | Navbatdagi vazifalarni bajarish, agent + SSH |
| **beat** | Vaqtli Celery vazifalari (masalan, heartbeat) |
| **postgres** | Doimiy ma’lumotlar |
| **redis** | Celery broker/backend + vazifa hodisalari pub/sub |
| **web** | Statik frontend + `/api` va `/api/ws` proksi |
| **bot** | Profil `telegram` — aiogram orqali foydalanuvchi xabarlari |

## Ma’lumot oqimi (vazifa)

1. Client `POST /api/tasks` yoki `/api/tasks/submit` yuboradi.
2. API `tasks` qatorini yozadi, holat `pending`, Celery `run_agent_task` chaqiriladi.
3. Worker `DevOpsAgent.run()` — intent (LLM), diagnostika, qaror sikli, SSH.
4. Har qadam `task_steps` va `logs` ga yoziladi; Redis orqali **hodisalar** yuboriladi.
5. Client `GET /api/tasks/{id}` yoki WebSocket orqali kuzatadi.

## Tarmoq (Docker)

Barcha servislar **`app-network`** ichida. Tashqi portlar odatda: `80` (web), `8000` (to‘g‘ridan-to‘g‘ri API).

## Keyingi kengaytirishlar

To‘liq UUID sxema, alohida analytics servisi, ko‘p LLM provayder router — `V2_QAMROV.md` ga qarang.
