# Real-time: Redis pub/sub va WebSocket

## Maqsad

Worker agent vazifa bajarayotganda brauzer yoki boshqa mijoz **darhol** hodisalarni olishi uchun ikki qatlam ishlatiladi:

1. **Redis pub/sub** — kanal bo‘yicha xabarlar.
2. **WebSocket** — API orqali mijozga uzatish.

## Redis kanali

**Fayl:** `app/services/task_events.py`

- Kanal nomi: `task:{task_id}:events`
- **Funksiya:** `publish_task_event(task_id, event_type, payload=dict)`
- Xabar tanasi: JSON qator (`type`, `task_id`, qo‘shimcha maydonlar).

Agent quyidagi hodisalarni yuborishi mumkin: `task_running`, `step_start`, `step_done`, `step_skipped`, `task_done`, `task_error`.

## WebSocket endpoint

- **URL:** `WS /api/ws/tasks/{task_id}/stream`
- **Fayl:** `app/api/websocket_tasks.py`
- Redis `async` pub/sub orqali tinglaydi va kelgan JSON qatorlarni mijozga `send_text` qiladi.

## Frontend

**Hook:** `frontend/src/hooks/useTaskStream.ts`  
**Sahifa:** `TaskDetail` — real-time blok (oxirgi qatorlar).

Proksi:

- **Vite dev:** `vite.config.ts` — `/api` uchun `ws: true`
- **nginx (production):** `location /api/ws/` — `Upgrade`, `Connection: upgrade`

## Eslatmalar

- WebSocket hozircha **JWT query** bilan cheklanmagan (ichki tarmoq uchun soddalashtirilgan). Tashqi ochiq muhitda **token** yoki boshqa auth qo‘shish tavsiya etiladi.
- Mijoz ulanishi uzilganda server tomonda kanal tozalashi `finally` blokida bajariladi.
