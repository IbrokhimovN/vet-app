# Vet-App — Arxitektura Hujjati

Telegram Mini App orqali uy hayvonlari egalari veterinarlarni topishi, ko'rishi va
chaqirishi mumkin bo'lgan platforma. Veterinarlar uchun alohida Mini App orqali ular
o'z profilini to'ldiradi va so'rovlarni boshqaradi.

- **Backend:** Django + Django REST Framework (DRF)
- **Frontend:** Har bir Mini App ichida Vanilla HTML / CSS / JS (Telegram WebApp SDK)
- **Hujjat sanasi:** 2026-05-30

---

## 1. Qabul qilingan asosiy qarorlar

| Qaror | Tanlov |
|---|---|
| Chaqirish turlari | **Uyga chaqirish** + **Online konsultatsiya** + **Telefon/Telegram kontakt** |
| Bot strukturasi | **2 ta alohida bot** (mijoz uchun va veterinar uchun) |
| To'lov tizimi | **Hozircha yo'q** — naqd / vet bilan to'g'ridan-to'g'ri kelishuv |
| Geo qidiruv | **Oddiy** — lat/lng + Haversine masofa (PostGIS shart emas) |
| Topish rejimlari | **2 ta:** (A) to'g'ridan vetni tanlash, (B) ochiq so'rov → vetlar taklif beradi (tender) |
| Monetizatsiya | MVP'da **to'lovsiz**, lekin model **vet-tomonlama** (TOP joylashuv / wallet) — maydonlar zaxiraga qo'yiladi |
| Mijoz platformasi | **API-first / headless** — bir API, ko'p frontend (Telegram → keyin web + mobil qo'shiladi, backend qayta yozilmaydi). 14-bo'limga qarang |

> **Ilhom manbai:** [ustabor.uz](https://www.ustabor.uz/uz) — O'zbekistondagi xizmat
> marketplace'i. Undan olingan asosiy g'oyalar: ikki xil topish rejimi (to'g'ridan
> tanlash + so'rov qoldirish/tender), profil to'liqligi = ko'rinish, yulduzli reyting,
> va **to'lov vetlardan olinadi (mijozdan emas)** — TOP joylashuv orqali.

---

## 2. Umumiy arxitektura

```
┌─────────────────┐         ┌─────────────────┐
│  MIJOZ BOTI     │         │   VET BOTI      │
│  @vet_client_bot│         │  @vet_doctor_bot│
└────────┬────────┘         └────────┬────────┘
         │ WebApp ochadi             │ WebApp ochadi
         ▼                           ▼
┌─────────────────┐         ┌─────────────────┐
│ Mijoz Mini App  │         │  Vet Mini App   │
│ (HTML/CSS/JS)   │         │  (HTML/CSS/JS)  │
└────────┬────────┘         └────────┬────────┘
         │  initData + REST API calls │
         └────────────┬───────────────┘
                      ▼
         ┌────────────────────────┐
         │   Django + DRF API     │
         │  (Gunicorn + Nginx)    │
         └───┬──────────┬─────────┘
             ▼          ▼
      ┌──────────┐  ┌──────────────┐
      │PostgreSQL│  │ Redis+Celery │──► Telegram Bot API
      └──────────┘  └──────────────┘    (bildirishnoma)
```

**Asosiy g'oyalar:**

- Ikkala Mini App bitta umumiy backend bilan ishlaydi.
- Foydalanuvchining roli (`client` yoki `vet`) qaysi bot orqali kirganidan aniqlanadi.
- HTTPS majburiy — Telegram faqat HTTPS domenni qabul qiladi (SSL sertifikat kerak).
- Bildirishnomalar asinxron tarzda (Celery) Telegram Bot API orqali yuboriladi.

---

## 3. Telegram Mini App texnik o'zagi

### 3.1. Autentifikatsiya oqimi

```
1. Foydalanuvchi botda "Ochish" (WebApp) tugmasini bosadi.
2. Telegram Mini App ochiladi va `window.Telegram.WebApp.initData` beradi.
3. Frontend initData ni → POST /api/auth/telegram/ ga yuboradi.
4. Backend:
   - initData ni bot_token bilan HMAC-SHA256 orqali tekshiradi (soxta emasligini).
   - auth_date eskimaganini tekshiradi (masalan < 24 soat).
   - telegram_id bo'yicha User topadi yoki yaratadi.
   - Rol botning turidan aniqlanadi (mijoz boti → client, vet boti → vet).
   - JWT access + refresh token qaytaradi.
5. Frontend JWT ni saqlaydi va keyingi har bir so'rovda
   Authorization: Bearer <token> header bilan yuboradi.
```

### 3.2. initData tekshirish algoritmi (HMAC-SHA256)

```
secret_key = HMAC_SHA256(key="WebAppData", message=bot_token)
data_check_string = initData dagi maydonlar (hash dan tashqari)
                    alfavit tartibida "key=value\n" ko'rinishida
calculated_hash = HMAC_SHA256(key=secret_key, message=data_check_string)
agar calculated_hash == initData.hash bo'lsa → haqiqiy
```

> Bu — parolsiz, ro'yxatdan o'tishsiz ishonchli autentifikatsiya. Foydalanuvchi
> ma'lumotlari (id, ism, username) Telegram tomonidan imzolanган holda keladi.

---

## 4. Ma'lumotlar modeli

```python
# accounts
User(telegram_id[null=True], role[client|vet], first_name, last_name,
     username, phone, language[uz|ru], photo_url, created_at)
     # telegram_id null bo'lishi mumkin — kelajakda web/mobil orqali kelgan
     # foydalanuvchi Telegramsiz ham mavjud bo'la oladi (14-bo'lim).
AuthIdentity(user → FK(User), provider[telegram|phone|email],
             external_id, is_verified)
     # bir User'ga bir nechta kirish usuli bog'lanadi (Telegram, telefon/OTP...).
     # MVP'da faqat provider=telegram ishlatiladi, qolganlari zaxira.

# vets
Specialization(name, icon, slug)        # it, mushuk, qoramol, qush, ekzotik...
VetProfile(user → OneToOne,
           bio, experience_years, clinic_name,
           lat, lng, address, city, district,
           is_verified, is_available,
           rating_avg, rating_count,
           specializations → ManyToMany(Specialization),
           accepts_home_visit, accepts_online,
           # --- monetizatsiya (MVP'da ishlatilmaydi, zaxira) ---
           is_top, top_until, wallet_balance)
Service(vet → FK(VetProfile), title, price, duration_min)

# pets
Pet(owner → FK(User), name, species, breed, age, gender, photo, notes)

# requests — REJIM A: to'g'ridan vetni tanlab chaqirish
CallRequest(client → FK(User),
            vet → FK(VetProfile),
            pet → FK(Pet),
            type[home|online|contact],
            status[pending|accepted|on_way|completed|rejected|cancelled],
            scheduled_at, address, lat, lng, note,
            price_agreed, created_at)

# requests — REJIM B: ochiq so'rov (tender) — mijoz vetni tanlamaydi
ServiceRequest(client → FK(User),
               pet → FK(Pet),
               specialization → FK(Specialization),
               type[home|online|contact],
               city, district, lat, lng,
               note, budget_hint,
               status[open|assigned|completed|cancelled|expired],
               assigned_offer → FK(Offer, null),
               created_at, expires_at)

Offer(request → FK(ServiceRequest),
      vet → FK(VetProfile),
      price, can_arrive_at, message,
      status[sent|accepted|declined|withdrawn],
      created_at)
      # unique(request, vet) — bir vet bir so'rovga bir marta taklif beradi

# reviews
Review(client → FK(User),
       vet → FK(VetProfile),
       request → OneToOne(CallRequest),
       stars[1-5], comment, created_at)
```

### 4.1. CallRequest turlari

| Turi | Tavsif | Majburiy maydonlar |
|---|---|---|
| `home` | Vet mijoz manziliga keladi (uyga chaqirish) | lat, lng, address |
| `online` | Telegram orqali yozishma/konsultatsiya | — (manzil shart emas) |
| `contact` | Vet kontaktini ochib berish, to'g'ridan bog'lanish | — |

### 4.2. CallRequest status oqimi (state machine)

```
pending ──accept──► accepted ──on_way──► on_way ──complete──► completed
   │                                                              │
   ├──reject──► rejected                                          ▼
   │                                                      (Review qoldirish)
   └──cancel──► cancelled (mijoz tomonidan)
```

### 4.3. Ikki topish rejimi (ustabor modeli)

Mijoz vetni **2 xil** yo'l bilan topadi — har ikkalasi qo'llab-quvvatlanadi:

**Rejim A — To'g'ridan tanlash (direct)**
```
Mijoz qidiradi → vet profilini ko'radi → o'zi tanlaydi → CallRequest yuboradi
→ faqat o'sha vetga boradi → vet accept/reject qiladi
```

**Rejim B — So'rov qoldirish / Tender (bidding)**
```
1. Mijoz ochiq ServiceRequest tashlaydi (vetni TANLAMAYDI):
   mutaxassislik + hudud + hayvon + izoh
2. So'rov mos vetlarga (specialization + city/district bo'yicha) bot orqali tarqaladi
3. Bir nechta vet Offer yuboradi: narx + qachon kela oladi + izoh
4. Mijoz kelgan takliflarni (reyting bilan) solishtirib bittasini tanlaydi
5. Tanlangach → ServiceRequest=assigned, tanlangan Offer=accepted,
   qolganlari=declined → keyin odatiy bajarilish va Review
```

**ServiceRequest status oqimi:**
```
open ──(vet tanlandi)──► assigned ──► completed
  │                                       │
  ├──cancel──► cancelled                  ▼
  │                              (Review qoldirish)
  └──(vaqt tugadi)──► expired
```

---

## 5. Backend tuzilishi (Django app'lar)

```
vet-app/
├── config/               # settings (base/dev/prod), urls, wsgi, asgi, celery
├── apps/
│   ├── accounts/         # User modeli, Telegram auth, JWT, HMAC validator
│   ├── vets/             # VetProfile, Specialization, Service, qidiruv
│   ├── pets/             # Pet CRUD
│   ├── requests/         # CallRequest, status oqimi (state machine)
│   ├── reviews/          # Review, reyting hisoblash
│   └── notifications/    # Telegram Bot API wrapper + Celery tasklar
├── frontend/
│   ├── client/           # index.html, app.js, style.css (mijoz mini app)
│   └── vet/              # index.html, app.js, style.css (vet mini app)
├── bots/                 # 2 bot: webhook/polling, /start, WebApp tugmasi
├── static/  media/
├── requirements.txt
├── .env.example
├── docker-compose.yml    # (ixtiyoriy)
└── manage.py
```

---

## 6. API endpoint'lar

> Barcha yo'llar **`/api/v1/`** prefiksi ostida (versiyalash — 14-bo'lim). Quyida
> qisqalik uchun `/api/...` deb yozilgan, to'liq shakli `/api/v1/...`.

### 6.1. Auth (umumiy)

| Method | Endpoint | Tavsif |
|---|---|---|
| POST | `/api/auth/telegram/` | initData → JWT (access + refresh) |
| POST | `/api/auth/refresh/` | refresh token → yangi access token |

### 6.2. Mijoz ilovasi

| Method | Endpoint | Tavsif |
|---|---|---|
| GET | `/api/vets/?spec=&lat=&lng=&sort=distance\|rating&type=home\|online` | Vetlarni qidirish/filtrlash |
| GET | `/api/vets/{id}/` | Vet sahifasi (xizmatlar, izohlar) |
| GET, POST | `/api/pets/` | Hayvonlarim ro'yxati / qo'shish |
| PUT, DELETE | `/api/pets/{id}/` | Tahrirlash / o'chirish |
| POST | `/api/requests/` | To'g'ridan chaqiruv yaratish (Rejim A) |
| GET | `/api/requests/?role=client` | Chaqiruvlarim + status |
| POST | `/api/requests/{id}/cancel/` | Chaqiruvni bekor qilish |
| POST | `/api/service-requests/` | Ochiq so'rov (tender) yaratish (Rejim B) |
| GET | `/api/service-requests/?role=client` | So'rovlarim + kelgan takliflar soni |
| GET | `/api/service-requests/{id}/offers/` | Kelgan takliflarni ko'rish |
| POST | `/api/offers/{id}/accept/` | Taklifni qabul qilish (vetni tanlash) |
| POST | `/api/service-requests/{id}/cancel/` | Tenderni bekor qilish |
| POST | `/api/reviews/` | Baho qoldirish |

### 6.3. Veterinar ilovasi

| Method | Endpoint | Tavsif |
|---|---|---|
| GET, PUT | `/api/vets/me/` | O'z profilini to'ldirish/tahrirlash |
| GET, POST | `/api/vets/me/services/` | Xizmatlarni boshqarish |
| DELETE | `/api/vets/me/services/{id}/` | Xizmatni o'chirish |
| GET | `/api/requests/?role=vet` | Kelgan so'rovlar |
| POST | `/api/requests/{id}/accept/` | Qabul qilish |
| POST | `/api/requests/{id}/reject/` | Rad etish |
| POST | `/api/requests/{id}/on_way/` | "Yo'ldaman" holati |
| POST | `/api/requests/{id}/complete/` | Yakunlash |
| PUT | `/api/vets/me/availability/` | Band/bo'sh holatni o'zgartirish |
| GET | `/api/service-requests/feed/` | Menga mos ochiq so'rovlar (tender lenta) |
| POST | `/api/service-requests/{id}/offer/` | So'rovga taklif yuborish |
| POST | `/api/offers/{id}/withdraw/` | O'z taklifini qaytarib olish |

---

## 7. Bildirishnomalar (Celery + Telegram Bot API)

| Hodisa | Kimga | Xabar namunasi |
|---|---|---|
| Yangi chaqiruv (Rejim A) | Vetga | "🔔 Yangi uyga chaqiruv so'rovi! [Ochish]" |
| So'rov qabul qilindi | Mijozga | "✅ Vet so'rovingizni qabul qildi" |
| Vet yo'lda | Mijozga | "🚗 Vet yo'lga chiqdi" |
| Yakunlandi | Mijozga | "✔️ Tashrif yakunlandi. Baho qoldiring ⭐" |
| So'rov rad etildi | Mijozga | "❌ Afsuski, so'rov rad etildi" |
| Yangi ochiq so'rov (Rejim B) | Mos vetlarga | "📢 Hududingizda yangi so'rov bor. Taklif yuboring! [Ochish]" |
| Yangi taklif keldi | Mijozga | "💬 So'rovingizga yangi taklif keldi" |
| Taklif qabul qilindi | Vetga | "🎉 Mijoz taklifingizni tanladi!" |

Barcha xabarlar Celery task orqali asinxron yuboriladi — foydalanuvchi javobni
kutib qolmaydi.

---

## 8. Geo qidiruv (Haversine)

PostGIS o'rniga oddiy yondashuv:

- Har bir `VetProfile` da `lat`, `lng` saqlanadi.
- Mijoz qidirganda o'z `lat/lng` sini yuboradi.
- Backend Haversine formulasi bilan masofani hisoblaydi va saralaydi.
- Dastlabki filtrlash uchun shahar/tuman (`city`, `district`) bo'yicha
  cheklov qo'yib, keyin masofani hisoblash mumkin (tezlik uchun).

> Kelajakda ko'lam o'ssa, PostGIS ga o'tish oson — model maydonlari mos.

---

## 9. Texnologiyalar steki

| Qatlam | Tanlov |
|---|---|
| Backend | Django 5 + Django REST Framework |
| Autentifikatsiya | djangorestframework-simplejwt + Telegram HMAC validator |
| Ma'lumotlar bazasi | PostgreSQL |
| Asinxron vazifalar | Redis + Celery |
| Telegram bot | python-telegram-bot (yoki to'g'ridan Bot API) |
| Frontend | Vanilla HTML / CSS / JS + Telegram WebApp SDK |
| Web server | Nginx + Gunicorn |
| HTTPS | Certbot / Let's Encrypt |
| Dev muhit | Docker Compose (ixtiyoriy) |

---

## 10. Xavfsizlik mulohazalari

- **initData har doim backendda tekshiriladi** — frontendga ishonmaslik.
- `auth_date` eskirgan bo'lsa rad etiladi (replay hujumlardan himoya).
- JWT muddati cheklangan (access qisqa, refresh uzunroq).
- Vet profilini faqat egasi tahrirlaydi; `is_verified` ni faqat admin qo'yadi.
- CallRequest status o'zgarishlari rol va egalikка qarab tekshiriladi
  (mijoz faqat `cancel`, vet faqat `accept/reject/on_way/complete`).
- Bot tokenlari `.env` da, repozitoriyga tushmaydi.
- Rasm yuklashda hajm/format cheklovlari.

---

## 11. MVP yo'l xaritasi (bosqichma-bosqich)

1. **Asos** — Django loyiha, settings (base/dev/prod), PostgreSQL, `User` modeli.
2. **Telegram Auth** — HMAC validator + JWT (ikkala bot uchun ishlaydi).
3. **Vet profili** — `VetProfile` CRUD + vet Mini App (profil to'ldirish ekrani).
4. **Qidiruv** — mutaxassislik / masofa bo'yicha + mijoz Mini App ro'yxati.
5. **Chaqiruv** — `CallRequest` yaratish + status oqimi (3 tur).
6. **Bildirishnoma** — Celery + Telegram bot xabarlari.
7. **Izohlar** — reyting tizimi (`Review`) + reyting o'rtachasini yangilash.
8. **Deploy** — Nginx, SSL (HTTPS), 2 botni ulash, webhook sozlash.

---

## 12. Monetizatsiya modeli (vet-tomonlama — ustabor'dan)

Asosiy tamoyil: **to'lov vetlardan olinadi, mijozdan emas.** MVP'da hech qanday
to'lov yo'q, lekin model va ma'lumotlar bazasi maydonlari (`is_top`, `top_until`,
`wallet_balance`) shu yo'nalishni hisobga olib zaxiraga qo'yiladi — kelajakda qayta
yozishdan saqlaydi.

Mumkin bo'lgan daromad oqimlari (keyinroq yoqiladi):

| Model | Qanday ishlaydi |
|---|---|
| **TOP joylashuv** | Vet pul to'lab qidiruv natijalarida yuqorida (`is_top`) chiqadi |
| **Javob krediti (lead)** | Vet ochiq so'rovga (tender) taklif yuborish uchun kredit sarflaydi |
| **Premium obuna** | Oylik to'lov: cheksiz taklif, "Tasdiqlangan" belgisi, statistika |

To'lov yoqilganda — O'zbekiston tizimlari (Payme / Click) yoki Telegram Payments
orqali `wallet_balance` to'ldiriladi. Hozircha bu maydonlar shunchaki mavjud, lekin
hech qayerda undirilmaydi.

---

## 13. Kelajakdagi kengaytmalar (MVP dan keyin)

- To'lov integratsiyasini yoqish (12-bo'limdagi monetizatsiya modeli uchun).
- PostGIS bilan kuchaytirilgan geo qidiruv va xarita.
- Vet ish jadvali (working hours / kalendar) va band vaqtlar.
- Push eslatmalar (uchrashuvdan oldin).
- Admin panel orqali vetlarni tasdiqlash (verifikatsiya) jarayoni.
- Ko'p tillilik (uz / ru) to'liq qo'llab-quvvatlash.
- Statistika va analitika paneli.

---

## 14. Ko'p mijozli tayyorlik (API-first)

**Maqsad:** kelajakda **web sayt** yoki **mobil ilova** qo'shilsa, backend
**qayta yozilmasin** — faqat yangi frontend va auth-provider yoqilsin.

### 14.1. Asosiy tamoyil — headless API

DRF REST API mijozdan mustaqil (headless): bir xil JSON endpoint'larni
**Telegram Mini App**, **web SPA** va **mobil ilova** bir xil ishlatadi. Biznes-mantiq,
modellar va API yo'llari o'zgarmaydi. Django **HTML render qilmaydi** — faqat JSON
beradi; har bir frontend alohida iste'molchi.

```
                ┌──────────────────────────────┐
                │     Django + DRF (JSON API)   │
                └───┬───────────┬───────────┬───┘
                    │           │           │
            Telegram Mini   Web sayt    Mobil ilova
            App (hozir)     (keyin)     (keyin)
```

### 14.2. Hozir qilib qo'yiladigan 5 ta moslama

| # | Moslama | Nega |
|---|---|---|
| 1 | `User.telegram_id = null=True` + `AuthIdentity` modeli | Telegramsiz (web/mobil) user mavjud bo'la oladi |
| 2 | **API versiyalash** — barcha yo'llar `/api/v1/...` ostida | Mobil ilovani buzmasdan API'ni rivojlantirish |
| 3 | **Auth'ni pluggable** qilish (provider abstraktsiyasi) | Keyin telefon/OTP, email qo'shilganda API qatlamiga tegilmaydi |
| 4 | **CORS** sozlamasi (django-cors-headers) | Web/mobil boshqa domendan so'rov yuboradi |
| 5 | **Bildirishnoma kanalini abstraktlash** | Telegram → keyin FCM/APNs (mobil), Web Push (sayt) |

### 14.3. Auth provider abstraktsiyasi

Barcha kirish usullari bir xil **JWT** beradi → API qatlami auth usulini bilmaydi.

```
POST /api/v1/auth/telegram/   → initData tekshiriladi   ┐
POST /api/v1/auth/phone/otp/  → SMS OTP (kelajak)        ├─► bir xil JWT
POST /api/v1/auth/email/      → email+parol (kelajak)    ┘
```

Har bir provider `AuthIdentity` orqali bitta `User`ga bog'lanadi. Bir foydalanuvchi
ham Telegram, ham telefon orqali kira oladi (bitta hisob).

### 14.4. Bildirishnoma kanali abstraktsiyasi

`notifications` app'i kanalga bog'lanmagan interfeys beradi:

```
notify(user, event, payload)
   ├─ Telegram kanali  (hozir — bot orqali)
   ├─ FCM / APNs       (kelajak — mobil push)
   └─ Web Push         (kelajak — sayt)
```

Foydalanuvchining qaysi kanallari bor — shularga yuboriladi. Yangi kanal qo'shish
biznes-mantiqqa tegmaydi.

### 14.5. Natija

Bu moslamalar bilan web yoki mobil qo'shilganda backendda **deyarli 0 o'zgarish**:
yangi frontend yoziladi, kerakli auth-provider va bildirishnoma kanali yoqiladi —
modellar, API va biznes-mantiq o'zgarishsiz qoladi.
