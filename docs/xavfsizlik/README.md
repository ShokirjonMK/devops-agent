# Xavfsizlik

## Buyruq filtri

**Fayl:** `app/services/command_filter.py`  
**Funksiya:** `is_command_allowed(command) -> (bool, reason | None)`

Bloklanadigan namunalar: `rm -rf /`, `shutdown`, `dd`, `mkfs`, `curl|sh` va hokazo. Agent har bir SSH buyrug‘ini bajarishdan oldin shu filtrdan o‘tkazadi.

## SSH

**Fayl:** `app/services/ssh_client.py`

- Ulanish **timeout** va **qayta urinish** (backoff).
- Kalit: fayl yo‘li (`key_path`) yoki `SSH_PRIVATE_KEY_B64`.
- **AutoAddPolicy** — qulaylik uchun; productionda `known_hosts` / qat’iy host key siyosati tavsiya etiladi.

## Shifrlash (vault)

**Fayl:** `app/services/encryption_service.py`

- **AES-256-GCM**, har yozuv uchun alohida IV va salt; kontekst **AAD** sifatida (noto‘g‘ri kontekstda decrypt yiqiladi).
- Master kalit: **`ENCRYPTION_MASTER_KEY_B64`** (32 bayt, base64).
- DB da faqat **binary** maydonlar; ochiq secret REST javobida qaytarilmaydi (faqat metadata ro‘yxat).

## Autentifikatsiya

### Telegram Login Widget

**Fayl:** `app/services/telegram_auth.py` — HMAC-SHA256, `auth_date` 1 soatdan oshmasligi.  
**Endpoint:** `POST /api/auth/telegram` (to‘liq widget maydonlari JSON).

### JWT

**Fayl:** `app/security_jwt.py`  
**Sozlama:** `JWT_SECRET`, `JWT_EXPIRE_MINUTES` (config).

Credentials va boshqa himoyalangan endpointlar: **Bearer** token.

## API

- Katta kiritma cheklovi: masalan `command_text` max uzunlik (Pydantic).
- **422** validatsiya xatolari strukturalangan JSON.

## Tavsiyalar (production)

- API uchun **rate limit**, **API key** yoki **OAuth** qatlami.
- SSH uchun cheklangan foydalanuvchi (read-only rejim ixtiyoriy).
- `.env` va kalitlarni hech qachon repoga commit qilmang.
