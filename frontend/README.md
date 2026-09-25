# Vet-App — Frontend

Mijoz Mini App (`client/`), veterinar Mini App (`vet/`) va admin panel (`admin/`):
oddiy HTML/CSS/JS, build kerak emas. **Caddy** beradi: avtomatik HTTPS, `/api` va `/admin`ni
backend'ga yo'naltiradi, admin panelni IP bo'yicha cheklaydi.

Bu papka mustaqil: o'z Dockerfile'i, compose fayllari va `.env` shabloni shu yerda.
Backend alohida: [`../backend`](../backend).

## Tuzilma

```
client/ · vet/ · admin/        — ilovalar (HTML/CSS/JS)
Caddyfile                      — marshrutlash, HTTPS, admin IP cheklovi
Dockerfile
docker-compose.yml · docker-compose.dev.yml
.env.prod.example
```

Marshrutlar: `/client/` (mijoz), `/vet/` (veterinar), `/admin-panel/` (admin), `/api/*`, `/admin/*`,
`/static/*` (backend'ga), `/media/*` (umumiy volume'dan). `/` → `/client/`.

## Production

**Avval backend** ishga tushirilgan bo'lishi kerak (`vetapp-edge` tarmog'i va `vetapp-media` volume'ini u yaratadi).

```bash
cp .env.prod.example .env.prod      # to'ldiring
docker compose up -d --build
```

- `SITE_ADDRESS=vet.example.uz` — Caddy HTTPS sertifikatni o'zi oladi va yangilaydi (80/443 ochiq, DNS shu serverga qaragan bo'lsin).
  Backend'dagi `ALLOWED_HOSTS` va `TELEGRAM_*_WEBAPP_URL` shu domen bilan mos bo'lishi kerak.
- `ADMIN_ALLOW=203.0.113.7` — `/admin-panel/`, `/admin/`, `/api/v1/admin/` faqat shu IP/CIDR'lardan ochiladi (qolganlarga 403).
  Cloudflare kabi proksi ortida bo'lsa, proksi IP'si ko'rinadi.
- Yangilash: `git pull && docker compose up -d --build`.

## Lokal dev

```bash
# 1. backend dev stack:   cd ../backend && docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
# 2. frontend:
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

| Manzil | Tavsif |
|---|---|
| http://localhost:8090/client/ | Mijoz Mini App |
| http://localhost:8090/vet/ | Veterinar Mini App |
| http://localhost:8090/admin-panel/ | Admin panel (faqat `is_staff` foydalanuvchilar) |

Front fayllari konteynerga ulangan, o'zgarish darhol ko'rinadi. Backend `runserver` bilan Docker'siz
yurgan bo'lsa, front'ni to'g'ridan-to'g'ri u ham beradi: http://127.0.0.1:8000/client/
