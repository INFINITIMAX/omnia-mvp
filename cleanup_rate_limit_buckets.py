"""Sterge fizic bucket-urile de rate limit expirate din public.rate_limit_buckets.

Ferestrele expira logic dupa 24 de ore (vezi access_control.py, expires_at), dar pana
acum nimic nu le stergea fizic din Supabase - contractul de retentie din DEPLOYMENT.md
(§7) nu era garantat, doar promis. Scriptul e gandit pentru rulare periodica (Railway
Cron Job sau echivalent), nu ca parte a procesului web `main.py`.

Foloseste --dry-run pentru a numara bucket-urile expirate fara sa stearga nimic si fara
sa deschida vreo tranzactie de scriere.
"""

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

from access_control import PostgresAccessControlRepository

ROOT_PROIECT = Path(__file__).resolve().parent

_SQL_NUMARA_EXPIRATE = "SELECT count(*) FROM public.rate_limit_buckets WHERE expires_at <= %s"


def _required_environment(name):
    value = os.getenv(name)
    if not value:
        raise ValueError(f"variabila de mediu {name} lipseste")
    return value


def conecteaza_baza_de_date():
    return psycopg2.connect(
        host=_required_environment("DB_HOST"),
        dbname=_required_environment("DB_NAME"),
        user=_required_environment("DB_USER"),
        password=_required_environment("DB_PASSWORD"),
        port=_required_environment("DB_PORT"),
    )


def numara_bucket_uri_expirate(conexiune, *, now):
    cursor = conexiune.cursor()
    try:
        cursor.execute(_SQL_NUMARA_EXPIRATE, (now,))
        return int(cursor.fetchone()[0])
    finally:
        cursor.close()


def sterge_bucket_urile_expirate(conexiune, *, now):
    """Sterge si face commit; apelantul (main) decide rollback-ul la eroare."""
    repository = PostgresAccessControlRepository(conexiune)
    sterse = repository.cleanup_expired_rate_limit_buckets(now=now)
    conexiune.commit()
    return sterse


def main():
    parser = argparse.ArgumentParser(
        description="Sterge fizic bucket-urile de rate limit expirate (peste 24h)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="numara doar bucket-urile expirate, fara DELETE"
    )
    args = parser.parse_args()

    load_dotenv(ROOT_PROIECT / ".env")
    now = datetime.now(UTC)
    conexiune = conecteaza_baza_de_date()
    try:
        if args.dry_run:
            expirate = numara_bucket_uri_expirate(conexiune, now=now)
            print(f"DRY RUN: {expirate} bucket-uri expirate ar fi sterse. Nimic modificat.")
            return
        sterse = sterge_bucket_urile_expirate(conexiune, now=now)
        print(f"Sterse {sterse} bucket-uri de rate limit expirate.")
    except Exception:
        conexiune.rollback()
        raise
    finally:
        conexiune.close()


if __name__ == "__main__":
    main()
