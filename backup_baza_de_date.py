"""Backup logic (dump de date) pentru tabelele din Supabase, inainte de schimbari majore
(import de documente noi, migrari). STRICT read-only: doar SELECT, niciodata scriere.

Salveaza fiecare tabel ca JSON intr-un folder `backups/<timestamp-UTC>/`, inclusiv
embeddings (ca vector::text), ca un eventual restore sa nu ceara re-embedding platit.

Nu este un restore automat - doar backup. Folder-ul `backups/` e local, nu intra in Git
(vezi .gitignore) - contine documente normative si e specific fiecarei masini.
"""

import argparse
import json
import os
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

ROOT_PROIECT = Path(__file__).resolve().parent
FOLDER_BACKUPS = ROOT_PROIECT / "backups"

TABELE_DE_BACKUP = (
    "documente",
    "documente_chunks",
    "anonymous_usage",
    "rate_limit_buckets",
    "paid_call_budget",
)


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


class _EncoderJSON(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, Decimal):
            return str(o)
        return super().default(o)


def _coloane_tabel(conexiune, tabel):
    """Interogheaza numele coloanelor, cu embedding castat explicit la text
    (pgvector nu are un decoder implicit in psycopg2 - il pastram ca text,
    suficient pentru un restore manual ulterior prin INSERT ... ::vector)."""
    cursor = conexiune.cursor()
    try:
        cursor.execute(
            """
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (tabel,),
        )
        return cursor.fetchall()
    finally:
        cursor.close()


def backup_tabel(conexiune, tabel):
    """Intoarce (nume_coloane, randuri) pentru un tabel, cu embedding ca text."""
    coloane = _coloane_tabel(conexiune, tabel)
    if not coloane:
        raise ValueError(f"tabelul public.{tabel} nu exista sau nu are coloane")

    selectii = [
        f'"{nume}"::text AS "{nume}"' if tip == "USER-DEFINED" else f'"{nume}"'
        for nume, tip in coloane
    ]
    nume_coloane = [nume for nume, _tip in coloane]

    cursor = conexiune.cursor()
    try:
        cursor.execute(f'SELECT {", ".join(selectii)} FROM public."{tabel}"')
        randuri = cursor.fetchall()
    finally:
        cursor.close()
    return nume_coloane, randuri


def executa_backup(conexiune, folder_destinatie, *, tabele=TABELE_DE_BACKUP):
    folder_destinatie.mkdir(parents=True, exist_ok=True)
    rezumat = {}
    for tabel in tabele:
        nume_coloane, randuri = backup_tabel(conexiune, tabel)
        cale_fisier = folder_destinatie / f"{tabel}.json"
        continut = [dict(zip(nume_coloane, rand)) for rand in randuri]
        cale_fisier.write_text(
            json.dumps(continut, cls=_EncoderJSON, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        rezumat[tabel] = len(continut)
    return rezumat


def main():
    parser = argparse.ArgumentParser(
        description="Backup read-only al tabelelor Supabase, ca JSON local"
    )
    parser.add_argument(
        "--destinatie", type=Path, default=None,
        help="folder de destinatie (implicit: backups/<timestamp-UTC>/)",
    )
    args = parser.parse_args()

    load_dotenv(ROOT_PROIECT / ".env")
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destinatie = args.destinatie or (FOLDER_BACKUPS / timestamp)

    conexiune = conecteaza_baza_de_date()
    try:
        rezumat = executa_backup(conexiune, destinatie)
    finally:
        conexiune.close()

    print(f"Backup salvat in: {destinatie}")
    for tabel, numar_randuri in rezumat.items():
        print(f"  {tabel}: {numar_randuri} randuri")


if __name__ == "__main__":
    main()
