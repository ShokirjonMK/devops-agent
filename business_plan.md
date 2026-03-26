# DevOps Agent — To'liq Biznes Reja

---

## 1. DAROMAD MODELI

### 1.1 Subscription (asosiy daromad)

| Tarif | Narx | Nima beradi |
|-------|------|-------------|
| **Free** | $0 | 3 server, 50 task/oy, community AI, 1 foydalanuvchi |
| **Pro** | $15/oy | 20 server, cheksiz task, o'z AI kalitlari, monitoring |
| **Team** | $49/oy | Cheksiz server, 10 jamoa a'zosi, RBAC, audit, SLA 99.5% |
| **Enterprise** | $300–$2000/oy | On-premise, SSO, white-label, dedicated support |

### 1.2 Default AI ustama to'lovi

Foydalanuvchida o'z AI kaliti yo'q bo'lsa — admin tomonidan belgilangan default AI ishlatiladi. Har so'rov uchun:

```
Haqiqiy narx (OpenAI/Anthropic) + 40-60% ustama = foydalanuvchidan olinadi
Misol: GPT-4o-mini = $0.001 → foydalanuvchiga $0.0017 hisoblanadi
Oylik kredit tizimi: $5 / $20 / $50 paketlar oldindan sotib olinadi
```

Bu model SaaS da klassik "metered billing" — foydalangan sari to'lanadi.

### 1.3 Qo'shimcha daromad oqimlari

**Reseller dasturi:**
- Hosting kompaniyalari, IT service provayderlar tizimni o'z brendlari bilan sotadi
- White-label: $200/oy + foydalanuvchi boshiga $5
- Revenue share: reseller daromadning 30% ini oladi

**Marketplace (keyingi bosqich):**
- Foydalanuvchilar o'z "runbook" va diagnostic scriptlarini sotadi
- Platforma 20% komissiya oladi
- Tayyorlanmiş deploy templatelar: $5–$50

**Konsalting va onboarding:**
- Enterprise mijozlar uchun to'liq sozlash xizmati
- $500–$2000 bir martalik to'lov

---

## 2. NARXLASH PSIXOLOGIYASI

**Nima uchun bu narxlar to'g'ri:**

- $15/oy = bir soatlik IT mutaxassis ishi. Tizim oyda 10+ soat tejaydi → 10x ROI
- Free tarif "bepul reklama" — foydalanuvchi ishlatib ko'radi, keyin to'laydi
- Team tarifi $49 = ikkita kofexona mehmonxonasi narxi. Startup uchun arzon
- Enterprise narx "qo'ng'iroq qiling" emas — aniq belgilangan (ishonch beradi)

**Freemium konversiya strategiyasi:**
1. Free foydalanuvchi 3 serverga yetganda: 