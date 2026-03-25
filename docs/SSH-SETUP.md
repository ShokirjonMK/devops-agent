# SSH ulanish usullari

## 1. ED25519 (tavsiya)

### Kalit yaratish

```bash
ssh-keygen -t ed25519 -C "devops-agent-$(date +%Y%m%d)" -f ~/.ssh/devops_agent_ed25519
```

### Serverga yuklash

```bash
ssh-copy-id -i ~/.ssh/devops_agent_ed25519.pub user@server-ip
```

Yoki qo‘lda:

```bash
cat ~/.ssh/devops_agent_ed25519.pub | ssh user@server "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### Tizimga

- **Nom:** masalan `prod-web`
- **Username:** `ubuntu`, `root`, `deploy` …
- **Kalit yo‘li:** konteynerda `/ssh-keys/...` yoki `SSH_PRIVATE_KEY_B64`

---

## 2. RSA (4096)

```bash
ssh-keygen -t rsa -b 4096 -C "devops-agent" -f ~/.ssh/devops_agent_rsa
```

Keyin `ssh-copy-id` yoki `authorized_keys` ga `.pub` qo‘shish.

---

## 3. Parol bilan

Serverda `PasswordAuthentication yes` bo‘lishi kerak. Tizimda `auth_type=password` va muhitda `SSH_PASSWORD` (yoki kelajakdagi vault paroli).

---

## 4. Passphrase bilan kalit

`ssh-keygen` paytida passphrase bering. Agent hozir passphrase ni vault orqali qo‘llab-quvvatlashi kerak — kalitni shifrlangan saqlang.

---

## Xatolar

| Xato | Yechim |
|------|--------|
| Permission denied (publickey) | `chmod 700 ~/.ssh` va `chmod 600 ~/.ssh/authorized_keys` |
| Connection refused | port 22 ochiqmi, firewall |
| Host key verification failed | productionda `known_hosts` siyosati |
