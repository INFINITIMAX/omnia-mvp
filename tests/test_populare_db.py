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


def metadata_valida():
    return {
        "document_id": "document-test",
        "source_key": "document_test",
        "cod_oficial": "NP TEST-2026",
        "titlu_oficial": "Document local de test",
        "an": 2026,
        "status": "indexed_pending_validation",
    }


def test_normalizeaza_articol_si_content_hash_fara_servicii_externe(modul_ingestie):
    assert modul_ingestie.normalizeaza_articol(" 3.2. (B). L. ") == "3.2.(b).l"
    assert modul_ingestie.calculeaza_content_hash("text local") == "728be0c85f3fa1f0bcb8188db123b44e"


@pytest.mark.parametrize("spatiu_pdf", ["\u00a0", "\u202f"])
def test_normalizeaza_articol_accepta_spatii_non_breaking_din_pdf(modul_ingestie, spatiu_pdf):
    assert modul_ingestie.normalizeaza_articol(f"3.2.{spatiu_pdf}(B).") == "3.2.(b)"


@pytest.mark.parametrize("articol", ["3.2.Ä.", "3.2./"])
def test_normalizeaza_articol_refuza_caractere_invalide(modul_ingestie, articol):
    with pytest.raises(ValueError):
        modul_ingestie.normalizeaza_articol(articol)


def test_valideaza_metadata_completa(modul_ingestie):
    assert modul_ingestie.valideaza_metadata(metadata_valida()) == metadata_valida()

    metadata_incompleta = metadata_valida()
    metadata_incompleta.pop("status")
    with pytest.raises(ValueError):
        modul_ingestie.valideaza_metadata(metadata_incompleta)

    metadata_status_invalid = metadata_valida()
    metadata_status_invalid["status"] = "publicat_fara_aprobare"
    with pytest.raises(ValueError, match="metadata.status"):
        modul_ingestie.valideaza_metadata(metadata_status_invalid)


def test_valideaza_chunkuri_refuza_lista_goala_si_date_invalide(modul_ingestie):
    with pytest.raises(ValueError, match="cel puțin un chunk"):
        modul_ingestie.valideaza_chunkuri([])

    with pytest.raises(ValueError, match="articolul normalizat"):
        modul_ingestie.valideaza_chunkuri([{"articol": "3.2./", "text": "Text valid"}])

    with pytest.raises(ValueError, match="textul chunk-ului"):
        modul_ingestie.valideaza_chunkuri([{"articol": "3.2.", "text": "   "}])


def test_gaseste_documente_refuza_metadata_incompleta(modul_ingestie, monkeypatch, tmp_path, capsys):
    folder_document = tmp_path / "document_incomplet"
    folder_document.mkdir()
    (folder_document / "metadata.json").write_text(
        '{"document_id": "document-test", "source_key": "document_test"}',
        encoding="utf-8",
    )
    (folder_document / "extracted.txt").write_text("text local", encoding="utf-8")
    monkeypatch.setattr(modul_ingestie, "FOLDER_DOCUMENTE", tmp_path)

    assert list(modul_ingestie.gaseste_documente()) == []
    assert "EROARE metadata" in capsys.readouterr().out


def test_importul_face_upsert_inainte_de_delete_si_populeaza_metadata_noilor_coloane(modul_ingestie):
    apeluri_sql = []

    class CursorFals:
        def execute(self, instructiune, parametri):
            apeluri_sql.append((instructiune, parametri))

        def fetchall(self):
            return []

        def fetchone(self):
            return ("document-test",)

    class ClientVoyageFals:
        def embed(self, *_args, **_kwargs):
            return types.SimpleNamespace(embeddings=[[0.1, 0.2]])

    modul_ingestie.importa_document(
        CursorFals(),
        ClientVoyageFals(),
        metadata_valida(),
        [{"articol": " 1.1. ", "text": "Text local valid."}],
    )

    assert "SELECT document_id, source_key" in apeluri_sql[0][0]
    assert "INSERT INTO documente" in apeluri_sql[1][0]
    assert "DELETE FROM documente_chunks" in apeluri_sql[2][0]
    instructiune, parametri = apeluri_sql[3]
    assert "articol_normalizat" in instructiune
    assert "content_hash" in instructiune
    assert "chunk_order" in instructiune
    assert parametri[1] == "1.1"
    assert parametri[3] == modul_ingestie.calculeaza_content_hash("Text local valid.")
    assert parametri[4:6] == (1, "document-test")


def test_chunk_invalid_opreste_inainte_de_sql_si_voyage(modul_ingestie):
    class CursorInterzis:
        def execute(self, *_args, **_kwargs):
            raise AssertionError("SQL nu trebuie executat pentru chunk invalid")

    class ClientVoyageInterzis:
        def embed(self, *_args, **_kwargs):
            raise AssertionError("Voyage nu trebuie apelat pentru chunk invalid")

    with pytest.raises(ValueError):
        modul_ingestie.importa_document(
            CursorInterzis(),
            ClientVoyageInterzis(),
            metadata_valida(),
            [{"articol": "3.2./", "text": "Text local valid."}],
        )


def test_conflict_document_sursa_opreste_inainte_de_delete_si_voyage(modul_ingestie):
    apeluri_sql = []

    class CursorConflict:
        def execute(self, instructiune, parametri):
            apeluri_sql.append((instructiune, parametri))

        def fetchall(self):
            return [("alt-document", "document_test")]

    class ClientVoyageInterzis:
        def embed(self, *_args, **_kwargs):
            raise AssertionError("Voyage nu trebuie apelat după conflict document/sursă")

    with pytest.raises(ValueError, match="conflict document_id/source_key"):
        modul_ingestie.importa_document(
            CursorConflict(),
            ClientVoyageInterzis(),
            metadata_valida(),
            [{"articol": "1.1.", "text": "Text local valid."}],
        )

    assert len(apeluri_sql) == 1


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
        """
        {
            "document_id": "document-test",
            "source_key": "document_test",
            "cod_oficial": "NP TEST-2026",
            "titlu_oficial": "Document local de test",
            "an": 2026,
            "status": "indexed_pending_validation"
        }
        """,
        encoding="utf-8",
    )
    (folder_document / "extracted.txt").write_text("1.1.\nText local valid.", encoding="utf-8")

    monkeypatch.setattr(modul_ingestie, "FOLDER_DOCUMENTE", tmp_path)
    monkeypatch.setattr(sys, "argv", ["populare_db.py", "--dry-run"])

    modul_ingestie.main()

    assert "DRY RUN: 1 chunk-uri validate" in capsys.readouterr().out
