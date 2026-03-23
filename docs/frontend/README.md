# Frontend (React)

**Kod:** `frontend/`  
**Stack:** React 18, TypeScript, Vite, Tailwind CSS, React Router

## Tuzilma

| Yo‘l | Mazmun |
|------|--------|
| `src/main.tsx` | Kirish, `BrowserRouter` |
| `src/App.tsx` | Navigatsiya, marshrutlar |
| `src/api.ts` | REST chaqiriqlari (`fetch`, nisbiy `/api`) |
| `src/pages/Dashboard.tsx` | Vazifalar ro‘yxati, yangi buyruq |
| `src/pages/Servers.tsx` | Serverlar CRUD |
| `src/pages/TaskDetail.tsx` | Timeline, audit, WebSocket qatorlari |
| `src/hooks/useTaskStream.ts` | Vazifa hodisalari WebSocket |

## Build va statik fayllar

- **Dev:** `npm run dev` — odatda `5173`, `/api` proksi `127.0.0.1:8000`
- **Prod:** `npm run build` → `dist/`, nginx `frontend/Dockerfile` ichida xizmat qiladi

## Marshrutlar

- `/` — Dashboard  
- `/servers` — Serverlar  
- `/tasks/:id` — Vazifa batafsil  

## UI tili

Interfeys matnlari o‘zbek tilida (lotin yozuvi). API xatoliklari inglizcha/JSON bo‘lishi mumkin.

## Bog‘liqlik

Backend bilan faqat **HTTP/WS** orqali; alohida build artefakti; autentifikatsiya UI da keyingi bosqichda (masalan Telegram Widget + JWT saqlash) qo‘shilishi mumkin.
