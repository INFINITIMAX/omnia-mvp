"""Importer manual, punctual și insert-only pentru un PDF deja verificat local.

Fără ``--commit``, modulul face numai validări locale. Cu ``--commit``, el
poate persista un document nou în ``indexed_pending_validation``; nu actualizează,
nu șterge și nu aprobă documente. Rularea reală rămâne o acțiune separată,
aprobată explicit de Lucian.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Callable, Mapping, Sequence

from manual_ingestion_preflight import (
    FOLDER_INBOX,
    FOLDER_RAPOARTE,
    ROOT_PROIECT,
    _creeaza_chunkuri_locale,
    _hash_sha256,
    _valideaza_chunkuri_locale,
)
from procesare_documente import extrage_text


STATUS_PENDING = "indexed_pending_validation"
MODEL_EMBEDDING = "voyage-3.5"
_TIMEOUT_CONECTARE_SECUNDE = 10
_TIMEOUT_STATEMENT_MS = 30_000
_MAX_TEXTE_LOT = 1000
_MAX_TOKENI_LOT = 320_000
_PATTERN_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PATTERN_ARTICOL_SPATII = re.compile(r"[ \t\n\r\f\v\u00a0\u202f]+")
_PATTERN_ARTICOL = re.compile(r"^[a-z0-9().-]+$")

_LOCK_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))"
_IDENTITATE_SQL = """
    SELECT document_id
    FROM public.documente
    WHERE document_id = %s OR source_key = %s OR cod_oficial = %s
    FOR UPDATE
"""
_INSERT_DOCUMENT_SQL = """
    INSERT INTO public.documente (
        document_id, source_key, cod_oficial, titlu_oficial, an, status
    ) VALUES (%s, %s, %s, %s, %s, %s)
"""
_INSERT_CHUNK_SQL = """
    INSERT INTO public.documente_chunks (
        articol, articol_normalizat, text, content_hash, chunk_order,
        document_id, embedding, sursa
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""


class ImportError(ValueError):
    """Eroare controlată: mesajul este un token local, fără text normativ ori secrete."""


def _cale_directa(cale: Path, director: Path, token: str, *, exista: bool) -> Path:
    """Acceptă numai fișiere directe din directorul local aprobat."""
    try:
        director_rezolvat = director.resolve()
        cale_rezolvata = cale.resolve()
    except OSError as error:
        raise ImportError(token) from error
    if cale_rezolvata.parent != director_rezolvat:
        raise ImportError(token)
    if exista and not cale_rezolvata.is_file():
        raise ImportError(token)
    return cale_rezolvata


def _valideaza_cale_pdf(cale: Path) -> Path:
    cale = _cale_directa(cale, FOLDER_INBOX, "outside_inbox", exista=True)
    if cale.suffix.casefold() != ".pdf":
        raise ImportError("invalid_pdf_path")
    return cale


def _valideaza_cale_raport(cale: Path, *, token: str) -> Path:
    return _cale_directa(cale, FOLDER_RAPOARTE, token, exista=True)


def _citeste_json(cale: Path, token: str) -> Mapping[str, object]:
    try:
        continut = json.loads(cale.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ImportError(token) from error
    if not isinstance(continut, dict):
        raise ImportError(token)
    return continut


def _metadata_valida(metadata: Mapping[str, object]) -> dict[str, object]:
    """Cere cele patru câmpuri aprobate, fără a accepta identitatea sursei de la operator."""
    document_id = metadata.get("document_id")
    cod = metadata.get("cod_oficial")
    titlu = metadata.get("titlu_oficial")
    an = metadata.get("an")
    if (
        not isinstance(document_id, str)
        or not document_id.strip()
        or not isinstance(cod, str)
        or not cod.strip()
        or not isinstance(titlu, str)
        or not titlu.strip()
        or isinstance(an, bool)
        or not isinstance(an, int)
        or not 1800 <= an <= 9999
    ):
        raise ImportError("invalid_metadata")
    return {
        "document_id": document_id.strip(),
        "cod_oficial": cod.strip(),
        "titlu_oficial": titlu.strip(),
        "an": an,
    }


def _valideaza_report(report: Mapping[str, object], metadata: Mapping[str, object], source_sha256: str) -> None:
    """Leagă importul de un preflight complet și de identitatea verificată manual."""
    if report.get("status") != "ready_for_human_metadata":
        raise ImportError("preflight_mismatch")
    sha_report = report.get("source_sha256")
    if not isinstance(sha_report, str) or not _PATTERN_SHA256.fullmatch(sha_report) or sha_report != source_sha256:
        raise ImportError("preflight_mismatch")
    candidati = report.get("metadata_candidates")
    if not isinstance(candidati, Mapping):
        raise ImportError("preflight_mismatch")
    for camp in ("cod_oficial", "titlu_oficial", "an"):
        if candidati.get(camp) != metadata[camp]:
            raise ImportError("metadata_mismatch")
    for camp, minimum in (("page_count", 1), ("character_count", 1), ("chunk_count", 1)):
        valoare = report.get(camp)
        if isinstance(valoare, bool) or not isinstance(valoare, int) or valoare < minimum:
            raise ImportError("preflight_mismatch")


def _normalizeaza_articol(articol: object) -> str:
    if not isinstance(articol, str):
        raise ValueError("invalid article")
    normalizat = _PATTERN_ARTICOL_SPATII.sub("", articol).lower().rstrip(".")
    if not _PATTERN_ARTICOL.fullmatch(normalizat):
        raise ValueError("invalid article")
    return normalizat


def _hash_chunk(text: object) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("invalid chunk")
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _valideaza_chunkuri(chunkuri: Sequence[object]) -> list[dict[str, str]]:
    """Păstrează numai contractul local; chunk-urile nu sunt scrise în rezultat."""
    validate = _valideaza_chunkuri_locale(chunkuri)
    rezultat: list[dict[str, str]] = []
    for chunk in validate:
        if not isinstance(chunk, Mapping):
            raise ValueError("invalid chunk")
        articol = chunk.get("articol")
        text = chunk.get("text")
        _normalizeaza_articol(articol)
        _hash_chunk(text)
        rezultat.append({"articol": articol, "text": text})
    return rezultat


def _loturi_embedding(chunkuri: Sequence[dict[str, str]], client: object) -> list[list[dict[str, str]]]:
    """Construiește loturi consecutive, verificând simultan limitele de text și tokeni."""
    loturi: list[list[dict[str, str]]] = []
    lot: list[dict[str, str]] = []
    tokeni_lot = 0
    for chunk in chunkuri:
        try:
            tokeni = int(client.count_tokens([chunk["text"]], model=MODEL_EMBEDDING))
        except Exception as error:
            raise ImportError("voyage_error") from error
        if tokeni <= 0 or tokeni > _MAX_TOKENI_LOT:
            raise ImportError("voyage_error")
        if lot and (len(lot) >= _MAX_TEXTE_LOT or tokeni_lot + tokeni > _MAX_TOKENI_LOT):
            loturi.append(lot)
            lot = []
            tokeni_lot = 0
        lot.append(chunk)
        tokeni_lot += tokeni
    if lot:
        loturi.append(lot)
    if not loturi:
        raise ImportError("voyage_error")
    return loturi


def _cere_embeddings(client: object, chunkuri: list[dict[str, str]]) -> list[tuple[dict[str, str], Sequence[float]]]:
    """Cere fiecare lot o singură dată; nu reîncearcă automat un apel plătit."""
    rezultat: list[tuple[dict[str, str], Sequence[float]]] = []
    for lot in _loturi_embedding(chunkuri, client):
        texte = [chunk["text"] for chunk in lot]
        try:
            raspuns = client.embed(texte, model=MODEL_EMBEDDING, input_type="document")
            embeddings = raspuns.embeddings
        except Exception as error:
            raise ImportError("voyage_error") from error
        if not isinstance(embeddings, Sequence) or isinstance(embeddings, (str, bytes)) or len(embeddings) != len(lot):
            raise ImportError("voyage_error")
        rezultat.extend(zip(lot, embeddings))
    return rezultat


def _required_environment(name: str) -> str:
    valoare = os.getenv(name)
    if not valoare:
        raise ImportError("configuration_error")
    return valoare


def _conexiune_implicita() -> object:
    """Încarcă configurarea și deschide DB numai pe calea explicită ``--commit``."""
    try:
        from dotenv import load_dotenv
        import psycopg2

        load_dotenv(ROOT_PROIECT / ".env")
        return psycopg2.connect(
            host=_required_environment("DB_HOST"),
            dbname=_required_environment("DB_NAME"),
            user=_required_environment("DB_USER"),
            password=_required_environment("DB_PASSWORD"),
            port=_required_environment("DB_PORT"),
            sslmode="require",
            connect_timeout=_TIMEOUT_CONECTARE_SECUNDE,
        )
    except ImportError:
        raise
    except Exception as error:
        raise ImportError("database_error") from error


def _client_voyage_implicit() -> object:
    """Construiește clientul fără retry automat, numai după verificarea identității DB."""
    try:
        import voyageai

        return voyageai.Client(
            api_key=_required_environment("VOYAGE_API_KEY"), timeout=30, max_retries=0
        )
    except ImportError:
        raise
    except Exception as error:
        raise ImportError("voyage_error") from error


def _inchide_sigur(obiect: object | None, metoda: str) -> None:
    if obiect is None:
        return
    try:
        getattr(obiect, metoda)()
    except Exception:
        pass


def import_document(
    cale_pdf: Path,
    cale_raport: Path,
    cale_metadata: Path,
    *,
    commit: bool = False,
    extract_pdf: Callable[[Path], tuple[str, int]] = extrage_text,
    create_chunks: Callable[[str], Sequence[object]] = _creeaza_chunkuri_locale,
    validate_chunks: Callable[[Sequence[object]], Sequence[object]] = _valideaza_chunkuri,
    connection_factory: Callable[[], object] = _conexiune_implicita,
    voyage_client_factory: Callable[[], object] = _client_voyage_implicit,
) -> dict[str, object]:
    """Validează sau importă un document nou, strict după aprobarea explicită a operatorului.

    În dry-run nu este creată nicio dependență externă. În commit, o eroare
    Voyage poate avea cost deja consumat, însă documentul nu este inserat până
    când toate embedding-urile sunt disponibile și verificarea finală SHA trece.
    """
    pdf = _valideaza_cale_pdf(Path(cale_pdf))
    raport = _citeste_json(_valideaza_cale_raport(Path(cale_raport), token="invalid_report"), "invalid_report")
    metadata = _metadata_valida(
        _citeste_json(_valideaza_cale_raport(Path(cale_metadata), token="invalid_metadata"), "invalid_metadata")
    )
    sha_initial = _hash_sha256(pdf)
    _valideaza_report(raport, metadata, sha_initial)

    try:
        text, pagini = extract_pdf(pdf)
        if not isinstance(text, str) or not text.strip() or isinstance(pagini, bool) or not isinstance(pagini, int) or pagini <= 0:
            raise ValueError("invalid extraction")
        chunkuri = list(validate_chunks(create_chunks(text)))
        chunkuri = _valideaza_chunkuri(chunkuri)
    except ImportError:
        raise
    except Exception as error:
        if _hash_sha256(pdf) != sha_initial:
            raise ImportError("unstable_pdf") from error
        raise ImportError("invalid_chunks") from error

    if _hash_sha256(pdf) != sha_initial:
        raise ImportError("unstable_pdf")
    if (
        pagini != raport["page_count"]
        or len(text) != raport["character_count"]
        or len(chunkuri) != raport["chunk_count"]
    ):
        raise ImportError("preflight_mismatch")

    rezultat = {
        "status": "validated",
        "source_sha256": sha_initial,
        "document_id": metadata["document_id"],
        "chunk_count": len(chunkuri),
    }
    if not commit:
        return rezultat

    source_key = f"pdf_{sha_initial}"
    connection: object | None = None
    cursor: object | None = None
    try:
        connection = connection_factory()
        cursor = connection.cursor()
        cursor.execute("SET LOCAL statement_timeout = %s", (_TIMEOUT_STATEMENT_MS,))
        for identitate in (sha_initial, metadata["document_id"], metadata["cod_oficial"]):
            cursor.execute(_LOCK_SQL, (identitate,))
        cursor.execute(
            _IDENTITATE_SQL,
            (metadata["document_id"], source_key, metadata["cod_oficial"]),
        )
        if cursor.fetchall():
            raise ImportError("existing_identity")

        try:
            client = voyage_client_factory()
            embeddings = _cere_embeddings(client, chunkuri)
        except ImportError:
            raise
        except Exception as error:
            raise ImportError("voyage_error") from error

        if _hash_sha256(pdf) != sha_initial:
            raise ImportError("unstable_pdf")
        cursor.execute(
            _INSERT_DOCUMENT_SQL,
            (
                metadata["document_id"],
                source_key,
                metadata["cod_oficial"],
                metadata["titlu_oficial"],
                metadata["an"],
                STATUS_PENDING,
            ),
        )
        for ordine, (chunk, embedding) in enumerate(embeddings, start=1):
            cursor.execute(
                _INSERT_CHUNK_SQL,
                (
                    chunk["articol"],
                    _normalizeaza_articol(chunk["articol"]),
                    chunk["text"],
                    _hash_chunk(chunk["text"]),
                    ordine,
                    metadata["document_id"],
                    embedding,
                    source_key,
                ),
            )
        connection.commit()
    except ImportError:
        if connection is not None:
            _inchide_sigur(connection, "rollback")
        raise
    except Exception as error:
        if connection is not None:
            _inchide_sigur(connection, "rollback")
        raise ImportError("database_error") from error
    finally:
        _inchide_sigur(cursor, "close")
        _inchide_sigur(connection, "close")

    rezultat["status"] = STATUS_PENDING
    return rezultat


def main(argv: Sequence[str] | None = None) -> int:
    """Primește toate căile explicit; ``--commit`` este singurul opt-in pentru persistență."""
    parser = argparse.ArgumentParser(description="Validează sau importă manual un PDF nou NormativAI.")
    parser.add_argument("--pdf", required=True, help="PDF direct din documente_noi/_inbox")
    parser.add_argument("--report", required=True, help="Raport preflight direct din documente_noi/_reports")
    parser.add_argument("--metadata", required=True, help="Metadata locală direct din documente_noi/_reports")
    parser.add_argument("--commit", action="store_true", help="Permite DB + Voyage după aprobare explicită")
    arguments = parser.parse_args(argv)
    try:
        rezultat = import_document(
            Path(arguments.pdf),
            Path(arguments.report),
            Path(arguments.metadata),
            commit=arguments.commit,
        )
    except ImportError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(rezultat, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
