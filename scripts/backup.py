#!/usr/bin/env python3
"""Backup PostgreSQL (container compose "db") -> file .sql.gz bertanggal,
lalu hapus backup yang berumur lebih dari 7 hari.

Versi Python dari scripts/backup.sh, bisa dijalankan langsung di PowerShell:
    python scripts/backup.py

Penjadwalan harian jam 02:00:
  - Linux/WSL (cron):   0 2 * * * cd /path/transaction-api && python3 scripts/backup.py
  - Windows (Task Scheduler): buat task harian yang menjalankan `python scripts/backup.py`
    dengan "Start in" = folder proyek.
"""
import gzip
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env(path: Path) -> dict:
    """Baca file .env sederhana (KEY=VALUE), abaikan baris kosong dan komentar."""
    values = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def rotate(backup_dir: Path, db: str, retention_days: int) -> list:
    """Hapus file backup yang lebih tua dari retention_days hari."""
    cutoff = time.time() - retention_days * 86400
    removed = []
    for f in backup_dir.glob(f"{db}_*.sql.gz"):
        if f.is_file() and f.stat().st_mtime < cutoff:
            f.unlink()
            removed.append(f.name)
    return removed


def log(msg: str) -> None:
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def main() -> int:
    env = {**load_env(ROOT / ".env"), **os.environ}
    try:
        user = env["POSTGRES_USER"]
        db = env["POSTGRES_DB"]
    except KeyError as missing:
        print(f"Variabel {missing} tidak ditemukan. Pastikan file .env ada.", file=sys.stderr)
        return 1

    backup_dir = Path(env.get("BACKUP_DIR", ROOT / "backups"))
    retention = int(env.get("RETENTION_DAYS", 7))
    service = env.get("DB_SERVICE", "db")
    backup_dir.mkdir(parents=True, exist_ok=True)

    target = backup_dir / f"{db}_{datetime.now():%Y-%m-%d_%H%M%S}.sql.gz"
    log(f"Mulai backup {db} -> {target}")

    # pg_dump berjalan di dalam container; hasilnya dikompres di sisi Python.
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", service, "pg_dump", "-U", user, db],
        cwd=ROOT,
        capture_output=True,
    )
    if result.returncode != 0 or not result.stdout:
        print(result.stderr.decode(errors="replace"), file=sys.stderr)
        print("Backup gagal. Pastikan container db sedang berjalan.", file=sys.stderr)
        return 1

    with gzip.open(target, "wb") as fh:
        fh.write(result.stdout)
    log(f"Backup selesai ({target.stat().st_size / 1024:.1f} KB)")

    removed = rotate(backup_dir, db, retention)
    for name in removed:
        log(f"Hapus backup lama: {name}")
    log(f"Rotasi selesai (simpan {retention} hari)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
