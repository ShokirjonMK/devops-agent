:::writing{variant=“standard” id=“73925”}

**Versiya:** 2.0.1 (2026-03-26). O‘zgarishlar: [CHANGELOG.md](CHANGELOG.md).

📘 TEXNIK TOPSHIRIQ (REVISED)

Loyiha: Avtonom DevOps / SysAdmin / NetAdmin AI Agent (Web + Telegram)

⸻

1. Loyiha maqsadi

Mazkur tizimning asosiy maqsadi — DevOps, SysAdmin va NetAdmin vazifalarini to‘liq avtomatlashtiruvchi AI agent yaratish.

Tizim quyidagilarni bajarishi kerak:
	•	Server (Linux) boshqaruvi
	•	Tarmoq (network) diagnostikasi va sozlash
	•	Deploy, monitoring va troubleshooting
	•	Xatoliklarni mustaqil aniqlash va tuzatish
	•	Infratuzilmani chat orqali boshqarish

👉 Yakuniy maqsad:

“Birgina chat orqali butun infratuzilmani boshqarish”

⸻

2. Scope (qamrov)

2.1 DevOps
	•	CI/CD (deploy, rollback)
	•	Docker / Docker Compose
	•	Nginx / Apache
	•	Database (MySQL/PostgreSQL)
	•	Redis / Queue

2.2 SysAdmin
	•	Service management (systemctl)
	•	Disk, RAM monitoring
	•	Log tahlili (journalctl, logs)
	•	Package management (apt, yum)
	•	User & permission management

2.3 NetAdmin
	•	Port va socket monitoring
	•	Firewall (ufw, iptables)
	•	DNS, routing
	•	Network connectivity (ping, traceroute)
	•	Bandwidth monitoring

⸻

3. Asosiy funksional talablar

⸻

3.1 Natural Language Command Processing

Foydalanuvchi quyidagicha yozadi:

sarbon serverida docker ishlamayapti
test serverda port 80 yopiq ochib ber
prod serverda disk to‘lib qolgan tozalab ber

Tizim:
	•	serverni aniqlaydi
	•	muammoni klassifikatsiya qiladi
	•	yechim ishlab chiqadi

⸻

3.2 Server Resolution Engine

Talab:
	•	server nom orqali aniqlanishi kerak
	•	alias qo‘llab-quvvatlanadi

Misol:

{
  "sarbon": { "host": "1.2.3.4" },
  "prod": { "host": "5.6.7.8" }
}


⸻

3.3 Multi-layer AI Agent

Agent quyidagi modullardan iborat:

1. Intent Parser
	•	NLP orqali maqsadni aniqlaydi

2. Task Planner
	•	bosqichlarga ajratadi

3. Diagnosis Engine
	•	server holatini tekshiradi

4. Decision Engine
	•	muammo sababini topadi

5. Execution Engine
	•	komandalarni bajaradi

6. Verification Engine
	•	natijani tekshiradi

⸻

3.4 Diagnose (universal)

Tizim avtomatik quyidagilarni bajaradi:

systemctl status <service>
docker ps -a
ss -tulnp
df -h
free -m
uptime

Network uchun:

ping
traceroute
curl
iptables -L
ufw status


⸻

3.5 Decision-making (AI reasoning)

AI:
	•	loglarni analiz qiladi
	•	root cause topadi
	•	optimal fixni tanlaydi

⸻

3.6 Execution Engine
	•	SSH orqali ulanadi
	•	komandalarni step-by-step bajaradi
	•	har bir step log qilinadi

⸻

3.7 Self-healing loop

Diagnose → Decide → Execute → Verify → Repeat

Agar muammo hal bo‘lmasa:
	•	qayta analiz qiladi
	•	alternativ yechim sinaydi

⸻

4. Telegram Bot talablar

4.1 Funksiyalar
	•	Buyruq qabul qilish
	•	Progress ko‘rsatish
	•	Real-time update

4.2 Response format

🔍 Server: sarbon
🧠 Diagnostika...

📊 Natija:
docker inactive

🛠 Tuzatish:
docker restart qilinmoqda...

✅ Bajarildi

📄 Hisobot:
- docker restart qilindi
- sabab: service crash


⸻

5. Web Interface talablar

5.1 Dashboard
	•	Active tasks
	•	Server status

5.2 Timeline view
	•	Step-by-step history

5.3 Server management
	•	CRUD serverlar

⸻

6. Database dizayn

servers

id
name
host
user
auth_type
key_path

tasks

id
server_id
command
status
created_at

steps

id
task_id
command
output
status
timestamp


⸻

7. Logging va observability
	•	Har bir command log qilinadi
	•	stdout/stderr saqlanadi
	•	Timeline UI da ko‘rinadi

⸻

8. Xavfsizlik (CRITICAL)

8.1 Cheklovlar
	•	dangerous command filtering
	•	sudo access nazorati

8.2 Audit
	•	kim nima yubordi
	•	qachon bajarildi

8.3 Isolation
	•	SSH key-based access
	•	containerized execution (optional)

⸻

9. Texnologiyalar

Backend
	•	FastAPI

Queue
	•	Redis + Celery

AI
	•	Claude API / Local LLM (Gemma)

SSH
	•	Paramiko

Frontend
	•	React

DB
	•	PostgreSQL

⸻

10. Deployment
	•	Docker-based
	•	Single VPS / multi-node
	•	Horizontal scaling (workers)

⸻

11. Real use-case (example)

Input:

sarbon serverda nginx ishlamayapti

Flow:
	1.	server → sarbon
	2.	SSH connect
	3.	systemctl status nginx
	4.	inactive → sabab topiladi
	5.	restart
	6.	verify
	7.	success

⸻

12. Qo‘shimcha imkoniyatlar
	•	Auto deploy (CI/CD)
	•	Auto scaling
	•	Alerting (Telegram notify)
	•	Predictive monitoring (AI)

⸻

13. Acceptance criteria

✔ Chat orqali boshqariladi
✔ DevOps vazifalarni bajaradi
✔ SysAdmin ishlarini qiladi
✔ Network muammolarni hal qiladi
✔ SSH orqali ishlaydi
✔ Muammoni o‘zi yechadi
✔ Timeline saqlaydi

⸻

14. Yakuniy xulosa

Mazkur tizim:
	•	DevOps + SysAdmin + NetAdmin rollarni birlashtiradi
	•	Infratuzilmani avtomatlashtiradi
	•	Chat-based boshqaruvni ta’minlaydi
	•	AI orqali self-healing tizim yaratadi

👉 Bu — oddiy bot emas, balki:
AI-driven Infrastructure Operator

⸻

15. Infratuzilma va v2 qatlam (2026-03 yangilanishi)

- `docker-compose.yml`: umumiy `x-backend-env`, Redis parol bilan, `postgres_data` / `redis_data` / `ssh_keys` volumelari, API `GET /api/health` (DB, Redis, Celery worker soni), worker `api` healthy bo‘lgach ishga tushadi.
- Shifrlash: `MASTER_ENCRYPTION_KEY` (64 hex) yoki `ENCRYPTION_MASTER_KEY_B64` (32 bayt base64); yangi yozuvlar 32 bayt salt + 600k PBKDF2, eski 16 bayt + 390k o‘qiladi.
- Bot: `POST /api/auth/bot-login` + `API_INTERNAL_SECRET`; muhitda `API_BASE_URL` yoki `API_URL`.
- Migratsiya **005–006**: `ai_token_configs`, `server_metrics`, `alert_rules`, `admin_settings`, `notifications`, `platform_audit_logs`; `users.role`, `servers` monitoring maydonlari; tizim `users` qatori (`telegram_id = -1`) default AI kalitlari uchun.
- API: `/api/ai-tokens`, `/api/admin/*`, RBAC (`owner/admin/operator/viewer`), WebSocket `?token=` ixtiyoriy JWT.
- Celery beat: metrikalar, alertlar, retention, oy boshida AI usage reset.
- Hujjatlar: `docs/SSH-SETUP.md`, `docs/AI-PROVIDERS.md`.
- Batafsil: [CHANGELOG.md](CHANGELOG.md).
