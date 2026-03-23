# Foydalanish (real misollar)

## 1. Server qo‘shish (alias)

Web UI → **Serverlar** yoki API:

```bash
curl -s -X POST http://localhost:8000/api/servers \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"sarbon\",\"host\":\"10.0.0.5\",\"user\":\"ubuntu\",\"auth_type\":\"ssh_key\",\"key_path\":\"/ssh-keys/id_rsa\"}"
```

`name` — tabiiy buyruqda ishlatiladigan alias (`sarbon serverida …`).

## 2. Vazifa yuborish (Web / API)

```bash
curl -s -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d "{\"command_text\":\"sarbon serverida nginx holatini tekshir va kerak bo‘lsa restart qil\"}"
```

Javob: `202`, tana ichida `id`. Timeline:

```bash
curl -s http://localhost:8000/api/tasks/1
```

## 3. Telegram

Botga xabar (matn):

`sarbon serverida docker konteynerlar ro‘yxatini ko‘rsat`

Bot vazifa yaratadi (`/api/tasks/submit`) va holatni so‘rov bilan kuzatadi.

## 4. Muammolar bo‘yicha misollar (agent xatti-harakati)

Quyidagilar **LLM + SSH chiqishi** ga bog‘liq; agent diagnostika buyruqlarini ishga tushirib, keyin xavfsiz tuzatish buyruqlarini taklif qiladi.

### 4.1 Nginx ishlamayapti

**Buyruq:** `prod serverida nginx ishlamayapti`

**Kutiladigan mantiq:** `systemctl status nginx`, loglar, so‘ngra `nginx -t`, `systemctl restart nginx` kabi qadamlar (LLM qaroriga ko‘ra).

**Siz tekshirasiz:** Web UI → vazifa → qadamlar va `summary`.

### 4.2 Docker to‘xtagan

**Buyruq:** `test serverida docker ishlamayapti`

**Kutiladigan:** `systemctl status docker`, `journalctl` fragmenti, `systemctl start docker` (agar LLM taklif qilsa va filtr ruxsat bersa).

### 4.3 Port yopiq

**Buyruq:** `sarbon serverida 80-port ochiqmi tekshir`

**Kutiladigan:** `ss -tulnp` / `curl`, firewall holati.

### 4.4 Disk to‘lib qolgan

**Buyruq:** `prod serverida disk to‘lib qolgan`

**Kutiladigan:** `df -h`, katta kataloglar; **TZ dagi “tozalash”** uchun agent faqat xavfsiz buyruqlarni bajaradi — `rm -rf /` kabi buyruqlar **filtr** bilan bloklanadi. Qo‘lda tozalash kerak bo‘lishi mumkin.

### 4.5 SSH muvaffaqiyatsiz

Kalit yo‘q, noto‘g‘ri `host`, tarmoq yopiq — vazifa `error`, `summary` va loglarda sabab. Worker **SSH ulanishni** bir necha marta qayta urinadi (`SSH_CONNECT_RETRIES` / config).

## 5. Xavfsizlik eslatmalari

- Productionda `AutoAddPolicy` o‘rniga known_hosts yoki siz tanlagan siyosatni qo‘llash tavsiya etiladi.
- AI taklif qilgan har bir buyruq **command filter** dan o‘tadi.
- Kritik muhitda alohida **read-only** rejim va inson tasdiqlash qo‘shish maqsadga muvofiq.

Batafsil REST: [API.md](API.md).
