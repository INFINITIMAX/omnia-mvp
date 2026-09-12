"""Contract RED mock-first pentru importerul persistent, manual și insert-only.

Runtime-ul `manual_ingestion_import` nu există încă. Testele fixează API-ul
injectabil `import_document()` înainte de implementare, folosind numai fișiere
sintetice și fake-uri DB/Voyage. Niciun test nu poate contacta un serviciu real.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import pytest


TEXT_SINTETIC = "1.1.\nText sintetic suficient de lung pentru un singur fragment valid."
METADATA_VALIDA = {
    "document_id": "np010_2026",
    "cod_oficial": "NP 010-2026",
    "titlu_oficial": "Normativ sintetic pentru testare locală",
    "an": 2026,
}
CANDIDATI_VALIZI = {
    "cod_oficial": "NP 010-2026",
    "titlu_oficial": "Normativ sintetic pentru testare locală",
    "an": 2026,
}


@pytest.fixture
def importer_module():
    """RED: modulul trebuie să lipsească până când hostul înregistrează eșecul."""
    return importlib.import_module("manual_ingestion_import")


@pytest.fixture
def directoare(tmp_path, importer_module, monkeypatch):
    inbox = tmp_path / "documente_noi" / "_inbox"
    rapoarte = tmp_path / "documente_noi" / "_reports"
    inbox.mkdir(parents=True)
    rapoarte.mkdir()
    monkeypatch.setattr(importer_module, "FOLDER_INBOX", inbox)
    monkeypatch.setattr(importer_module, "FOLDER_RAPOARTE", rapoarte)
    return inbox, rapoarte


def scrie_pdf(inbox: Path, continut: bytes = b"%PDF-1.7\nsintetic") -> Path:
    cale = inbox / "document.pdf"
    cale.write_bytes(continut)
    return cale


def scrie_intrari(rapoarte: Path, pdf: Path, *, report_override=None, metadata_override=None):
    report = {
        "status": "ready_for_human_metadata",
        "source_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "page_count": 1,
        "character_count": len(TEXT_SINTETIC),
        "chunk_count": 1,
        "metadata_candidates": CANDIDATI_VALIZI,
    }
    if report_override:
        report.update(report_override)
    metadata = dict(METADATA_VALIDA)
    if metadata_override:
        metadata.update(metadata_override)
    cale_raport = rapoarte / "document.preflight.json"
    cale_metadata = rapoarte / "document.metadata.json"
    cale_raport.write_text(json.dumps(report), encoding="utf-8")
    cale_metadata.write_text(json.dumps(metadata), encoding="utf-8")
    return cale_raport, cale_metadata


def extractor_valid(_pdf: Path) -> tuple[str, int]:
    return TEXT_SINTETIC, 1


def chunker_valid(_text: str) -> list[dict[str, str]]:
    return [{"articol": "1.1.", "text": TEXT_SINTETIC}]


def validator_valid(chunkuri):
    assert chunkuri
    return chunkuri


def forbidden(*_args, **_kwargs):
    raise AssertionError("Testul nu are voie să contacteze DB, rețea sau provider real")


class CursorFake:
    def __init__(self, *, existing: bool = False):
        self.existing = existing
        self.calls = []
        self.closed = False
        self._last_sql = ""

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        self._last_sql = sql

    def fetchall(self):
        if "FROM public.documente" in self._last_sql:
            return [("existing",)] if self.existing else []
        return []

    def fetchone(self):
        return None

    def close(self):
        self.closed = True


class ConnectionFake:
    def __init__(self, cursor: CursorFake, *, commit_error: bool = False):
        self.cursor_value = cursor
        self.commit_error = commit_error
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.commits += 1
        if self.commit_error:
            raise RuntimeError("db commit failed")

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class VoyageFake:
    def __init__(self, *, failure: bool = False, wrong_cardinality: bool = False):
        self.failure = failure
        self.wrong_cardinality = wrong_cardinality
        self.calls = []

    def count_tokens(self, texts, model=None):
        self.calls.append(("count", list(texts), model))
        return 5

    def embed(self, texts, model=None, input_type=None):
        self.calls.append(("embed", list(texts), model, input_type))
        if self.failure:
            raise RuntimeError("voyage unavailable")
        embeddings = [] if self.wrong_cardinality else [[0.1, 0.2] for _ in texts]
        return type("EmbeddingResponse", (), {"embeddings": embeddings})()


def ruleaza(importer_module, pdf: Path, raport: Path, metadata: Path, *, commit=False, **overrides):
    arguments = {
        "extract_pdf": extractor_valid,
        "create_chunks": chunker_valid,
        "validate_chunks": validator_valid,
        "connection_factory": forbidden,
        "voyage_client_factory": forbidden,
    }
    arguments.update(overrides)
    return importer_module.import_document(pdf, raport, metadata, commit=commit, **arguments)


def test_dry_run_valid_revalideaza_local_si_nu_apeleaza_dependente(importer_module, directoare):
    inbox, rapoarte = directoare
    pdf = scrie_pdf(inbox)
    raport, metadata = scrie_intrari(rapoarte, pdf)

    rezultat = ruleaza(importer_module, pdf, raport, metadata)

    assert rezultat == {
        "status": "validated",
        "source_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "document_id": "np010_2026",
        "chunk_count": 1,
    }
    serializat = json.dumps(rezultat)
    assert TEXT_SINTETIC not in serializat
    assert "embedding" not in serializat
    assert "source_key" not in serializat


@pytest.mark.parametrize(
    ("report_override", "metadata_override"),
    [
        ({"source_sha256": "0" * 64}, None),
        ({"page_count": 2}, None),
        ({"character_count": len(TEXT_SINTETIC) + 1}, None),
        (None, {"cod_oficial": "NP 011-2026"}),
        (None, {"titlu_oficial": "Alt titlu"}),
        (None, {"an": 2025}),
    ],
)
def test_report_sau_metadata_nepotrivite_opresc_inainte_de_dependente(
    importer_module, directoare, report_override, metadata_override
):
    inbox, rapoarte = directoare
    pdf = scrie_pdf(inbox)
    raport, metadata = scrie_intrari(
        rapoarte, pdf, report_override=report_override, metadata_override=metadata_override
    )

    with pytest.raises(importer_module.ImportError, match="preflight_mismatch|metadata_mismatch"):
        ruleaza(importer_module, pdf, raport, metadata, commit=True)


def test_pdf_instabil_opreste_inainte_de_dependente(importer_module, directoare):
    inbox, rapoarte = directoare
    pdf = scrie_pdf(inbox)
    raport, metadata = scrie_intrari(rapoarte, pdf)

    def extractor_instabil(cale_pdf: Path):
        cale_pdf.write_bytes(b"%PDF-1.7\nmodificat")
        return TEXT_SINTETIC, 1

    with pytest.raises(importer_module.ImportError, match="unstable_pdf"):
        ruleaza(importer_module, pdf, raport, metadata, commit=True, extract_pdf=extractor_instabil)


def test_metadata_incompleta_sau_cu_tip_gresit_este_refuzata_local(importer_module, directoare):
    inbox, rapoarte = directoare
    pdf = scrie_pdf(inbox)

    for camp, valoare in (("document_id", ""), ("an", True)):
        raport, metadata = scrie_intrari(rapoarte, pdf, metadata_override={camp: valoare})
        with pytest.raises(importer_module.ImportError, match="invalid_metadata"):
            ruleaza(importer_module, pdf, raport, metadata)
        raport.unlink()
        metadata.unlink()


def test_commit_nou_foloseste_numai_insert_pending_si_sql_parametrizat(importer_module, directoare):
    inbox, rapoarte = directoare
    pdf = scrie_pdf(inbox)
    raport, metadata = scrie_intrari(rapoarte, pdf)
    cursor = CursorFake()
    connection = ConnectionFake(cursor)
    voyage = VoyageFake()

    rezultat = ruleaza(
        importer_module,
        pdf,
        raport,
        metadata,
        commit=True,
        connection_factory=lambda: connection,
        voyage_client_factory=lambda: voyage,
    )

    assert rezultat["status"] == "indexed_pending_validation"
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert cursor.closed and connection.closed
    assert any("pg_advisory_xact_lock" in sql for sql, _ in cursor.calls)
    statements = [sql.lstrip().upper() for sql, _ in cursor.calls]
    assert not any(sql.startswith(("UPDATE", "DELETE")) for sql in statements)
    assert any(sql.startswith("INSERT INTO PUBLIC.DOCUMENTE") for sql in statements)
    assert any(sql.startswith("INSERT INTO PUBLIC.DOCUMENTE_CHUNKS") for sql in statements)
    assert all(params is not None for _sql, params in cursor.calls)
    insert_document = next(params for sql, params in cursor.calls if "INSERT INTO public.documente" in sql)
    assert insert_document[-1] == "indexed_pending_validation"
    assert voyage.calls[-1][0] == "embed"


def test_identitate_existenta_nu_creeaza_client_voyage(importer_module, directoare):
    inbox, rapoarte = directoare
    pdf = scrie_pdf(inbox)
    raport, metadata = scrie_intrari(rapoarte, pdf)
    cursor = CursorFake(existing=True)
    connection = ConnectionFake(cursor)
    creatori_voyage = []

    with pytest.raises(importer_module.ImportError, match="existing_identity"):
        ruleaza(
            importer_module,
            pdf,
            raport,
            metadata,
            commit=True,
            connection_factory=lambda: connection,
            voyage_client_factory=lambda: creatori_voyage.append(object()),
        )

    assert creatori_voyage == []
    assert connection.rollbacks == 1
    assert not any("INSERT INTO" in sql for sql, _ in cursor.calls)


@pytest.mark.parametrize("failure, wrong_cardinality", [(True, False), (False, True)])
def test_voyage_esuat_sau_incomplet_face_rollback_inainte_de_insert(
    importer_module, directoare, failure, wrong_cardinality
):
    inbox, rapoarte = directoare
    pdf = scrie_pdf(inbox)
    raport, metadata = scrie_intrari(rapoarte, pdf)
    cursor = CursorFake()
    connection = ConnectionFake(cursor)
    voyage = VoyageFake(failure=failure, wrong_cardinality=wrong_cardinality)

    with pytest.raises(importer_module.ImportError, match="voyage_error"):
        ruleaza(
            importer_module,
            pdf,
            raport,
            metadata,
            commit=True,
            connection_factory=lambda: connection,
            voyage_client_factory=lambda: voyage,
        )

    assert connection.rollbacks == 1
    assert not any("INSERT INTO" in sql for sql, _ in cursor.calls)
    assert [call for call in voyage.calls if call[0] == "embed"] == [
        ("embed", [TEXT_SINTETIC], "voyage-3.5", "document")
    ]


def test_eroare_db_rollback_si_nu_publica_stare_partiala(importer_module, directoare):
    inbox, rapoarte = directoare
    pdf = scrie_pdf(inbox)
    raport, metadata = scrie_intrari(rapoarte, pdf)
    cursor = CursorFake()
    connection = ConnectionFake(cursor, commit_error=True)

    with pytest.raises(importer_module.ImportError, match="database_error"):
        ruleaza(
            importer_module,
            pdf,
            raport,
            metadata,
            commit=True,
            connection_factory=lambda: connection,
            voyage_client_factory=VoyageFake,
        )

    assert connection.commits == 1
    assert connection.rollbacks == 1
    assert connection.closed and cursor.closed


def test_cli_commit_este_opt_in_si_transmite_numai_caile_explicite(importer_module, directoare, monkeypatch):
    inbox, rapoarte = directoare
    pdf = scrie_pdf(inbox)
    raport, metadata = scrie_intrari(rapoarte, pdf)
    apeluri = []

    def import_fals(cale_pdf, cale_raport, cale_metadata, *, commit=False):
        apeluri.append((cale_pdf, cale_raport, cale_metadata, commit))
        return {"status": "validated"}

    monkeypatch.setattr(importer_module, "import_document", import_fals)

    assert importer_module.main(["--pdf", str(pdf), "--report", str(raport), "--metadata", str(metadata)]) == 0
    assert apeluri == [(pdf, raport, metadata, False)]

    assert importer_module.main(
        ["--pdf", str(pdf), "--report", str(raport), "--metadata", str(metadata), "--commit"]
    ) == 0
    assert apeluri[-1] == (pdf, raport, metadata, True)
