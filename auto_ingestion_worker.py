"""Worker local, insert-only, pentru PDF-uri normative noi din `_inbox`.

Nu este un endpoint web și nu aprobă documente. Rulează local prin Windows Task
Scheduler, observă numai fișiere PDF direct în `documente_noi/_inbox/` și oprește
importul înainte de DB/Voyage dacă PDF-ul sau metadata nu pot fi validate sigur.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Sequence
from zoneinfo import ZoneInfo

if os.name == "nt":
    import msvcrt
else:  # Testele CI rulează pe Linux; workerul de producție rămâne Windows-only.
    import fcntl

import psycopg2
import voyageai
from dotenv import load_dotenv

from populare_db import (
    MODEL_EMBEDDING,
    calculeaza_content_hash,
    creeaza_chunkuri,
    creeaza_loturi_embedding,
    normalizeaza_articol,
    valideaza_chunkuri,
)

ROOT_PROIECT = Path(__file__).resolve().parent
FOLDER_INBOX = ROOT_PROIECT / "documente_noi" / "_inbox"
FOLDER_STARE = ROOT_PROIECT / "documente_noi" / "_auto_state"
STATUS_PENDING = "indexed_pending_validation"
INTERVAL_POLL_SECUNDE = 5
FUS_ORAR_BUGET = ZoneInfo("Europe/Bucharest")
MAX_PDF_URI_NOI_PE_ZI = 5
MAX_CHUNK_URI_NOI_PE_ZI = 10_000
_TIMEOUT_LOCK_BUGET_SECUNDE = 10
_INTERVAL_REINCERCARE_LOCK_SECUNDE = 0.05

# Sunt acceptate doar forme cu anul inclus. Mai multe coduri diferite sau lipsa
# unui cod opresc importul: este mai sigur să refuzăm decât să ghicim identitatea.
_PATTERN_COD = re.compile(
    r"(?im)^\s*((?:NP|P|I|C|NE|GP|GT|CR|STAS|SR(?:\s+EN(?:\s+ISO)?)?)\s*"
    r"\d+(?:\s*[./-]\s*\d+){0,3}(?:\s*[-/]\s*\d{4})?)\s*$"
)
_PATTERN_TITLU = re.compile(
    r"(?im)^\s*((?:NORMATIV(?:UL)?|REGLEMENTARE(?:A)?|GHID(?:UL)?|"
    r"INSTRUCȚIUNI(?:LE)?|INSTRUCTIUNI(?:LE)?|COD(?:UL)?|METODOLOGIA)\b[^\n]{12,500})\s*$"
)
_PATTERN_AN = re.compile(r"(?:^|[^0-9])(18[0-9]{2}|19[0-9]{2}|20[0-9]{2})(?:$|[^0-9])")

_STATEMENT_TIMEOUT_SQL = "SET LOCAL statement_timeout = %s"
_STATEMENT_TIMEOUT_MS = 30_000
_LOCK_SQL = "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))"
_SOURCE_EXISTS_SQL = "SELECT source_sha256 FROM public.document_ingestion_sources WHERE source_sha256 = %s"
_DOCUMENT_EXISTS_SQL = """
    SELECT document_id
    FROM public.documente
    WHERE document_id = %s OR source_key = %s OR cod_oficial = %s
    FOR UPDATE
"""
_INSERT_DOCUMENT_SQL = """
    INSERT INTO public.documente (
        document_id, source_key, cod_oficial, titlu_oficial, an, status
    ) VALUES (%s, %s, %s, %s, %s, %s)
"""
_INSERT_SOURCE_SQL = """
    INSERT INTO public.document_ingestion_sources (
        source_sha256, document_id, original_filename
    ) VALUES (%s, %s, %s)
"""
_INSERT_CHUNK_SQL = """
    INSERT INTO public.documente_chunks (
        articol, articol_normalizat, text, content_hash, chunk_order,
        document_id, embedding, sursa
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""


class IngestionError(Exception):
    """Eroare controlată, sigură pentru raportul local al unui singur PDF."""


class DuplicateSourceError(IngestionError):
    """Același PDF este deja înregistrat; nu este un import nou."""


class ConflictError(IngestionError):
    """PDF-ul încearcă să folosească o identitate documentară deja existentă."""


class DailyBudgetExhaustedError(IngestionError):
    """Plafonul local zilnic a fost atins înainte de DB sau Voyage."""


@dataclass(frozen=True)
class DailyBudgetUsage:
    """Contor local minim, fără text normativ sau secrete."""

    date_eet: str
    pdf_count: int
    chunk_count: int


@dataclass(frozen=True)
class DocumentMetadata:
    document_id: str
    source_key: str
    cod_oficial: str
    titlu_oficial: str
    an: int
    status: str = STATUS_PENDING


@dataclass(frozen=True)
class ProcessResult:
    status: str
    reason: str
    source_sha256: str | None = None


class LocalStateStore:
    """Stare minimă, locală și fără text normativ, pentru a evita retry-uri automate."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def _path(self, source_sha256: str) -> Path:
        return self._directory / f"{source_sha256}.json"

    def is_final(self, source_sha256: str) -> bool:
        path = self._path(source_sha256)
        if not path.is_file():
            return False
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return True
        return payload.get("status") in {"imported", "failed", "duplicate", "conflict"}

    def record(self, source_sha256: str, filename: str, status: str, reason: str) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "source_sha256": source_sha256,
            "filename": filename,
            "status": status,
            "reason": reason,
        }
        self._scrie_atomic(self._path(source_sha256), payload)

    def defer_until_next_eet_day(self, source_sha256: str, filename: str, *, now: datetime) -> None:
        """Reține numai data locală după care un PDF epuizat poate fi reevaluat."""
        next_date = self._eet_date(now) + timedelta(days=1)
        self._directory.mkdir(parents=True, exist_ok=True)
        self._scrie_atomic(
            self._path(source_sha256),
            {
                "source_sha256": source_sha256,
                "filename": filename,
                "status": "budget_exhausted",
                "reason": "daily_limit",
                "not_before_eet": next_date.isoformat(),
            },
        )

    def is_deferred(self, source_sha256: str, *, now: datetime) -> bool:
        """Spune fail-closed dacă un PDF trebuie amânat până la următoarea zi EET."""
        path = self._path(source_sha256)
        if not path.is_file():
            return False
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("status") != "budget_exhausted":
                return False
            not_before = datetime.fromisoformat(str(payload["not_before_eet"])).date()
        except (KeyError, OSError, TypeError, ValueError):
            return True
        return self._eet_date(now) < not_before

    @staticmethod
    def _eet_date(now: datetime):
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise IngestionError("invalid_budget_clock")
        return now.astimezone(FUS_ORAR_BUGET).date()

    @contextmanager
    def _daily_budget_lock(self):
        """Exclusivitate inter-proces pentru citirea și rescrierea bugetului local.

        Workerul rulează pe Windows și folosește `msvcrt` pentru un lock pe primul
        octet al unui fișier separat. Fallback-ul `fcntl` păstrează testele CI
        portabile; nu este calea de producție. Lock-ul nu depinde de memorie, deci
        două procese pornite accidental nu pot rezerva același ultim slot.
        """
        self._directory.mkdir(parents=True, exist_ok=True)
        cale_lock = self._directory / "daily_budget.lock"
        try:
            lock_file = cale_lock.open("a+b")
        except OSError as error:
            raise IngestionError("budget_lock_unavailable") from error

        with lock_file:
            acquired = False
            try:
                if os.name == "nt":
                    # Inițializarea octetului se face o singură dată. Dacă alt
                    # proces tocmai a creat și blocat fișierul, scrierea poate fi
                    # refuzată de Windows; lock-ul de mai jos așteaptă în loc să
                    # presupună că fișierul este liber.
                    lock_file.seek(0, os.SEEK_END)
                    if lock_file.tell() == 0:
                        try:
                            lock_file.write(b"\0")
                            lock_file.flush()
                        except OSError:
                            pass
                    deadline = time.monotonic() + _TIMEOUT_LOCK_BUGET_SECUNDE
                    while True:
                        try:
                            lock_file.seek(0)
                            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                            acquired = True
                            break
                        except OSError as error:
                            if time.monotonic() >= deadline:
                                raise IngestionError("budget_lock_unavailable") from error
                            time.sleep(_INTERVAL_REINCERCARE_LOCK_SECUNDE)
                else:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                    acquired = True
                yield
            finally:
                if acquired:
                    try:
                        lock_file.seek(0)
                        if os.name == "nt":
                            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                        else:
                            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                    except OSError as error:
                        raise IngestionError("budget_lock_unavailable") from error

    def reserve_daily_budget(self, chunk_count: int, *, now: datetime) -> DailyBudgetUsage | None:
        """Rezervă atomic un PDF și chunk-urile lui pentru ziua EET curentă.

        `None` înseamnă plafon depășit; fișierul de buget nu este schimbat. O
        rezervare reușită nu este eliberată la eșecul providerului, ca retry-urile
        automate să nu poată depăși plafonul zilnic aprobat.
        """
        if type(chunk_count) is not int or chunk_count <= 0:
            raise IngestionError("invalid_chunk_count")
        date_eet = self._eet_date(now).isoformat()
        target = self._directory / "daily_budget.json"
        with self._daily_budget_lock():
            usage = self._citeste_budget(target, date_eet)
            if (
                usage.pdf_count >= MAX_PDF_URI_NOI_PE_ZI
                or usage.chunk_count + chunk_count > MAX_CHUNK_URI_NOI_PE_ZI
            ):
                return None
            reserved = DailyBudgetUsage(
                date_eet, usage.pdf_count + 1, usage.chunk_count + chunk_count
            )
            self._scrie_atomic(
                target,
                {
                    "date_eet": reserved.date_eet,
                    "pdf_count": reserved.pdf_count,
                    "chunk_count": reserved.chunk_count,
                },
            )
            return reserved

    @staticmethod
    def _scrie_atomic(target: Path, payload: dict[str, object]) -> None:
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        temporary.replace(target)

    @staticmethod
    def _citeste_budget(target: Path, date_eet: str) -> DailyBudgetUsage:
        if not target.is_file():
            return DailyBudgetUsage(date_eet, 0, 0)
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
            usage = DailyBudgetUsage(
                str(payload["date_eet"]), int(payload["pdf_count"]), int(payload["chunk_count"])
            )
        except (KeyError, OSError, TypeError, ValueError) as error:
            raise IngestionError("invalid_budget_state") from error
        if usage.pdf_count < 0 or usage.chunk_count < 0:
            raise IngestionError("invalid_budget_state")
        return usage if usage.date_eet == date_eet else DailyBudgetUsage(date_eet, 0, 0)


def now_eet() -> datetime:
    return datetime.now(FUS_ORAR_BUGET)


def calculeaza_sha256(cale_pdf: Path) -> str:
    """Hash streaming; PDF-ul nu este copiat sau modificat."""
    digest = hashlib.sha256()
    with cale_pdf.open("rb") as fisier:
        for bloc in iter(lambda: fisier.read(1024 * 1024), b""):
            digest.update(bloc)
    return digest.hexdigest()


def valideaza_pdf(cale_pdf: Path) -> None:
    """Filtru ieftin înainte de parsare, DB sau provider."""
    if not cale_pdf.is_file() or cale_pdf.suffix.casefold() != ".pdf":
        raise IngestionError("invalid_pdf")
    try:
        with cale_pdf.open("rb") as fisier:
            header = fisier.read(5)
    except OSError as error:
        raise IngestionError("invalid_pdf") from error
    if header != b"%PDF-":
        raise IngestionError("invalid_pdf")


def snapshot_pdf(cale_pdf: Path) -> tuple[int, int]:
    """Identitatea fizică a fișierului, pentru detectarea copierii/modificării active."""
    try:
        stat = cale_pdf.stat()
    except OSError as error:
        raise IngestionError("unstable_pdf") from error
    return stat.st_size, stat.st_mtime_ns


def verifica_pdf_neschimbat(
    cale_pdf: Path, snapshot_initial: tuple[int, int], source_sha256: str
) -> None:
    """Refuză înainte de DB/Voyage un PDF schimbat în timpul extracției locale."""
    if snapshot_pdf(cale_pdf) != snapshot_initial or calculeaza_sha256(cale_pdf) != source_sha256:
        raise IngestionError("unstable_pdf")


def _normalizare_spatii(value: str) -> str:
    return " ".join(value.split())


def _coduri_unice(preview: str) -> tuple[str, ...]:
    values = []
    for match in _PATTERN_COD.finditer(preview):
        normalized = _normalizare_spatii(match.group(1))
        if not _PATTERN_AN.search(normalized):
            continue
        values.append(normalized)
    return tuple(dict.fromkeys(values))


def _titluri_unice(preview: str) -> tuple[str, ...]:
    values = [_normalizare_spatii(match.group(1)) for match in _PATTERN_TITLU.finditer(preview)]
    return tuple(dict.fromkeys(values))


def _document_id(cod_oficial: str) -> str:
    parts = re.findall(r"[a-z]+|[0-9]+", cod_oficial.casefold())
    if len(parts) < 3:
        raise IngestionError("ambiguous_metadata")
    return "_".join((parts[0] + parts[1], *parts[2:]))


def extrage_metadata(preview: str, source_sha256: str) -> DocumentMetadata:
    """Extrage numai valori unice din primele pagini; nu inventează metadata."""
    if not isinstance(preview, str) or not preview.strip():
        raise IngestionError("ambiguous_metadata")
    coduri = _coduri_unice(preview)
    titluri = _titluri_unice(preview)
    if len(coduri) != 1 or len(titluri) != 1:
        raise IngestionError("ambiguous_metadata")
    cod = coduri[0]
    ani = tuple(dict.fromkeys(int(value) for value in _PATTERN_AN.findall(cod)))
    if len(ani) != 1:
        raise IngestionError("ambiguous_metadata")
    return DocumentMetadata(
        document_id=_document_id(cod),
        source_key=f"pdf_{source_sha256}",
        cod_oficial=cod,
        titlu_oficial=titluri[0],
        an=ani[0],
    )


def extrage_pdf_local(cale_pdf: Path) -> tuple[str, str]:
    """Citește local preview-ul din primele trei pagini și textul complet normalizat."""
    import fitz
    from procesare_documente import extrage_text

    with fitz.open(cale_pdf) as document:
        if document.needs_pass or not document.is_pdf:
            raise IngestionError("invalid_pdf")
        preview = "\n".join(page.get_text() for page in document[:3])
    text, _pages = extrage_text(cale_pdf)
    if not text.strip():
        raise IngestionError("invalid_pdf")
    return preview, text


def _required_environment(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise IngestionError("configuration_error")
    return value


def deschide_conexiune() -> object:
    """Deschide DB numai prin TLS și nu așteaptă conectarea la nesfârșit."""
    return psycopg2.connect(
        host=_required_environment("DB_HOST"),
        dbname=_required_environment("DB_NAME"),
        user=_required_environment("DB_USER"),
        password=_required_environment("DB_PASSWORD"),
        port=_required_environment("DB_PORT"),
        sslmode="require",
        connect_timeout=10,
    )


def creeaza_client_voyage() -> object:
    """Nu reîncearcă automat apelurile plătite; eșecul este raportat local."""
    return voyageai.Client(
        api_key=_required_environment("VOYAGE_API_KEY"), timeout=30, max_retries=0
    )


def _blocheaza_si_verifica_noutatea(cursor: object, metadata: DocumentMetadata, source_sha256: str) -> None:
    """Aplică limita query-urilor, serializează aceeași sursă/cod și refuză identități existente."""
    cursor.execute(_STATEMENT_TIMEOUT_SQL, (_STATEMENT_TIMEOUT_MS,))
    for identity in (source_sha256, metadata.document_id, metadata.cod_oficial):
        cursor.execute(_LOCK_SQL, (identity,))
    cursor.execute(_SOURCE_EXISTS_SQL, (source_sha256,))
    if cursor.fetchone() is not None:
        raise DuplicateSourceError("duplicate")
    cursor.execute(
        _DOCUMENT_EXISTS_SQL,
        (metadata.document_id, metadata.source_key, metadata.cod_oficial),
    )
    if cursor.fetchall():
        raise ConflictError("conflict")


def _embeddings(client: object, chunkuri: list[dict[str, str]]) -> list[tuple[dict[str, str], Sequence[float]]]:
    def numara_tokeni(text: str) -> int:
        return int(client.count_tokens([text], model=MODEL_EMBEDDING))

    pairs: list[tuple[dict[str, str], Sequence[float]]] = []
    for lot in creeaza_loturi_embedding(chunkuri, numara_tokeni):
        texts = [chunk["text"] for chunk in lot]
        embeddings = client.embed(texts, model=MODEL_EMBEDDING, input_type="document").embeddings
        if len(embeddings) != len(lot):
            raise IngestionError("provider_error")
        pairs.extend(zip(lot, embeddings))
    return pairs


def importa_pdf_nou(
    cale_pdf: Path,
    *,
    state_store: LocalStateStore,
    now_factory: Callable[[], datetime] = now_eet,
    extract_pdf: Callable[[Path], tuple[str, str]] = extrage_pdf_local,
    connection_factory: Callable[[], object] = deschide_conexiune,
    voyage_client_factory: Callable[[], object] = creeaza_client_voyage,
) -> str:
    """Procesează un singur PDF complet nou; toate scrierile DB sunt INSERT-only."""
    valideaza_pdf(cale_pdf)
    snapshot_initial = snapshot_pdf(cale_pdf)
    source_sha256 = calculeaza_sha256(cale_pdf)
    preview, text = extract_pdf(cale_pdf)
    metadata = extrage_metadata(preview, source_sha256)
    chunkuri = creeaza_chunkuri(text)
    valideaza_chunkuri(chunkuri)
    # Revalidarea este ultimul pas local: conexiunea DB și clientul Voyage nu
    # pot exista dacă PDF-ul a fost înlocuit sau încă se copiază.
    verifica_pdf_neschimbat(cale_pdf, snapshot_initial, source_sha256)

    connection = connection_factory()
    cursor = None
    try:
        cursor = connection.cursor()
        # Numai un PDF confirmat nou rezervă buget. Duplicatele și conflictele
        # fac rollback înainte de această linie, fără cost Voyage sau consum zilnic.
        _blocheaza_si_verifica_noutatea(cursor, metadata, source_sha256)
        if state_store.reserve_daily_budget(len(chunkuri), now=now_factory()) is None:
            raise DailyBudgetExhaustedError("budget_exhausted")
        embeddings = _embeddings(voyage_client_factory(), chunkuri)
        cursor.execute(
            _INSERT_DOCUMENT_SQL,
            (
                metadata.document_id, metadata.source_key, metadata.cod_oficial,
                metadata.titlu_oficial, metadata.an, STATUS_PENDING,
            ),
        )
        cursor.execute(_INSERT_SOURCE_SQL, (source_sha256, metadata.document_id, cale_pdf.name))
        for chunk_order, (chunk, embedding) in enumerate(embeddings, start=1):
            cursor.execute(
                _INSERT_CHUNK_SQL,
                (
                    chunk["articol"], normalizeaza_articol(chunk["articol"]), chunk["text"],
                    calculeaza_content_hash(chunk["text"]), chunk_order, metadata.document_id,
                    embedding, metadata.source_key,
                ),
            )
        connection.commit()
        return source_sha256
    except Exception:
        connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def proceseaza_pdf(
    cale_pdf: Path,
    *,
    state_store: LocalStateStore,
    now_factory: Callable[[], datetime] = now_eet,
    extract_pdf: Callable[[Path], tuple[str, str]] = extrage_pdf_local,
    connection_factory: Callable[[], object] = deschide_conexiune,
    voyage_client_factory: Callable[[], object] = creeaza_client_voyage,
) -> ProcessResult:
    """Wrapper injectabil: raportează coduri sigure și nu reîncearcă automat eșecurile."""
    source_sha256: str | None = None
    now: datetime | None = None
    try:
        if cale_pdf.is_file():
            source_sha256 = calculeaza_sha256(cale_pdf)
            if state_store.is_final(source_sha256):
                return ProcessResult("skipped", "already_reported", source_sha256)
            now = now_factory()
            if state_store.is_deferred(source_sha256, now=now):
                return ProcessResult("skipped", "budget_deferred", source_sha256)
        valideaza_pdf(cale_pdf)
        if source_sha256 is None:
            source_sha256 = calculeaza_sha256(cale_pdf)
        imported_sha = importa_pdf_nou(
            cale_pdf,
            state_store=state_store,
            now_factory=(lambda: now) if now is not None else now_factory,
            extract_pdf=extract_pdf,
            connection_factory=connection_factory,
            voyage_client_factory=voyage_client_factory,
        )
        state_store.record(imported_sha, cale_pdf.name, "imported", "pending_validation")
        return ProcessResult("imported", "pending_validation", imported_sha)
    except DailyBudgetExhaustedError:
        if source_sha256 is not None:
            # `budget_exhausted` nu este stare finală: același PDF devine reeligibil după resetul EET.
            state_store.defer_until_next_eet_day(
                source_sha256, cale_pdf.name, now=now if now is not None else now_factory()
            )
        return ProcessResult("budget_exhausted", "daily_limit", source_sha256)
    except DuplicateSourceError:
        if source_sha256 is not None:
            state_store.record(source_sha256, cale_pdf.name, "duplicate", "already_in_database")
        return ProcessResult("duplicate", "already_in_database", source_sha256)
    except ConflictError:
        if source_sha256 is not None:
            state_store.record(source_sha256, cale_pdf.name, "conflict", "document_identity_exists")
        return ProcessResult("conflict", "document_identity_exists", source_sha256)
    except IngestionError as error:
        if source_sha256 is not None:
            state_store.record(source_sha256, cale_pdf.name, "failed", str(error))
        return ProcessResult("failed", str(error), source_sha256)
    except Exception:
        if source_sha256 is not None:
            state_store.record(source_sha256, cale_pdf.name, "failed", "processing_error")
        return ProcessResult("failed", "processing_error", source_sha256)


class InboxWorker:
    """Polling local standard-library: observă numai PDF-uri directe din `_inbox`."""

    def __init__(
        self,
        inbox: Path = FOLDER_INBOX,
        state_store: LocalStateStore | None = None,
        process: Callable[[Path], ProcessResult] | None = None,
    ) -> None:
        self._inbox = inbox
        self._state_store = state_store or LocalStateStore(FOLDER_STARE)
        self._process = process or (lambda path: proceseaza_pdf(path, state_store=self._state_store))
        self._snapshots: dict[Path, tuple[int, int]] = {}

    def poll_once(self) -> tuple[ProcessResult, ...]:
        if not self._inbox.is_dir():
            return ()
        results = []
        files = [path for path in self._inbox.iterdir() if path.is_file() and path.suffix.casefold() == ".pdf"]
        for path in sorted(files, key=lambda item: item.name.casefold()):
            try:
                stat = path.stat()
            except OSError:
                continue
            snapshot = (stat.st_size, stat.st_mtime_ns)
            if self._snapshots.get(path) != snapshot:
                self._snapshots[path] = snapshot
                continue
            results.append(self._process(path))
        self._snapshots = {path: snapshot for path, snapshot in self._snapshots.items() if path in files}
        return tuple(results)


def main() -> None:
    """Punctul de intrare pentru Task Scheduler; operatorul nu rulează comenzi manuale."""
    load_dotenv(ROOT_PROIECT / ".env")
    worker = InboxWorker()
    while True:
        worker.poll_once()
        time.sleep(INTERVAL_POLL_SECUNDE)


if __name__ == "__main__":
    main()
