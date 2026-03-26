"""Bot billing buyruqlari: /plan, /referral, /credits."""
from __future__ import annotations

import os

import httpx
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

API_URL = (os.environ.get("API_BASE_URL") or os.environ.get("API_URL") or "http://127.0.0.1:8000").rstrip("/")
APP_URL = os.environ.get("APP_URL", "https://devagent.z7.uz")
INTERNAL = os.environ.get("API_INTERNAL_SECRET", "").strip()


def _hdrs() -> dict:
    h: dict = {}
    if INTERNAL:
        h["X-Internal-Secret"] = INTERNAL
    return h


def _bar(used: int, limit: int, width: int = 10) -> str:
    if limit <= 0:
        return "∞"
    pct = min(1.0, used / limit)
    filled = round(pct * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"{bar} {used}/{limit}"


async def _get_json(path: str, user_id: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{API_URL}{path}",
                headers={**_hdrs(), "X-Telegram-User-Id": user_id},
            )
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return None


@router.message(Command("plan"))
async def cmd_plan(message: Message) -> None:
    if not message.from_user:
        return
    uid = str(message.from_user.id)

    data = await _get_json(f"/api/internal/user-subscription/{uid}", uid)
    if not data:
        await message.answer(
            "📋 <b>Tarifingiz</b>\n\nMa'lumot yuklanmadi. Iltimos keyinroq urinib ko'ring.\n\n"
            f"Tariflarni ko'rish: {APP_URL}/upgrade",
            parse_mode="HTML",
        )
        return

    plan = data.get("plan_name", "Free")
    tasks_used = data.get("tasks_used_month", 0)
    tasks_limit = data.get("tasks_limit", 10)
    servers_used = data.get("servers_used", 0)
    servers_limit = data.get("servers_limit", 1)
    credit = data.get("ai_credit_balance_usd", 0.0)
    period_end = data.get("period_end", "")
    trial_end = data.get("trial_ends_at")

    tasks_bar = _bar(tasks_used, tasks_limit)
    servers_bar = _bar(servers_used, servers_limit)

    lines = [
        f"📋 <b>Sizning Tarifingiz: {plan}</b>",
        "",
        f"📌 Vazifalar:  {tasks_bar}",
        f"🖥 Serverlar:  {servers_bar}",
        f"💰 AI Kredit:  ${credit:.2f}",
    ]
    if trial_end:
        lines.append(f"⏰ Trial tugaydi: {trial_end[:10]}")
    if period_end:
        lines.append(f"📅 Obuna tugaydi: {period_end[:10]}")
    lines += ["", f"🔗 Yangilash: {APP_URL}/upgrade"]

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("referral"))
async def cmd_referral(message: Message) -> None:
    if not message.from_user:
        return
    uid = str(message.from_user.id)

    data = await _get_json(f"/api/internal/user-referral/{uid}", uid)
    if not data:
        await message.answer(
            "🎁 <b>Referral dasturi</b>\n\nMa'lumot yuklanmadi.\n\n"
            f"Referral havolangizni ko'rish: {APP_URL}/billing",
            parse_mode="HTML",
        )
        return

    code = data.get("code", "—")
    total = data.get("total_referrals", 0)
    converted = data.get("converted", 0)
    earned = data.get("total_earned_usd", 0.0)
    bot_url = data.get("bot_url", f"https://t.me/devOpsmkbot?start=ref_{code}")
    web_url = data.get("web_url", f"{APP_URL}?ref={code}")
    reward = data.get("reward_referrer_usd", 5.0)
    trial_days = data.get("reward_referred_days", 14)

    conv_bar = _bar(converted, max(total, 1), width=8)

    lines = [
        "🎁 <b>Referral Dasturi</b>",
        "",
        f"🔑 Kod: <code>{code}</code>",
        f"👥 Taklif qilinganlar: {total}",
        f"✅ To'lov qilganlar: {conv_bar}",
        f"💵 Jami daromad: ${earned:.2f}",
        "",
        f"🎯 Har bir to'lov uchun: ${reward:.0f} kredit",
        f"🎁 Yangi foydalanuvchiga: {trial_days} kun Pro trial",
        "",
        f"🔗 Havola:\n{bot_url}",
        f"🌐 Web:\n{web_url}",
    ]
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("credits"))
async def cmd_credits(message: Message) -> None:
    if not message.from_user:
        return
    uid = str(message.from_user.id)

    data = await _get_json(f"/api/internal/user-credits/{uid}", uid)
    if not data:
        await message.answer(
            f"💰 <b>AI Kredit</b>\n\nMa'lumot yuklanmadi.\n\n{APP_URL}/billing",
            parse_mode="HTML",
        )
        return

    balance = data.get("balance_usd", 0.0)
    deposited = data.get("total_deposited_usd", 0.0)
    spent = data.get("total_spent_usd", 0.0)

    lines = [
        "💰 <b>AI Kredit Balans</b>",
        "",
        f"💵 Joriy balans: <b>${balance:.2f}</b>",
        f"📥 Jami to'ldirilgan: ${deposited:.2f}",
        f"📤 Jami sarflangan: ${spent:.2f}",
        "",
        f"🔗 Kredit to'ldirish: {APP_URL}/billing",
    ]
    await message.answer("\n".join(lines), parse_mode="HTML")
