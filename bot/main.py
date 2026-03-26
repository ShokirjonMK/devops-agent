"""
Telegram bot (aiogram 3): API orqali vazifa + bosqichma-bosqich progress (timeline poll).
"""

from __future__ import annotations

import asyncio
import logging
import os

import httpx
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from handlers.admin_handler import router as admin_handler_router
from handlers.extra_commands import router as extra_router
from handlers.servers_wizard import router as servers_wizard_router
from handlers.tokens_handler import router as tokens_handler_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("telegram_bot")

API_URL = (
    os.environ.get("API_BASE_URL") or os.environ.get("API_URL") or "http://127.0.0.1:8000"
).rstrip("/")
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
INTERNAL = os.environ.get("API_INTERNAL_SECRET", "").strip()
HTTP_RETRIES = int(os.environ.get("HTTP_RETRIES", "3"))
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL_SEC", "2"))
POLL_MAX = int(os.environ.get("POLL_MAX_ROUNDS", "180"))
TG_MSG_MAX = 3900


def _api_headers() -> dict[str, str]:
    h: dict[str, str] = {}
    if INTERNAL:
        h["X-Internal-Secret"] = INTERNAL
    return h


async def _request_with_retries(
    method: str,
    url: str,
    *,
    json_body: dict | None = None,
    timeout: float = 60.0,
) -> httpx.Response:
    last: Exception | None = None
    for attempt in range(HTTP_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method.upper() == "POST":
                    r = await client.post(url, json=json_body, headers=_api_headers())
                else:
                    r = await client.get(url, headers=_api_headers())
                r.raise_for_status()
                return r
        except Exception as e:
            last = e
            log.warning("HTTP %s %s xato (urinish %s/%s): %s", method, url, attempt + 1, HTTP_RETRIES, e)
            await asyncio.sleep(1.0 * (attempt + 1))
    assert last is not None
    raise last


async def submit_task(command_text: str, user_id: str, telegram_message_id: int | None = None) -> dict:
    body: dict = {
        "command_text": command_text,
        "user_id": user_id,
        "source": "telegram",
    }
    if telegram_message_id is not None:
        body["telegram_message_id"] = telegram_message_id
    r = await _request_with_retries(
        "POST",
        f"{API_URL}/api/tasks/submit",
        json_body=body,
        timeout=60.0,
    )
    return r.json()


async def poll_task(task_id: int) -> dict:
    r = await _request_with_retries(
        "GET",
        f"{API_URL}/api/tasks/{task_id}",
        timeout=30.0,
    )
    return r.json()


def _format_step_line(step: dict) -> str:
    cmd = (step.get("command") or "").strip()
    ph = (step.get("phase") or "").strip()
    ex = (step.get("explanation") or "").strip()
    st = (step.get("status") or "").strip()
    parts = []
    if ph:
        parts.append(f"[{ph}]")
    if cmd:
        parts.append(cmd[:200])
    if ex:
        parts.append(f"→ {ex[:280]}")
    if st:
        parts.append(f"({st})")
    return " ".join(parts) if parts else str(step.get("id", ""))


def _build_progress_text(tid: int, detail: dict, last_n: int = 4) -> str:
    st = str(detail.get("status", ""))
    steps = detail.get("steps") or []
    if not isinstance(steps, list):
        steps = []
    tail = steps[-last_n:] if len(steps) > last_n else steps
    lines = [
        f"Vazifa #{tid} — {st}",
        f"Jami qadamlar: {len(steps)}",
        "",
    ]
    for s in tail:
        if isinstance(s, dict):
            lines.append(_format_step_line(s))
    body = "\n".join(lines)
    if len(body) > TG_MSG_MAX:
        body = body[: TG_MSG_MAX - 20] + "\n…(qisqartirildi)"
    return body


router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Salom! Tabiiy til buyrug‘ini yuboring.\n"
        "Masalan: sarbon serverida nginx ishlamayapti\n\n"
        "Avval Web UI da serverlar ro‘yxatiga alias qo‘shilgan bo‘lishi kerak.\n"
        "Progress: har yangi qadamda xabar yangilanadi.",
    )


@router.message(F.text)
async def on_text(message: Message) -> None:
    if not message.text or not message.from_user:
        return
    text = message.text.strip()
    if not text or text.startswith("/"):
        return
    chat_id = str(message.chat.id)
    status_msg = await message.answer("Qabul qilindi. Agent ishga tushmoqda…")
    last_step_count = -1
    try:
        task = await submit_task(text, chat_id, status_msg.message_id)
        tid = int(task["id"])
        await status_msg.edit_text(
            f"Vazifa #{tid} navbatda…\nServer aniqlanishi va SSH diagnostikasi boshlanadi."
        )
        for _ in range(POLL_MAX):
            await asyncio.sleep(POLL_INTERVAL)
            detail = await poll_task(tid)
            steps = detail.get("steps") or []
            n = len(steps) if isinstance(steps, list) else 0
            st = str(detail.get("status", ""))

            if n > last_step_count or st in ("done", "error"):
                last_step_count = n
                if st in ("done", "error"):
                    summary = detail.get("summary") or st
                    body = "\n".join(
                        [
                            f"Vazifa #{tid}: {st}",
                            "",
                            f"Buyruq: {str(detail.get('command_text', ''))[:400]}",
                            "",
                            str(summary)[:3200],
                        ]
                    )
                    if len(body) > TG_MSG_MAX:
                        body = body[: TG_MSG_MAX - 15] + "\n…"
                    try:
                        await status_msg.edit_text(body)
                    except Exception:
                        await message.answer(body[:4096])
                    return
                prog = _build_progress_text(tid, detail)
                try:
                    await status_msg.edit_text(prog)
                except Exception as edit_err:
                    log.debug("edit_text: %s", edit_err)
        await status_msg.edit_text(f"Vazifa #{tid} vaqti tugadi. Web UI dan kuzating.")
    except Exception as e:
        log.exception("task failed")
        try:
            await status_msg.edit_text(f"Xato: {e}")
        except Exception:
            await message.answer(f"Xato: {e}")


async def main() -> None:
    if not TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required")
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(extra_router)
    dp.include_router(servers_wizard_router)
    dp.include_router(tokens_handler_router)
    dp.include_router(admin_handler_router)
    dp.include_router(router)
    log.info("Aiogram polling… API_URL=%s", API_URL)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
