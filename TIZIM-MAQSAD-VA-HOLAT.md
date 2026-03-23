# Tizimning maqsadi va joriy holati

Bu hujjat **devops-agent** loyihasining *nimaga* xizmat qilishi va *hozirgi kod bazasida* nimalarning amalda ekanini bitta joyda yig‘adi. Texnik topshiriqlar: `tz.md`, `tz1.md`.

---

## 1. Maqsad

**Asosiy maqsad:** foydalanuvchi tabiiy til bilan (o‘zbek/rus/ingliz aralash mumkin) serverlar haqida muammo yoki vazifa yozadi; tizim serverni **alias** bo‘yicha topadi, **SSH** orqali ulanadi, **diagnostika** qiladi, **LLM** yordamida keyingi qadamlarni rejalashtiradi, xavfsiz chegarada **buyruqlarni bajaradi**, natijani **timeline** va **audit jurnal**da saqlaydi.

**Yakuniy viziya (TZ bilan mos):** “Bitta chat orqali infratuzilmani boshqarish” — ya’ni oddiy chat emas, balki **AI-driven infrastructure operator** yo‘nalishidagi platforma.

**Qamrov (TZ bo‘yicha ma’no):**

- **DevOps:** servislar, Docker, tarmoq portlari, umumiy holat (to‘liq CI/CD pipeline bu loyihada alohida mahsulot sifatida emas, lekin servis/docker diagnostikasi va restart kabi amallar qamrab olinadi).
- **SysAdmin:** `systemctl`, disk/RAM, loglar, paketlar haqida ma’lumot olish va cheklangan tuzatishlar.
- **NetAdmin:** portlar, `ss`/`netstat`, firewall holatini o‘qish, ulanish tekshiruvlari.

---

## 2. Joriy arxitektura (qanday ishlaydi)

```text
Foydalanuvchi
    ├── Web (React + nginx) ──► /api ──► FastAPI
    └── Telegram (aiogram)   ──► HTTP  ──► FastAPI

FastAPI
    ├── PostgreSQL (servers, tasks, task_steps, logs)
    └── Redis + Celery: vazifa yaratilganda worker chaqiriladi

Celery worker
    └── DevOpsAgent: LLM (intent + qaror sikli) + Paramiko SSH → maqsadli Linux server
```

**Servislar (Docker Compose):**

| Servis   | Rol |
|----------|-----|
| `postgres` | Ma’lumotlar bazasi |
| `redis`    | Navbat (broker) |
| `api`      | FastAPI, migratsiya (entrypoint) |
| `worker`   | Celery + agent + SSH |
| `web`      | Frontend build + nginx, `/api` proksi |
| `bot`      | (profil `telegram`) aiogram bot |

---

## 3. Realizatsiya holati — nima tayyor va ishlaydi

Quyidagilar **mavjud kodda amalga oshirilgan** va bir-biri bilan bog‘langan:

| Bo‘lim | Holat |
|--------|--------|
| **REST API** | Serverlar CRUD (`/api/servers`), vazifalar (`/api/tasks`, `/api/tasks/submit`), bitta vazifa + qadamlar + loglar (`GET /api/tasks/{id}`), `GET /health`, Swagger `/docs` |
| **Navbat** | Redis + Celery; vazifa yaratilganda `run_agent_task` workerda ishga tushadi |
| **SSH** | Paramiko; kalit fayl (`key_path`, odatda konteynerda `/ssh-keys/...`) yoki `SSH_PRIVATE_KEY_B64`; ulanish **timeout**, **qayta urinish** va **backoff** |
| **AI agent** | Intent: `server_name`, `problem_summary`, `diagnostic_plan[{command, explanation}]`. Keyin sikl: tahlil + `next_steps[{command, explanation}]` + `step_phase` (`execute` / `verify`). Diagnostika → qaror → bajarish → verifikatsiya takrorlanadi (iteratsiya limiti bilan) |
| **Server topish** | Alias nom bo‘yicha moslashtirish; buyruqdan server nomini aniqlash; **bitta server** bo‘lsa avtomatik ishlatish + audit yozuvi |
| **Cheksiz sikl himoyasi** | `agent_max_iterations` + bir xil buyruqlar ketma-ket 2 marta takrorlansa to‘xtash |
| **Timeline** | Har qadam: `step_order`, `command`, `output`, `status`, vaqt, **`explanation` (nima uchun)**, **`phase`** (`diagnose` / `execute` / `verify`) |
| **Audit** | `logs` jadvali: vazifa bo‘yicha xabarlar (intent, server, tahlil, xatolar) |
| **Xavfsizlik** | Xavfli buyruqlar filtri; buyruq uzunligi cheklovi; `command_text` max 8000 belgi |
| **Web UI** | Dashboard (vazifa yuborish, ro‘yxat), serverlar boshqaruvi, vazifa sahifasida timeline + audit |
| **Telegram** | Matn buyrug‘i → API; polling orqali yangi qadamlar chiqqanda progress matni yangilanadi |
| **Migratsiya** | Alembic: `001` sxema, `002` — `task_steps.explanation`, `task_steps.phase` |

**AI provayder:** OpenAI (yoki mos `OPENAI_BASE_URL`, masalan mahalliy LLM) yoki Anthropic — muhit o‘zgaruvchilari orqali (`AI_PROVIDER`).

---

## 4. Ma’lumotlar bazasi (joriy sxema)

| Jadval | Vazifa |
|--------|--------|
| `servers` | Alias `name`, `host`, `user`, `auth_type`, `key_path`, vaqt |
| `tasks` | Foydalanuvchi buyrug‘i, `server_id`, `status`, `source` (web/telegram), `user_id` (Telegram uchun), `summary` |
| `task_steps` | Timeline: buyruq, chiqish, holat, **`explanation`**, **`phase`**, tartib raqami |
| `logs` | Audit yozuvlari (matn, daraja, vaqt) |

---

## 5. Vazifa hayoti (statuslar)

- `pending` — yaratildi, worker kutmoqda  
- `running` — agent SSH/LLM ishlayapti  
- `done` — agent yakuniy xulosaga keldi  
- `error` — server topilmadi, SSH/LLM xatosi yoki boshqa fatal holat  

---

## 6. Nima hali to‘liq “enterprise” emas (ochiq holat)

TZdagi ba’zi nuqtalar **keyingi iteratsiya** uchun qoldirilgan yoki soddalashtirilgan:

- **API autentifikatsiya / multi-user** — hozir ochiq API (ichki tarmoq yoki reverse proxy bilan himoya qilish tavsiya etiladi).
- **Rate limiting**, **maxsus RBAC** — kodda yo‘q.
- **SSH host key siyosati** — `AutoAddPolicy` qulay; productionda `known_hosts` yoki sertifikatlar bilan qat’iyroq model yaxshiroq.
- **To‘liq CI/CD integratsiyasi** (GitLab/Jenkins pipeline boshqaruvi) — alohida modul sifatida rejalashtirilishi kerak.
- **LLM xatoliklari** — JSON buzilsa yoki model noto‘g‘ri javob bersa, vazifa `error` yoki qisman to‘xtashi mumkin; retry strategiyasi soddalashtirilgan.

Bu “ishlamayapti” degani emas — **hozirgi holat shaffof chegaralar bilan ishchi MVP+ darajasida**.

---

## 7. Tezkor ishga tushirish

Batafsil qadamlar: [INSTALL.md](INSTALL.md). Qisqacha:

```bash
cp .env.example .env
# AI kalitlari va SSH sozlang
docker compose up -d --build
```

- UI: `http://localhost`  
- API hujjatlari: `http://localhost:8000/docs`  
- Telegram: `docker compose --profile telegram up -d --build`

Misollar: [USAGE.md](USAGE.md). REST: [API.md](API.md).

---

## 8. Xulosa

| Savol | Javob |
|-------|--------|
| **Tizim nima qiladi?** | Tabiiy til buyrug‘ini server aliasiga bog‘lab, SSH orqali diagnostika va LLM boshqaruvidagi xavfsiz buyruqlar zanjirini bajaradi; barcha qadam va audit saqlanadi. |
| **TZ bilan bog‘liqlik?** | Asosiy oqim (chat, server registry, agent modullari, timeline, Telegram, Web, PostgreSQL, Redis, Docker) qoplangan; enterprise xavfsizlik va CI/CD chuqurligi keyingi bosqich. |
| **Hozirgi barqarorlik?** | Docker orqali butun zanjir ishga tushirish mo‘ljallangan; migratsiya avtomatik; agent sikli limit va takrorlanish himoyasi bilan. |

---

*Oxirgi yangilanish: loyiha holati ushbu fayl yozilgan paytdagi kod bazasiga mosdir.*
