"""Teste locale pentru ingestie; toate serviciile externe sunt blocate."""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT_PROIECT = Path(__file__).resolve().parents[1]
CALE_MODUL = ROOT_PROIECT / "populare_db.py"


@pytest.fixture
def modul_ingestie(monkeypatch):
    """Încarcă modulul cu clienți falși, care opresc orice apel extern."""
    def apel_extern_interzis(*_args, **_kwargs):
        raise AssertionError("Testul local nu are voie să apeleze servicii externe.")

    voyageai_fals = types.ModuleType("voyageai")
    voyageai_fals.Client = apel_extern_interzis
    psycopg2_fals = types.ModuleType("psycopg2")
    psycopg2_fals.connect = apel_extern_interzis
    dotenv_fals = types.ModuleType("dotenv")
    dotenv_fals.load_dotenv = apel_extern_interzis

    monkeypatch.setitem(sys.modules, "voyageai", voyageai_fals)
    monkeypatch.setitem(sys.modules, "psycopg2", psycopg2_fals)
    monkeypatch.setitem(sys.modules, "dotenv", dotenv_fals)

    specificatie = importlib.util.spec_from_file_location("populare_db_test", CALE_MODUL)
    modul = importlib.util.module_from_spec(specificatie)
    assert specificatie.loader is not None
    specificatie.loader.exec_module(modul)
    return modul


def test_normalizeaza_articol_si_content_hash_fara_servicii_externe(modul_ingestie):
    assert modul_ingestie.normalizeaza_articol(" 3.2. (B). L. ") == "3.2.(b).l"
    assert modul_ingestie.calculeaza_content_hash("text local") == "728be0c85f3fa1f0bcb8188db123b44e"


def test_importul_populeaza_metadata_noilor_coloane(modul_ingestie):
    apeluri_sql = []

    class CursorFals:
        def execute(self, instructiune, parametri):
            apeluri_sql.append((instructiune, parametri))

    class ClientVoyageFals:
        def embed(self, *_args, **_kwargs):
            return types.SimpleNamespace(embeddings=[[0.1, 0.2]])

    modul_ingestie.importa_document(
        CursorFals(),
        ClientVoyageFals(),
        {"document_id": "document-test", "source_key": "document_test"},
        [{"articol": " 1.1. ", "text": "Text local valid."}],
    )

    instructiune, parametri = apeluri_sql[1]
    assert "articol_normalizat" in instructiune
    assert "content_hash" in instructiune
    assert "chunk_order" in instructiune
    assert parametri[1] == "1.1"
    assert parametri[3] == modul_ingestie.calculeaza_content_hash("Text local valid.")
    assert parametri[4:6] == (1, "document-test")


def test_creeaza_chunkuri_elimina_cuprinsul_si_pastreaza_articolul(modul_ingestie):
    continut = "Cuprins........................ 1\n1.1.\nTextul articolului valid."

    assert modul_ingestie.creeaza_chunkuri(continut) == [
        {"articol": "1.1.", "text": "Textul articolului valid."}
    ]


def test_creeaza_chunkuri_pastreaza_doar_varianta_mai_lunga_a_articolului(modul_ingestie):
    continut = "1.1.\nText scurt.\n1.1.\nTextul mai lung al aceluiași articol."

    assert modul_ingestie.creeaza_chunkuri(continut) == [
        {"articol": "1.1.", "text": "Textul mai lung al aceluiași articol."}
    ]


def test_dry_run_nu_apeleaza_voyage_sau_supabase(modul_ingestie, monkeypatch, tmp_path, capsys):
    folder_document = tmp_path / "document_test"
    folder_document.mkdir()
    (folder_document / "metadata.json").write_text(
        '{"document_id": "document-test", "source_key": "document_test"}', encoding="utf-8"
    )
    (folder_document / "extracted.txt").write_text("1.1.\nText local valid.", encoding="utf-8")

    monkeypatch.setattr(modul_ingestie, "FOLDER_DOCUMENTE", tmp_path)
    monkeypatch.setattr(sys, "argv", ["populare_db.py", "--dry-run"])

    modul_ingestie.main()

    assert "DRY RUN: 1 chunk-uri validate" in capsys.readouterr().out
