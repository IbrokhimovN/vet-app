# Vet-App backend (Django + DRF) — ARCHITECTURE.md 8-bo'lim (deploy)
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Tizim kutubxonalari (psycopg2/Pillow wheel'lari uchun yetarli, runtime'da kerak)
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

# Standart buyruq compose'da override qilinadi (web / worker)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
