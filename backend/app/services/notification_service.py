"""Billing bildirishnomalari — Telegram bot orqali."""
from __future__ import annotations

import httpx
import structlog

log = structlog.get_logger("notification_service")


class NotificationService:

    def _send(self, chat_id: int | str, text: str) -> None:
        from app.config import get_settings
        settings = get_settings()
        token = settings.telegram_bot_token
        if not token:
            log.warning("TELEGRAM_BOT_TOKEN yo'q, bildirishnoma yuborilmadi")
            return
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            httpx.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
        except Exception as e:
            log.error("telegram_notify_failed", error=str(e))

    def trial_ending_soon(self, telegram_id: int, days_left: int) -> None:
        self._send(
            telegram_id,
            f"⏰ <b>Trial tugaydi!</b>\n"
            f"Sizning bepul sinov muddatingiz <b>{days_left} kun</b> ichida tugaydi.\n"
            f"Uzluksiz foydalanish uchun obunani yangilang: /billing"
        )

    def trial_expired(self, telegram_id: int) -> None:
        self._send(
            telegram_id,
            "❌ <b>Trial muddati tugadi</b>\n"
            "Siz Free rejimiga o'tdingiz. Pro imkoniyatlardan foydalanish uchun: /plan"
        )

    def payment_failed(self, telegram_id: int, plan_name: str) -> None:
        self._send(
            telegram_id,
            f"💳 <b>To'lov amalga oshmadi</b>\n"
            f"<b>{plan_name}</b> tarifi uchun to'lov muammosi yuz berdi.\n"
            f"Iltimos, to'lov ma'lumotlarini yangilang yoki biz bilan bog'laning."
        )

    def payment_success(self, telegram_id: int, plan_name: str, amount_usd: float) -> None:
        self._send(
            telegram_id,
            f"✅ <b>To'lov qabul qilindi</b>\n"
            f"Tarif: <b>{plan_name}</b>\n"
            f"Summa: <b>${amount_usd:.2f}</b>\n"
            f"Obunangiz yangilandi!"
        )

    def quota_warning(self, telegram_id: int, resource: str, percent: int) -> None:
        self._send(
            telegram_id,
            f"⚠️ <b>Limit {percent}% ishlatildi</b>\n"
            f"<b>{resource}</b> limiti {percent}%ga yetdi.\n"
            f"Limitni oshirish uchun: /plan"
        )

    def quota_exceeded(self, telegram_id: int, resource: str) -> None:
        self._send(
            telegram_id,
            f"🚫 <b>Limit tugadi</b>\n"
            f"<b>{resource}</b> limiti to'liq ishlatildi.\n"
            f"Tarif yangilang: /plan"
        )

    def low_credit_warning(self, telegram_id: int, balance_usd: float) -> None:
        self._send(
            telegram_id,
            f"💰 <b>AI kredit kam qoldi</b>\n"
            f"Joriy balans: <b>${balance_usd:.2f}</b>\n"
            f"Kredit qo'shish uchun: /billing"
        )

    def referral_reward(self, telegram_id: int, reward_usd: float, referred_username: str) -> None:
        self._send(
            telegram_id,
            f"🎁 <b>Referral mukofoti!</b>\n"
            f"<b>{referred_username}</b> siz taklif qilgan va to'lov qildi.\n"
            f"Hisobingizga <b>${reward_usd:.2f}</b> kredit qo'shildi!"
        )

    def subscription_cancelled(self, telegram_id: int, end_date: str) -> None:
        self._send(
            telegram_id,
            f"📅 <b>Obuna bekor qilindi</b>\n"
            f"Obunangiz <b>{end_date}</b> gacha ishlaydi, so'ng Free rejimga o'tiladi.\n"
            f"Qayta faollashtirish uchun: /plan"
        )


notification_service = NotificationService()
