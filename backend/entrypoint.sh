#!/bin/sh
# Konteyner ishga tushishidan oldingi tayyorgarlik.
set -e

# Xavfsizlik tekshiruvi: DEBUG=False bo'lsa-yu SECRET_KEY sukut qiymatda qolsa, ishga tushmaydi.
python manage.py check

# Migratsiya va statik fayllar faqat API konteynerida (RUN_MIGRATIONS=1),
# worker va botlar bilan poyga bo'lmasligi uchun.
if [ "$RUN_MIGRATIONS" = "1" ]; then
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
fi

exec "$@"
