"""FSM: server qo‘shish — `POST /api/internal/servers` (X-Internal-Secret)."""

from __future__ import annotations

import os

import httpx
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

API_URL = (os.environ.get("API_BASE_URL") or os.environ.get("API_URL") or "").rstrip("/")
INTERNAL = os.environ.get("API_INTERNAL_SECRET", "").strip()

router = Router()


class AddServerFSM(StatesGroup):
    name = State()
    host = State()
    ssh_user = State()
    auth_type = State()
    key_path = State()
    confirm = State()


def _headers() -> dict[str, str]:
    h: dict[str, str] = {"Content-Type": "application/json"}
    if INTERNAL:
        h["X-Internal-Secret"] = INTERNAL
    return h


@router.message(Command("addserver"))
async def addserver_entry(message: Message, state: FSMContext) -> None:
    if not INTERNAL:
        await message.answer("API_INTERNAL_SECRET sozlanmagan — server qo‘shish uchun backend va bot .env ni tekshiring.")
        return
    await state.set_state(AddServerFSM.name)
    await message.answer("Yangi server: qisqa nom (alias) yuboring (masalan: prod-web).")


@router.message(AddServerFSM.name, F.text)
async def srv_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(AddServerFSM.host)
    await message.answer("Host (IP yoki DNS), SSH odatda 22-port:")


@router.message(AddServerFSM.host, F.text)
async def srv_host(message: Message, state: FSMContext) -> None:
    await state.update_data(host=message.text.strip())
    await state.set_state(AddServerFSM.ssh_user)
    await message.answer("SSH foydalanuvchi (masalan root yoki ubuntu):")


@router.message(AddServerFSM.ssh_user, F.text)
async def srv_user(message: Message, state: FSMContext) -> None:
    await state.update_data(ssh_user=message.text.strip())
    await state.set_state(AddServerFSM.auth_type)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Kalit (konteyner path)", callback_data="auth:key"),
            ],
            [
                InlineKeyboardButton(text="Parol (SSH_PASSWORD muhitda)", callback_data="auth:pwd"),
            ],
        ]
    )
    await message.answer("Autentifikatsiya turini tanlang:", reply_markup=kb)


@router.callback_query(AddServerFSM.auth_type, F.data.startswith("auth:"))
async def srv_auth_cb(query: CallbackQuery, state: FSMContext) -> None:
    kind = query.data.split(":", 1)[1] if query.data else "key"
    await state.update_data(auth_type="ssh_key" if kind == "key" else "password")
    await state.set_state(AddServerFSM.key_path)
    await query.message.answer(
        "Konteynerdagi kalit yo‘li (masalan /ssh-keys/id_ed25519) yoki `default` — /ssh-keys/id_rsa"
    )
    await query.answer()


@router.message(AddServerFSM.key_path, F.text)
async def srv_keypath(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    path = "/ssh-keys/id_rsa" if raw.lower() == "default" else raw
    await state.update_data(key_path=path)
    data = await state.get_data()
    await state.set_state(AddServerFSM.confirm)
    summary = (
        f"Nom: {data.get('name')}\n"
        f"Host: {data.get('host')}\n"
        f"User: {data.get('ssh_user')}\n"
        f"Auth: {data.get('auth_type')}\n"
        f"Key path: {path}\n\n"
        "Tasdiqlaysizmi?"
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Ha, yuborish", callback_data="srv:yes"),
                InlineKeyboardButton(text="Bekor", callback_data="srv:no"),
            ],
        ]
    )
    await message.answer(summary, reply_markup=kb)


@router.callback_query(AddServerFSM.confirm, F.data == "srv:no")
async def srv_cancel(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await query.message.answer("Bekor qilindi.")
    await query.answer()


@router.callback_query(AddServerFSM.confirm, F.data == "srv:yes")
async def srv_submit(query: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    if not API_URL or not INTERNAL:
        await query.message.answer("API yoki secret sozlanmagan.")
        await query.answer()
        return
    body = {
        "name": data.get("name"),
        "host": data.get("host"),
        "user": data.get("ssh_user"),
        "auth_type": data.get("auth_type"),
        "key_path": data.get("key_path"),
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{API_URL}/api/internal/servers", json=body, headers=_headers())
            r.raise_for_status()
        await query.message.answer("Server API ga yozildi. Web UI dan tekshiring.")
    except Exception as e:
        await query.message.answer(f"API xato: {e}")
    await query.answer()
