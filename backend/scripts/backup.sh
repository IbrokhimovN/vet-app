#!/usr/bin/env bash
# Postgres zaxira nusxasi:  ./scripts/backup.sh
# Cron (har kuni 03:00):  0 3 * * * cd /path/to/vet-app/backend && ./scripts/backup.sh >> backups/backup.log 2>&1
# Tiklash:  gunzip -c backups/<fayl>.sql.gz | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
set -euo pipefail
cd "$(dirname "$0")/.."

KEEP_DAYS="${KEEP_DAYS:-14}"
mkdir -p backups
FILE="backups/vetapp_$(date +%F_%H%M).sql.gz"

docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$FILE"

# Bo'sh yoki buzilgan fayl qolib ketmasin
if [ ! -s "$FILE" ] || [ "$(stat -c%s "$FILE")" -lt 200 ]; then
  echo "XATO: zaxira fayli bo'sh: $FILE" >&2
  rm -f "$FILE"
  exit 1
fi

find backups -name 'vetapp_*.sql.gz' -mtime +"$KEEP_DAYS" -delete
echo "OK: $FILE ($(du -h "$FILE" | cut -f1))"
