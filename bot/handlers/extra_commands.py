"""Qisqa buyruqlar: /settings, /help."""

from __future__ import annotations

import os

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

API_URL = (os.environ.get("API_BASE_URL") or os.environ.get("API_URL") or "").rstrip("/")


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    await message.answer(
        "Sozlamalar:\n"
        f"• API: {API_URL or '(noma’lum)'}\n"
        "• Bildirishnomalar: vazifa xabarlari tahrirlanadi (progress).\n"
        "• AI tokenlar: Web UI (xavfsizroq) yoki /tokens havolasi.\n"
        "• Server: Web UI yoki /addserver (API_INTERNAL_SECRET kerak).\n",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Buyruqlar:\n"
        "/start — boshlash\n"
        "/help — yordam\n"
        "/settings — eslatmalar\n"
        "/addserver — server qo‘shish (FSM)\n"
        "/tokens — AI tokenlar (Web UI havolasi)\n"
        "/admin — admin health (faqat ADMIN_TELEGRAM_IDS)\n"
        "Matn yuborsangiz — vazifa (server alias yozing).\n",
    )
