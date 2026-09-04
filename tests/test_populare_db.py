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


def test_chunkurile_sunt_neschimbate_compara_hash_uri_local_vs_db(modul_ingestie):
    chunkuri = [{"articol": "1.1.", "text": "Text A"}, {"articol": "1.2.", "text": "Text B"}]
    hash_a = modul_ingestie.calculeaza_content_hash("Text A")
    hash_b = modul_ingestie.calculeaza_content_hash("Text B")

    class CursorDbIdentic:
        def execute(self, _instructiune, _parametri):
            self.rezultat = [(hash_a,), (hash_b,)]

        def fetchall(self):
            return self.rezultat

    assert modul_ingestie.chunkurile_sunt_neschimbate(CursorDbIdentic(), "sursa", chunkuri) is True

    class CursorDbDiferit:
        def execute(self, _instructiune, _parametri):
            self.rezultat = [(hash_a,), ("alt-hash",)]

        def fetchall(self):
            return self.rezultat

    assert modul_ingestie.chunkurile_sunt_neschimbate(CursorDbDiferit(), "sursa", chunkuri) is False

    class CursorDbGol:
        def execute(self, _instructiune, _parametri):
            self.rezultat = []

        def fetchall(self):
            return self.rezultat

    assert modul_ingestie.chunkurile_sunt_neschimbate(CursorDbGol(), "sursa", chunkuri) is False


def test_import_real_sare_documentele_neschimbate_fara_apel_voyage(modul_ingestie, monkeypatch, tmp_path, capsys):
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
    monkeypatch.setattr(sys, "argv", ["populare_db.py"])

    hash_existent = modul_ingestie.calculeaza_content_hash("Text local valid.")

    class CursorFalsNeschimbat:
        def execute(self, instructiune, _parametri):
            self.select_hash = "SELECT content_hash" in instructiune

        def fetchall(self):
            return [(hash_existent,)]

        def fetchone(self):
            raise AssertionError("nu trebuie apelat cand documentul e neschimbat")

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

    class ConexiuneFalsa:
        def cursor(self):
            return CursorFalsNeschimbat()

        def commit(self):
            pass

        def close(self):
            pass

    class ClientVoyageInterzis:
        def embed(self, *_args, **_kwargs):
            raise AssertionError("Voyage nu trebuie apelat pentru document neschimbat")

    monkeypatch.setattr(modul_ingestie, "load_dotenv", lambda *_a, **_k: None)
    monkeypatch.setattr(modul_ingestie.voyageai, "Client", lambda **_k: ClientVoyageInterzis())
    monkeypatch.setattr(modul_ingestie, "conecteaza_baza_de_date", lambda: ConexiuneFalsa())
    monkeypatch.setattr(modul_ingestie.os, "getenv", lambda *_a, **_k: "fals")

    modul_ingestie.main()

    assert "NESCHIMBAT: document-test" in capsys.readouterr().out


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


def test_creeaza_chunkuri_recunoaste_articolul_citat_din_act_modificator(modul_ingestie):
    """Actele modificatoare pun numărul articolului după ghilimeaua de deschidere a citatului."""
    continut = (
        "1. Articolul 1.2 se modifică și va avea următorul cuprins:\n"
        "„1.2. Domeniul de aplicare al normativului este cel privind:\n"
        "a) sistemele de instalații de încălzire din clădiri noi.”"
    )

    chunkuri = modul_ingestie.creeaza_chunkuri(continut)

    assert chunkuri == [
        {
            "articol": "1.2.",
            "text": (
                "Domeniul de aplicare al normativului este cel privind:\n"
                "a) sistemele de instalații de încălzire din clădiri noi.”"
            ),
        }
    ]


def test_creeaza_chunkuri_articole_citate_multiple_devin_chunkuri_separate(modul_ingestie):
    continut = (
        "1. Articolul 1.2 se modifică și va avea următorul cuprins:\n"
        "„1.2. Text pentru primul articol modificat.”\n"
        "2. Articolul 1.3 se modifică și va avea următorul cuprins:\n"
        "„1.3. Text pentru al doilea articol modificat.”\n"
        "3. Articolul 10.14 se modifică și va avea următorul cuprins:\n"
        "„10.14. Text pentru al treilea articol modificat.”"
    )

    chunkuri = modul_ingestie.creeaza_chunkuri(continut)

    assert [chunk["articol"] for chunk in chunkuri] == ["1.2.", "1.3.", "10.14."]
    assert chunkuri[2]["text"] == "Text pentru al treilea articol modificat.”"


def test_creeaza_chunkuri_articol_nequotat_ramane_neschimbat(modul_ingestie):
    """Ghilimeaua opțională nu trebuie să schimbe comportamentul pe normativele fără citate."""
    continut = "1.1.\nTextul articolului valid, fără ghilimele."

    assert modul_ingestie.creeaza_chunkuri(continut) == [
        {"articol": "1.1.", "text": "Textul articolului valid, fără ghilimele."}
    ]


NUMAR_CHUNKURI_ASTEPTAT_PER_DOCUMENT = {
    "i5_2022": 701,
    "i7_2011": 1444,
    "i9_2022": 650,
    "np004_03": 81,
    "np010_2022": 408,
    "np057_02": 286,
    "p118_1_2025": 1401,
    "spitale_2022": 578,
}


@pytest.mark.skipif(
    not (ROOT_PROIECT / "documente_noi").exists(),
    reason="documente_noi nu e prezent în acest worktree (folder gitignored)",
)
@pytest.mark.parametrize("nume_document, numar_asteptat", sorted(NUMAR_CHUNKURI_ASTEPTAT_PER_DOCUMENT.items()))
def test_chunking_documentelor_deja_validate_ramane_neschimbat(modul_ingestie, nume_document, numar_asteptat):
    """Invariantă critică: fragmentarea documentelor existente nu are voie să se schimbe.

    Altfel se schimbă content_hash-urile și Lucian ar trebui să reimporte toată baza.
    """
    cale_text = ROOT_PROIECT / "documente_noi" / nume_document / "extracted.txt"
    continut = cale_text.read_text(encoding="utf-8")

    chunkuri = modul_ingestie.creeaza_chunkuri(continut)

    assert len(chunkuri) == numar_asteptat


@pytest.mark.skipif(
    not (ROOT_PROIECT / "documente_noi" / "i13_2015_modificari").exists(),
    reason="documente_noi/i13_2015_modificari nu e prezent în acest worktree",
)
def test_chunking_actului_modificator_i13_recunoaste_articolele_citate(modul_ingestie):
    """i13_2015_modificari are 160 de articole modificate; înainte de fix producea doar 14 chunk-uri."""
    cale_text = ROOT_PROIECT / "documente_noi" / "i13_2015_modificari" / "extracted.txt"
    continut = cale_text.read_text(encoding="utf-8")

    chunkuri = modul_ingestie.creeaza_chunkuri(continut)
    articole = {chunk["articol"] for chunk in chunkuri}

    assert 150 <= len(chunkuri) <= 170
    assert {"1.2.", "1.3.", "1.5.", "2.1.", "5.38."}.issubset(articole)


@pytest.mark.skipif(
    not (ROOT_PROIECT / "documente_noi" / "p118_2_2013_modificari").exists(),
    reason="documente_noi/p118_2_2013_modificari nu e prezent în acest worktree",
)
def test_chunking_actului_modificator_p118_2_creste_fata_de_fragmentarea_veche(modul_ingestie):
    """p118_2_2013_modificari producea doar 22 de chunk-uri înainte de fix; trebuie să crească."""
    cale_text = ROOT_PROIECT / "documente_noi" / "p118_2_2013_modificari" / "extracted.txt"
    continut = cale_text.read_text(encoding="utf-8")

    chunkuri = modul_ingestie.creeaza_chunkuri(continut)

    assert len(chunkuri) > 22


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
