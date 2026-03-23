# Telegram bot

**Asosiy kod:** `bot/` (Docker Compose shu kontekstni ishlatadi)  
**Kutubxona:** aiogram 3.x  
**Eski nusxa:** `telegram_bot/` — ixtiyoriy arxiv; faol deploy **`bot/`** ga yo‘naltirilgan.

## Vazifa

1. Foydalanuvchi matn yuboradi (tabiiy til buyruq).
2. Bot `POST {API_URL}/api/tasks/submit` chaqiradi (`source=telegram`, `user_id=chat.id`).
3. Har bir necha soniyada `GET /api/tasks/{id}` bilan holatni yangilaydi.
4. Yangi `steps` paydo bo‘lganda yoki vazifa tugaganda xabarni **tahrir** qiladi (progress matni).

## Muhit o‘zgaruvchilari

| O‘zgaruvchi | Tavsif |
|-------------|--------|
| `TELEGRAM_BOT_TOKEN` | BotFather tokeni (majburiy) |
| `API_URL` | Masalan `http://api:8000` (Compose ichida) |
| `HTTP_RETRIES`, `POLL_INTERVAL_SEC`, `POLL_MAX_ROUNDS` | HTTP va polling sozlamalari |

## Docker

```bash
docker compose --profile telegram up -d bot
```

## Bog‘lanish API bilan

Bot **faqat REST** ishlatadi; WebSocket ishlatmaydi. Real-time effekt **polling** orqali.

## Keyingi yaxshilanishlar (TZ)

- Webhook rejimi  
- Middleware orqali foydalanuvchini DB bilan bog‘lash  
- Inline tugmalar (tasdiqlash / bekor)  
- Uzun javobni fayl yoki havola bilan yuborish  
