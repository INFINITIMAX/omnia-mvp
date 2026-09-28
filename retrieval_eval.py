"""Runner permanent pentru setul de aur al căutării (30 de întrebări cu articol cunoscut).

Compune retrieval identic cu ruta publică (catalog aprobat -> parser, repository,
RetrievalService cu valorile implicite) și aplică aceeași poartă anti-calcul, dar
fără generare Anthropic: scopul este să măsurăm corectitudinea căutării cu cifre,
nu să validăm răspunsul generat (asta face R05, `real_grounding_eval.py`).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Callable, Mapping, Sequence

from main import _open_db_connection
from real_grounding_eval import RealEvaluationError, _build_runtime_embedder, _write_report_atomically
from retrieval_core import (
    ArticleParser,
    Evidence,
    PostgresApprovedCatalogRepository,
    PostgresRetrievalRepository,
    RetrievalService,
)
from scope_core import is_engineering_calculation_request


MAX_CASES = 30
MAX_EMBEDDING_CALLS = 30
_TYPES = frozenset({"exact", "semantic", "negativ"})
_REFUSAL_STATUSES = frozenset({"not_found", "ambiguous_reference", "ambiguous_article", "out_of_scope"})


@dataclass(frozen=True)
class GoldExpectation:
    """Un articol acceptat ca răspuns corect; `articol` e deja normalizat la citire."""

    document_id: str
    articol: str


@dataclass(frozen=True)
class GoldCase:
    """Un caz din setul de aur, fără nimic derivat: exact ce a scris planner-ul."""

    id: str
    tip: str
    intrebare: str
    asteptat: tuple[GoldExpectation, ...]


def load_gold_set(path: Path) -> tuple[GoldCase, ...]:
    """Citește și validează strict `evaluare/set_aur.json`; nu completează nimic implicit."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RealEvaluationError("invalid_set") from error
    if not isinstance(raw, Mapping) or set(raw) != {"versiune", "cazuri"} or raw["versiune"] != 1:
        raise RealEvaluationError("invalid_set")
    cazuri_raw = raw["cazuri"]
    if not isinstance(cazuri_raw, list) or not cazuri_raw or len(cazuri_raw) > MAX_CASES:
        raise RealEvaluationError("invalid_set")

    cases: list[GoldCase] = []
    seen_ids: set[str] = set()
    for value in cazuri_raw:
        if not isinstance(value, Mapping) or set(value) != {"id", "tip", "intrebare", "asteptat"}:
            raise RealEvaluationError("invalid_set")
        case_id, tip, intrebare, asteptat_raw = value["id"], value["tip"], value["intrebare"], value["asteptat"]
        if (
            not isinstance(case_id, str) or not case_id.strip()
            or not isinstance(tip, str) or tip not in _TYPES
            or not isinstance(intrebare, str) or not intrebare.strip()
            or not isinstance(asteptat_raw, list)
        ):
            raise RealEvaluationError("invalid_set")
        case_id = case_id.strip()
        if case_id in seen_ids:
            raise RealEvaluationError("invalid_set")
        seen_ids.add(case_id)

        if tip == "negativ":
            if asteptat_raw:
                raise RealEvaluationError("invalid_set")
            asteptat: tuple[GoldExpectation, ...] = ()
        else:
            if not asteptat_raw:
                raise RealEvaluationError("invalid_set")
            expectations: list[GoldExpectation] = []
            for item in asteptat_raw:
                if not isinstance(item, Mapping) or set(item) != {"document_id", "articol"}:
                    raise RealEvaluationError("invalid_set")
                document_id, articol = item["document_id"], item["articol"]
                if (
                    not isinstance(document_id, str) or not document_id.strip()
                    or not isinstance(articol, str) or not articol.strip()
                ):
                    raise RealEvaluationError("invalid_set")
                try:
                    normalized_articol = ArticleParser.normalize_article(articol)
                except ValueError as error:
                    raise RealEvaluationError("invalid_set") from error
                expectations.append(GoldExpectation(document_id.strip(), normalized_articol))
            asteptat = tuple(expectations)

        cases.append(GoldCase(case_id, tip, intrebare.strip(), asteptat))

    return tuple(cases)


class _CountingEmbedder:
    """Blochează al 31-lea apel înainte ca el să poată ajunge la Voyage."""

    def __init__(self, delegate: object, limit: int) -> None:
        self._delegate = delegate
        self._limit = limit
        self.calls = 0

    def embed_query(self, question: str) -> object:
        if self.calls >= self._limit:
            raise RealEvaluationError("cost_limit")
        self.calls += 1
        return self._delegate.embed_query(question)


def _is_match(expected_articol: str, evidence_articol: str) -> bool:
    """O dovadă e potrivire dacă e articolul așteptat sau un copil direct al lui."""
    return (
        evidence_articol == expected_articol
        or evidence_articol.startswith(expected_articol + ".")
        or evidence_articol.startswith(expected_articol + "(")
    )


def _score(case: GoldCase, evidence: Sequence[Evidence]) -> tuple[bool, int | None, list[dict[str, str]]]:
    """`gasit`/`rang` pe baza primei dovezi care potrivește un articol acceptat."""
    dovezi = [{"document_id": item.document_id, "articol_normalizat": item.articol_normalizat} for item in evidence]
    if not case.asteptat:
        return False, None, dovezi
    gasit = False
    rang: int | None = None
    for index, item in enumerate(evidence, start=1):
        if any(
            item.document_id == expected.document_id and _is_match(expected.articol, item.articol_normalizat)
            for expected in case.asteptat
        ):
            gasit = True
            if rang is None:
                rang = index
    return gasit, rang, dovezi


def _is_correct(case: GoldCase, status: str, gasit: bool) -> bool:
    if case.tip == "negativ":
        return status in _REFUSAL_STATUSES
    return status == "found" and gasit


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _build_summary(evaluated: Sequence[Mapping[str, object]], embedding_calls: int) -> dict[str, object]:
    total = len(evaluated)
    corecte_total = sum(1 for item in evaluated if item["corect"])

    pe_tip: dict[str, dict[str, object]] = {}
    for tip in sorted(_TYPES):
        subset = [item for item in evaluated if item["case"].tip == tip]
        corecte = sum(1 for item in subset if item["corect"])
        pe_tip[tip] = {"total": len(subset), "corecte": corecte, "acuratete": _safe_ratio(corecte, len(subset))}

    pe_document: dict[str, dict[str, object]] = {}
    for item in evaluated:
        for expected in item["case"].asteptat:
            entry = pe_document.setdefault(expected.document_id, {"total": 0, "corecte": 0})
            entry["total"] += 1
            if item["corect"]:
                entry["corecte"] += 1
    for entry in pe_document.values():
        entry["acuratete"] = _safe_ratio(entry["corecte"], entry["total"])

    pozitive = [item for item in evaluated if item["case"].tip != "negativ"]
    recall_1 = _safe_ratio(sum(1 for item in pozitive if item["rang"] == 1), len(pozitive))
    recall_5 = _safe_ratio(sum(1 for item in pozitive if item["rang"] is not None and item["rang"] <= 5), len(pozitive))

    return {
        "total": total,
        "corecte": corecte_total,
        "acuratete_totala": _safe_ratio(corecte_total, total),
        "pe_tip": pe_tip,
        "pe_document": pe_document,
        "recall_at_1": recall_1,
        "recall_at_5": recall_5,
        "embedding_calls": embedding_calls,
    }


def run_evaluation(
    cases: Sequence[GoldCase],
    report_path: Path,
    *,
    connection_factory: Callable[[], object],
    embedder_factory: Callable[[], object],
) -> dict[str, object]:
    """O singură conexiune readonly, o singură compunere de retrieval, fail-fast pe erori reale."""
    connection: object | None = None
    public_cases: list[dict[str, object]] = []
    evaluated: list[dict[str, object]] = []
    embedder = _CountingEmbedder(embedder_factory(), MAX_EMBEDDING_CALLS)
    try:
        connection = connection_factory()
        connection.set_session(readonly=True, autocommit=False)
        catalog = PostgresApprovedCatalogRepository(connection).load()
        parser = catalog.create_parser()
        repository = PostgresRetrievalRepository(connection)
        retrieval = RetrievalService(parser, repository, embedder)

        for case in cases:
            try:
                # Aceeași poartă anti-calcul ca ruta publică, aplicată înainte de căutare.
                if is_engineering_calculation_request(case.intrebare):
                    status, evidence = "out_of_scope", ()
                else:
                    result = retrieval.retrieve(case.intrebare)
                    status, evidence = result.status, tuple(result.evidence)
                if not isinstance(status, str) or not isinstance(evidence, Sequence):
                    raise RealEvaluationError("execution_error")
            except RealEvaluationError:
                raise
            except Exception as error:
                raise RealEvaluationError(f"case_failed:{case.id}:execution_error") from error

            gasit, rang, dovezi = _score(case, evidence)
            corect = _is_correct(case, status, gasit)
            evaluated.append({"case": case, "status": status, "gasit": gasit, "rang": rang, "corect": corect})
            public_cases.append(
                {"id": case.id, "tip": case.tip, "status": status, "gasit": gasit, "rang": rang, "dovezi": dovezi}
            )
    finally:
        if connection is not None:
            try:
                connection.rollback()
            finally:
                connection.close()

    report: dict[str, object] = {"cazuri": public_cases, "sumar": _build_summary(evaluated, embedder.calls)}
    _write_report_atomically(Path(report_path), report)
    return report


def _default_report_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path("evaluare/rapoarte") / f"raport_{stamp}.json"


def main(argv: Sequence[str] | None = None) -> int:
    """Fără `--run`: validează setul și iese, fără DB/Voyage. Cu `--run`: rulează real."""
    parser = argparse.ArgumentParser(description="Evaluează căutarea pe setul permanent de aur.")
    parser.add_argument("--set", type=Path, default=Path("evaluare/set_aur.json"), dest="set_path")
    parser.add_argument("--raport", type=Path, default=None, dest="report_path")
    parser.add_argument("--run", action="store_true", help="Confirmă apelurile reale către DB și Voyage.")
    arguments = parser.parse_args(argv)

    try:
        cases = load_gold_set(arguments.set_path)
    except RealEvaluationError as error:
        print(str(error), file=sys.stderr)
        return 2

    if not arguments.run:
        print("set_valid", file=sys.stderr)
        return 0

    report_path = arguments.report_path or _default_report_path()
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        print("report_dir_error", file=sys.stderr)
        return 3

    try:
        report = run_evaluation(
            cases, report_path,
            connection_factory=_open_db_connection,
            embedder_factory=_build_runtime_embedder,
        )
    except RealEvaluationError as error:
        print(str(error), file=sys.stderr)
        return 3

    print(json.dumps(report["sumar"], ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
