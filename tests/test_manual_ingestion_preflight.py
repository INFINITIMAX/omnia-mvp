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
METADATA_CONFIRMATA = {
    "document_id": "np015_2022",
    "cod_oficial": "NP 015-2022",
    "titlu_oficial": "Normativ sintetic confirmat de operator",
    "an": 2022,
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


def scrie_metadata_confirmata(rapoarte: Path, values=None) -> Path:
    cale = rapoarte / "metadata-confirmata.json"
    cale.write_text(json.dumps(values or METADATA_CONFIRMATA), encoding="utf-8")
    return cale


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


def test_publicarea_atomica_nu_expune_raport_final_gol(preflight_module, directoare, monkeypatch):
    inbox, rapoarte = directoare
    pdf = scrie_pdf_sintetic(inbox)
    raport = rapoarte / "atomic.json"
    replace_real = preflight_module.os.replace
    momente_replace = []

    def replace_verificat(temporar: Path, final: Path):
        lock = preflight_module._cale_lock_raport(final)
        assert not final.exists()
        assert lock.exists()
        momente_replace.append((temporar, final, lock))
        replace_real(temporar, final)

    monkeypatch.setattr(preflight_module.os, "replace", replace_verificat)

    rezultat = ruleaza_valid(preflight_module, pdf, raport)

    assert momente_replace
    assert raport.exists()
    assert json.loads(raport.read_text(encoding="utf-8")) == rezultat
    assert not preflight_module._cale_lock_raport(raport).exists()


def test_metadata_confirmata_de_operator_pastreaza_ambiguitatea_automata_fara_a_publica_text(
    preflight_module, directoare
):
    inbox, rapoarte = directoare
    pdf = scrie_pdf_sintetic(inbox)
    raport = rapoarte / "operator-confirmed.json"
    metadata = scrie_metadata_confirmata(rapoarte)
    candidati_ambigui = {
        "cod_oficial": ("NP 015-2022", "NP 999-2022"),
        "titlu_oficial": ("Titlu A", "Titlu B"),
        "an": (2022, 2023),
    }

    rezultat = ruleaza_valid(
        preflight_module,
        pdf,
        raport,
        metadata_path=metadata,
        find_metadata_candidates=lambda _text: candidati_ambigui,
    )

    assert rezultat["status"] == "ready_for_human_metadata"
    assert rezultat["metadata_source"] == "operator_confirmed"
    assert rezultat["metadata_confirmation"] == METADATA_CONFIRMATA
    assert "metadata_candidates" not in rezultat
    serializat = json.dumps(rezultat, ensure_ascii=False)
    assert TEXT_NORMATIV_SINTETIC not in serializat
    assert '"text"' not in serializat
    assert '"chunks"' not in serializat


def test_metadata_confirmata_invalida_sau_externa_este_refuzata(preflight_module, directoare, tmp_path):
    inbox, rapoarte = directoare
    pdf = scrie_pdf_sintetic(inbox)
    invalid = scrie_metadata_confirmata(rapoarte, {"cod_oficial": "NP 015-2022"})
    with pytest.raises(preflight_module.PreflightError, match="invalid_metadata"):
        ruleaza_valid(preflight_module, pdf, rapoarte / "invalid.json", metadata_path=invalid)

    externa = tmp_path / "metadata.json"
    externa.write_text(json.dumps(METADATA_CONFIRMATA), encoding="utf-8")
    with pytest.raises(preflight_module.PreflightError, match="outside_reports"):
        ruleaza_valid(preflight_module, pdf, rapoarte / "extern.json", metadata_path=externa)


def test_pipeline_implicit_valideaza_articolul_si_refuza_caractere_neacceptate(preflight_module, directoare):
    inbox, rapoarte = directoare
    pdf = scrie_pdf_sintetic(inbox)
    text_valid = (
        "NP 010-2026\n"
        "Normativ privind testarea locală sigură\n\n"
        "1.1.\n"
        "Text sintetic suficient de lung pentru un chunk valid."
    )

    rezultat = preflight_module.preflight_pdf(
        pdf,
        rapoarte / "implicit-valid.json",
        extract_pdf=lambda _pdf: (text_valid, 1),
    )

    assert rezultat["status"] == "ready_for_human_metadata"
    assert rezultat["chunk_count"] == 1
    assert rezultat["metadata_candidates"]["cod_oficial"] == "NP 010-2026"

    text_articol_cu_virgula_delimitatoare = text_valid.replace("1.1.\n", "1.1.,\n")
    rezultat_cu_virgula = preflight_module.preflight_pdf(
        pdf,
        rapoarte / "implicit-virgula-delimitatoare.json",
        extract_pdf=lambda _pdf: (text_articol_cu_virgula_delimitatoare, 1),
    )
    assert rezultat_cu_virgula["chunk_count"] == 1

    text_articol_parentetic_cu_virgula = text_valid.replace("1.1.\n", "1.1.(1),\n")
    rezultat_parentetic_cu_virgula = preflight_module.preflight_pdf(
        pdf,
        rapoarte / "implicit-parentetic-virgula-delimitatoare.json",
        extract_pdf=lambda _pdf: (text_articol_parentetic_cu_virgula, 1),
    )
    assert rezultat_parentetic_cu_virgula["chunk_count"] == 1

    for nume, sufix in (("slash", "/"), ("virgula-ne-delimitatoare", ",text")):
        text_articol_neacceptat = text_valid.replace("1.1.\n", f"1.1.{sufix}\n")
        with pytest.raises(preflight_module.PreflightError, match="invalid_chunks"):
            preflight_module.preflight_pdf(
                pdf,
                rapoarte / f"implicit-{nume}.json",
                extract_pdf=lambda _pdf, text=text_articol_neacceptat: (text, 1),
            )


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

    def preflight_fals(cale_pdf: Path, cale_raport: Path, *, metadata_path=None):
        apeluri.append((cale_pdf, cale_raport, metadata_path))
        return {"status": "ready_for_human_metadata"}

    monkeypatch.setattr(preflight_module, "preflight_pdf", preflight_fals)

    assert preflight_module.main(["--pdf", str(pdf), "--report", str(raport)]) == 0
    assert apeluri == [(pdf, raport, None)]

    metadata = scrie_metadata_confirmata(rapoarte)
    assert preflight_module.main(["--pdf", str(pdf), "--report", str(raport), "--metadata", str(metadata)]) == 0
    assert apeluri[-1] == (pdf, raport, metadata)


def test_cli_emite_json_ascii_portabil_pentru_metadata_cu_diacritice(
    preflight_module, directoare, monkeypatch, capsys
):
    inbox, rapoarte = directoare
    pdf = scrie_pdf_sintetic(inbox)
    raport = rapoarte / "cli-unicode.json"
    rezultat_cu_diacritice = {
        "status": "ready_for_human_metadata",
        "metadata_confirmation": {"titlu_oficial": "Construcții spitalicești"},
    }

    monkeypatch.setattr(preflight_module, "preflight_pdf", lambda *_args, **_kwargs: rezultat_cu_diacritice)

    assert preflight_module.main(["--pdf", str(pdf), "--report", str(raport)]) == 0
    stdout = capsys.readouterr().out

    assert "\\u021b" in stdout
    assert json.loads(stdout) == rezultat_cu_diacritice


def test_chunker_implicit_limiteaza_articol_lung_fara_subpuncte_la_1000(preflight_module):
    text = "1.1.\n" + ("propozitie sintetica lunga. " * 120)
    chunks = preflight_module._creeaza_chunkuri_locale(text)

    assert len(chunks) > 1
    assert all(0 < len(chunk["text"]) <= 1000 for chunk in chunks)
    preflight_module._valideaza_chunkuri_locale(chunks)
