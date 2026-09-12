"""Contract RED pentru preflight-ul local și fără cost al unui singur PDF.

Testele folosesc numai PDF-uri sintetice de câțiva octeți. Ele descriu interfața
internă minimă: `preflight_pdf()` primește dependențele locale ca argumente,
iar `main()` este doar CLI-ul care îi transmite cele două căi explicite.
"""

import hashlib
import importlib
import inspect
import json
import socket
import sys
import types
from pathlib import Path

import pytest


TEXT_NORMATIV_SINTETIC = "1.1. Text sintetic care nu trebuie să ajungă în raport."
CANDIDATI_VALIZI = {
    "cod_oficial": ("NP 010-2026",),
    "titlu_oficial": ("Normativ sintetic pentru testare locală",),
    "an": (2026,),
}


@pytest.fixture
def preflight_module():
    """Importul trebuie să eșueze acum: runtime-ul este adăugat numai după RED."""
    return importlib.import_module("manual_ingestion_preflight")


@pytest.fixture
def directoare(tmp_path, preflight_module, monkeypatch):
    """Izolează inbox-ul și rapoartele în fixture, nu în documente reale."""
    inbox = tmp_path / "documente_noi" / "_inbox"
    rapoarte = tmp_path / "documente_noi" / "_reports"
    inbox.mkdir(parents=True)
    rapoarte.mkdir()
    monkeypatch.setattr(preflight_module, "FOLDER_INBOX", inbox)
    monkeypatch.setattr(preflight_module, "FOLDER_RAPOARTE", rapoarte)
    return inbox, rapoarte


def scrie_pdf_sintetic(inbox: Path, name: str = "document.pdf") -> Path:
    """Creează un fișier minim local; PyMuPDF nu este invocat în aceste teste."""
    pdf = inbox / name
    pdf.write_bytes(b"%PDF-1.7\ncontinut-sintetic")
    return pdf


def extractor_valid(_pdf: Path) -> tuple[str, int]:
    return TEXT_NORMATIV_SINTETIC, 2


def chunker_valid(_text: str) -> list[dict[str, str]]:
    return [{"articol": "1.1", "text": TEXT_NORMATIV_SINTETIC}]


def validator_valid(chunkuri: list[dict[str, str]]) -> list[dict[str, str]]:
    assert chunkuri
    return chunkuri


def candidati_valizi(_text: str) -> dict[str, tuple[object, ...]]:
    return CANDIDATI_VALIZI


def ruleaza_valid(preflight_module, pdf: Path, raport: Path, **overrides):
    """Apelează API-ul testabil cu dependențe locale, explicit controlate."""
    arguments = {
        "extract_pdf": extractor_valid,
        "create_chunks": chunker_valid,
        "validate_chunks": validator_valid,
        "find_metadata_candidates": candidati_valizi,
    }
    arguments.update(overrides)
    return preflight_module.preflight_pdf(pdf, raport, **arguments)


def test_pdf_valid_scrie_raport_minim_fara_text_sau_chunkuri(preflight_module, directoare):
    inbox, rapoarte = directoare
    pdf = scrie_pdf_sintetic(inbox)
    raport = rapoarte / "document.preflight.json"

    rezultat = ruleaza_valid(preflight_module, pdf, raport)

    assert rezultat == json.loads(raport.read_text(encoding="utf-8"))
    assert rezultat["status"] == "ready_for_human_metadata"
    assert rezultat["source_sha256"] == hashlib.sha256(pdf.read_bytes()).hexdigest()
    assert rezultat["page_count"] == 2
    assert rezultat["character_count"] == len(TEXT_NORMATIV_SINTETIC)
    assert rezultat["chunk_count"] == 1
    assert rezultat["metadata_candidates"] == {
        "cod_oficial": "NP 010-2026",
        "titlu_oficial": "Normativ sintetic pentru testare locală",
        "an": 2026,
    }
    serializat = json.dumps(rezultat, ensure_ascii=False)
    assert TEXT_NORMATIV_SINTETIC not in serializat
    assert '"text"' not in serializat
    assert '"chunks"' not in serializat
    assert "embedding" not in serializat


def test_refuza_pdf_din_afara_inbox_inainte_de_extragere(preflight_module, directoare, tmp_path):
    _inbox, rapoarte = directoare
    pdf_extern = tmp_path / "extern.pdf"
    pdf_extern.write_bytes(b"%PDF-1.7\nextern")
    apeluri = []

    with pytest.raises(preflight_module.PreflightError, match="outside_inbox"):
        ruleaza_valid(preflight_module, pdf_extern, rapoarte / "raport.json", extract_pdf=lambda _pdf: apeluri.append(1))

    assert apeluri == []


def test_refuza_pdf_din_subdirectorul_inbox_ului(preflight_module, directoare):
    inbox, rapoarte = directoare
    subdirector = inbox / "subdirector"
    subdirector.mkdir()
    pdf = scrie_pdf_sintetic(subdirector)

    with pytest.raises(preflight_module.PreflightError, match="outside_inbox"):
        ruleaza_valid(preflight_module, pdf, rapoarte / "raport.json")


def test_refuza_raport_din_afara_directorului_reports(preflight_module, directoare, tmp_path):
    inbox, _rapoarte = directoare
    pdf = scrie_pdf_sintetic(inbox)

    with pytest.raises(preflight_module.PreflightError, match="outside_reports"):
        ruleaza_valid(preflight_module, pdf, tmp_path / "raport.json")


def test_refuza_extensie_ne_pdf_inainte_de_extragere(preflight_module, directoare):
    inbox, rapoarte = directoare
    fisier = scrie_pdf_sintetic(inbox, "document.txt")
    apeluri = []

    with pytest.raises(preflight_module.PreflightError, match="invalid_pdf_path"):
        ruleaza_valid(preflight_module, fisier, rapoarte / "raport.json", extract_pdf=lambda _pdf: apeluri.append(1))

    assert apeluri == []


def test_refuza_pdf_modificat_in_timpul_extragerii(preflight_module, directoare):
    inbox, rapoarte = directoare
    pdf = scrie_pdf_sintetic(inbox)

    def extractor_instabil(cale_pdf: Path) -> tuple[str, int]:
        cale_pdf.write_bytes(b"%PDF-1.7\nmodificat-in-timpul-extragerii")
        return TEXT_NORMATIV_SINTETIC, 2

    with pytest.raises(preflight_module.PreflightError, match="unstable_pdf"):
        ruleaza_valid(preflight_module, pdf, rapoarte / "raport.json", extract_pdf=extractor_instabil)


def test_refuza_extragere_sau_chunking_invalid(preflight_module, directoare):
    inbox, rapoarte = directoare
    pdf = scrie_pdf_sintetic(inbox)

    with pytest.raises(preflight_module.PreflightError, match="invalid_extraction"):
        ruleaza_valid(preflight_module, pdf, rapoarte / "extractie.json", extract_pdf=lambda _pdf: ("", 0))

    with pytest.raises(preflight_module.PreflightError, match="invalid_chunks"):
        ruleaza_valid(preflight_module, pdf, rapoarte / "chunking.json", create_chunks=lambda _text: [])


def test_refuza_metadata_lipsa_sau_ambigua(preflight_module, directoare):
    inbox, rapoarte = directoare
    pdf = scrie_pdf_sintetic(inbox)

    for nume_caz, candidati in (
        ("cod-lipsa", {"cod_oficial": (), "titlu_oficial": ("Titlu",), "an": (2026,)}),
        (
            "cod-ambiguu",
            {"cod_oficial": ("NP 010-2026", "NP 011-2026"), "titlu_oficial": ("Titlu",), "an": (2026,)},
        ),
        ("titlu-lipsa", {"cod_oficial": ("NP 010-2026",), "titlu_oficial": (), "an": (2026,)}),
        (
            "titlu-ambiguu",
            {"cod_oficial": ("NP 010-2026",), "titlu_oficial": ("Titlu A", "Titlu B"), "an": (2026,)},
        ),
        ("an-lipsa", {"cod_oficial": ("NP 010-2026",), "titlu_oficial": ("Titlu",), "an": ()}),
        (
            "an-ambiguu",
            {"cod_oficial": ("NP 010-2026",), "titlu_oficial": ("Titlu",), "an": (2025, 2026)},
        ),
    ):
        with pytest.raises(preflight_module.PreflightError, match="ambiguous_metadata"):
            ruleaza_valid(
                preflight_module,
                pdf,
                rapoarte / f"{nume_caz}.json",
                find_metadata_candidates=lambda _text, valori=candidati: valori,
            )


def test_refuza_suprascrierea_raportului(preflight_module, directoare):
    inbox, rapoarte = directoare
    pdf = scrie_pdf_sintetic(inbox)
    raport = rapoarte / "existent.json"
    raport.write_text('{"status":"vechi"}', encoding="utf-8")

    with pytest.raises(preflight_module.PreflightError, match="report_exists"):
        ruleaza_valid(preflight_module, pdf, raport)


def test_modulul_nu_importa_servicii_externe_sau_importeri(preflight_module):
    sursa = inspect.getsource(preflight_module)

    for interzis in (
        "import psycopg2",
        "import voyageai",
        "load_dotenv",
        "auto_ingestion_worker",
        "populare_db",
    ):
        assert interzis not in sursa


def test_preflight_valid_nu_cheama_db_retea_sau_provider(preflight_module, directoare, monkeypatch):
    inbox, rapoarte = directoare
    pdf = scrie_pdf_sintetic(inbox)

    def interzis(*_args, **_kwargs):
        raise AssertionError("Preflight-ul local nu are voie să apeleze servicii externe")

    psycopg2_fals = types.ModuleType("psycopg2")
    psycopg2_fals.connect = interzis
    voyage_fals = types.ModuleType("voyageai")
    voyage_fals.Client = interzis
    dotenv_fals = types.ModuleType("dotenv")
    dotenv_fals.load_dotenv = interzis
    monkeypatch.setitem(sys.modules, "psycopg2", psycopg2_fals)
    monkeypatch.setitem(sys.modules, "voyageai", voyage_fals)
    monkeypatch.setitem(sys.modules, "dotenv", dotenv_fals)
    monkeypatch.setattr(socket, "create_connection", interzis)

    rezultat = ruleaza_valid(preflight_module, pdf, rapoarte / "fara-servicii.json")

    assert rezultat["status"] == "ready_for_human_metadata"


def test_cli_transmite_numai_caile_explicite(preflight_module, directoare, monkeypatch):
    inbox, rapoarte = directoare
    pdf = scrie_pdf_sintetic(inbox)
    raport = rapoarte / "cli.json"
    apeluri = []

    def preflight_fals(cale_pdf: Path, cale_raport: Path):
        apeluri.append((cale_pdf, cale_raport))
        return {"status": "ready_for_human_metadata"}

    monkeypatch.setattr(preflight_module, "preflight_pdf", preflight_fals)

    assert preflight_module.main(["--pdf", str(pdf), "--report", str(raport)]) == 0
    assert apeluri == [(pdf, raport)]
