"""Teste locale pentru scriptul de curatare a bucket-urilor expirate; fara DB reala."""

import importlib.util
import sys
import types
from datetime import UTC, datetime

import pytest

from pathlib import Path

ROOT_PROIECT = Path(__file__).resolve().parents[1]
CALE_MODUL = ROOT_PROIECT / "cleanup_rate_limit_buckets.py"

NOW = datetime(2026, 9, 5, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def modul_cleanup(monkeypatch):
    """Încarcă modulul cu psycopg2/dotenv false, care opresc orice apel extern real."""
    def apel_extern_interzis(*_args, **_kwargs):
        raise AssertionError("Testul local nu are voie să apeleze servicii externe.")

    psycopg2_fals = types.ModuleType("psycopg2")
    psycopg2_fals.connect = apel_extern_interzis
    dotenv_fals = types.ModuleType("dotenv")
    dotenv_fals.load_dotenv = lambda *_a, **_k: None

    monkeypatch.setitem(sys.modules, "psycopg2", psycopg2_fals)
    monkeypatch.setitem(sys.modules, "dotenv", dotenv_fals)

    specificatie = importlib.util.spec_from_file_location("cleanup_rate_limit_buckets_test", CALE_MODUL)
    modul = importlib.util.module_from_spec(specificatie)
    assert specificatie.loader is not None
    specificatie.loader.exec_module(modul)
    return modul


class CursorFals:
    def __init__(self, conexiune):
        self.conexiune = conexiune

    def execute(self, sql, parametri):
        self.conexiune.apeluri.append((sql, parametri))

    def fetchone(self):
        return (self.conexiune.numar_expirate,)

    def close(self):
        pass


class ConexiuneFalsa:
    def __init__(self, numar_expirate=0, sterse=0):
        self.numar_expirate = numar_expirate
        self.sterse = sterse
        self.apeluri = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return CursorFals(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


def test_numara_bucket_urile_expirate_fara_a_le_sterge(modul_cleanup):
    conexiune = ConexiuneFalsa(numar_expirate=7)

    rezultat = modul_cleanup.numara_bucket_uri_expirate(conexiune, now=NOW)

    assert rezultat == 7
    assert conexiune.commits == 0
    (sql, parametri), = conexiune.apeluri
    assert "SELECT count(*)" in sql
    assert "rate_limit_buckets" in sql
    assert parametri == (NOW,)


def test_sterge_bucket_urile_expirate_apeleaza_repository_si_face_commit(modul_cleanup, monkeypatch):
    conexiune = ConexiuneFalsa()
    apeluri_repository = []

    class RepositoryFals:
        def __init__(self, conexiune_primita):
            assert conexiune_primita is conexiune

        def cleanup_expired_rate_limit_buckets(self, *, now):
            apeluri_repository.append(now)
            return 5

    monkeypatch.setattr(modul_cleanup, "PostgresAccessControlRepository", RepositoryFals)

    sterse = modul_cleanup.sterge_bucket_urile_expirate(conexiune, now=NOW)

    assert sterse == 5
    assert apeluri_repository == [NOW]
    assert conexiune.commits == 1


def test_main_dry_run_nu_sterge_si_nu_face_commit(modul_cleanup, monkeypatch, capsys):
    conexiune = ConexiuneFalsa(numar_expirate=3)
    monkeypatch.setattr(modul_cleanup, "conecteaza_baza_de_date", lambda: conexiune)
    monkeypatch.setattr(sys, "argv", ["cleanup_rate_limit_buckets.py", "--dry-run"])

    modul_cleanup.main()

    assert conexiune.commits == 0
    assert conexiune.closed
    assert "DRY RUN: 3 bucket-uri expirate" in capsys.readouterr().out


def test_main_real_sterge_si_inchide_conexiunea(modul_cleanup, monkeypatch, capsys):
    conexiune = ConexiuneFalsa()
    monkeypatch.setattr(modul_cleanup, "conecteaza_baza_de_date", lambda: conexiune)
    monkeypatch.setattr(modul_cleanup, "sterge_bucket_urile_expirate", lambda _conexiune, now: 9)
    monkeypatch.setattr(sys, "argv", ["cleanup_rate_limit_buckets.py"])

    modul_cleanup.main()

    assert conexiune.closed
    assert "Sterse 9 bucket-uri" in capsys.readouterr().out


def test_main_eroare_face_rollback_si_repropaga(modul_cleanup, monkeypatch):
    conexiune = ConexiuneFalsa()

    def sterge_defect(_conexiune, now):
        raise RuntimeError("DB indisponibila")

    monkeypatch.setattr(modul_cleanup, "conecteaza_baza_de_date", lambda: conexiune)
    monkeypatch.setattr(modul_cleanup, "sterge_bucket_urile_expirate", sterge_defect)
    monkeypatch.setattr(sys, "argv", ["cleanup_rate_limit_buckets.py"])

    with pytest.raises(RuntimeError, match="DB indisponibila"):
        modul_cleanup.main()

    assert conexiune.rollbacks == 1
    assert conexiune.closed


def test_variabila_de_mediu_lipsa_este_eroare_clara(modul_cleanup, monkeypatch):
    monkeypatch.delenv("DB_HOST", raising=False)

    with pytest.raises(ValueError, match="DB_HOST"):
        modul_cleanup._required_environment("DB_HOST")
