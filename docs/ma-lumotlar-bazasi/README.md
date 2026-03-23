# Ma’lumotlar bazasi

**SGBD:** PostgreSQL  
**ORM:** SQLAlchemy 2.0 (sinxron sessiya)  
**Migratsiya:** Alembic (`backend/alembic/`)

## Jadvalar (joriy sxema)

### `users`

- UUID `id` (default `gen_random_uuid()`)
- `telegram_id` (unique), `username`, `first_name`, `is_active`, `created_at`

### `credential_vault`

- UUID `id`
- `user_id` → `users.id` (CASCADE)
- `name`, `credential_type`
- **Shifrlangan maydonlar:** `cipher_text`, `iv`, `tag`, `salt` (ochiq matn yo‘q)
- Unique: (`user_id`, `name`)

### `servers`

- `id` (serial), `name` (unique alias), `host`, `user`, `auth_type`, `key_path`, `created_at`

### `tasks`

- `id`, `user_id` (matn, masalan Telegram chat), `server_id`, `command_text`, `status`, `source`, `summary`, `created_at`

### `task_steps`

- `id`, `task_id`, `step_order`, `command`, `output`, `status`, `explanation`, `phase`, `created_at`

### `logs` (audit)

- `id`, `task_id`, `message`, `level`, `timestamp`

## Migratsiya fayllari

| Revision | Mazmun |
|----------|--------|
| `001_initial.py` | Asosiy jadvalar (servers, tasks, task_steps, logs) |
| `002_task_step_meta.py` | `explanation`, `phase` ustunlari |
| `003_users_credential_vault.py` | `users`, `credential_vault` |

Ishga tushirish: `alembic upgrade head` (Docker entrypoint avtomatik bajaradi).

## ORM

Barcha modellar **`app/models.py`** da. Alembic `env.py` da `Base.metadata` uchun modellar import qilinadi.

## Indekslar

- `servers.name`, `tasks.user_id`, `task_steps.task_id`, `logs.task_id`
- `users.telegram_id`, `credential_vault.user_id`
