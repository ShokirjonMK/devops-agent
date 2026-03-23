# TZ.md — DevOps Agent v2: To'liq Texnik Topshiriq

> **Versiya:** 2.0  
> **Maqsad:** Telegram bot + Web UI orqali AI-boshqaruvidagi infratuzilma operatori  
> **Holat:** Loyihalash bosqichi

---

## 1. Umumiy maqsad va viziya

**Platforma** foydalanuvchiga bitta interface orqali (Telegram bot yoki Web UI) o'z serverlarini boshqarish, muammolarni diagnostika qilish va loyihalarni deploy qilish imkonini beradi. Har bir foydalanuvchi o'z SSH kalitlari, AI token to'plami va server registri bilan mustaqil ishlaydi.

### 1.1 Asosiy foydalanuvchi stsenariylar

| # | Stsenariy | Interface |
|---|-----------|-----------|
| 1 | "nginx ishlamayapti" → diagnostika + tuzatish | Bot / Web |
| 2 | "production serverga deploy qil" → CI pipeline | Bot / Web |
| 3 | "disk to'lib qoldi" → tahlil + tozalash | Bot / Web |
| 4 | Serverlar monitoringi dashboardi | Web |
| 5 | AI token va SSH kalitlarini boshqarish | Web |
| 6 | Jamoa a'zolari va huquqlarni boshqarish | Web |

---

## 2. Arxitektura

### 2.1 Umumiy sxema

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENTS                              │
│   Telegram Bot (aiogram 3.x)    Web UI (React + Vite)       │
└──────────────┬──────────────────────────┬───────────────────┘
               │ HTTP/WS                  │ HTTP/WS
┌──────────────▼──────────────────────────▼───────────────────┐
│                    FastAPI (Python 3.12)                     │
│  • JWT Auth (Telegram Login Widget / Bot token verify)      │
│  • REST API + WebSocket (real-time task stream)             │
│  • Rate limiting (slowapi)                                   │
└────┬─────────────────┬────────────────────┬─────────────────┘
     │                 │                    │
┌────▼────┐    ┌───────▼──────┐    ┌────────▼───────┐
│PostgreSQL│    │  Redis 7     │    │   Vault / AES  │
│(primary) │    │  • Celery    │    │  (secrets mgr) │
│(replica) │    │  • Cache     │    └────────────────┘
└────┬────┘    │  • Pub/Sub   │
     │         └───────┬──────┘
     │                 │
┌────▼─────────────────▼──────────────────────────────────────┐
│                   Celery Workers (scalable)                  │
│   DevOpsAgent: LLM Router → SSH Executor → Result Parser    │
└─────────────────────────────────────────────────────────────┘
                          │ SSH / Paramiko
               ┌──────────▼──────────┐
               │   Target Linux Servers              │
               └─────────────────────┘
```

### 2.2 Docker Compose servislari

| Servis | Image | Rol |
|--------|-------|-----|
| `postgres` | postgres:16-alpine | Asosiy DB + replication |
| `redis` | redis:7-alpine | Broker + cache + pub/sub |
| `api` | custom (FastAPI) | Backend, migrations |
| `worker` | custom (Celery) | Agent + SSH executor |
| `beat` | custom (Celery beat) | Scheduled tasks (monitoring) |
| `web` | custom (nginx + React build) | Frontend + reverse proxy |
| `bot` | custom (aiogram) | Telegram bot |
| `vault` | hashicorp/vault (optional) | Secrets backend (prod) |

---

## 3. Autentifikatsiya va foydalanuvchi boshqaruvi

### 3.1 Telegram Login

**Web UI uchun:**
- Telegram Login Widget (`login.js`) orqali OAuth-like flow
- Widget `hash` parametrini HMAC-SHA256 bilan verifikatsiya (bot token asosida)
- Verifikatsiyadan o'tgach JWT (access: 15 min, refresh: 30 kun) beriladi
- JWT `HttpOnly` cookie + `Authorization: Bearer` ikkalasini qo'llab-quvvatlash

**Bot uchun:**
- `/start` → Telegram `user_id` + `username` orqali avtomatik ro'yxatdan o'tish
- Yangi foydalanuvchi `role = viewer` bilan yaratiladi (admin aktivlashtiradi)

### 3.2 Foydalanuvchi modeli

```python
class User:
    id: UUID
    telegram_id: int          # unique
    telegram_username: str
    telegram_first_name: str
    telegram_photo_url: str
    role: Enum["owner", "admin", "operator", "viewer"]
    is_active: bool
    created_at: datetime
    last_seen_at: datetime
    settings: JSONB           # UI preferences
```

### 3.3 Rol va huquqlar (RBAC)

| Huquq | owner | admin | operator | viewer |
|-------|-------|-------|----------|--------|
| Serverlar qo'shish/o'chirish | ✅ | ✅ | ❌ | ❌ |
| Buyruq bajarish (execute) | ✅ | ✅ | ✅ | ❌ |
| Diagnostika (read-only) | ✅ | ✅ | ✅ | ✅ |
| Foydalanuvchi boshqaruvi | ✅ | ✅ | ❌ | ❌ |
| Token boshqaruvi (o'z) | ✅ | ✅ | ✅ | ✅ |
| Analytics ko'rish | ✅ | ✅ | ✅ | ✅ |
| Monitoring sozlash | ✅ | ✅ | ❌ | ❌ |

---

## 4. Secrets boshqaruvi (SSH + AI tokenlar)

### 4.1 Shifrlash strategiyasi

```
Master Key (env: MASTER_ENCRYPTION_KEY, AES-256-GCM)
    └── Per-user derived key (PBKDF2 / HKDF)
           └── Encrypted secret stored in PostgreSQL
```

- Barcha maxfiy ma'lumotlar `secrets` jadvalida **AES-256-GCM** bilan shifrlangan
- Master kalit faqat environment variable yoki HashiCorp Vault orqali
- DB da hech qachon ochiq matn saqlanmaydi
- Har bir secret o'ziga xo's `salt` + `nonce` bilan shifrlangan

### 4.2 SSH Credentials

```python
class SSHCredential:
    id: UUID
    user_id: UUID
    name: str                  # "Production VPS", "Dev Server"
    label: str                 # foydalanuvchi uchun ko'rsatma
    auth_type: Enum["key", "password", "key+passphrase"]
    encrypted_private_key: bytes
    encrypted_passphrase: bytes | None
    encrypted_password: bytes | None
    public_key_fingerprint: str  # ochiq — identifikatsiya uchun
    default_user: str          # "ubuntu", "root"
    created_at: datetime
    last_used_at: datetime
```

### 4.3 AI Token boshqaruvi

```python
class AIToken:
    id: UUID
    user_id: UUID
    provider: Enum[
        "openai", "anthropic", "google_gemini",
        "mistral", "cohere", "groq", "together",
        "openrouter", "deepseek", "xai_grok",
        "perplexity", "fireworks", "custom"
    ]
    name: str                  # "GPT-4 token", "My Claude key"
    encrypted_token: bytes
    base_url: str | None       # custom endpoint uchun
    model_override: str | None # default model
    is_active: bool
    is_default: bool           # provider uchun standart
    monthly_budget_usd: float | None
    usage_this_month_usd: float
    created_at: datetime
    last_used_at: datetime
```

**Qo'llab-quvvatlanadigan provayderlar va modellar:**

| Provider | Modellar |
|----------|---------|
| OpenAI | gpt-4o, gpt-4-turbo, gpt-3.5-turbo, o1, o3 |
| Anthropic | claude-opus-4, claude-sonnet-4, claude-haiku-4 |
| Google | gemini-2.0-flash, gemini-1.5-pro, gemini-ultra |
| Mistral | mistral-large, mistral-medium, codestral |
| Groq | llama-3.3-70b, mixtral-8x7b |
| DeepSeek | deepseek-chat, deepseek-coder |
| xAI | grok-2, grok-beta |
| OpenRouter | barcha modellar (unified API) |
| Custom | istalgan OpenAI-compatible endpoint |

### 4.4 LLM Router (aqlli tanlash)

```python
class LLMRouter:
    """
    Foydalanuvchining aktiv tokenlaridan eng yaxshisini tanlaydi:
    1. task_type bo'yicha preferred model (deploy → codestral, diagnose → gpt-4o)
    2. budget limit tekshiruvi
    3. fallback zanjiri: preferred → default → birinchi aktiv
    4. rate limit yutilsa → keyingi provayderga o'tish
    """
```

---

## 5. Server registry

```python
class Server:
    id: UUID
    user_id: UUID              # egasi
    name: str                  # alias ("prod-web", "staging-db")
    description: str
    host: str                  # IP yoki hostname
    port: int                  # default 22
    ssh_user: str
    ssh_credential_id: UUID    # FK → SSHCredential
    tags: list[str]            # ["production", "web", "nginx"]
    environment: Enum["production", "staging", "development", "testing"]
    os_type: str               # auto-detect yoki manual
    os_version: str
    last_check_at: datetime
    last_check_status: Enum["online", "offline", "unknown"]
    monitoring_enabled: bool
    monitoring_interval_minutes: int  # default 5
    created_at: datetime
    metadata: JSONB            # CPU count, RAM total — auto-populated
```

---

## 6. Agent tizimi

### 6.1 Vazifa turlari

```python
class TaskType(Enum):
    DIAGNOSE    = "diagnose"    # muammoni aniqlash (read-only birinchi)
    EXECUTE     = "execute"     # buyruq bajarish
    DEPLOY      = "deploy"      # loyiha deploy
    MONITOR     = "monitor"     # holatni tekshirish
    REPORT      = "report"      # hisobot tayyorlash
    INTERACTIVE = "interactive" # bot bilan dialog
```

### 6.2 Agent sikli

```
User input (natural language)
        │
        ▼
[1] IntentParser (LLM)
    → task_type, server_alias, problem_summary,
      risk_level (low/medium/high/critical),
      requires_confirmation (bool)
        │
        ├─ risk_level = high/critical ──► Foydalanuvchidan tasdiqlash so'raladi
        │
        ▼
[2] PlanGenerator (LLM)
    → diagnostic_steps: [{command, explanation, phase, safe}]
    → estimated_duration
        │
        ▼
[3] SafetyFilter
    → Har bir buyruq: safe / warn / block
    → Bloklangan buyruqlar ro'yxati (rm -rf /, mkfs, ...)
        │
        ▼
[4] SSHExecutor (Paramiko)
    → timeout per command: 30s (default), configurable
    → output streaming: Redis pub/sub → WebSocket → UI/Bot
        │
        ▼
[5] ResultAnalyzer (LLM)
    → status: resolved / partial / needs_more / escalate
    → next_steps yoki final_summary
        │
        ├─ resolved ──────────────────► Task DONE
        ├─ needs_more (max 10 iter) ──► [3] ga qaytish
        └─ escalate ─────────────────► Foydalanuvchiga ogohlantirish
```

### 6.3 Deploy pipeline

```python
class DeployConfig:
    """Auto-detected yoki user-defined"""
    project_type: Enum["docker-compose", "docker", "systemd", "pm2", "custom"]
    repo_url: str | None
    branch: str
    pre_deploy_commands: list[str]
    deploy_command: str
    post_deploy_commands: list[str]
    health_check_url: str | None
    health_check_command: str | None
    rollback_command: str | None
    env_file_path: str | None
```

**Deploy qadamlari:**
1. Pre-checks (disk space, git status, running processes)
2. Backup (optional: DB snapshot, config backup)
3. Pull/build
4. Migration (agar aniqlansa)
5. Restart/reload
6. Health check (retry 3x, 10s interval)
7. Rollback (agar health check muvaffaqiyatsiz)
8. Notification

---

## 7. Real-time streaming

### 7.1 WebSocket protokoli

```
Client → WS /ws/tasks/{task_id}?token=...

Server → JSON events:
  {"type": "step_start", "step_id": "...", "command": "...", "explanation": "..."}
  {"type": "output_chunk", "step_id": "...", "chunk": "..."}
  {"type": "step_done", "step_id": "...", "status": "ok", "duration_ms": 1230}
  {"type": "agent_thinking", "message": "Natijalarni tahlil qilmoqda..."}
  {"type": "confirmation_required", "message": "...", "risk": "high"}
  {"type": "task_done", "summary": "...", "duration_ms": 45000}
  {"type": "task_error", "error": "..."}
```

### 7.2 Telegram real-time

- Task boshlanganda: progress xabari yuboriladi
- Har step tugaganda: xabar **edit** (yangi xabar emas) qilinadi
- Uzun output: `...` bilan qisqartiriladi + "To'liq natija: [link]" qo'shiladi
- Task tugaganda: yakuniy hisobot + inline tugmalar

---

## 8. Telegram Bot

### 8.1 Buyruqlar

```
/start          — Kirish, ro'yxatdan o'tish
/help           — Yordam
/servers        — Serverlar ro'yxati
/status [alias] — Server holati
/tasks          — So'nggi 10 ta vazifa
/task [id]      — Vazifa tafsilotlari
/tokens         — AI tokenlar boshqaruvi (inline keyboard)
/settings       — Sozlamalar
/cancel         — Joriy vazifani bekor qilish
```

### 8.2 Natural language flow

```
User: "production serverda nginx restart qil"

Bot: 🔍 Vazifa qabul qilindi
     Server: prod-web (192.168.1.10)
     Amal: nginx restart
     ⚠️ Xizmat vaqtincha to'xtaydi. Davom etaymi?
     [✅ Ha] [❌ Yo'q]

User: [✅ Ha kliklar]

Bot: ⚙️ Bajarilmoqda...
     [1/3] systemctl status nginx ✅
     [2/3] systemctl restart nginx ⏳

     [2/3] systemctl restart nginx ✅ (1.2s)
     [3/3] systemctl status nginx ✅

     ✅ Muvaffaqiyatli
     nginx active (running) — uptime: 0:00:05
     Davomiylik: 8.3s
```

### 8.3 Interaktiv so'rovnoma (onboarding)

Yangi foydalanuvchi `/start` bosganda:
1. Xush kelibsiz xabari
2. "Server qo'shish" inline tugmasi
3. Deep link orqali web UI ga yo'naltirish yoki botda to'g'ridan-to'g'ri server qo'shish wizardi

---

## 9. Web UI

### 9.1 Sahifalar

```
/login                    — Telegram Login Widget
/dashboard                — Asosiy panel
/servers                  — Serverlar ro'yxati
/servers/new              — Server qo'shish
/servers/[id]             — Server tafsilotlari + monitoring grafiklari
/tasks                    — Vazifalar tarixi (filter + search)
/tasks/[id]               — Vazifa tafsilotlari (timeline + logs + output)
/credentials/ssh          — SSH kalitlar boshqaruvi
/credentials/tokens       — AI tokenlar boshqaruvi
/analytics                — To'liq analytics dashboard
/team                     — Jamoa a'zolari (admin/owner)
/settings                 — Shaxsiy sozlamalar
/settings/notifications   — Bildirishnoma sozlamalari
```

### 9.2 Dashboard

- **Jonli holat kartlari:** har bir server (online/offline/warning)
- **Faol vazifalar:** real-time progress
- **So'nggi harakatlar:** timeline
- **Tezkor amallar:** "Yangi vazifa" tugmasi
- **Ogohlantirish paneli:** disk > 80%, servis to'xtagani, SSH ulanmayapti

### 9.3 Vazifa sahifasi (real-time)

- Terminal-uslub chiqish (xterm.js yoki custom)
- Timeline: har bir qadam phase + status + davomiylik
- Audit log panel
- "Bekor qilish" tugmasi
- "Qayta ishga tushirish" tugmasi (agar xato bo'lsa)
- LLM fikrlash jarayoni (collapsible "Agent reasoning")

---

## 10. Monitoring va Analytics

### 10.1 Server monitoringi (Celery beat)

Har `monitoring_interval_minutes` da:
```
SSH → gather metrics:
  - CPU: top -bn1
  - RAM: free -m
  - Disk: df -h
  - Load: uptime
  - Services: systemctl list-units --failed
  - Processes: ps aux --sort=-%cpu | head -10
```

Natijalar `server_metrics` jadvalida saqlanadi (time-series).

### 10.2 Alert qoidalari

```python
class AlertRule:
    metric: Enum["cpu", "ram", "disk", "load", "service_down", "ssh_unreachable"]
    threshold: float
    duration_minutes: int      # N daqiqa davomida threshold oshsa
    severity: Enum["info", "warning", "critical"]
    notification_channels: list[Enum["telegram", "email", "webhook"]]
```

### 10.3 Analytics dashboard ko'rsatkichlari

**Foydalanish statistikasi:**
- Jami vazifalar (kun/hafta/oy)
- Muvaffaqiyat vs xato nisbati
- Eng ko'p ishlatiladigan buyruqlar top-10
- O'rtacha vazifa davomiyligi

**Server statistikasi:**
- Uptime foizi (30 kun)
- CPU/RAM/Disk trend grafigi
- Eng ko'p muammo bo'lgan serverlar
- Incident tarixi

**AI foydalanish:**
- Har provider bo'yicha so'rovlar soni
- Token sarfi (narx hisoblash)
- Eng ko'p ishlatiladigan model
- Oylik xarajat dinamikasi

**Foydalanuvchi faolligi:**
- Aktiv foydalanuvchilar (DAU/WAU/MAU)
- Bot vs Web UI nisbati
- Peak foydalanish vaqtlari

---

## 11. Xavfsizlik

### 11.1 Buyruq filtri

```python
BLOCKED_COMMANDS = [
    r"rm\s+-rf\s+/(?!\w)",    # rm -rf / (root delete)
    r"mkfs\.",                  # disk format
    r"dd\s+if=.*of=/dev/[sh]d", # disk overwrite
    r">\s*/dev/[sh]d[a-z]",    # disk write
    r"chmod\s+777\s+/",        # global permissions
    r":(){ :|:& };:",           # fork bomb
    r"curl.*\|\s*bash",         # pipe to bash (suspicious)
    r"wget.*\|\s*sh",
]

HIGH_RISK_PATTERNS = [
    r"systemctl\s+(stop|disable)\s+(ssh|sshd)",  # SSH disable
    r"iptables\s+-F",           # firewall flush
    r"ufw\s+disable",
    r"passwd\s+root",
    r"userdel",
]
```

### 11.2 Rate limiting

| Endpoint | Limit |
|----------|-------|
| POST /api/tasks/submit | 10/daqiqa per user |
| POST /api/auth/* | 5/daqiqa per IP |
| GET /api/* | 100/daqiqa per user |
| WebSocket connections | 5 simultaneous per user |

### 11.3 Audit log

Barcha amallar audit_logs jadvalida:
- Foydalanuvchi kim, qachon, qayerdan (IP)
- Qanday amal bajarildi
- Muvaffaqiyatli/muvaffaqiyatsiz
- SSH buyruqlar to'liq yoziladi

---

## 12. Ma'lumotlar bazasi sxemasi

```sql
-- Foydalanuvchilar
users (id, telegram_id, username, first_name, last_name, photo_url,
       role, is_active, created_at, last_seen_at, settings JSONB)

-- Secrets (barcha shifrlangan ma'lumotlar uchun universal jadval)
secrets (id, user_id, secret_type, name, label, encrypted_data BYTEA,
         iv BYTEA, salt BYTEA, metadata JSONB, created_at, last_used_at)

-- Serverlar
servers (id, user_id, name, description, host, port, ssh_user,
         ssh_credential_id, tags TEXT[], environment, os_type,
         monitoring_enabled, monitoring_interval_minutes,
         last_check_at, last_check_status, metadata JSONB, created_at)

-- Vazifalar
tasks (id, user_id, server_id, input_text, task_type, status,
       source [web/telegram/api], risk_level, summary,
       ai_provider, ai_model, token_cost_usd,
       created_at, started_at, completed_at, duration_ms)

-- Vazifa qadamlari (timeline)
task_steps (id, task_id, step_order, phase, command, output TEXT,
            status, explanation, started_at, duration_ms)

-- Audit log
audit_logs (id, user_id, action_type, resource_type, resource_id,
            ip_address, user_agent, details JSONB, created_at)

-- Server metrikalari (time-series)
server_metrics (id, server_id, collected_at, cpu_percent, ram_percent,
                disk_percent, load_1, load_5, load_15, failed_services TEXT[],
                raw JSONB)

-- Alert qoidalari
alert_rules (id, user_id, server_id, metric, threshold, duration_minutes,
             severity, channels TEXT[], is_active, created_at)

-- Bildirishnomalar
notifications (id, user_id, type, title, message, is_read,
               related_task_id, related_server_id, created_at)

-- Sessions (refresh tokenlar)
user_sessions (id, user_id, refresh_token_hash, ip_address,
               user_agent, expires_at, created_at, revoked_at)
```

---

## 13. API endpointlari

```
AUTH
  POST   /api/auth/telegram-login     — Telegram widget login
  POST   /api/auth/refresh            — Token yangilash
  POST   /api/auth/logout             — Chiqish

USERS
  GET    /api/users/me                — Joriy foydalanuvchi
  PATCH  /api/users/me                — Profil yangilash
  GET    /api/users                   — Ro'yxat (admin)
  PATCH  /api/users/{id}/role         — Rol o'zgartirish (admin)
  DELETE /api/users/{id}              — O'chirish (owner)

SERVERS
  GET    /api/servers                 — Ro'yxat
  POST   /api/servers                 — Qo'shish
  GET    /api/servers/{id}            — Tafsilot + metrics
  PATCH  /api/servers/{id}            — Yangilash
  DELETE /api/servers/{id}            — O'chirish
  POST   /api/servers/{id}/test       — SSH ulanishni tekshirish
  GET    /api/servers/{id}/metrics    — Metrikalar tarixi

CREDENTIALS
  GET    /api/credentials/ssh         — SSH kalitlar ro'yxati
  POST   /api/credentials/ssh         — Yangi kalit qo'shish
  DELETE /api/credentials/ssh/{id}    — O'chirish
  GET    /api/credentials/tokens      — AI tokenlar ro'yxati
  POST   /api/credentials/tokens      — Yangi token qo'shish
  PATCH  /api/credentials/tokens/{id} — Yangilash
  DELETE /api/credentials/tokens/{id} — O'chirish

TASKS
  GET    /api/tasks                   — Tarixi (filter, pagination)
  POST   /api/tasks/submit            — Yangi vazifa
  GET    /api/tasks/{id}              — Tafsilot + steps + logs
  POST   /api/tasks/{id}/cancel       — Bekor qilish
  POST   /api/tasks/{id}/confirm      — Xavfli amal tasdiqlash
  WS     /ws/tasks/{id}               — Real-time stream

ANALYTICS
  GET    /api/analytics/overview      — Umumiy ko'rsatkichlar
  GET    /api/analytics/tasks         — Vazifa statistikasi
  GET    /api/analytics/servers       — Server statistikasi
  GET    /api/analytics/ai-usage      — AI foydalanish + xarajat
  GET    /api/analytics/activity      — Faollik heatmap

ALERTS
  GET    /api/alerts/rules            — Qoidalar
  POST   /api/alerts/rules            — Qoida qo'shish
  PATCH  /api/alerts/rules/{id}       — Yangilash
  DELETE /api/alerts/rules/{id}       — O'chirish
  GET    /api/notifications           — Bildirishnomalar
  POST   /api/notifications/read-all  — Barchasini o'qilgan deb belgilash

SYSTEM
  GET    /api/health                  — Tizim holati
  GET    /api/ai-providers            — Mavjud provayderlar ro'yxati
```

---

## 14. Xato boshqaruvi va ishonchlilik

### 14.1 Xato turlari va qayta urinish

| Xato | Strategiya |
|------|------------|
| SSH ulanish xatosi | 3x retry, exponential backoff (2s, 4s, 8s) |
| SSH timeout | 30s command timeout, 10s connect timeout |
| LLM API xatosi | Fallback next provider → next model |
| LLM JSON parse xatosi | 2x retry with stricter prompt |
| DB ulanish xatosi | Connection pool (min=2, max=20), retry |
| Celery worker crash | Task auto-retry (max 3), DLQ |

### 14.2 Graceful degradation

- LLM ishlamasa → rule-based diagnostika (regex patterns)
- SSH ishlamasa → server "offline" belgilanadi, alert yuboriladi
- Redis ishlamasa → vazifa sinxron bajariladi (slow mode)

### 14.3 Health check

```json
GET /api/health →
{
  "status": "healthy",
  "components": {
    "database": "ok",
    "redis": "ok",
    "celery_workers": 3,
    "ssh_test": "ok"
  },
  "version": "2.0.0",
  "uptime_seconds": 86400
}
```

---

## 15. Deployment

### 15.1 Environment o'zgaruvchilari

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/devops_agent
DATABASE_POOL_MIN=2
DATABASE_POOL_MAX=20

# Redis
REDIS_URL=redis://redis:6379/0

# Security
MASTER_ENCRYPTION_KEY=<32-byte-hex>    # openssl rand -hex 32
JWT_SECRET=<64-byte-hex>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# Telegram
TELEGRAM_BOT_TOKEN=<token>
TELEGRAM_BOT_USERNAME=<username>
TELEGRAM_WEBHOOK_SECRET=<random>

# App
APP_ENV=production                      # development | staging | production
APP_URL=https://devops.example.com
ALLOWED_ORIGINS=https://devops.example.com

# Optional: Default AI provider (fallback if user has no token)
DEFAULT_AI_PROVIDER=openai
DEFAULT_AI_API_KEY=<key>

# Agent settings
AGENT_MAX_ITERATIONS=10
AGENT_COMMAND_TIMEOUT=30
AGENT_MAX_OUTPUT_CHARS=8000
```

### 15.2 Ishga tushirish

```bash
# 1. Konfiguratsiya
cp .env.example .env
# .env ni tahrirlash

# 2. Ishga tushirish (barcha servislar)
docker compose up -d --build

# 3. Telegram bot bilan
docker compose --profile telegram up -d --build

# 4. Migratsiya (avtomatik api containerda)
# yoki qo'lda:
docker compose exec api alembic upgrade head
```

---

## 16. Loyiha tuzilmasi

```
devops-agent/
├── docker-compose.yml
├── docker-compose.override.yml     # dev sozlamalari
├── .env.example
├── INSTALL.md
├── API.md
├── USAGE.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── main.py                 # FastAPI app
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── dependencies.py         # DI: current_user, db session
│   │   │
│   │   ├── models/                 # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── server.py
│   │   │   ├── secret.py
│   │   │   ├── task.py
│   │   │   └── ...
│   │   │
│   │   ├── schemas/                # Pydantic schemas
│   │   ├── routers/                # FastAPI routers
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── servers.py
│   │   │   ├── credentials.py
│   │   │   ├── tasks.py
│   │   │   ├── analytics.py
│   │   │   ├── alerts.py
│   │   │   └── websocket.py
│   │   │
│   │   ├── services/
│   │   │   ├── auth_service.py
│   │   │   ├── encryption_service.py
│   │   │   ├── ssh_service.py
│   │   │   └── notification_service.py
│   │   │
│   │   ├── agent/
│   │   │   ├── agent.py            # Main DevOpsAgent class
│   │   │   ├── llm_router.py       # Multi-provider LLM router
│   │   │   ├── intent_parser.py
│   │   │   ├── plan_generator.py
│   │   │   ├── safety_filter.py
│   │   │   ├── result_analyzer.py
│   │   │   ├── deploy_handler.py
│   │   │   └── providers/
│   │   │       ├── openai_provider.py
│   │   │       ├── anthropic_provider.py
│   │   │       ├── google_provider.py
│   │   │       └── base_provider.py
│   │   │
│   │   └── worker/
│   │       ├── celery_app.py
│   │       └── tasks.py
│
├── bot/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── handlers/
│       │   ├── start.py
│       │   ├── tasks.py
│       │   ├── servers.py
│       │   └── settings.py
│       ├── keyboards/
│       └── middlewares/
│
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── pages/
        ├── components/
        ├── hooks/
        ├── stores/               # Zustand
        ├── api/                  # API client (axios + react-query)
        └── utils/
```

---

## 17. Texnologiyalar to'plami

| Qatlam | Texnologiya |
|--------|-------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| DB | PostgreSQL 16, Alembic migrations |
| Cache/Queue | Redis 7, Celery 5 |
| SSH | Paramiko 3.x |
| Crypto | cryptography (PyCA) — AES-256-GCM, PBKDF2 |
| Bot | aiogram 3.x |
| Frontend | React 18, TypeScript, Vite, TailwindCSS, Zustand, React Query, xterm.js |
| Charts | Recharts yoki ApexCharts |
| Containerization | Docker, Docker Compose v2 |
| Web server | nginx 1.25 (reverse proxy + static) |
| Auth | JWT (python-jose), Telegram Login Widget |

---

*Oxirgi yangilanish: 2026. Barcha talablar ushbu TZ asosida amalga oshirilishi kerak.*
