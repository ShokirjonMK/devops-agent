# Backend API (FastAPI)

**Kod joyi:** `backend/app/`

## Kirish nuqtasi

| Fayl | Rol |
|------|-----|
| `main.py` | FastAPI ilova, CORS, `lifespan`, structlog, `/health` |
| `config.py` | `pydantic-settings` — barcha env o‘zgaruvchilari |
| `database.py` | SQLAlchemy `engine`, `SessionLocal`, `get_db` |

API prefiksi: **`/api`**. Swagger: **`/docs`**.

## Routerlar (`app/api/`)

Barcha routerlar `api/__init__.py` orqali birlashtiriladi.

| Fayl | Yo‘l (taxminiy) | Tavsif |
|------|------------------|--------|
| `health_api.py` | `GET /api/health` | PostgreSQL va Redis tekshiruvi |
| `auth_router.py` | `POST /api/auth/telegram` | Telegram Login Widget → JWT |
| `credentials_router.py` | `GET/POST /api/credentials` | Shifrlangan vault (Bearer JWT) |
| `websocket_tasks.py` | `WS /api/ws/tasks/{id}/stream` | Vazifa hodisalari oqimi |
| `servers.py` | `/api/servers` | Serverlar CRUD |
| `tasks.py` | `/api/tasks`, `/api/tasks/submit` | Vazifalar |

## Bog‘liqliklar

| Fayl | Rol |
|------|-----|
| `dependencies.py` | `get_current_user`, `get_encryption_service` |
| `security_jwt.py` | JWT yaratish / `sub` dan UUID |
| `schemas.py` | Pydantic sxemalar (kirish/chiqish) |
| `models.py` | SQLAlchemy modellar |

## Xatoliklar

- **422** — validatsiya (`RequestValidationError` → JSON `detail`).
- **401/403** — auth/credentials uchun.
- **503** — JWT/shifrlash/telegram sozlanmagan bo‘lsa (tegishli endpointlar).

## Ishga tushirish (mahalliy)

`PYTHONPATH=backend` yoki Docker ichida `WORKDIR /app`. Batafsil: [../../INSTALL.md](../../INSTALL.md).
