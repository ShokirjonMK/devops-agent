import asyncio
import logging
import os

import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("telegram_bot")

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000").rstrip("/")
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return
    await update.effective_chat.send_message(
        "Salom! Tabiiy til buyrug‘ini yuboring.\n"
        "Masalan: sarbon serverida nginx ishlamayapti\n\n"
        "Avval Web UI da serverlar ro‘yxatiga alias qo‘shilgan bo‘lishi kerak.",
    )


async def submit_task(command_text: str, user_id: str) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f"{API_URL}/api/tasks/submit",
            json={
                "command_text": command_text,
                "user_id": user_id,
                "source": "telegram",
            },
        )
        r.raise_for_status()
        return r.json()


async def poll_task(task_id: int) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(f"{API_URL}/api/tasks/{task_id}")
        r.raise_for_status()
        return r.json()


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text or not update.effective_chat:
        return
    text = update.message.text.strip()
    if not text:
        return
    chat_id = str(update.effective_chat.id)
    status_msg = await update.message.reply_text("Qabul qilindi. Agent ishga tushmoqda…")
    try:
        task = await submit_task(text, chat_id)
        tid = task["id"]
        await status_msg.edit_text(f"Vazifa #{tid} navbatda…")
        for _ in range(120):
            await asyncio.sleep(3)
            detail = await poll_task(tid)
            st = detail["status"]
            if st in ("done", "error"):
                summary = detail.get("summary") or st
                lines = [
                    f"Vazifa #{tid}: {st}",
                    "",
                    f"Buyruq: {detail['command_text'][:500]}",
                    "",
                    summary[:3500],
                ]
                await status_msg.edit_text("\n".join(lines))
                return
            await status_msg.edit_text(f"Vazifa #{tid} holati: {st}…")
        await status_msg.edit_text(f"Vazifa #{tid} hali tugamagan. Web UI dan kuzating.")
    except Exception as e:
        log.exception("task failed")
        await status_msg.edit_text(f"Xato: {e}")


def main() -> None:
    if not TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    log.info("Bot polling… API_URL=%s", API_URL)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
