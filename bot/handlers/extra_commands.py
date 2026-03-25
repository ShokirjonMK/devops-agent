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
        "• Server qo‘shish: Web UI yoki /addserver (tez orada to‘liq wizard)\n"
        "• AI tokenlar: Web UI → AI tokens\n",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Buyruqlar:\n"
        "/start — boshlash\n"
        "/help — yordam\n"
        "/settings — API va eslatmalar\n"
        "Matn yuborsangiz — vazifa yaratiladi (server alias yozing).\n",
    )
