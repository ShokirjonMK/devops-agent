"""Admin/owner: qisqa health (faqat ro‘yxatdagi ID lar)."""

from __future__ import annotations

import os

import httpx
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

API_URL = (os.environ.get("API_BASE_URL") or os.environ.get("API_URL") or "").rstrip("/")


def _admin_ids() -> set[int]:
    raw = os.environ.get("ADMIN_TELEGRAM_IDS", "")
    out: set[int] = set()
    for p in raw.split(","):
        p = p.strip()
        if p.lstrip("-").isdigit():
            out.add(int(p))
    return out


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    uid = message.from_user.id if message.from_user else 0
    if uid not in _admin_ids():
        await message.answer("Bu buyruq faqat admin/owner Telegram ID lar uchun.")
        return
    if not API_URL:
        await message.answer("API_URL sozlanmagan.")
        return
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{API_URL}/api/health")
            r.raise_for_status()
            data = r.json()
        await message.answer(f"API health:\n{data}")
    except Exception as e:
        await message.answer(f"Health olishda xato: {e}")
