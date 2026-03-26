"""AI tokenlar: Web UI ga yo‘naltirish (JWT talab)."""

from __future__ import annotations

import os

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

router = Router()

WEB_UI = os.environ.get("WEB_UI_URL", "http://localhost:5173").rstrip("/")


@router.message(Command("tokens"))
async def cmd_tokens(message: Message) -> None:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="AI tokens (Web)", url=f"{WEB_UI}/credentials/tokens")],
            [InlineKeyboardButton(text="AI provayderlar qo‘llanmasi", url=f"{WEB_UI}/credentials/tokens")],
        ]
    )
    await message.answer(
        "AI kalitlarni bot orqali saqlash xavfsiz emas — Web UI da `AI tokens` bo‘limidan qo‘shing.\n"
        "Token qiymati hech qachon API javobida qaytmaydi.",
        reply_markup=kb,
    )
