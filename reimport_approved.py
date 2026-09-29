"""Reimport controlat, per document, al chunk-urilor unui document `approved` cu
chunker-ul unificat R14 (`chunking_core.creeaza_chunkuri`).

Un singur document per rulare, cu poarta automată D24 (vezi `docs/DECISIONS.md`):
fără `--commit`/`--restore`, scriptul e strict dry-run (DB `readonly`, fără Voyage).
`--commit` scrie DB + Voyage numai dacă poarta trece, după un backup local al
chunk-urilor vechi. `--restore` revine dintr-un backup, fără cost Voyage și fără
poartă de acoperire (e revenire la starea anterioară, nu import nou).

Reutilizează helper-ele deja validate din `manual_ingestion_import.py` (lock
advisory, loturi embedding, hash chunk, conexiune, client Voyage cu
`timeout=30, max_retries=0`, `commit_unknown`) prin import, fără copiere.
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Mapping, Sequence

import manual_ingestion_import as base
import chunking_core
from procesare_documente import extrage_text

ROOT_PROIECT = Path(__file__).resolve().parent
FOLDER_DOCUMENTE = ROOT_PROIECT / "documente_noi"
FOLDER_RAPOARTE = ROOT_PROIECT / "documente_noi" / "_reports"
FOLDER_BACKUPS = ROOT_PROIECT / "backups"

# document_id -> source_key așteptat; `None` marchează identitatea `pdf_<sha>`,
# unde sha-ul real vine din PDF-ul dat explicit prin `--pdf` (numai np091_2003).
DOCUMENTE_APROBATE: dict[str, str | None] = {
    "i5_2022": "i5_2022_extras.txt",
    "i7_2011": "i7_2011_extras.txt",
    "i9_2022": "I9_2022_extras.txt",
    "np004_03": "np004_03_extras.txt",
    "np010_2022": "NP010_extras.txt",
    "np057_02": "NP0572002_extras.txt",
    "p118_1_2025": "P118_1_2025_extras.txt",
    "spitale_2022": "NP015_2022_extras.txt",
    "np091_2003": None,
    "p118_2_2013": "P118_2_2013_consolidat.txt",
    "p118_3_2015": "P118_3_2015_consolidat.txt",
    "np064_02": "NP064_02_extras.txt",
    "np127_2009": "NP127_2009_extras.txt",
}

# Pragurile D24, provizorii, ajustabile doar prin PR — identice cu
# PRAG_ACOPERIRE_MINIM_PER_DOCUMENT din tests/test_populare_db.py.
PRAGURI_ACOPERIRE: dict[str, float] = {
    "i5_2022": 0.97,
    "i7_2011": 0.95,
    "i9_2022": 0.96,
    "np004_03": 0.90,
    "np010_2022": 0.99,
    "np057_02": 0.87,
    "p118_1_2025": 0.99,
    "spitale_2022": 0.97,
    "np091_2003": 0.95,
    "p118_2_2013": 0.98,
    "p118_3_2015": 0.94,
    "np064_02": 0.98,
    "np127_2009": 0.93,
}

_SELECT_DOCUMENT_SQL = "SELECT document_id, source_key, status FROM public.documente WHERE document_id = %s"
_SELECT_DOCUMENT_FOR_UPDATE_SQL = (
    "SELECT document_id, source_key, status FROM public.documente WHERE document_id = %s FOR UPDATE"
)
_NUMARA_CHUNKURI_SQL = "SELECT count(*) FROM public.documente_chunks WHERE document_id = %s"
_BACKUP_CHUNKURI_SQL = """
    SELECT articol, articol_normalizat, text, content_hash, chunk_order,
           document_id, embedding::text, sursa
    FROM public.documente_chunks
    WHERE document_id = %s
    ORDER BY chunk_order
"""
_DELETE_CHUNKS_SQL = "DELETE FROM public.documente_chunks WHERE document_id = %s"
_INSERT_CHUNK_RESTORE_SQL = """
    INSERT INTO public.documente_chunks (
        articol, articol_normalizat, text, content_hash, chunk_order,
        document_id, embedding, sursa
    ) VALUES (%s, %s, %s, %s, %s, %s, %s::vector, %s)
"""


class ReimportError(ValueError):
    """Eroare controlată: mesajul este un token local, fără text normativ ori secrete."""


def _un_singur_tip_de_eroare(functie):
    """Runda 3: la granița funcțiilor publice, orice `base.ImportError` scăpat dintr-un
    helper importat (ex. `_cale_directa`, `_hash_sha256`) devine `ReimportError` cu
    exact același token, ca apelanții (inclusiv `main()`) să prindă un singur tip."""

    @functools.wraps(functie)
    def wrapper(*args, **kwargs):
        try:
            return functie(*args, **kwargs)
        except ReimportError:
            raise
        except base.ImportError as error:
            raise ReimportError(str(error)) from error

    return wrapper


def _conexiune_readonly() -> object:
    """Conexiune numai-citire pentru dry-run și pentru pașii de verificare/backup ai commit-ului."""
    try:
        from dotenv import load_dotenv
        import psycopg2

        load_dotenv(ROOT_PROIECT / ".env")
        conexiune = psycopg2.connect(
            host=base._required_environment("DB_HOST"),
            dbname=base._required_environment("DB_NAME"),
            user=base._required_environment("DB_USER"),
            password=base._required_environment("DB_PASSWORD"),
            port=base._required_environment("DB_PORT"),
            sslmode="require",
            connect_timeout=base._TIMEOUT_CONECTARE_SECUNDE,
        )
        conexiune.set_session(readonly=True, autocommit=False)
        return conexiune
    except (ReimportError, base.ImportError) as error:
        raise ReimportError(str(error)) from error
    except Exception as error:
        raise ReimportError("database_error") from error


def _scrie_json_atomic(cale: Path, continut: Mapping[str, object]) -> None:
    cale.parent.mkdir(parents=True, exist_ok=True)
    temporar = cale.with_name(f".{cale.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporar.open("w", encoding="utf-8", newline="\n") as fisier:
            json.dump(continut, fisier, ensure_ascii=False, indent=2, sort_keys=True)
            fisier.write("\n")
            fisier.flush()
            os.fsync(fisier.fileno())
        os.replace(temporar, cale)
    except OSError as error:
        raise ReimportError("report_write_failed") from error
    finally:
        temporar.unlink(missing_ok=True)


def _obtine_text(document_id: str, cale_pdf_arg: str | None, extract_pdf: Callable[[Path], tuple[str, int]]) -> tuple[str, str]:
    """Întoarce (text, source_key așteptat) pentru documentul cerut."""
    sursa_asteptata = DOCUMENTE_APROBATE[document_id]
    if sursa_asteptata is None:
        if not cale_pdf_arg:
            raise ReimportError("missing_pdf_argument")
        pdf = base._cale_directa(Path(cale_pdf_arg), base.FOLDER_INBOX, "outside_inbox", exista=True)
        if pdf.suffix.casefold() != ".pdf":
            raise ReimportError("invalid_pdf_path")
        sha_initial = base._hash_sha256(pdf)
        try:
            text, pagini = extract_pdf(pdf)
        except Exception as error:
            raise ReimportError("invalid_extraction") from error
        if (
            not isinstance(text, str)
            or not text.strip()
            or isinstance(pagini, bool)
            or not isinstance(pagini, int)
            or pagini <= 0
        ):
            raise ReimportError("invalid_extraction")
        if base._hash_sha256(pdf) != sha_initial:
            raise ReimportError("unstable_pdf")
        return text, f"pdf_{sha_initial}"

    cale_text = FOLDER_DOCUMENTE / document_id / "extracted.txt"
    if not cale_text.is_file():
        raise ReimportError("missing_text_source")
    text = cale_text.read_text(encoding="utf-8")
    if not text.strip():
        raise ReimportError("empty_text_source")
    return text, sursa_asteptata


def _construieste_chunkuri_noi(text: str, create_chunks: Callable[[str], Sequence[object]]) -> list[dict[str, str]]:
    """Construiește chunk-urile noi și le validează cu exact contractul importerului."""
    try:
        chunkuri = list(create_chunks(text))
        return list(base._valideaza_chunkuri(chunkuri))
    except ReimportError:
        raise
    except Exception as error:
        raise ReimportError("invalid_chunks") from error


def _verifica_document(cursor: object, document_id: str, sursa_asteptata: str) -> int:
    """Verifică identitatea/statusul documentului și întoarce numărul curent de chunk-uri."""
    cursor.execute(_SELECT_DOCUMENT_SQL, (document_id,))
    randuri = cursor.fetchall()
    if len(randuri) != 1:
        raise ReimportError("unknown_document")
    _document_id, sursa_db, status_db = randuri[0]
    if status_db != "approved":
        raise ReimportError("not_approved")
    if sursa_db != sursa_asteptata:
        raise ReimportError("source_key_mismatch")
    cursor.execute(_NUMARA_CHUNKURI_SQL, (document_id,))
    return cursor.fetchone()[0]


def _contine_antet_mo(text: str) -> bool:
    return any(chunking_core.PATTERN_ANTET_MO.match(linie) for linie in text.split("\n"))


def _p118_gate_trece(text: str, chunkuri: Sequence[Mapping[str, str]]) -> bool:
    """Toate articolele „Art. N.N…” urmate de majusculă trebuie să apară ca articol de bază."""
    articole_asteptate = {
        potrivire.group(1) for potrivire in chunking_core.PATTERN_ARTICOL_ART.finditer("\n" + text)
    }
    articole_din_chunkuri = {chunk["articol"].split("(")[0] for chunk in chunkuri}
    return not (articole_asteptate - articole_din_chunkuri)


def _evalueaza_poarta(document_id: str, text: str, chunkuri: Sequence[Mapping[str, str]]) -> dict[str, object]:
    """Poarta automată D24: toate criteriile trebuie să treacă pentru `trece = True`."""
    motive: list[str] = []
    acoperire = chunking_core.acoperire_text_brut(text, chunkuri)
    prag = PRAGURI_ACOPERIRE[document_id]
    if acoperire < prag:
        motive.append(f"acoperire {acoperire:.4f} sub pragul {prag}")

    chunkuri_cu_antet = [chunk for chunk in chunkuri if _contine_antet_mo(chunk["text"])]
    if chunkuri_cu_antet:
        motive.append(f"{len(chunkuri_cu_antet)} chunk-uri conțin antetul de pagină MO")

    if len(chunkuri) <= 0:
        motive.append("zero chunk-uri noi")

    if document_id == "p118_1_2025" and not _p118_gate_trece(text, chunkuri):
        motive.append("cel puțin un articol „Art. N.N…” lipsește ca articol propriu")

    return {
        "trece": not motive,
        "motive": motive,
        "acoperire": acoperire,
        "prag_acoperire": prag,
    }


def _exemple_scurte(chunkuri: Sequence[Mapping[str, str]], numar: int = 3) -> list[dict[str, str]]:
    return [{"articol": chunk["articol"], "extras": chunk["text"][:120]} for chunk in chunkuri[:numar]]


def _evalueaza(
    document_id: str,
    cale_pdf_arg: str | None,
    connection_factory: Callable[[], object],
    extract_pdf: Callable[[Path], tuple[str, int]],
    create_chunks: Callable[[str], Sequence[object]],
) -> tuple[str, str, list[dict[str, str]], int, dict[str, object], dict[str, object]]:
    """Pașii comuni dry-run/commit: text, chunk-uri noi, verificare DB readonly, poartă, raport."""
    if document_id not in DOCUMENTE_APROBATE:
        raise ReimportError("unknown_document")

    text, sursa = _obtine_text(document_id, cale_pdf_arg, extract_pdf)
    chunkuri_noi = _construieste_chunkuri_noi(text, create_chunks)

    connection = None
    try:
        connection = connection_factory()
        cursor = connection.cursor()
        numar_vechi = _verifica_document(cursor, document_id, sursa)
    except (ReimportError, base.ImportError) as error:
        raise ReimportError(str(error)) from error
    except Exception as error:
        raise ReimportError("database_error") from error
    finally:
        if connection is not None:
            base._inchide_sigur(connection, "rollback")
            base._inchide_sigur(connection, "close")

    poarta = _evalueaza_poarta(document_id, text, chunkuri_noi)
    raport = {
        "document_id": document_id,
        "source_key": sursa,
        "chunk_count_vechi": numar_vechi,
        "chunk_count_nou": len(chunkuri_noi),
        "acoperire": poarta["acoperire"],
        "prag_acoperire": poarta["prag_acoperire"],
        "poarta_trece": poarta["trece"],
        "motive_poarta": poarta["motive"],
        "statistici_chunking": chunking_core.ultimele_statistici(),
        "exemple": _exemple_scurte(chunkuri_noi),
        "generat_utc": datetime.now(UTC).isoformat(),
    }
    _scrie_json_atomic(FOLDER_RAPOARTE / f"{document_id}.reimport.json", raport)
    return text, sursa, chunkuri_noi, numar_vechi, poarta, raport


@_un_singur_tip_de_eroare
def dry_run(
    document_id: str,
    cale_pdf_arg: str | None = None,
    *,
    connection_factory: Callable[[], object] = _conexiune_readonly,
    extract_pdf: Callable[[Path], tuple[str, int]] = extrage_text,
    create_chunks: Callable[[str], Sequence[object]] = chunking_core.creeaza_chunkuri,
) -> dict[str, object]:
    """DB `readonly`, fără Voyage, fără scriere; scrie doar raportul JSON local."""
    _text, _sursa, _chunkuri, _numar_vechi, _poarta, raport = _evalueaza(
        document_id, cale_pdf_arg, connection_factory, extract_pdf, create_chunks
    )
    return raport


def _backup_chunkuri_curente(
    document_id: str, sursa: str, connection_factory: Callable[[], object]
) -> Path:
    """Backup read-only al chunk-urilor curente, scris atomic, înainte de Voyage/scriere."""
    connection = None
    try:
        connection = connection_factory()
        cursor = connection.cursor()
        cursor.execute(_BACKUP_CHUNKURI_SQL, (document_id,))
        randuri = cursor.fetchall()
    except (ReimportError, base.ImportError) as error:
        raise ReimportError(str(error)) from error
    except Exception as error:
        raise ReimportError("database_error") from error
    finally:
        if connection is not None:
            base._inchide_sigur(connection, "rollback")
            base._inchide_sigur(connection, "close")

    coloane = ("articol", "articol_normalizat", "text", "content_hash", "chunk_order", "document_id", "embedding", "sursa")
    continut = {
        "document_id": document_id,
        "source_key": sursa,
        "backup_utc": datetime.now(UTC).isoformat(),
        "chunkuri": [dict(zip(coloane, rand)) for rand in randuri],
    }
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    cale_backup = FOLDER_BACKUPS / f"reimport-{document_id}-{timestamp}.json"
    _scrie_json_atomic(cale_backup, continut)
    return cale_backup


@_un_singur_tip_de_eroare
def commit_document(
    document_id: str,
    cale_pdf_arg: str | None = None,
    *,
    readonly_connection_factory: Callable[[], object] = _conexiune_readonly,
    write_connection_factory: Callable[[], object] = base._conexiune_implicita,
    voyage_client_factory: Callable[[], object] = base._client_voyage_implicit,
    extract_pdf: Callable[[Path], tuple[str, int]] = extrage_text,
    create_chunks: Callable[[str], Sequence[object]] = chunking_core.creeaza_chunkuri,
) -> dict[str, object]:
    """Aceiași pași ca `dry_run`; dacă poarta trece: backup, embeddings, o singură tranzacție."""
    _text, sursa, chunkuri_noi, numar_vechi, poarta, raport = _evalueaza(
        document_id, cale_pdf_arg, readonly_connection_factory, extract_pdf, create_chunks
    )
    if not poarta["trece"]:
        raport["status"] = "poarta_respinsa"
        return raport

    cale_backup = _backup_chunkuri_curente(document_id, sursa, readonly_connection_factory)
    try:
        embeddings = base._cere_embeddings(voyage_client_factory(), chunkuri_noi)
    except base.ImportError as error:
        raise ReimportError(str(error)) from error

    connection = cursor = None
    commit_incert = False
    try:
        connection = write_connection_factory()
        cursor = connection.cursor()
        cursor.execute("SET LOCAL statement_timeout = %s", (base._TIMEOUT_STATEMENT_MS,))
        cursor.execute(base._LOCK_SQL, (document_id,))
        cursor.execute(_SELECT_DOCUMENT_FOR_UPDATE_SQL, (document_id,))
        randuri = cursor.fetchall()
        if len(randuri) != 1:
            raise ReimportError("unknown_document")
        _document_id, sursa_db, status_db = randuri[0]
        if status_db != "approved" or sursa_db != sursa:
            raise ReimportError("concurrent_change")
        cursor.execute(_NUMARA_CHUNKURI_SQL, (document_id,))
        numar_curent = cursor.fetchone()[0]
        if numar_curent != numar_vechi:
            raise ReimportError("concurrent_change")

        cursor.execute(_DELETE_CHUNKS_SQL, (document_id,))
        for ordine, (chunk, embedding) in enumerate(embeddings, start=1):
            cursor.execute(
                base._INSERT_CHUNK_SQL,
                (
                    chunk["articol"],
                    base._normalizeaza_articol(chunk["articol"]),
                    chunk["text"],
                    base._hash_chunk(chunk["text"]),
                    ordine,
                    document_id,
                    embedding,
                    sursa,
                ),
            )
        try:
            connection.commit()
        except Exception as error:
            # După un eșec de commit nu știm dacă serverul a persistat deja
            # tranzacția; un rollback ulterior ar masca această stare incertă.
            commit_incert = True
            raise ReimportError("commit_unknown") from error
    except (ReimportError, base.ImportError) as error:
        if connection is not None and not commit_incert:
            base._inchide_sigur(connection, "rollback")
        raise ReimportError(str(error)) from error
    except Exception as error:
        if connection is not None:
            base._inchide_sigur(connection, "rollback")
        raise ReimportError("database_error") from error
    finally:
        base._inchide_sigur(cursor, "close")
        base._inchide_sigur(connection, "close")

    raport["status"] = "reimportat"
    raport["backup"] = str(cale_backup)
    raport["chunk_count_inserat"] = len(embeddings)
    return raport


@_un_singur_tip_de_eroare
def restore_from_backup(
    document_id: str,
    cale_backup_arg: str,
    *,
    write_connection_factory: Callable[[], object] = base._conexiune_implicita,
) -> dict[str, object]:
    """Revenire dintr-un backup local, fără Voyage și fără poarta de acoperire."""
    cale_backup = base._cale_directa(Path(cale_backup_arg), FOLDER_BACKUPS, "outside_backups", exista=True)
    try:
        continut = json.loads(cale_backup.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReimportError("invalid_backup") from error

    if not isinstance(continut, Mapping) or continut.get("document_id") != document_id:
        raise ReimportError("backup_document_mismatch")
    sursa = continut.get("source_key")
    chunkuri_backup = continut.get("chunkuri")
    if not isinstance(sursa, str) or not sursa.strip() or not isinstance(chunkuri_backup, list) or not chunkuri_backup:
        raise ReimportError("invalid_backup")
    for chunk in chunkuri_backup:
        if not isinstance(chunk, Mapping) or chunk.get("document_id") != document_id or chunk.get("sursa") != sursa:
            raise ReimportError("invalid_backup")
        for camp in ("articol", "articol_normalizat", "text", "content_hash", "chunk_order", "embedding"):
            if camp not in chunk:
                raise ReimportError("invalid_backup")

    connection = cursor = None
    commit_incert = False
    try:
        connection = write_connection_factory()
        cursor = connection.cursor()
        cursor.execute("SET LOCAL statement_timeout = %s", (base._TIMEOUT_STATEMENT_MS,))
        cursor.execute(base._LOCK_SQL, (document_id,))
        cursor.execute(_SELECT_DOCUMENT_FOR_UPDATE_SQL, (document_id,))
        randuri = cursor.fetchall()
        if len(randuri) != 1:
            raise ReimportError("unknown_document")
        _document_id, sursa_db, status_db = randuri[0]
        if status_db != "approved" or sursa_db != sursa:
            raise ReimportError("restore_identity_mismatch")

        cursor.execute(_DELETE_CHUNKS_SQL, (document_id,))
        for chunk in chunkuri_backup:
            cursor.execute(
                _INSERT_CHUNK_RESTORE_SQL,
                (
                    chunk["articol"],
                    chunk["articol_normalizat"],
                    chunk["text"],
                    chunk["content_hash"],
                    chunk["chunk_order"],
                    document_id,
                    chunk["embedding"],
                    sursa,
                ),
            )
        try:
            connection.commit()
        except Exception as error:
            commit_incert = True
            raise ReimportError("commit_unknown") from error
    except (ReimportError, base.ImportError) as error:
        if connection is not None and not commit_incert:
            base._inchide_sigur(connection, "rollback")
        raise ReimportError(str(error)) from error
    except Exception as error:
        if connection is not None:
            base._inchide_sigur(connection, "rollback")
        raise ReimportError("database_error") from error
    finally:
        base._inchide_sigur(cursor, "close")
        base._inchide_sigur(connection, "close")

    return {
        "document_id": document_id,
        "source_key": sursa,
        "status": "restored",
        "chunk_count": len(chunkuri_backup),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reimport controlat, per document approved, cu chunker-ul R14 și poarta automată D24."
    )
    parser.add_argument("--document", required=True, help="document_id approved, din lista aprobată R15")
    parser.add_argument("--pdf", help="PDF direct din documente_noi/_inbox, obligatoriu doar pentru np091_2003")
    mod = parser.add_mutually_exclusive_group()
    mod.add_argument("--commit", action="store_true", help="scrie DB + Voyage numai dacă poarta automată trece")
    mod.add_argument("--restore", metavar="FISIER_BACKUP", help="revenire dintr-un backup direct din backups/")
    arguments = parser.parse_args(argv)

    try:
        if arguments.restore:
            rezultat = restore_from_backup(arguments.document, arguments.restore)
        elif arguments.commit:
            rezultat = commit_document(arguments.document, arguments.pdf)
        else:
            rezultat = dry_run(arguments.document, arguments.pdf)
    except ReimportError as error:
        print(str(error), file=sys.stderr)
        return 2

    print(json.dumps(rezultat, ensure_ascii=True, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
