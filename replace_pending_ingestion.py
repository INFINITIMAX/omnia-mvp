"""Înlocuire controlată, doar pentru un document indexed_pending_validation existent."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Callable, Sequence
import manual_ingestion_import as base
from procesare_documente import extrage_text
from manual_ingestion_preflight import _creeaza_chunkuri_locale

_DELETE_CHUNKS_SQL = "DELETE FROM public.documente_chunks WHERE document_id = %s"
_PENDING_IDENTITY_SQL = """
SELECT document_id, source_key, cod_oficial, status FROM public.documente
WHERE document_id = %s AND source_key = %s AND cod_oficial = %s FOR UPDATE
"""


def replace_pending_document(cale_pdf: Path, cale_raport: Path, cale_metadata: Path, *, commit: bool = False,
    extract_pdf: Callable[[Path], tuple[str, int]] = extrage_text,
    create_chunks: Callable[[str], Sequence[object]] = _creeaza_chunkuri_locale,
    connection_factory: Callable[[], object] = base._conexiune_implicita,
    voyage_client_factory: Callable[[], object] = base._client_voyage_implicit) -> dict[str, object]:
    """Dry-run implicit; commit înlocuiește atomic numai chunk-urile unui pending identic."""
    pdf = base._valideaza_cale_pdf(Path(cale_pdf))
    report = base._citeste_json(base._valideaza_cale_raport(Path(cale_raport), token="invalid_report"), "invalid_report")
    metadata = base._metadata_valida(base._citeste_json(base._valideaza_cale_raport(Path(cale_metadata), token="invalid_metadata"), "invalid_metadata"))
    sha = base._hash_sha256(pdf)
    base._valideaza_report(report, metadata, sha)
    try:
        text, pages = extract_pdf(pdf)
        chunks = base._valideaza_chunkuri(list(create_chunks(text)))
    except Exception as error:
        raise base.ImportError("invalid_chunks") from error
    if base._hash_sha256(pdf) != sha:
        raise base.ImportError("unstable_pdf")
    if pages != report["page_count"] or len(text) != report["character_count"] or len(chunks) != report["chunk_count"] or not chunks:
        raise base.ImportError("preflight_mismatch")
    result = {"status":"validated", "document_id":metadata["document_id"], "chunk_count":len(chunks), "source_sha256":sha}
    if not commit:
        return result
    connection = cursor = None
    uncertain = False
    try:
        # Costul se obține înainte de DELETE; DB-ul vechi nu este atins la eșec Voyage.
        embeddings = base._cere_embeddings(voyage_client_factory(), chunks)
        if base._hash_sha256(pdf) != sha:
            raise base.ImportError("unstable_pdf")
        connection = connection_factory(); cursor = connection.cursor()
        cursor.execute("SET LOCAL statement_timeout = %s", (base._TIMEOUT_STATEMENT_MS,))
        for identity in (sha, metadata["document_id"], metadata["cod_oficial"]):
            cursor.execute(base._LOCK_SQL, (identity,))
        cursor.execute(_PENDING_IDENTITY_SQL, (metadata["document_id"], f"pdf_{sha}", metadata["cod_oficial"]))
        rows = cursor.fetchall()
        if len(rows) != 1 or rows[0][3] != base.STATUS_PENDING:
            raise base.ImportError("pending_identity_mismatch")
        cursor.execute(_DELETE_CHUNKS_SQL, (metadata["document_id"],))
        if cursor.rowcount <= 0:
            raise base.ImportError("no_existing_chunks")
        inserted = 0
        for order, (chunk, embedding) in enumerate(embeddings, 1):
            cursor.execute(base._INSERT_CHUNK_SQL, (chunk["articol"], base._normalizeaza_articol(chunk["articol"]), chunk["text"], base._hash_chunk(chunk["text"]), order, metadata["document_id"], embedding, f"pdf_{sha}"))
            if cursor.rowcount != 1:
                raise base.ImportError("insert_cardinality")
            inserted += 1
        if inserted != len(chunks):
            raise base.ImportError("insert_cardinality")
        try:
            connection.commit()
        except Exception as error:
            uncertain = True
            raise base.ImportError("commit_unknown") from error
    except base.ImportError:
        if connection is not None and not uncertain: base._inchide_sigur(connection, "rollback")
        raise
    except Exception as error:
        if connection is not None: base._inchide_sigur(connection, "rollback")
        raise base.ImportError("database_error") from error
    finally:
        base._inchide_sigur(cursor, "close"); base._inchide_sigur(connection, "close")
    result["status"] = base.STATUS_PENDING
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Înlocuiește chunk-uri doar pentru un document pending explicit.")
    parser.add_argument("--pdf", required=True); parser.add_argument("--report", required=True); parser.add_argument("--metadata", required=True); parser.add_argument("--commit", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(replace_pending_document(Path(args.pdf), Path(args.report), Path(args.metadata), commit=args.commit), ensure_ascii=True, sort_keys=True))
    except base.ImportError as error:
        print(str(error)); return 2
    return 0
if __name__ == "__main__": raise SystemExit(main())
