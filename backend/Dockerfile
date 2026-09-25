# Vet-App BACKEND (Django + DRF + Celery + botlar) — faqat API, frontend alohida (../frontend).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# psycopg2-binary va Pillow wheel'lari uchun runtime kutubxonasi yetarli
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Ildiz (root) bo'lmagan foydalanuvchi — konteyner buzilsa ham zarar cheklangan
RUN useradd --create-home --uid 1000 app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=app:app . .
# `WORKDIR /app` /app'ni root egaligida yaratadi (COPY --chown yuqoridagi qatorda
# faqat ko'chirilgan fayllarni, katalogning o'zini emas, app'ga o'tkazadi) —
# shuning uchun bu yerda alohida chown qilinadi. Aks holda ildizsiz foydalanuvchi
# /app ichiga yozolmaydi (masalan, Celery beat'ning celerybeat-schedule fayli).
RUN chown app:app /app \
    && mkdir -p /app/media /app/staticfiles /app/.offsets \
    && chown -R app:app /app/media /app/staticfiles /app/.offsets \
    && chmod +x /app/entrypoint.sh

USER app
EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
# Standart buyruq: API. Compose'da worker / botlar uchun override qilinadi.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-"]
