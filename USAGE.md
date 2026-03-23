# Foydalanish va test ssenariylari

## 1. Server (alias)

```bash
curl -s -X POST http://localhost:8000/api/servers \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"sarbon\",\"host\":\"10.0.0.5\",\"user\":\"ubuntu\",\"auth_type\":\"ssh_key\",\"key_path\":\"/ssh-keys/id_rsa\"}"
```

## 2. Misollar (tabiiy til)

```
sarbon serverida nginx ishlamayapti
prod serverda disk to‘lib qolgan
test serverida docker ishlamayapti
```

Web Dashboard yoki:

```bash
curl -s -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d "{\"command_text\":\"sarbon serverida nginx ishlamayapti\"}"
```

## 3. Timeline maydonlari (API / UI)

Har bir `task_steps` elementi:

- `step_order`, `command`, `output`, `status`, `created_at`
- **`phase`**: `diagnose` | `execute` | `verify`
- **`explanation`**: nima uchun bu buyruq ishlatilgani (LLM)

## 4. Simulyatsiya: kutiladigan buyruqlar va mantiq

Quyidagi jadval **taxminiy** SSH qadamlar; aniq ketma-ketlik LLM va server holatiga bog‘liq.

| Ssenari | Diagnostika (misol) | Tahlil / qaror | Tuzatish yoki verify (misol) |
|---------|---------------------|----------------|------------------------------|
| **nginx down** | `systemctl status nginx`, `journalctl -u nginx -n 50` | inactive / config xato | `nginx -t`, `systemctl restart nginx`, verify: `systemctl is-active nginx` |
| **docker stopped** | `systemctl status docker`, `docker ps` | daemon o‘chiq | `systemctl start docker`, verify: `docker ps` |
| **port closed** | `ss -tulnp`, `curl -sI localhost:80` | servis eshitmayapti / firewall | `ufw status`, servisni yoqish yoki `ufw allow` (filtrdan o‘tsa) |
| **disk full** | `df -h`, `du -xh /var 2>/dev/null \| head` | partition 100% | Agent xavfsiz **tozalovchi** buyruqlarni cheklangan holda taklif qiladi; `rm -rf /` **bloklanadi** |
| **SSH failure** | — | ulanish yoki kalit | vazifa `error`, `summary` + audit; ulanish **retry** |

**Fix** qatlami: agent bir xil buyruqlar ketma-ket 2 marta takrorlansa, sikl **avtomatik to‘xtaydi** (cheksiz loop oldini olish).

## 5. Telegram

Bot yangi qadam qo‘shilganda progress xabarini yangilaydi (oxirgi 4 qadam + holat).

## 6. Namuna API chiqishi (qisqa)

```json
{
  "id": 1,
  "status": "running",
  "steps": [
    {
      "step_order": 1,
      "phase": "diagnose",
      "command": "systemctl status nginx",
      "explanation": "Nginx unit holatini tekshirish.",
      "status": "success",
      "output": "..."
    }
  ]
}
```

To‘liq REST: [API.md](API.md).
