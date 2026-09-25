#!/bin/sh
# Postgres avtomatik zaxira nusxasi — docker-compose.yml'dagi `backup` xizmati
# shu skriptni doim ishga tushirib turadi (10-bo'lim: avval bu qo'lda edi).
#
# Ishga tushgan zahoti bitta nusxa oladi (birinchi deploy'da ham xotirjam bo'lish
# uchun), keyin har kuni BACKUP_HOUR soatida (server vaqti, konteyner UTC'da
# ishlaydi) yana bittadan. Eski nusxalar BACKUP_KEEP_DAYS kundan keyin o'chiriladi.
#
# Qo'lda ishga tushirish: docker compose exec backup /backup_loop.sh --once
# Tiklash: gunzip -c backups/<fayl>.sql.gz | docker compose exec -T db psql -U "$POSTGRES_USER" "$POSTGRES_DB"
set -eu

export PGPASSWORD="${POSTGRES_PASSWORD:-}"
HOST="${DB_HOST:-db}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
HOUR="${BACKUP_HOUR:-03}"
DIR=/backups
MARKER="$DIR/.last_backup_date"

mkdir -p "$DIR"

dump_once() {
  FILE="$DIR/vetapp_$(date +%F_%H%M).sql.gz"
  echo "[$(date -Iseconds)] Zaxira boshlandi: $FILE"
  if pg_dump -h "$HOST" -U "$POSTGRES_USER" "$POSTGRES_DB" 2>"$DIR/.last_error" | gzip > "$FILE" && [ -s "$FILE" ]; then
    echo "[$(date -Iseconds)] OK: $FILE ($(du -h "$FILE" | cut -f1))"
    date +%F > "$MARKER"
  else
    echo "[$(date -Iseconds)] XATO: pg_dump muvaffaqiyatsiz — qarang: $DIR/.last_error"
    cat "$DIR/.last_error" 2>/dev/null || true
    rm -f "$FILE"
  fi
  find "$DIR" -name 'vetapp_*.sql.gz' -mtime "+$KEEP_DAYS" -delete 2>/dev/null || true
}

dump_once
[ "${1:-}" = "--once" ] && exit 0

while true; do
  sleep 300
  if [ "$(date +%H)" = "$HOUR" ] && [ "$(date +%F)" != "$(cat "$MARKER" 2>/dev/null || echo "")" ]; then
    dump_once
  fi
done
