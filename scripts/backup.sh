#!/usr/bin/env bash
# Backup PostgreSQL (container compose "db") -> file .sql.gz bertanggal,
# lalu hapus backup yang berumur lebih dari 7 hari.
#
# Pemakaian (dari folder proyek, di WSL atau Git Bash):
#   cp .env.example .env     # isi password
#   chmod +x scripts/backup.sh
#   ./scripts/backup.sh
#
# Penjadwalan harian jam 02:00 dengan cron (crontab -e):
#   0 2 * * * cd /path/ke/transaction-api && ./scripts/backup.sh >> backups/backup.log 2>&1
set -euo pipefail

cd "$(dirname "$0")/.."

# Muat variabel dari .env (POSTGRES_USER, POSTGRES_DB) jika ada.
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DB_SERVICE="${DB_SERVICE:-db}"
STAMP="$(date +%Y-%m-%d_%H%M%S)"
FILE="${BACKUP_DIR}/${POSTGRES_DB}_${STAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[$(date '+%F %T')] Mulai backup ${POSTGRES_DB} -> ${FILE}"
# -T: tanpa TTY supaya aman dipakai di cron. Password tidak perlu karena
# pg_dump berjalan di dalam container lewat koneksi lokal.
docker compose exec -T "$DB_SERVICE" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$FILE"

# Pastikan file tidak kosong.
if [ ! -s "$FILE" ]; then
  echo "Backup gagal: file kosong" >&2
  rm -f "$FILE"
  exit 1
fi

echo "[$(date '+%F %T')] Backup selesai ($(du -h "$FILE" | cut -f1))"

# Rotasi: hapus backup yang lebih tua dari RETENTION_DAYS hari.
find "$BACKUP_DIR" -name "${POSTGRES_DB}_*.sql.gz" -type f -mtime +"$RETENTION_DAYS" -print -delete
echo "[$(date '+%F %T')] Rotasi selesai (simpan ${RETENTION_DAYS} hari)"
