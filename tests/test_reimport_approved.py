"""Teste pentru `reimport_approved.py` (R15/D24): DB și Voyage complet falsificate,
fără rețea, fără `.env`. Fiecare test reproduce o singură regulă din handoff
(`docs/handoff/R15-tester.md`) sau din D24 (`docs/DECISIONS.md`).
"""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import pytest


# O linie suficient de lungă (>120 caractere) ca să verificăm și trunchierea
# exemplelor la 120 de caractere din raport.
LINIE = (
    "Continut normativ sintetic suficient de lung pentru a depasi pragul minim de acoperire "
    "cerut de metrica interna si pentru a testa si trunchierea exemplelor din raport clar."
)
TEXT_VALID = f"\n1.1. {LINIE}\n"


@pytest.fixture
def module():
    return importlib.import_module("reimport_approved")


@pytest.fixture
def dirs(tmp_path, module, monkeypatch):
    documente = tmp_path / "documente_noi"
    rapoarte = documente / "_reports"
    backups = tmp_path / "backups"
    inbox = documente / "_inbox"
    documente.mkdir()
    rapoarte.mkdir()
    backups.mkdir()
    inbox.mkdir()
    monkeypatch.setattr(module, "FOLDER_DOCUMENTE", documente)
    monkeypatch.setattr(module, "FOLDER_RAPOARTE", rapoarte)
    monkeypatch.setattr(module, "FOLDER_BACKUPS", backups)
    monkeypatch.setattr(module.base, "FOLDER_INBOX", inbox)
    return documente, rapoarte, backups, inbox


def scrie_text(documente: Path, document_id: str, text: str = TEXT_VALID) -> Path:
    pasta = documente / document_id
    pasta.mkdir(parents=True, exist_ok=True)
    cale = pasta / "extracted.txt"
    cale.write_text(text, encoding="utf-8")
    return cale


def chunker_ok(_text):
    """Chunk unic al cărui conținut reproduce exact `LINIE`, ca acoperirea să fie 1.0."""
    return [{"articol": "1.1.", "text": LINIE}]


def forbidden(*_args, **_kwargs):
    raise AssertionError("Testul nu are voie să contacteze DB, Voyage sau extragerea PDF reală")


# --- Fake-uri DB/Voyage --------------------------------------------------------


class ReadCursor:
    """Cursor pentru conexiunea readonly: SELECT document, COUNT chunk-uri, backup."""

    def __init__(self, document_id, source_key, status="approved", chunk_count=1, backup_rows=None, gaseste_document=True, events=None):
        self.document_id = document_id
        self.source_key = source_key
        self.status = status
        self.chunk_count = chunk_count
        self.backup_rows = backup_rows if backup_rows is not None else []
        self.gaseste_document = gaseste_document
        self.calls = []
        self.closed = False
        self._last = ""
        self.events = events if events is not None else []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        self._last = sql
        if "embedding::text" in sql:
            self.events.append("backup")

    def fetchall(self):
        if "embedding::text" in self._last:
            return self.backup_rows
        if "public.documente" in self._last:
            return [(self.document_id, self.source_key, self.status)] if self.gaseste_document else []
        return []

    def fetchone(self):
        if "count(*)" in self._last:
            return (self.chunk_count,)
        return None

    def close(self):
        self.closed = True


class ReadConn:
    def __init__(self, cursor):
        self.c = cursor
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return self.c

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class WriteCursor:
    """Cursor pentru tranzacția de scriere (`--commit` sau `--restore`)."""

    def __init__(self, document_id, source_key, status="approved", chunk_count=1, gaseste_document=True, events=None):
        self.document_id = document_id
        self.source_key = source_key
        self.status = status
        self.chunk_count = chunk_count
        self.gaseste_document = gaseste_document
        self.calls = []
        self.closed = False
        self._last = ""
        self.events = events if events is not None else []

    def execute(self, sql, params=None):
        self.calls.append((sql, params))
        self._last = sql
        if "DELETE" in sql:
            self.events.append("delete")

    def fetchall(self):
        if "FOR UPDATE" in self._last:
            return [(self.document_id, self.source_key, self.status)] if self.gaseste_document else []
        return []

    def fetchone(self):
        if "count(*)" in self._last:
            return (self.chunk_count,)
        return None

    def close(self):
        self.closed = True


class WriteConn:
    def __init__(self, cursor, commit_error=False, events=None):
        self.c = cursor
        self.commit_error = commit_error
        self.commits = 0
        self.rollbacks = 0
        self.closed = False
        self.events = events if events is not None else []

    def cursor(self):
        return self.c

    def commit(self):
        self.commits += 1
        if self.commit_error:
            raise RuntimeError("db commit failed")

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class VoyageFake:
    def __init__(self, events=None, failure=False):
        self.events = events if events is not None else []
        self.failure = failure
        self.calls = []

    def count_tokens(self, texts, model=None):
        self.calls.append(("count", list(texts)))
        return 5

    def embed(self, texts, model=None, input_type=None):
        self.calls.append(("embed", list(texts), model, input_type))
        self.events.append("embed")
        if self.failure:
            raise RuntimeError("voyage indisponibil")
        return type("R", (), {"embeddings": [[0.1, 0.2] for _ in texts]})()


# --- Dry-run: readonly, fără scrieri, raport complet ---------------------------


def test_dry_run_este_readonly_fara_voyage_si_scrie_raportul_complet(module, dirs):
    """Ar pica dacă dry-run ar deschide o conexiune de scriere, ar apela Voyage,
    sau dacă raportul JSON nu ar conține toate câmpurile cerute de D24."""
    documente, rapoarte, _backups, _inbox = dirs
    scrie_text(documente, "i5_2022")
    cursor = ReadCursor("i5_2022", "i5_2022_extras.txt", chunk_count=3)
    conn = ReadConn(cursor)

    raport = module.dry_run(
        "i5_2022",
        connection_factory=lambda: conn,
        extract_pdf=forbidden,
        create_chunks=chunker_ok,
    )

    assert raport["poarta_trece"] is True
    assert raport["motive_poarta"] == []
    assert raport["chunk_count_vechi"] == 3
    assert raport["chunk_count_nou"] == 1
    assert raport["acoperire"] == pytest.approx(1.0)
    assert raport["prag_acoperire"] == 0.97
    assert isinstance(raport["statistici_chunking"], dict)
    assert raport["exemple"] == [{"articol": "1.1.", "extras": LINIE[:120]}]
    assert len(raport["exemple"][0]["extras"]) <= 120
    assert not any(sql.upper().startswith(("INSERT", "UPDATE", "DELETE")) for sql, _ in cursor.calls)
    assert conn.rollbacks == 1

    cale_raport = rapoarte / "i5_2022.reimport.json"
    assert cale_raport.is_file()
    continut = json.loads(cale_raport.read_text(encoding="utf-8"))
    for camp in ("poarta_trece", "motive_poarta", "acoperire", "prag_acoperire", "chunk_count_vechi", "chunk_count_nou", "statistici_chunking", "exemple"):
        assert camp in continut
    assert not list(rapoarte.glob("*.tmp"))


# --- Identitate document --------------------------------------------------------


def test_document_necunoscut_in_lista_aprobata_nu_atinge_dependente(module, dirs):
    """Ar pica dacă un document_id în afara `DOCUMENTE_APROBATE` ar ajunge totuși
    să citească fișiere sau să deschidă o conexiune."""
    with pytest.raises(module.ReimportError, match="unknown_document"):
        module.dry_run(
            "document_inexistent",
            connection_factory=forbidden,
            extract_pdf=forbidden,
            create_chunks=forbidden,
        )


def test_document_absent_din_db_da_unknown_document(module, dirs):
    """Ar pica dacă documentul aprobat local, dar absent din DB, ar trece verificarea."""
    documente, _r, _b, _i = dirs
    scrie_text(documente, "i5_2022")
    cursor = ReadCursor("i5_2022", "i5_2022_extras.txt", gaseste_document=False)
    conn = ReadConn(cursor)

    with pytest.raises(module.ReimportError, match="unknown_document"):
        module.dry_run("i5_2022", connection_factory=lambda: conn, extract_pdf=forbidden, create_chunks=chunker_ok)


def test_document_nu_e_approved_da_not_approved(module, dirs):
    """Ar pica dacă un document `pending`/`archived` ar trece drept reimportabil."""
    documente, _r, _b, _i = dirs
    scrie_text(documente, "i5_2022")
    cursor = ReadCursor("i5_2022", "i5_2022_extras.txt", status="pending")
    conn = ReadConn(cursor)

    with pytest.raises(module.ReimportError, match="not_approved"):
        module.dry_run("i5_2022", connection_factory=lambda: conn, extract_pdf=forbidden, create_chunks=chunker_ok)


def test_source_key_diferit_da_source_key_mismatch(module, dirs):
    """Ar pica dacă scriptul ar accepta un `source_key` diferit de cel din
    `DOCUMENTE_APROBATE`, riscând să reimporte identitatea greșită."""
    documente, _r, _b, _i = dirs
    scrie_text(documente, "i5_2022")
    cursor = ReadCursor("i5_2022", "alt_fisier.txt")
    conn = ReadConn(cursor)

    with pytest.raises(module.ReimportError, match="source_key_mismatch"):
        module.dry_run("i5_2022", connection_factory=lambda: conn, extract_pdf=forbidden, create_chunks=chunker_ok)


# --- Sursa textului: fișier local -----------------------------------------------


def test_extracted_txt_lipsa_da_eroare_fara_conexiune(module, dirs):
    """Ar pica dacă lipsa `extracted.txt` ar fi ignorată sau ar ajunge să deschidă
    o conexiune la DB înainte de a valida sursa textului."""
    with pytest.raises(module.ReimportError, match="missing_text_source"):
        module.dry_run("i5_2022", connection_factory=forbidden, extract_pdf=forbidden, create_chunks=forbidden)


def test_extracted_txt_gol_da_empty_text_source(module, dirs):
    """Ar pica dacă un fișier gol (sau doar spații) ar fi acceptat ca sursă validă."""
    documente, _r, _b, _i = dirs
    scrie_text(documente, "i5_2022", text="   \n\n  ")

    with pytest.raises(module.ReimportError, match="empty_text_source"):
        module.dry_run("i5_2022", connection_factory=forbidden, extract_pdf=forbidden, create_chunks=forbidden)


# --- Sursa textului: PDF (np091_2003) -------------------------------------------


def scrie_pdf(inbox: Path, continut: bytes = b"%PDF-1.7\nsintetic") -> Path:
    cale = inbox / "np091.pdf"
    cale.write_bytes(continut)
    return cale


def test_pdf_lipsa_argument_da_missing_pdf_argument(module, dirs):
    """Ar pica dacă np091_2003 (identitate `pdf_<sha>`) ar accepta să ruleze fără
    `--pdf`, fiindcă atunci sha-ul așteptat nu ar putea fi calculat."""
    with pytest.raises(module.ReimportError, match="missing_pdf_argument"):
        module.dry_run("np091_2003", None, connection_factory=forbidden, extract_pdf=forbidden, create_chunks=forbidden)


def test_pdf_cu_extensie_gresita_da_invalid_pdf_path(module, dirs):
    """Ar pica dacă un fișier care nu e `.pdf` ar fi acceptat ca sursă pentru np091_2003."""
    _documente, _r, _b, inbox = dirs
    cale = inbox / "np091.txt"
    cale.write_text("nu e pdf", encoding="utf-8")

    with pytest.raises(module.ReimportError, match="invalid_pdf_path"):
        module.dry_run("np091_2003", str(cale), connection_factory=forbidden, extract_pdf=forbidden, create_chunks=forbidden)


def test_pdf_in_afara_inbox_da_outside_inbox(module, dirs, tmp_path):
    """Ar pica dacă un PDF din afara `documente_noi/_inbox` ar fi acceptat, ocolind
    garanția că sursa e mereu un fișier verificat local direct în inbox."""
    cale = tmp_path / "altundeva.pdf"
    cale.write_bytes(b"%PDF-1.7\nsintetic")

    with pytest.raises(module.ReimportError, match="outside_inbox"):
        module.dry_run("np091_2003", str(cale), connection_factory=forbidden, extract_pdf=forbidden, create_chunks=forbidden)


def test_pdf_instabil_da_unstable_pdf_fara_conexiune(module, dirs):
    """Ar pica dacă un PDF care se modifică în timpul extragerii (SHA diferit
    înainte/după) ar fi acceptat ca sursă stabilă."""
    _documente, _r, _b, inbox = dirs
    pdf = scrie_pdf(inbox)

    def extractor_instabil(cale_pdf: Path):
        cale_pdf.write_bytes(b"%PDF-1.7\nmodificat")
        return TEXT_VALID, 1

    with pytest.raises(module.ReimportError, match="unstable_pdf"):
        module.dry_run(
            "np091_2003",
            str(pdf),
            connection_factory=forbidden,
            extract_pdf=extractor_instabil,
            create_chunks=forbidden,
        )


def test_pdf_valid_calculeaza_source_key_din_sha(module, dirs):
    """Ar pica dacă identitatea `pdf_<sha>` nu ar fi calculată corect din conținutul
    real al PDF-ului (ex. dacă ar folosi un sha declarat de operator, nu cel real)."""
    _documente, _r, _b, inbox = dirs
    pdf = scrie_pdf(inbox)
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    source_key = f"pdf_{sha}"
    cursor = ReadCursor("np091_2003", source_key, chunk_count=1)
    conn = ReadConn(cursor)

    raport = module.dry_run(
        "np091_2003",
        str(pdf),
        connection_factory=lambda: conn,
        extract_pdf=lambda _pdf: (TEXT_VALID, 1),
        create_chunks=chunker_ok,
    )

    assert raport["source_key"] == source_key
    assert raport["poarta_trece"] is True


# --- Chunk-uri invalide: eroare directă, înainte de poartă ----------------------


def test_chunkuri_invalide_opresc_inainte_de_poarta_fara_scriere(module, dirs):
    """Documentează comportamentul real: un chunk invalid (peste 1000 caractere)
    oprește execuția cu `invalid_chunks` înainte ca poarta D24 să fie evaluată și
    fără să scrie raportul JSON — nu produce `poarta_trece=False` cu motiv, cum ar
    sugera o citire literală a handoff-ului. Ar pica dacă validarea locală a
    chunk-urilor ar fi eliminată sau relaxată."""
    documente, rapoarte, _b, _i = dirs
    scrie_text(documente, "i5_2022")

    def chunker_invalid(_text):
        return [{"articol": "1.1.", "text": "x" * 1001}]

    with pytest.raises(module.ReimportError, match="invalid_chunks"):
        module.dry_run("i5_2022", connection_factory=forbidden, extract_pdf=forbidden, create_chunks=chunker_invalid)

    assert not (rapoarte / "i5_2022.reimport.json").exists()


# --- Poarta automată D24 ---------------------------------------------------------


def test_poarta_respinge_acoperire_sub_prag(module, dirs):
    """Ar pica dacă poarta ar accepta o acoperire sub pragul documentului, permițând
    pierderi de conținut la reimport."""
    documente, _r, _b, _i = dirs
    scrie_text(documente, "i5_2022")
    cursor = ReadCursor("i5_2022", "i5_2022_extras.txt")
    conn = ReadConn(cursor)

    def chunker_nepotrivit(_text):
        return [{"articol": "1.1.", "text": "Continut complet fara nicio legatura cu randul original din document."}]

    raport = module.dry_run(
        "i5_2022", connection_factory=lambda: conn, extract_pdf=forbidden, create_chunks=chunker_nepotrivit
    )

    assert raport["poarta_trece"] is False
    assert any("acoperire" in motiv for motiv in raport["motive_poarta"])


def test_poarta_respinge_chunk_cu_antet_mo(module, dirs):
    """Ar pica dacă un chunk care conține antetul de pagină MO ar trece poarta,
    lăsând zgomot de tipar în producție."""
    documente, _r, _b, _i = dirs
    scrie_text(documente, "i5_2022")
    cursor = ReadCursor("i5_2022", "i5_2022_extras.txt")
    conn = ReadConn(cursor)

    def chunker_cu_antet(_text):
        text = LINIE + "\nMONITORUL OFICIAL AL ROMÂNIEI, PARTEA I, Nr. 50"
        return [{"articol": "1.1.", "text": text}]

    raport = module.dry_run(
        "i5_2022", connection_factory=lambda: conn, extract_pdf=forbidden, create_chunks=chunker_cu_antet
    )

    assert raport["poarta_trece"] is False
    assert any("antet" in motiv for motiv in raport["motive_poarta"])


def test_poarta_p118_respinge_articol_art_lipsa(module, dirs):
    """Ar pica dacă, pentru P 118/1, un articol „Art. N.N…” urmat de majusculă ar
    putea lipsi complet din chunk-urile noi fără ca poarta să-l semnaleze."""
    documente, _r, _b, _i = dirs
    text_p118 = f"\nArt. 1.1. {LINIE}\n"
    scrie_text(documente, "p118_1_2025", text=text_p118)
    cursor = ReadCursor("p118_1_2025", "P118_1_2025_extras.txt")
    conn = ReadConn(cursor)

    def chunker_fara_art_1_1(_text):
        return [{"articol": "9.9.", "text": LINIE}]

    raport = module.dry_run(
        "p118_1_2025", connection_factory=lambda: conn, extract_pdf=forbidden, create_chunks=chunker_fara_art_1_1
    )

    assert raport["poarta_trece"] is False
    assert any("Art." in motiv for motiv in raport["motive_poarta"])


def test_poarta_p118_trece_cand_articolul_art_e_prezent(module, dirs):
    """Control pozitiv pentru testul de mai sus: dacă articolul „Art. 1.1.” chiar
    apare ca articol de bază, poarta P 118/1 nu trebuie să-l semnaleze. Ar pica
    dacă `_p118_gate_trece` ar respinge greșit și cazul valid."""
    documente, _r, _b, _i = dirs
    text_p118 = f"\nArt. 1.1. {LINIE}\n"
    scrie_text(documente, "p118_1_2025", text=text_p118)
    cursor = ReadCursor("p118_1_2025", "P118_1_2025_extras.txt")
    conn = ReadConn(cursor)

    def chunker_cu_art_1_1(_text):
        return [{"articol": "1.1.", "text": LINIE}]

    raport = module.dry_run(
        "p118_1_2025", connection_factory=lambda: conn, extract_pdf=forbidden, create_chunks=chunker_cu_art_1_1
    )

    assert raport["poarta_trece"] is True
    assert raport["motive_poarta"] == []


def test_commit_cu_poarta_picata_nu_atinge_voyage_backup_sau_scriere(module, dirs):
    """Ar pica dacă `--commit`, cu poarta picată, ar apela totuși Voyage, ar scrie
    un backup, sau ar deschide conexiunea de scriere."""
    documente, _r, backups, _i = dirs
    scrie_text(documente, "i5_2022")
    cursor = ReadCursor("i5_2022", "i5_2022_extras.txt")
    conn = ReadConn(cursor)

    def chunker_nepotrivit(_text):
        return [{"articol": "1.1.", "text": "Continut complet fara nicio legatura cu randul original din document."}]

    raport = module.commit_document(
        "i5_2022",
        readonly_connection_factory=lambda: conn,
        write_connection_factory=forbidden,
        voyage_client_factory=forbidden,
        extract_pdf=forbidden,
        create_chunks=chunker_nepotrivit,
    )

    assert raport["status"] == "poarta_respinsa"
    assert raport["poarta_trece"] is False
    assert list(backups.glob("*")) == []


# --- Commit reușit: ordine strictă backup -> Voyage -> tranzacție unică --------


def test_commit_reusit_respecta_ordinea_backup_voyage_tranzactie(module, dirs):
    """Ar pica dacă backup-ul nu ar fi scris înaintea apelului Voyage, dacă
    tranzacția de scriere ar începe înainte de backup/Voyage, dacă DELETE ar afecta
    alt document, dacă `chunk_order`/`sursa` ar fi greșite, sau dacă statusul
    documentului ar fi modificat."""
    documente, rapoarte, backups, _i = dirs
    scrie_text(documente, "i5_2022")
    events = []
    backup_rows = [("1.1.", "1.1", "text vechi", "hashvechi", 1, "i5_2022", "[0.9,0.9]", "i5_2022_extras.txt")]
    read_cursor = ReadCursor("i5_2022", "i5_2022_extras.txt", chunk_count=1, backup_rows=backup_rows, events=events)
    read_conn = ReadConn(read_cursor)
    write_cursor = WriteCursor("i5_2022", "i5_2022_extras.txt", chunk_count=1, events=events)
    write_conn = WriteConn(write_cursor, events=events)
    voyage = VoyageFake(events=events)

    raport = module.commit_document(
        "i5_2022",
        readonly_connection_factory=lambda: read_conn,
        write_connection_factory=lambda: write_conn,
        voyage_client_factory=lambda: voyage,
        extract_pdf=forbidden,
        create_chunks=chunker_ok,
    )

    assert raport["status"] == "reimportat"
    assert raport["chunk_count_inserat"] == 1
    assert events == ["backup", "embed", "delete"]
    assert write_conn.commits == 1 and write_conn.rollbacks == 0

    lock_index = next(i for i, c in enumerate(write_cursor.calls) if "pg_advisory_xact_lock" in c[0])
    for_update_index = next(i for i, c in enumerate(write_cursor.calls) if "FOR UPDATE" in c[0])
    delete_index = next(i for i, c in enumerate(write_cursor.calls) if "DELETE" in c[0])
    insert_index = next(i for i, c in enumerate(write_cursor.calls) if "INSERT INTO public.documente_chunks" in c[0])
    assert lock_index < for_update_index < delete_index < insert_index

    delete_calls = [c for c in write_cursor.calls if "DELETE" in c[0]]
    assert delete_calls == [(delete_calls[0][0], ("i5_2022",))]
    insert_calls = [c for c in write_cursor.calls if "INSERT INTO public.documente_chunks" in c[0]]
    assert len(insert_calls) == 1
    _sql, params = insert_calls[0]
    assert params[4] == 1  # chunk_order
    assert params[5] == "i5_2022"  # document_id
    assert params[7] == "i5_2022_extras.txt"  # sursa = source_key

    assert not any(sql.upper().startswith("UPDATE") for sql, _ in write_cursor.calls)

    fisiere_backup = list(backups.glob("reimport-i5_2022-*.json"))
    assert len(fisiere_backup) == 1
    continut_backup = json.loads(fisiere_backup[0].read_text(encoding="utf-8"))
    assert continut_backup["document_id"] == "i5_2022"
    assert continut_backup["chunkuri"][0]["embedding"] == "[0.9,0.9]"


def test_concurrent_change_face_rollback_fara_scriere_persistata(module, dirs):
    """Ar pica dacă o schimbare a numărului de chunk-uri între citirea inițială și
    tranzacția de scriere ar fi ignorată, permițând un DELETE/INSERT pe date
    depășite."""
    documente, _r, _b, _i = dirs
    scrie_text(documente, "i5_2022")
    read_cursor = ReadCursor("i5_2022", "i5_2022_extras.txt", chunk_count=1)
    read_conn = ReadConn(read_cursor)
    write_cursor = WriteCursor("i5_2022", "i5_2022_extras.txt", chunk_count=2)
    write_conn = WriteConn(write_cursor)
    voyage = VoyageFake()

    with pytest.raises(module.ReimportError, match="concurrent_change"):
        module.commit_document(
            "i5_2022",
            readonly_connection_factory=lambda: read_conn,
            write_connection_factory=lambda: write_conn,
            voyage_client_factory=lambda: voyage,
            extract_pdf=forbidden,
            create_chunks=chunker_ok,
        )

    assert write_conn.commits == 0 and write_conn.rollbacks == 1
    assert not any("DELETE" in sql for sql, _ in write_cursor.calls)
    assert not any("INSERT" in sql for sql, _ in write_cursor.calls)


def test_voyage_esuat_nu_scrie_nimic_in_db_dar_backup_ramane(module, dirs):
    """Ar pica dacă un eșec Voyage ar lăsa scriptul să deschidă totuși conexiunea
    de scriere sau să insereze date fără embeddings valide."""
    documente, _r, backups, _i = dirs
    scrie_text(documente, "i5_2022")
    read_cursor = ReadCursor("i5_2022", "i5_2022_extras.txt", chunk_count=1)
    read_conn = ReadConn(read_cursor)
    voyage = VoyageFake(failure=True)

    with pytest.raises(module.ReimportError, match="voyage_error"):
        module.commit_document(
            "i5_2022",
            readonly_connection_factory=lambda: read_conn,
            write_connection_factory=forbidden,
            voyage_client_factory=lambda: voyage,
            extract_pdf=forbidden,
            create_chunks=chunker_ok,
        )

    assert len(list(backups.glob("reimport-i5_2022-*.json"))) == 1


def test_commit_incert_nu_reincearca_si_nu_face_rollback(module, dirs):
    """Ar pica dacă un eșec de `commit()` cu rezultat necunoscut ar declanșa un
    rollback (ar masca o tranzacție posibil deja persistată) sau un retry automat."""
    documente, _r, _b, _i = dirs
    scrie_text(documente, "i5_2022")
    read_cursor = ReadCursor("i5_2022", "i5_2022_extras.txt", chunk_count=1)
    read_conn = ReadConn(read_cursor)
    write_cursor = WriteCursor("i5_2022", "i5_2022_extras.txt", chunk_count=1)
    write_conn = WriteConn(write_cursor, commit_error=True)
    voyage = VoyageFake()

    with pytest.raises(module.ReimportError, match="commit_unknown"):
        module.commit_document(
            "i5_2022",
            readonly_connection_factory=lambda: read_conn,
            write_connection_factory=lambda: write_conn,
            voyage_client_factory=lambda: voyage,
            extract_pdf=forbidden,
            create_chunks=chunker_ok,
        )

    assert write_conn.commits == 1
    assert write_conn.rollbacks == 0
    assert write_conn.closed and write_cursor.closed


# --- Restore ---------------------------------------------------------------------


def backup_valid(document_id="i5_2022", source_key="i5_2022_extras.txt"):
    return {
        "document_id": document_id,
        "source_key": source_key,
        "chunkuri": [
            {
                "articol": "1.1.",
                "articol_normalizat": "1.1",
                "text": "Text din backup.",
                "content_hash": "hash123",
                "chunk_order": 1,
                "document_id": document_id,
                "embedding": "[0.1,0.2]",
                "sursa": source_key,
            }
        ],
    }


def scrie_backup(backups: Path, nume: str, continut: dict) -> Path:
    cale = backups / nume
    cale.write_text(json.dumps(continut), encoding="utf-8")
    return cale


def test_restore_refuza_backup_pentru_alt_document(module, dirs):
    """Ar pica dacă un backup scris pentru alt document ar putea fi restaurat peste
    documentul cerut la linia de comandă."""
    _documente, _r, backups, _i = dirs
    cale = scrie_backup(backups, "backup.json", backup_valid(document_id="i7_2011"))

    with pytest.raises(module.ReimportError, match="backup_document_mismatch"):
        module.restore_from_backup("i5_2022", str(cale), write_connection_factory=forbidden)


def test_restore_refuza_source_key_diferit_de_cel_din_db(module, dirs):
    """Ar pica dacă un backup cu `source_key` care nu se mai potrivește cu cel
    curent din DB ar fi acceptat, restaurând o identitate greșită."""
    _documente, _r, backups, _i = dirs
    cale = scrie_backup(backups, "backup.json", backup_valid())
    write_cursor = WriteCursor("i5_2022", "alt_source_key.txt")
    write_conn = WriteConn(write_cursor)

    with pytest.raises(module.ReimportError, match="restore_identity_mismatch"):
        module.restore_from_backup("i5_2022", str(cale), write_connection_factory=lambda: write_conn)

    assert write_conn.commits == 0 and write_conn.rollbacks == 1


def test_restore_valid_scrie_o_singura_tranzactie_fara_voyage(module, dirs):
    """Ar pica dacă restore nu ar face DELETE+INSERT din backup într-o singură
    tranzacție, sau dacă embedding-ul nu ar fi trimis ca text pentru `::vector`."""
    _documente, _r, backups, _i = dirs
    continut = backup_valid()
    cale = scrie_backup(backups, "backup.json", continut)
    write_cursor = WriteCursor("i5_2022", "i5_2022_extras.txt")
    write_conn = WriteConn(write_cursor)

    rezultat = module.restore_from_backup("i5_2022", str(cale), write_connection_factory=lambda: write_conn)

    assert rezultat["status"] == "restored"
    assert rezultat["chunk_count"] == 1
    assert write_conn.commits == 1 and write_conn.rollbacks == 0
    delete_index = next(i for i, c in enumerate(write_cursor.calls) if "DELETE" in c[0])
    insert_index = next(i for i, c in enumerate(write_cursor.calls) if "INSERT INTO public.documente_chunks" in c[0])
    assert delete_index < insert_index
    _sql, params = next(c for c in write_cursor.calls if "INSERT INTO public.documente_chunks" in c[0])
    assert params[6] == "[0.1,0.2]"  # embedding trimis ca text, cast la ::vector în SQL


def test_restore_backup_in_afara_folderului_backups_e_refuzat(module, dirs, tmp_path):
    """Ar pica dacă un fișier de backup din afara `backups/` ar putea fi restaurat,
    ocolind garanția că sursa e mereu locală și verificată."""
    cale = tmp_path / "backup_extern.json"
    cale.write_text(json.dumps(backup_valid()), encoding="utf-8")

    with pytest.raises(module.ReimportError, match="outside_backups"):
        module.restore_from_backup("i5_2022", str(cale), write_connection_factory=forbidden)


def test_restore_backup_invalid_e_refuzat(module, dirs):
    """Ar pica dacă un fișier de backup incomplet (fără `chunkuri` valide) ar fi
    acceptat ca sursă de restore."""
    _documente, _r, backups, _i = dirs
    cale = scrie_backup(backups, "backup.json", {"document_id": "i5_2022", "source_key": "i5_2022_extras.txt", "chunkuri": []})

    with pytest.raises(module.ReimportError, match="invalid_backup"):
        module.restore_from_backup("i5_2022", str(cale), write_connection_factory=forbidden)


# --- CLI: modurile se exclud reciproc --------------------------------------------


def test_cli_commit_si_restore_impreuna_da_eroare_de_argumente(module, dirs, monkeypatch):
    """Ar pica dacă `--commit` și `--restore` ar putea fi date simultan, lăsând
    ambiguu ce mod rulează efectiv."""
    monkeypatch.setattr(module, "dry_run", forbidden)
    monkeypatch.setattr(module, "commit_document", forbidden)
    monkeypatch.setattr(module, "restore_from_backup", forbidden)

    with pytest.raises(SystemExit) as exc:
        module.main(["--document", "i5_2022", "--commit", "--restore", "backup.json"])

    assert exc.value.code == 2
