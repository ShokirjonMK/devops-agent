:::writing{variant=“standard” id=“48291”}

📘 Texnik Topshiriq (Technical Specification)

Loyiha: Avtonom DevOps AI Agent (Web + Telegram)

⸻

1. Umumiy tavsif

Mazkur tizim — bu AI asosida ishlovchi avtonom DevOps agent bo‘lib, foydalanuvchi tomonidan berilgan tabiiy til buyruqlarini (Telegram yoki Web orqali) qabul qilib:
	•	serverni nomi orqali aniqlaydi
	•	SSH orqali ulanadi
	•	muammoni diagnostika qiladi
	•	yechim ishlab chiqadi
	•	avtomatik bajaradi
	•	barcha jarayonni log va timeline ko‘rinishida saqlaydi

Tizim minimal inson aralashuvi bilan muammolarni mustaqil hal qilishga mo‘ljallangan.

⸻

2. Loyiha maqsadi
	•	DevOps jarayonlarini avtomatlashtirish
	•	Server monitoring va troubleshootingni soddalashtirish
	•	Telegram orqali boshqariladigan infra tizim yaratish
	•	Har bir operatsiyani audit va history bilan saqlash

⸻

3. Asosiy funksional talablar

3.1 Buyruq qabul qilish

Tizim quyidagi interfeyslar orqali buyruq qabul qiladi:

Telegram Bot
	•	Matnli buyruqlar
	•	Real-time javob
	•	Status update (progress)

Web Interface
	•	Input panel
	•	Task history
	•	Timeline visualization

⸻

3.2 Serverni aniqlash (Server Resolution)

Foydalanuvchi buyruq beradi:

sarbon serverida nginx ishlamayapti

Tizim:
	•	“sarbon” nomini aniqlaydi
	•	server registry orqali mos serverni topadi

Server registry format:

{
  "sarbon": {
    "host": "1.2.3.4",
    "user": "root",
    "auth_type": "ssh_key",
    "key_path": "~/.ssh/id_rsa"
  }
}


⸻

3.3 AI orqali muammoni aniqlash

Tizim quyidagi bosqichlarni bajaradi:
	1.	Intent parsing
	2.	Muammo klassifikatsiyasi
	3.	Diagnostika komandalarini generatsiya qilish
	4.	Natijalarni analiz qilish

⸻

3.4 Diagnostika (Diagnosis Engine)

Tizim avtomatik ravishda quyidagi komandalarni ishlatadi:

systemctl status <service>
docker ps
netstat -tulnp
df -h
free -m


⸻

3.5 Qaror qabul qilish (Decision Engine)

AI model asosida:
	•	muammo sababini aniqlaydi
	•	optimal yechimni tanlaydi
	•	komandalar ketma-ketligini ishlab chiqadi

⸻

3.6 Bajarish (Execution Engine)
	•	SSH orqali ulanadi
	•	komandalarni ketma-ket bajaradi
	•	har bir natijani qayd qiladi

⸻

3.7 Verifikatsiya (Verification)
	•	Muammo hal bo‘lganini tekshiradi
	•	Agar hal bo‘lmasa → qayta diagnose loop

⸻

3.8 Feedback (User Response)

Telegram/Web orqali:
	•	real-time progress
	•	bajarilgan komandalar
	•	sabab va izohlar

⸻

4. Non-functional talablar

4.1 Performance
	•	Response time: < 2s (initial response)
	•	Execution: serverga bog‘liq

4.2 Reliability
	•	Retry mechanism
	•	Failure handling

4.3 Security
	•	SSH key-based authentication
	•	Command whitelist (optional)
	•	Audit logging

4.4 Scalability
	•	Multi-server support
	•	Queue-based processing

⸻

5. Arxitektura

Client (Telegram/Web)
↓
API (FastAPI)
↓
AI Agent (Planner + Analyzer)
↓
Task Queue (Redis)
↓
Worker (Executor)
↓
SSH Layer
↓
Server
↓
Logs → Database
↓
Frontend (Timeline UI)


⸻

6. Texnologiyalar

Backend
	•	Python (FastAPI)
	•	Celery / RQ (queue)
	•	Redis

AI
	•	Claude API / OpenAI
	•	yoki local model (Gemma / LLaMA)

Frontend
	•	React.js
	•	Tailwind CSS

Database
	•	PostgreSQL

DevOps
	•	Docker
	•	Nginx

⸻

7. Ma’lumotlar bazasi (Database Schema)

Table: servers

id
name
host
user
auth_type
key_path
created_at


⸻

Table: tasks

id
user_id
server_id
command_text
status (pending/running/done/error)
created_at


⸻

Table: steps

id
task_id
step_order
command
output
status
created_at


⸻

Table: logs

id
task_id
message
level
timestamp


⸻

8. Timeline tizimi

Har bir task uchun:
	•	step-by-step log
	•	vaqt bilan
	•	komandalar + output

Example:

[10:01] Server aniqlandi: sarbon
[10:01] SSH ulanish: OK
[10:02] nginx status: inactive
[10:02] restart nginx
[10:03] status: active


⸻

9. Telegram Bot talablar
	•	Real-time javob
	•	Progress update
	•	Xatolik haqida ogohlantirish

Buyruq formati:

<server> serverida <muammo>


⸻

10. Web Interface talablar
	•	Dashboard
	•	Task list
	•	Timeline view
	•	Server management

⸻

11. AI Agent logikasi

Loop:

1. Parse
2. Detect server
3. Diagnose
4. Decide
5. Execute
6. Verify
7. If not fixed → repeat


⸻

12. Xavfsizlik
	•	Root access cheklash (optional)
	•	Dangerous command filtering:
	•	rm -rf /
	•	shutdown
	•	Timeout limit

⸻

13. Logging va Audit
	•	Har bir command log qilinadi
	•	Kim yuborgan → saqlanadi
	•	Nima bajarilgan → yoziladi

⸻

14. Deployment talablari
	•	Docker-based deployment
	•	Single VPS support
	•	Multi-node support (optional)

⸻

15. Qo‘shimcha imkoniyatlar (Future scope)
	•	Voice command (Telegram)
	•	Multi-language support
	•	AI learning from history
	•	Auto-scaling infra management

⸻

16. Acceptance Criteria

Tizim quyidagilarni bajarsa tayyor hisoblanadi:

✔ Telegram orqali buyruq qabul qiladi
✔ Serverni nom orqali aniqlaydi
✔ SSH orqali ulanadi
✔ Muammoni o‘zi aniqlaydi
✔ Yechimni mustaqil bajaradi
✔ Natijani userga qaytaradi
✔ Timeline saqlaydi
✔ Web interfeysda ko‘rsatadi

⸻

17. Xulosa

Mazkur tizim DevOps jarayonlarini avtomatlashtirish orqali:
	•	inson xatolarini kamaytiradi
	•	vaqtni tejaydi
	•	server boshqaruvini soddalashtiradi

va kelajakda AI-driven infrastructure management asosini yaratadi.