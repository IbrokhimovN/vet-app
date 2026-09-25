# Vet-App — Backend

Django 5 · DRF · SimpleJWT · PostgreSQL · Celery + Redis · Telegram Bot API

Bu papka mustaqil: o'z Dockerfile'i, compose fayllari va `.env` shablonlari shu yerda.
Frontend alohida: [`../frontend`](../frontend).

## Tuzilma

```
config/          — Django sozlamalari, urls, celery
apps/
  accounts/      — User, Telegram auth
  vets/          — VetProfile, mutaxassislik, xizmatlar, qidiruv
  pets/          — Pet
  requests/      — CallRequest (to'g'ridan) + ServiceRequest/Offer (tender)
  reviews/       — Review
  notifications/ — Telegram bot xabarlari (Celery)
  moderation/    — shikoyatlar
  adminpanel/    — admin panel API
bots/            — 2 ta Telegram bot
Dockerfile · entrypoint.sh · requirements.txt · manage.py
docker-compose.yml · docker-compose.dev.yml
.env.prod.example (prod) · .env.example (lokal dev) · scripts/backup.sh
```

## Production

Kerak: Docker + Compose. **Frontend'dan oldin** ishga tushiring.

```bash
cp .env.prod.example .env.prod      # to'ldiring
docker compose up -d --build
docker compose exec backend python manage.py createsuperuser
```

- Compose xizmatlari: `db` (Postgres), `redis`, `backend` (gunicorn API), `worker` (Celery), `client_bot`, `vet_bot`.
- Loyiha `vetapp-edge` tarmog'i va `vetapp-media` volume'ini yaratadi; frontend ularga ulanadi.
- **Xavfsizlik tekshiruvi:** `DEBUG=False` bo'lsa-yu `SECRET_KEY` sukut qiymatda qolsa, backend ishga tushmaydi.
- **Telegram:** `.env.prod`da tokenlar va `TELEGRAM_*_WEBAPP_URL=https://<domen>/client/` (va `/vet/`).
- **Yangilash:** `git pull && docker compose up -d --build` (migratsiya avtomatik).
- **Zaxira nusxa:** avtomatik — `backup` xizmati (`docker-compose.yml`) har kuni o'zi nusxa oladi (`backups/`, `.env.prod`dagi `BACKUP_HOUR`/`BACKUP_KEEP_DAYS` bilan sozlanadi), server cron kerak emas. Qo'lda darhol nusxa olish: `docker compose exec backup /backup_loop.sh --once`. Tiklash: `gunzip -c backups/<fayl>.sql.gz | docker compose exec -T db psql -U "$POSTGRES_USER" "$POSTGRES_DB"`. Eski qo'lda-ishga-tushiriladigan variant (`scripts/backup.sh`, host cron talab qiladi) ham qoldirilgan — kerak bo'lmasa e'tiborsiz qoldiring.
- Loglar: `docker compose logs -f backend` · `worker` · `client_bot` · `vet_bot`.

## Lokal dev

### Docker bilan

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python manage.py createsuperuser
```

API: http://localhost:8000/api/v1/ · DB: `localhost:5433`. Lokal qiymatlar `.env.docker`dan
olinadi (git'da yo'q; `.env.example` asosida o'zingiz yarating). Kod konteynerga ulangan.
Frontend'ni ko'rish uchun: [`../frontend`](../frontend) dagi dev yo'riqnoma.

### Docker'siz backend (venv + Docker DB)

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # localhost:5433 ga sozlangan
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver           # ../frontend papkasidan front ham beradi
```

- Admin: http://127.0.0.1:8000/admin/ · API: http://127.0.0.1:8000/api/v1/
- Testlar: `python manage.py test --noinput`
- Sozlamalar `backend/.env` (yoki loyiha ildizidagi `.env`) dan o'qiladi; konteynerda `env_file` ustun turadi.

## Telegram botlar (2 ta)

Botlar yengil: foydalanuvchini kutib oladi va Mini App'ni ochadigan tugma beradi.
Asosiy mantiq API'da. Qo'shimcha kutubxonasiz — `requests` long-polling.

```bash
# .env'da to'ldiring (HTTPS shart — dev'da ngrok/cloudflared tunnel):
#   TELEGRAM_CLIENT_BOT_TOKEN=...   TELEGRAM_CLIENT_WEBAPP_URL=https://<tunnel>/client/
#   TELEGRAM_VET_BOT_TOKEN=...      TELEGRAM_VET_WEBAPP_URL=https://<tunnel>/vet/

cd backend
python -m bots.client_bot      # mijoz boti
python -m bots.vet_bot         # vet boti
```

- `/start` → kutib olish + Mini App'ni ochuvchi tugma; chat menyu tugmasi ham ulanadi.
- Token yoki URL bo'lmasa bot chiroyli xabar bilan to'xtaydi.

