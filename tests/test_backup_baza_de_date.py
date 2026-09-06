"""Teste locale pentru scriptul de backup; fara DB reala."""

import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT_PROIECT = Path(__file__).resolve().parents[1]
CALE_MODUL = ROOT_PROIECT / "backup_baza_de_date.py"


@pytest.fixture
def modul_backup(monkeypatch):
    def apel_extern_interzis(*_args, **_kwargs):
        raise AssertionError("Testul local nu are voie să apeleze servicii externe.")

    psycopg2_fals = types.ModuleType("psycopg2")
    psycopg2_fals.connect = apel_extern_interzis
    psycopg2_extras_fals = types.ModuleType("psycopg2.extras")
    psycopg2_fals.extras = psycopg2_extras_fals
    dotenv_fals = types.ModuleType("dotenv")
    dotenv_fals.load_dotenv = lambda *_a, **_k: None

    monkeypatch.setitem(sys.modules, "psycopg2", psycopg2_fals)
    monkeypatch.setitem(sys.modules, "psycopg2.extras", psycopg2_extras_fals)
    monkeypatch.setitem(sys.modules, "dotenv", dotenv_fals)

    specificatie = importlib.util.spec_from_file_location("backup_baza_de_date_test", CALE_MODUL)
    modul = importlib.util.module_from_spec(specificatie)
    assert specificatie.loader is not None
    specificatie.loader.exec_module(modul)
    return modul


class CursorFals:
    def __init__(self, conexiune):
        self.conexiune = conexiune
        self.rezultat = []

    def execute(self, sql, parametri=None):
        if "information_schema.columns" in sql:
            tabel = parametri[0]
            self.rezultat = self.conexiune.coloane[tabel]
        else:
            tabel = sql.split('public."')[1].split('"')[0]
            self.rezultat = self.conexiune.randuri[tabel]

    def fetchall(self):
        return self.rezultat

    def close(self):
        pass


class ConexiuneFalsa:
    def __init__(self, coloane, randuri):
        self.coloane = coloane
        self.randuri = randuri

    def cursor(self):
        return CursorFals(self)


def test_backup_tabel_casteaza_embedding_la_text(modul_backup):
    coloane = {"documente_chunks": [("id", "integer"), ("embedding", "USER-DEFINED"), ("text", "text")]}
    randuri = {"documente_chunks": [(1, "[0.1,0.2]", "fragment")]}
    conexiune = ConexiuneFalsa(coloane, randuri)

    nume_coloane, randuri_rezultat = modul_backup.backup_tabel(conexiune, "documente_chunks")

    assert nume_coloane == ["id", "embedding", "text"]
    assert randuri_rezultat == [(1, "[0.1,0.2]", "fragment")]


def test_backup_tabel_tabel_inexistent_esueaza_clar(modul_backup):
    conexiune = ConexiuneFalsa({"gol": []}, {"gol": []})

    with pytest.raises(ValueError, match="nu exista"):
        modul_backup.backup_tabel(conexiune, "gol")


def test_executa_backup_scrie_cate_un_json_per_tabel(modul_backup, tmp_path):
    coloane = {
        "documente": [("document_id", "text"), ("an", "integer")],
        "documente_chunks": [("id", "integer"), ("embedding", "USER-DEFINED")],
    }
    randuri = {
        "documente": [("doc-1", 2022), ("doc-2", 2023)],
        "documente_chunks": [(1, "[0.1]")],
    }
    conexiune = ConexiuneFalsa(coloane, randuri)
    destinatie = tmp_path / "backup"

    rezumat = modul_backup.executa_backup(
        conexiune, destinatie, tabele=("documente", "documente_chunks")
    )

    assert rezumat == {"documente": 2, "documente_chunks": 1}
    continut = (destinatie / "documente.json").read_text(encoding="utf-8")
    assert '"document_id": "doc-1"' in continut
    assert '"an": 2022' in continut


def test_variabila_de_mediu_lipsa_este_eroare_clara(modul_backup, monkeypatch):
    monkeypatch.delenv("DB_HOST", raising=False)

    with pytest.raises(ValueError, match="DB_HOST"):
        modul_backup._required_environment("DB_HOST")
