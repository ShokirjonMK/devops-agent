# DevOps AI Agent — hujjatlar markazi

Bu papkada tizim **modul-modul** tushuntiriladi. Har bir modul o‘z papkasida `README.md` orqali yozilgan.

## Mundarija

| Papka | Mazmun |
|--------|--------|
| [tizim-arxitekturasi](tizim-arxitekturasi/) | Umumiy arxitektura, ma’lumot oqimi, servislar |
| [backend-api](backend-api/) | FastAPI, routerlar, konfiguratsiya, kirish nuqtasi |
| [agent-va-worker](agent-va-worker/) | Celery, DevOpsAgent, LLM, SSH bajarish |
| [ma-lumotlar-bazasi](ma-lumotlar-bazasi/) | Jadvalar, migratsiyalar, ORM modellar |
| [xavfsizlik](xavfsizlik/) | Shifrlash, JWT, Telegram login, buyruq filtri |
| [realtime-websocket](realtime-websocket/) | Redis pub/sub, WebSocket oqimi |
| [frontend](frontend/) | React UI, Vite, nginx |
| [telegram-bot](telegram-bot/) | aiogram bot (`bot/` papkasi) |
| [docker-va-deploy](docker-va-deploy/) | Compose, Makefile, healthcheck |
| [sozlamalar-env](sozlamalar-env/) | Muhit o‘zgaruvchilari, kalitlar |

## Tashqi hujjatlar (repo ildizi)

- [../INSTALL.md](../INSTALL.md) — o‘rnatish va ishga tushirish
- [../USAGE.md](../USAGE.md) — foydalanish misollari
- [../API.md](../API.md) — REST va WebSocket qisqacha
- [../TIZIM-MAQSAD-VA-HOLAT.md](../TIZIM-MAQSAD-VA-HOLAT.md) — maqsad va holat
- [../V2_QAMROV.md](../V2_QAMROV.md) — v2 kengaytirish chegaralari

---

*Hujjatlar loyiha kod bazasiga mos kelishi kerak; nomuvofiqlik topsangiz, PR yoki issue orqali yangilang.*
