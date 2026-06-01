# Vet-App

Telegram Mini App orqali uy hayvonlari egalari veterinarlarni topadi va chaqiradi.
Veterinarlar uchun alohida Mini App. Backend: **Django + DRF**.

Arxitektura: [`ARCHITECTURE.md`](./ARCHITECTURE.md)

## Texnologiyalar

Django 5 · DRF · SimpleJWT · PostgreSQL · Celery + Redis · Docker · Telegram Bot API

## Docker bilan ishga tushirish (tavsiya — PostgreSQL + Redis + Celery)

Eng oson yo'l. Postgres, Redis, Django va Celery worker bitta buyruq bilan ko'tariladi:

```bash
docker compose up --build        # birinchi marta (rasm quriladi)
# keyingilarida: docker compose up -d

# Admin foydalanuvchi (ixtiyoriy)
docker compose exec web python manage.py createsuperuser
```

| Manzil | Tavsif |
|---|---|
| http://localhost:8090/client/ | Mijoz Mini App |
| http://localhost:8090/vet/ | Veterinar Mini App |
| http://localhost:8090/admin/ | Admin panel |
| http://localhost:8090/api/v1/ | API (v1) |

- **DB:** PostgreSQL 16 (`db` service), **broker:** Redis 7 (`redis` service).
- Sozlamalar `.env.docker`'da; `CELERY_TASK_ALWAYS_EAGER=False` — worker haqiqatan async ishlaydi.
- Loyiha papkasi container'ga ulangan — kod o'zgarishi darhol qayta yuklanadi (runserver).
- To'xtatish: `docker compose down` · ma'lumotlar bilan o'chirish: `docker compose down -v`.
- Loglar: `docker compose logs -f web` yoki `... worker`.

> Host portlari band bo'lsa: web `8090:8000`, DB `5433:5432`'ga o'tkazilgan, redis host'ga chiqarilmagan.

## O'rnatish (dev — virtual muhit + Docker DB)

Ma'lumotlar bazasi **PostgreSQL**. Faqat DB'ni Docker'da ko'tarib, Django'ni venv'da
yuritish mumkin:

```bash
# 1. Virtual muhit
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Muhit sozlamalari
cp .env.example .env        # DATABASE_URL allaqachon localhost:5433 ga sozlangan

# 3. Faqat PostgreSQL'ni Docker'da ko'taramiz (host porti 5433)
docker compose up -d db

# 4. Migratsiya + admin
python manage.py migrate
python manage.py createsuperuser

# 5. Server
python manage.py runserver
```

- Admin panel: http://127.0.0.1:8000/admin/
- API (v1): http://127.0.0.1:8000/api/v1/

DB ulanishi `DATABASE_URL` orqali (`.env`). Default ham PostgreSQL
(`postgres://vetapp:vetapp@localhost:5433/vetapp`) — SQLite ishlatilmaydi.

## Telegram botlar (2 ta)

Botlar yengil: foydalanuvchini kutib oladi va Mini App'ni ochadigan tugma beradi.
Asosiy mantiq API'da. Qo'shimcha kutubxonasiz — `requests` long-polling.

```bash
# .env'da to'ldiring (HTTPS shart — dev'da ngrok/cloudflared tunnel):
#   TELEGRAM_CLIENT_BOT_TOKEN=...   TELEGRAM_CLIENT_WEBAPP_URL=https://<tunnel>/client/
#   TELEGRAM_VET_BOT_TOKEN=...      TELEGRAM_VET_WEBAPP_URL=https://<tunnel>/vet/

python -m bots.client_bot      # mijoz boti
python -m bots.vet_bot         # vet boti
```

- `/start` → kutib olish + Mini App'ni ochuvchi tugma; chat menyu tugmasi ham ulanadi.
- Token yoki URL bo'lmasa bot chiroyli xabar bilan to'xtaydi.

## Loyiha tuzilmasi

```
config/        — Django sozlamalari, urls, celery
apps/
  accounts/    — User, AuthIdentity, Telegram auth (modellar tayyor)
  vets/        — VetProfile, mutaxassislik, xizmatlar, qidiruv
  pets/        — Pet
  requests/    — CallRequest (to'g'ridan) + ServiceRequest/Offer (tender)
  reviews/     — Review
  notifications/ — Telegram bot xabarlari (Celery)
frontend/      — client/ va vet/ Mini App'lari (HTML/CSS/JS)
bots/          — 2 ta Telegram bot
```

## Holat (yo'l xaritasi — ARCHITECTURE.md 11-bo'lim)

- [x] **1. Asos** — Django loyiha, sozlamalar, User modeli, admin
- [x] **2. Telegram auth** — HMAC initData tekshirish + JWT (7 test o'tdi)
- [x] **3. Vet profili + vet Mini App** — VetProfile/Service/Specialization API + front (7 test)
- [x] **4. Qidiruv + mijoz Mini App** — Haversine qidiruv + vet sahifa + mijoz front (7 test)
- [x] **5. Chaqiruv + tender oqimi** — Pet + CallRequest + ServiceRequest/Offer + frontlar (17 test)
- [x] **6. Bildirishnomalar** — Notification modeli + Celery + Telegram Bot API + in-app lenta (11 test)
- [x] **7. Izohlar / reyting** — Review modeli + avto reyting (signal) + izoh front (9 test)
- [ ] 8. Deploy (Nginx, SSL)
