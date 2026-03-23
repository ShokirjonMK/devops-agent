"""Telegram Login Widget: HMAC-SHA256 hash tekshiruvi."""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any


def verify_telegram_login(data: dict[str, Any], bot_token: str) -> bool:
    """
    https://core.telegram.org/widgets/login#checking-authorization
    secret_key = SHA256(bot_token)
    data_check_string = key=value qatorlari, kalitlar bo'yicha tartiblangan, \\n bilan.
    """
    if not bot_token or not data:
        return False
    check_hash = data.get("hash")
    if not check_hash or not isinstance(check_hash, str):
        return False
    try:
        auth_date = int(data.get("auth_date", 0))
    except (TypeError, ValueError):
        return False
    if time.time() - auth_date > 3600:
        return False
    parts: list[str] = []
    for key in sorted(k for k in data.keys() if k != "hash"):
        val = data[key]
        if val is None:
            continue
        parts.append(f"{key}={val}")
    data_check_string = "\n".join(parts)
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    h = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(h, check_hash)
