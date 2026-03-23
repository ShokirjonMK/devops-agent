# CURSOR SUPER PROMPT — DevOps Agent v2

## VAZIFA
Sen tajribali senior full-stack va DevOps muhandisisan. Quyida berilgan TZ.md asosida **production-ready** DevOps Agent platformasini **to'liq, ishlaydigan holda** yozasan. Hech narsa "placeholder" yoki "TODO" bo'lmasligi kerak — har bir modul ishga tayyor bo'lishi shart.

---

## QOIDALAR (BUZSIZ BAJARILADI)

1. **Har bir fayl to'liq yoziladi** — snippet emas, to'liq kod
2. **Type hint** — Python da barcha funksiyalarda, TypeScript da strict mode
3. **Error handling** — har bir `async` blokda `try/except`, har bir API callda fallback
4. **Encryption** — barcha secret ma'lumotlar AES-256-GCM bilan, HECH QACHON ochiq matn DB ga
5. **Tests** — har bir service uchun kamida unit test skeleti (pytest)
6. **Logging** — structlog, har muhim qadamda log yoziladi
7. **No hardcoded secrets** — faqat env o'zgaruvchilardan
8. **Docker** — barcha servislar docker-compose da, health check bilan
9. **Migrations** — Alembic, har jadval uchun to'liq migration
10. **Real-time** — WebSocket + Redis pub/sub to'liq ishlashi kerak

---

## BOSQICHLAR (HAR BIRINI TARTIB BILAN BAJARA)

### BOSQICH 1 — Loyiha skeleti va Docker muhiti

```
Yarating:
├── docker-compose.yml          (postgres, redis, api, worker, beat, web, bot)
├── docker-compose.override.yml (dev: volume mounts, hot reload)
├── .env.example                (barcha o'zgaruvchilar izoh bilan)
├── Makefile                    (up, down, logs, migrate, test, shell)
├── backend/
│   ├── Dockerfile              (multi-stage: builder + runtime)
│   ├── requirements.txt        (pinned versions)
│   └── entrypoint.sh           (migrate then start)
├── bot/
│   ├── Dockerfile
│   └── requirements.txt
└── frontend/
    ├── Dockerfile              (build + nginx)
    └── nginx.conf              (gzip, /api proxy, SPA fallback)
```

**Muhim:** docker-compose da barcha servislar uchun:
- `healthcheck` qo'shilsin
- `depends_on: condition: service_healthy`
- `restart: unless-stopped`
- Tarmoq: internal `app-network`

---

### BOSQICH 2 — Database sxemasi va migrations

`backend/alembic/versions/` da quyidagi migrationlarni yarat:

**001_initial_schema.py** — barcha jadvallar:
```sql
users, secrets, servers, tasks, task_steps, 
audit_logs, server_metrics, alert_rules, 
notifications, user_sessions
```

Har jadval uchun:
- `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- `created_at TIMESTAMPTZ DEFAULT now()`
- Kerakli indexlar (user_id, created_at, status bo'yicha)
- Foreign key constraints + CASCADE qoidalari

---

### BOSQICH 3 — Encryption service (ENG MUHIM)

`backend/app/services/encryption_service.py`:

```python
class EncryptionService:
    """
    AES-256-GCM asosida end-to-end encryption.
    
    Metodlar:
    - encrypt(plaintext: str, context: str) -> EncryptedData
    - decrypt(data: EncryptedData, context: str) -> str  
    - derive_key(master_key: bytes, salt: bytes) -> bytes (PBKDF2/HKDF)
    
    EncryptedData: {ciphertext: bytes, iv: bytes, salt: bytes, tag: bytes}
    
    MUHIM: 
    - Har encrypt chaqiruvida yangi random IV va salt
    - Context (user_id + secret_type) AAD sifatida ishlatiladi
    - Master key env dan olinadi, hech qachon loglanmaydi
    """
```

**Test yoz:** encrypt → decrypt aylanmasi, context mismatch xatosi

---

### BOSQICH 4 — FastAPI asosi va Auth

`backend/app/` da:

**config.py** — Pydantic Settings, barcha env o'zgaruvchilari

**database.py** — async SQLAlchemy engine, session factory, Base

**models/** — Har jadval uchun alohida fayl, to'liq SQLAlchemy 2.0 modeli

**schemas/** — Pydantic v2 sxemalar (Create, Update, Response, DB)

**routers/auth.py** — Telegram login verifikatsiya:
```python
async def verify_telegram_login(data: TelegramLoginData) -> bool:
    """
    HMAC-SHA256 bilan hash tekshirish.
    hash = HMAC-SHA256(bot_token_sha256, sorted_data_string)
    data_check_string = sorted key=value pairs, \n bilan
    auth_date 1 soatdan eski bo'lsa rad etish
    """
```

**dependencies.py** — `get_current_user`, `require_role(role)`, `get_db`

---

### BOSQICH 5 — Barcha REST API routerlar

Har endpoint uchun:
1. **Pydantic validation** (input)
2. **Permission check** (`require_role`)
3. **Business logic** (service layer orqali)
4. **Structured response** (Pydantic output schema)
5. **Audit log yozish**
6. **HTTP status codes to'g'ri** (201 created, 404 not found, 403 forbidden)

Barcha routerlarni yoz:
- `auth.py`, `users.py`, `servers.py`
- `credentials.py` (ssh + tokens, HECH QACHON decrypted value qaytarma — faqat metadata)
- `tasks.py`, `websocket.py`
- `analytics.py`, `alerts.py`

---

### BOSQICH 6 — SSH Service

`backend/app/services/ssh_service.py`:

```python
class SSHService:
    async def connect(self, server: Server, credential: DecryptedCredential) -> SSHConnection:
        """
        Paramiko bilan ulanish.
        - connect_timeout=10
        - 3x retry, exponential backoff
        - known_hosts: RejectPolicy (production) yoki AutoAddPolicy (dev)
        - key_type: RSA, ED25519, ECDSA barchasini qo'llab-quvvatla
        """
    
    async def execute(self, conn: SSHConnection, command: str, timeout: int = 30) -> CommandResult:
        """
        - output streaming: stdout + stderr alohida
        - timeout enforcement
        - exit_code qaytarish
        - max output 8000 char (truncate with notice)
        """
    
    async def test_connection(self, server: Server, credential: DecryptedCredential) -> TestResult:
        """
        Ulanib 'echo OK' bajarib qaytaradi.
        Natija: {success, latency_ms, error_message}
        """
```

---

### BOSQICH 7 — LLM Router (multi-provider)

`backend/app/agent/llm_router.py`:

```python
class LLMRouter:
    """
    Foydalanuvchining aktiv tokenlaridan eng mosini tanlaydi.
    
    Prioritet:
    1. task_type uchun preferred provider (config)
    2. budget_remaining > 0
    3. is_default=True
    4. Birinchi aktiv token
    
    Fallback:
    - RateLimitError → keyingi provider
    - APIError → keyingi provider  
    - AllProvidersFailed → rule-based fallback
    """
    
    async def complete(self, messages: list, user_id: UUID, 
                       task_type: TaskType, response_format: str = "json") -> LLMResponse:
        """JSON mode: strict JSON qaytarish"""
```

**Har provider uchun adapter yoz:**

```python
# base_provider.py
class BaseProvider(ABC):
    @abstractmethod
    async def complete(self, messages, model, **kwargs) -> str: ...
    
    @abstractmethod  
    async def count_tokens(self, text: str) -> int: ...

# openai_provider.py, anthropic_provider.py, google_provider.py,
# mistral_provider.py, groq_provider.py, deepseek_provider.py,
# openrouter_provider.py, custom_provider.py
```

---

### BOSQICH 8 — DevOps Agent (ASOSIY)

`backend/app/agent/agent.py` — `DevOpsAgent` klassi:

```python
class DevOpsAgent:
    async def run(self, task: Task, user: User) -> None:
        """
        To'liq agent sikli:
        
        1. Decrypt user SSH credentials
        2. SSH connect
        3. IntentParser: task_type, server, risk_level
        4. risk = high → confirmation_required → WAIT (task status = waiting_confirmation)
        5. PlanGenerator: qadamlar ro'yxati
        6. SafetyFilter: har buyruqni tekshir
        7. Loop (max 10):
           a. Execute command via SSH
           b. Stream output → Redis pub/sub
           c. ResultAnalyzer: resolved? needs_more? escalate?
           d. Update task_step in DB
        8. Final summary → task.summary
        9. Task status → done/error
        10. Send Telegram notification (if source=telegram)
        """
```

**SafetyFilter:**
```python
class SafetyFilter:
    BLOCKED = [...]   # yuqoridagi TZ ro'yxati
    HIGH_RISK = [...] # tasdiqlash kerak
    
    def check(self, command: str) -> SafetyResult:
        # {allowed: bool, requires_confirmation: bool, reason: str}
```

**Deploy handler alohida:**
```python
class DeployHandler:
    async def detect_project_type(self, ssh, path: str) -> DeployConfig:
        """docker-compose.yml, Dockerfile, package.json, requirements.txt — detect"""
    
    async def execute_deploy(self, ssh, config: DeployConfig) -> DeployResult:
        """pre → backup → pull → build → migrate → restart → health_check → rollback if failed"""
```

---

### BOSQICH 9 — Celery tasks

`backend/app/worker/tasks.py`:

```python
@celery_app.task(bind=True, max_retries=3, 
                  autoretry_for=(SSHException, ConnectionError),
                  retry_backoff=True)
async def run_agent_task(self, task_id: str) -> None:
    """
    - Task status → running
    - DevOpsAgent.run() chaqir
    - Exception → task status → error, log yoz
    - Har holda connection cleanup
    """

@celery_app.task
async def collect_server_metrics(server_id: str) -> None:
    """Monitoring: metrics yig'ish, alert qoidalarini tekshirish"""

@celery_app.task  
async def send_alert(alert_rule_id: str, metric_value: float) -> None:
    """Telegram/webhook orqali ogohlantirish yuborish"""
```

---

### BOSQICH 10 — WebSocket real-time

`backend/app/routers/websocket.py`:

```python
# Redis pub/sub → WebSocket stream
# Channel: f"task:{task_id}:output"
# 
# Connection manager: har user uchun max 5 simultaneous
# Heartbeat: 30s ping/pong
# Auth: token query param yoki cookie
# Reconnect: exponential backoff client tomonda
```

---

### BOSQICH 11 — Telegram Bot (aiogram 3.x)

`bot/app/` — to'liq bot:

**main.py** — webhook yoki polling (env bilan sozlanadi)

**middlewares/auth.py:**
```python
class AuthMiddleware(BaseMiddleware):
    """
    Har xabar uchun:
    1. telegram_id bo'yicha user toping
    2. is_active tekshiring
    3. Topilmasa → register (inactive)
    4. handler ga user ob'ektini uzating
    """
```

**handlers/tasks.py:**
- Natural language xabarni API ga yuborish
- `typing...` animatsiyasi task ishlayotganda
- Polling (3s) → xabarni **edit** qilish progress bilan
- Inline keyboard: [✅ Tasdiqlash] [❌ Bekor qilish]
- Uzun output → truncate + "To'liq ko'rish" link

**handlers/servers.py:**
- `/servers` → inline keyboard ro'yxati
- Server tanlash → holatni ko'rsatish

**keyboards/inline.py:**
- Barcha inline keyboard generatorlar

---

### BOSQICH 12 — Frontend (React + TypeScript)

**Tech stack:** React 18, TypeScript strict, Vite, TailwindCSS, Zustand, React Query v5, axios

**stores/auth.ts** — Zustand:
```typescript
interface AuthStore {
  user: User | null;
  accessToken: string | null;
  login: (telegramData: TelegramLoginData) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
}
```

**pages/Login.tsx:**
```typescript
// Telegram Login Widget integratsiya
// <script src="https://telegram.org/js/telegram-widget.js"
//   data-telegram-login={BOT_USERNAME}
//   data-size="large"
//   data-onauth="onTelegramAuth"
//   data-request-access="write">
// </script>
// onTelegramAuth → API → JWT → redirect /dashboard
```

**pages/Dashboard.tsx:**
- Server holat kartlari (online/offline/warning chip)
- Faol vazifalar (real-time yangilanadi)
- Tezkor vazifa yuborish (modal + textarea)
- Oxirgi 10 ta vazifa ro'yxati

**pages/Tasks/[id].tsx:**
- Terminal-uslub output (monospace font, dark bg)
- Timeline (har step: icon + buyruq + natija + vaqt)
- WebSocket ulanish + reconnect
- "Agent fikrlayapti..." animatsiya
- Confirmation modal (xavfli amallar uchun)

**pages/Credentials/SSH.tsx:**
- SSH kalitlar jadval
- "Kalit qo'shish" modal: name, username, private key paste (server ga yuboriladi, hech qachon local cache emas)
- Fingerprint ko'rsatish (ochiq)
- "Test" tugmasi

**pages/Credentials/Tokens.tsx:**
- Provider bo'yicha guruhlangan kartlar
- Har provider uchun: aktiv/nofaol, default belgilash, budget sozlash
- Token qo'shish: provider tanlash → base_url (optional) → token input (password field)
- Monthly usage grafigi

**pages/Analytics.tsx:**
- Umumiy KPI kartlar (jami vazifa, success rate, uptime %)
- Vazifa tarixi chart (Recharts LineChart)
- AI xarajatlar pie chart (provider bo'yicha)
- Server uptime bar chart
- Faollik heatmap (GitHub style)

**components/ServerCard.tsx:**
- Real-time status badge
- CPU/RAM/Disk mini progress bar
- "Vazifa yuborish" tugmasi

**hooks/useTaskStream.ts:**
```typescript
// WebSocket ulanish hook
// exponential backoff reconnect
// events: step_start, output_chunk, step_done, task_done, error
```

---

### BOSQICH 13 — Analytics service

`backend/app/services/analytics_service.py`:

```python
class AnalyticsService:
    async def get_overview(self, user_id: UUID, period_days: int = 30) -> OverviewStats
    async def get_task_stats(self, user_id: UUID, ...) -> TaskStats  
    async def get_server_stats(self, user_id: UUID, ...) -> ServerStats
    async def get_ai_usage(self, user_id: UUID, ...) -> AIUsageStats
    async def get_activity_heatmap(self, user_id: UUID) -> HeatmapData
```

---

### BOSQICH 14 — Monitoring (Celery beat)

`backend/app/worker/tasks.py` ga qo'shish:

```python
# Celery beat schedule:
# collect_all_metrics: har 5 daqiqada
# cleanup_old_metrics: har kuni (30 kundan eski o'chirish)
# check_alerts: har 2 daqiqada

async def collect_all_metrics() -> None:
    """monitoring_enabled=True barcha serverlar uchun parallel metrics yig'ish"""

async def check_alerts() -> None:
    """So'nggi metrikalarni alert qoidalari bilan solishtirib alert yuborish"""
```

---

### BOSQICH 15 — Tests

```
backend/tests/
├── conftest.py              (pytest fixtures: test db, mock SSH, mock LLM)
├── test_encryption.py       (encrypt/decrypt, context mismatch)
├── test_auth.py             (telegram hash verify, JWT)
├── test_ssh_service.py      (mock paramiko)
├── test_safety_filter.py    (blocked commands, high-risk patterns)
├── test_agent.py            (mock LLM + SSH, full flow)
├── test_api_servers.py      (CRUD endpoints)
├── test_api_tasks.py        (submit, status, cancel)
└── test_analytics.py
```

---

## FINAL TEKSHIRISH

Hammasi tayyor bo'lgandan so'ng quyidagilarni tekshir:

```bash
# 1. Build
docker compose build --no-cache

# 2. Ishga tushirish
docker compose up -d

# 3. Health check
curl http://localhost:8000/api/health
# → {"status": "healthy", "components": {...}}

# 4. Migration
docker compose exec api alembic upgrade head

# 5. Frontend
curl http://localhost
# → HTML qaytishi kerak

# 6. Tests
docker compose exec api pytest tests/ -v

# 7. Bot (optional)
docker compose --profile telegram up -d bot
```

---

## QABUL QILISH MEZONLARI

- [ ] `docker compose up -d` dan keyin hamma servis `healthy`
- [ ] Web UI ochiladi, Telegram login ishlaydi
- [ ] Server qo'shish, SSH test — ishlaydi
- [ ] AI token qo'shish, barcha provayderlar tanlanadi
- [ ] Vazifa yuborish → real-time output WebSocket orqali keladi
- [ ] Telegram botda `/start` → buyruq yuborish → progress ko'rinadi
- [ ] Analytics sahifasi ma'lumot ko'rsatadi
- [ ] Barcha secret ma'lumotlar DB da shifrlangan (base64/hex ko'rinishda)
- [ ] `pytest tests/ -v` — barcha testlar o'tadi
- [ ] `docker compose logs` da hech qanday unhandled exception yo'q

---

**ESLATMA:** Bitta buyruq bilan butun tizim ishga tushishi shart:
```bash
cp .env.example .env && docker compose up -d --build
```
