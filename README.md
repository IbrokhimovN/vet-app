# Vet-App

Telegram Mini App orqali uy hayvonlari egalari veterinarlarni topadi va chaqiradi.
Veterinarlar uchun alohida Mini App, administratorlar uchun veb panel.

Arxitektura: [`ARCHITECTURE.md`](./ARCHITECTURE.md)

## Loyiha ikki mustaqil qismdan iborat

Har bir qismning o'z kodi, Dockerfile'i, `docker-compose.yml`i, `.env` fayllari, `.gitignore`i va README'si bor:

| Qism | Papka | Nima | Yo'riqnoma |
|---|---|---|---|
| **Backend** | [`backend/`](./backend) | Django + DRF API, Celery, Telegram botlar, PostgreSQL, Redis | [`backend/README.md`](./backend/README.md) |
| **Frontend** | [`frontend/`](./frontend) | Mijoz va vet Mini App'lari, admin panel (Caddy orqali, HTTPS) | [`frontend/README.md`](./frontend/README.md) |

Ikkalasi alohida ishga tushiriladi. Ular umumiy Docker tarmog'i (`vetapp-edge`) va media
volume'i (`vetapp-media`) orqali ulanadi. **Tartib: avval backend, keyin frontend.**

```
vet-app/
  backend/    Dockerfile · docker-compose.yml · docker-compose.dev.yml · .env.prod.example · .env.example · scripts/
  frontend/   Dockerfile · docker-compose.yml · docker-compose.dev.yml · .env.prod.example · Caddyfile
  docs/       taqdimot va qo'llanma (pptx)
  .github/    CI (GitHub shu joyni talab qiladi)
```

## Tezkor boshlash (production)

```bash
# 1. Backend
cd backend
cp .env.prod.example .env.prod          # to'ldiring: SECRET_KEY, parollar, tokenlar, domen
docker compose up -d --build
docker compose exec backend python manage.py createsuperuser

# 2. Frontend
cd ../frontend
cp .env.prod.example .env.prod          # to'ldiring: domen (SITE_ADDRESS), ADMIN_ALLOW
docker compose up -d --build
```

Batafsil: har bir qismning README'sida.

## Holat (yo'l xaritasi — ARCHITECTURE.md 11-bo'lim)

- [x] **1. Asos** — Django loyiha, sozlamalar, User modeli, admin
- [x] **2. Telegram auth** — HMAC initData tekshirish + JWT (7 test o'tdi)
- [x] **3. Vet profili + vet Mini App** — VetProfile/Service/Specialization API + front (7 test)
- [x] **4. Qidiruv + mijoz Mini App** — Haversine qidiruv + vet sahifa + mijoz front (7 test)
- [x] **5. Chaqiruv + tender oqimi** — Pet + CallRequest + ServiceRequest/Offer + frontlar (17 test)
- [x] **6. Bildirishnomalar** — Notification modeli + Celery + Telegram Bot API + in-app lenta (11 test)
- [x] **7. Izohlar / reyting** — Review modeli + avto reyting (signal) + izoh front (9 test)
- [x] **8. Deploy** — alohida backend/frontend image'lari, Caddy (avtomatik HTTPS), admin IP cheklovi, zaxira skripti
