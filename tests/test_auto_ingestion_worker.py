"""Teste mockuite pentru workerul automat, insert-only, de PDF-uri noi."""

import importlib.util
import multiprocessing
import os
import sys
import types
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODUL_PATH = ROOT / "auto_ingestion_worker.py"


def _rezerva_ultimul_slot_din_proces(directory, results):
    """Ținta top-level rămâne serializabilă pentru multiprocessing spawn pe Windows."""
    from auto_ingestion_worker import LocalStateStore

    now = datetime(2026, 1, 15, 12, tzinfo=ZoneInfo("Europe/Bucharest"))
    results.put(LocalStateStore(Path(directory)).reserve_daily_budget(1, now=now) is not None)


@pytest.fixture
def worker_module(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("Testul nu are voie să apeleze servicii externe")

    psycopg2_fake = types.ModuleType("psycopg2")
    psycopg2_fake.connect = forbidden
    voyage_fake = types.ModuleType("voyageai")
    voyage_fake.Client = forbidden
    dotenv_fake = types.ModuleType("dotenv")
    dotenv_fake.load_dotenv = forbidden
    monkeypatch.setitem(sys.modules, "psycopg2", psycopg2_fake)
    monkeypatch.setitem(sys.modules, "voyageai", voyage_fake)
    monkeypatch.setitem(sys.modules, "dotenv", dotenv_fake)

    spec = importlib.util.spec_from_file_location("auto_ingestion_worker_test", MODUL_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    monkeypatch.setitem(sys.modules, "auto_ingestion_worker_test", module)
    spec.loader.exec_module(module)
    return module


def write_pdf(tmp_path, name="normativ.pdf", content=b"%PDF-1.7\nlocal"):
    path = tmp_path / name
    path.write_bytes(content)
    return path


def preview_valid():
    return "NP 010-2026\nNormativ privind cerințele tehnice pentru testare"


def text_valid():
    return "1.1.\nTextul articolului este suficient de lung pentru chunking."


EET = ZoneInfo("Europe/Bucharest")
NOW_EET = datetime(2026, 1, 15, 12, tzinfo=EET)


class CursorFake:
    def __init__(self, *, duplicate=False, conflict=False):
        self.duplicate = duplicate
        self.conflict = conflict
        self.calls = []
        self.last_sql = ""
        self.closed = False

    def execute(self, sql, params):
        self.calls.append((sql, params))
        self.last_sql = sql

    def fetchone(self):
        if "document_ingestion_sources" in self.last_sql and "SELECT" in self.last_sql:
            return ("already",) if self.duplicate else None
        return None

    def fetchall(self):
        if "FROM public.documente" in self.last_sql:
            return [("old-document",)] if self.conflict else []
        return []

    def close(self):
        self.closed = True


class ConnectionFake:
    def __init__(self, cursor):
        self.cursor_value = cursor
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class VoyageFake:
    def __init__(self, *, failure=False):
        self.failure = failure
        self.calls = []

    def count_tokens(self, texts, model=None):
        self.calls.append(("count", list(texts), model))
        return len(texts[0].split())

    def embed(self, texts, model=None, input_type=None):
        self.calls.append(("embed", list(texts), model, input_type))
        if self.failure:
            raise RuntimeError("provider unavailable")
        return types.SimpleNamespace(embeddings=[[0.1, 0.2] for _ in texts])


def test_valid_pdf_new_uses_only_insert_pending_and_commits(worker_module, tmp_path):
    pdf = write_pdf(tmp_path)
    cursor = CursorFake()
    connection = ConnectionFake(cursor)
    client = VoyageFake()
    state = worker_module.LocalStateStore(tmp_path / "state")

    result = worker_module.proceseaza_pdf(
        pdf,
        state_store=state,
        extract_pdf=lambda _path: (preview_valid(), text_valid()),
        connection_factory=lambda: connection,
        voyage_client_factory=lambda: client,
    )

    assert result.status == "imported"
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert client.calls[-1][0] == "embed"
    writes = [sql for sql, _ in cursor.calls if "INSERT INTO" in sql]
    assert len(writes) == 3
    assert cursor.calls[0] == (worker_module._STATEMENT_TIMEOUT_SQL, (30_000,))
    assert cursor.calls[1] == (worker_module._LOCK_SQL, (result.source_sha256,))
    # `SELECT ... FOR UPDATE` este un lock read-only; interzicem doar statement-uri mutatoare.
    assert not any(sql.lstrip().upper().startswith(("UPDATE", "DELETE")) for sql, _ in cursor.calls)
    document_insert = next(params for sql, params in cursor.calls if "INSERT INTO public.documente" in sql)
    assert document_insert[-1] == "indexed_pending_validation"
    assert state.is_final(result.source_sha256)


@pytest.mark.parametrize(
    ("duplicate", "conflict", "expected_status"),
    [(True, False, "duplicate"), (False, True, "conflict")],
)
def test_duplicatele_si_conflictele_nu_consuma_buget_sau_voyage(
    worker_module, tmp_path, duplicate, conflict, expected_status
):
    pdf = write_pdf(tmp_path)
    cursor = CursorFake(duplicate=duplicate, conflict=conflict)
    connection = ConnectionFake(cursor)
    client = VoyageFake()
    state = worker_module.LocalStateStore(tmp_path / "state")
    for _ in range(4):
        assert state.reserve_daily_budget(1, now=NOW_EET) is not None

    result = worker_module.proceseaza_pdf(
        pdf,
        state_store=state,
        now_factory=lambda: NOW_EET,
        extract_pdf=lambda _path: (preview_valid(), text_valid()),
        connection_factory=lambda: connection,
        voyage_client_factory=lambda: client,
    )

    assert result.status == expected_status
    assert client.calls == []
    assert not any("INSERT INTO" in sql for sql, _ in cursor.calls)
    assert connection.rollbacks == 1
    usage = state.reserve_daily_budget(1, now=NOW_EET)
    assert usage is not None
    assert usage.pdf_count == 5


def test_pdf_modificat_in_timpul_extragerii_opreste_inainte_de_database_sau_voyage(
    worker_module, tmp_path
):
    pdf = write_pdf(tmp_path)
    connections = []
    clients = []

    def extractor_care_modifica_pdf(cale_pdf):
        cale_pdf.write_bytes(b"%PDF-1.7\ncontinut modificat")
        return preview_valid(), text_valid()

    result = worker_module.proceseaza_pdf(
        pdf,
        state_store=worker_module.LocalStateStore(tmp_path / "state"),
        extract_pdf=extractor_care_modifica_pdf,
        connection_factory=lambda: connections.append(object()),
        voyage_client_factory=lambda: clients.append(object()),
    )

    assert result.status == "failed"
    assert result.reason == "unstable_pdf"
    assert connections == []
    assert clients == []


def test_ambiguous_metadata_stops_before_database_or_voyage(worker_module, tmp_path):
    pdf = write_pdf(tmp_path)
    connections = []
    clients = []

    result = worker_module.proceseaza_pdf(
        pdf,
        state_store=worker_module.LocalStateStore(tmp_path / "state"),
        extract_pdf=lambda _path: ("NP 010-2026\nNP 011-2026\nNormativ privind testarea", text_valid()),
        connection_factory=lambda: connections.append(object()),
        voyage_client_factory=lambda: clients.append(object()),
    )

    assert result.status == "failed"
    assert result.reason == "ambiguous_metadata"
    assert connections == []
    assert clients == []


@pytest.mark.parametrize("content", [b"not a pdf", b""])
def test_invalid_pdf_stops_before_database_or_voyage(worker_module, tmp_path, content):
    pdf = write_pdf(tmp_path, content=content)
    connections = []
    clients = []

    result = worker_module.proceseaza_pdf(
        pdf,
        state_store=worker_module.LocalStateStore(tmp_path / "state"),
        connection_factory=lambda: connections.append(object()),
        voyage_client_factory=lambda: clients.append(object()),
    )

    assert result.status == "failed"
    assert result.reason == "invalid_pdf"
    assert connections == []
    assert clients == []


def test_provider_failure_rolls_back_records_failure_and_does_not_retry(worker_module, tmp_path):
    pdf = write_pdf(tmp_path)
    cursor = CursorFake()
    connection = ConnectionFake(cursor)
    client = VoyageFake(failure=True)
    state = worker_module.LocalStateStore(tmp_path / "state")

    failed = worker_module.proceseaza_pdf(
        pdf,
        state_store=state,
        extract_pdf=lambda _path: (preview_valid(), text_valid()),
        connection_factory=lambda: connection,
        voyage_client_factory=lambda: client,
    )
    skipped = worker_module.proceseaza_pdf(
        pdf,
        state_store=state,
        extract_pdf=lambda _path: (_ for _ in ()).throw(AssertionError("nu trebuie extras din nou")),
        connection_factory=lambda: (_ for _ in ()).throw(AssertionError("nu trebuie DB")),
        voyage_client_factory=lambda: (_ for _ in ()).throw(AssertionError("nu trebuie Voyage")),
    )

    assert failed.status == "failed"
    assert failed.reason == "processing_error"
    assert connection.rollbacks == 1
    assert skipped.status == "skipped"
    assert skipped.reason == "already_reported"


def test_daily_budget_refuza_a_sasea_rezervare_pdf(worker_module, tmp_path):
    state = worker_module.LocalStateStore(tmp_path / "state")

    for expected_count in range(1, 6):
        usage = state.reserve_daily_budget(1, now=NOW_EET)
        assert usage is not None
        assert usage.pdf_count == expected_count

    assert state.reserve_daily_budget(1, now=NOW_EET) is None


def test_daily_budget_refuza_chunkuri_peste_zece_mii(worker_module, tmp_path):
    state = worker_module.LocalStateStore(tmp_path / "state")

    assert state.reserve_daily_budget(10_000, now=NOW_EET) is not None
    assert state.reserve_daily_budget(1, now=NOW_EET) is None


@pytest.mark.skipif(os.name != "nt", reason="lock-ul de producție este msvcrt pe Windows")
def test_doua_procese_nu_pot_rezerva_ambele_ultimul_slot(worker_module, tmp_path):
    state = worker_module.LocalStateStore(tmp_path / "state")
    for _ in range(4):
        assert state.reserve_daily_budget(1, now=NOW_EET) is not None

    context = multiprocessing.get_context("spawn")
    results = context.Queue()
    processes = [
        context.Process(target=_rezerva_ultimul_slot_din_proces, args=(str(tmp_path / "state"), results))
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=15)

    assert all(process.exitcode == 0 for process in processes)
    assert sorted(results.get(timeout=2) for _ in processes) == [False, True]


def test_lockul_bugetului_este_eliberat_dupa_eroare(worker_module, tmp_path, monkeypatch):
    state = worker_module.LocalStateStore(tmp_path / "state")
    original = state._citeste_budget

    def read_failure(*_args):
        raise worker_module.IngestionError("invalid_budget_state")

    monkeypatch.setattr(state, "_citeste_budget", read_failure)
    with pytest.raises(worker_module.IngestionError, match="invalid_budget_state"):
        state.reserve_daily_budget(1, now=NOW_EET)
    monkeypatch.setattr(state, "_citeste_budget", original)

    assert state.reserve_daily_budget(1, now=NOW_EET) is not None


def test_budget_exhausted_amana_fara_db_sau_voyage_pana_in_ziua_eet_urmatoare(
    worker_module, tmp_path
):
    pdf = write_pdf(tmp_path)
    state = worker_module.LocalStateStore(tmp_path / "state")
    for _ in range(5):
        assert state.reserve_daily_budget(1, now=NOW_EET) is not None
    cursor = CursorFake()
    connection = ConnectionFake(cursor)
    connections = []
    clients = []

    exhausted = worker_module.proceseaza_pdf(
        pdf,
        state_store=state,
        now_factory=lambda: NOW_EET,
        extract_pdf=lambda _path: (preview_valid(), text_valid()),
        connection_factory=lambda: connections.append(connection) or connection,
        voyage_client_factory=lambda: clients.append(object()),
    )
    deferred = worker_module.proceseaza_pdf(
        pdf,
        state_store=state,
        now_factory=lambda: NOW_EET,
        extract_pdf=lambda _path: (_ for _ in ()).throw(AssertionError("nu trebuie extras")),
        connection_factory=lambda: (_ for _ in ()).throw(AssertionError("nu trebuie DB")),
        voyage_client_factory=lambda: (_ for _ in ()).throw(AssertionError("nu trebuie Voyage")),
    )

    assert exhausted.status == "budget_exhausted"
    assert connections == [connection]
    assert connection.rollbacks == 1
    assert cursor.calls[0] == (worker_module._STATEMENT_TIMEOUT_SQL, (30_000,))
    assert not any("INSERT INTO" in sql for sql, _ in cursor.calls)
    assert clients == []
    assert state.is_final(exhausted.source_sha256) is False
    assert deferred == worker_module.ProcessResult("skipped", "budget_deferred", exhausted.source_sha256)

    next_day = datetime(2026, 1, 16, 0, tzinfo=EET)
    next_connection = ConnectionFake(CursorFake())
    next_client = VoyageFake()
    retried = worker_module.proceseaza_pdf(
        pdf,
        state_store=state,
        now_factory=lambda: next_day,
        extract_pdf=lambda _path: (preview_valid(), text_valid()),
        connection_factory=lambda: next_connection,
        voyage_client_factory=lambda: next_client,
    )

    assert retried.status == "imported"
    assert next_connection.commits == 1
    assert next_client.calls[-1][0] == "embed"


def test_provider_failure_dupa_rezervare_pastreaza_bugetul_consumat(worker_module, tmp_path):
    pdf = write_pdf(tmp_path)
    state = worker_module.LocalStateStore(tmp_path / "state")
    for _ in range(4):
        assert state.reserve_daily_budget(1, now=NOW_EET) is not None

    result = worker_module.proceseaza_pdf(
        pdf,
        state_store=state,
        now_factory=lambda: NOW_EET,
        extract_pdf=lambda _path: (preview_valid(), text_valid()),
        connection_factory=lambda: ConnectionFake(CursorFake()),
        voyage_client_factory=lambda: VoyageFake(failure=True),
    )

    assert result.status == "failed"
    assert state.reserve_daily_budget(1, now=NOW_EET) is None


def test_watcher_waits_for_stability_and_only_uses_direct_pdf_files(worker_module, tmp_path):
    inbox = tmp_path / "_inbox"
    inbox.mkdir()
    direct = write_pdf(inbox, "direct.PDF")
    (inbox / "ignore.txt").write_text("x", encoding="utf-8")
    nested = inbox / "nested"
    nested.mkdir()
    write_pdf(nested, "nested.pdf")
    processed = []
    worker = worker_module.InboxWorker(
        inbox,
        state_store=worker_module.LocalStateStore(tmp_path / "state"),
        process=lambda path: processed.append(path) or worker_module.ProcessResult("imported", "test"),
    )

    assert worker.poll_once() == ()
    results = worker.poll_once()

    assert processed == [direct]
    assert len(results) == 1


def test_connection_and_voyage_clients_have_explicit_tls_timeouts_and_no_retry(worker_module, monkeypatch):
    connection_calls = []
    voyage_calls = []
    environment = {
        "DB_HOST": "db.test",
        "DB_NAME": "database_test",
        "DB_USER": "worker_test",
        "DB_PASSWORD": "test-only-value",
        "DB_PORT": "5432",
        "VOYAGE_API_KEY": "test-only-value",
    }

    monkeypatch.setattr(worker_module.os, "getenv", environment.get)
    monkeypatch.setattr(
        worker_module.psycopg2, "connect", lambda **kwargs: connection_calls.append(kwargs) or object()
    )
    monkeypatch.setattr(
        worker_module.voyageai, "Client", lambda **kwargs: voyage_calls.append(kwargs) or object()
    )

    worker_module.deschide_conexiune()
    worker_module.creeaza_client_voyage()

    assert connection_calls == [{
        "host": "db.test", "dbname": "database_test", "user": "worker_test",
        "password": "test-only-value", "port": "5432", "sslmode": "require", "connect_timeout": 10,
    }]
    assert voyage_calls == [{"api_key": "test-only-value", "timeout": 30, "max_retries": 0}]


def test_task_scheduler_script_requires_install_and_checks_existing_task_before_register():
    script = (ROOT / "scripts" / "register_auto_ingestion_worker.ps1").read_text(encoding="utf-8")
    install_guard = script.index("if (-not $Install)")
    existing_task_check = script.index("Get-ScheduledTask -TaskName $TaskName")
    register_task = script.index("Register-ScheduledTask")

    assert install_guard < existing_task_check < register_task
    assert "throw" in script[install_guard:existing_task_check]
    assert "throw" in script[existing_task_check:register_task]


def test_worker_is_insert_only_and_migration_has_required_guards(worker_module):
    source = MODUL_PATH.read_text(encoding="utf-8")
    migration = (ROOT / "supabase/migrations/20260909000000_document_ingestion_sources.sql").read_text(encoding="utf-8")

    assert "UPDATE public.documente" not in source
    assert "DELETE FROM public.documente" not in source
    assert "DELETE FROM public.documente_chunks" not in source
    assert "INSERT INTO public.documente" in source
    assert "INSERT INTO public.documente_chunks" in source
    assert "source_sha256 text primary key" in migration
    assert "document_id text not null unique" in migration
    assert "foreign key (document_id)" in migration
    assert "enable row level security" in migration
    assert "revoke all on table public.document_ingestion_sources from anon, authenticated" in migration
