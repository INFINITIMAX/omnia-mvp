"""Runner local pentru pilotul R05; dependențele reale se injectează numai la rularea aprobată."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Callable, Mapping, Sequence


MAX_CASES = 20
MAX_EMBEDDING_CALLS = 8
MAX_GENERATION_CALLS = 16
_CATEGORIES = frozenset({"exact", "semantic", "negative"})
_EXPECTED_CATEGORIES = {"exact": 8, "semantic": 8, "negative": 4}


class RealEvaluationError(RuntimeError):
    """Semnalizează un manifest, rezultat sau mediu de evaluare neacceptat."""


@dataclass(frozen=True)
class RealEvaluationCase:
    """Un caz aprobat, fără răspuns gold inclus în manifest."""

    id: str
    category: str
    question: str


def load_cases(manifest_path: Path) -> tuple[RealEvaluationCase, ...]:
    """Citește exact pilotul aprobat, fără a interpreta sau completa cazuri lipsă."""
    try:
        raw = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RealEvaluationError("invalid_cases") from error
    if not isinstance(raw, Mapping) or set(raw) != {"cases"} or not isinstance(raw["cases"], list):
        raise RealEvaluationError("invalid_cases")

    cases: list[RealEvaluationCase] = []
    for value in raw["cases"]:
        if not isinstance(value, Mapping) or set(value) != {"id", "category", "question"}:
            raise RealEvaluationError("invalid_cases")
        case_id = value["id"]
        category = value["category"]
        question = value["question"]
        if (
            not isinstance(case_id, str)
            or not case_id.strip()
            or not isinstance(category, str)
            or category not in _CATEGORIES
            or not isinstance(question, str)
            or not question.strip()
        ):
            raise RealEvaluationError("invalid_cases")
        cases.append(RealEvaluationCase(case_id.strip(), category, question.strip()))

    category_counts = {category: sum(case.category == category for case in cases) for category in _CATEGORIES}
    if len(cases) != MAX_CASES or len({case.id for case in cases}) != MAX_CASES or category_counts != _EXPECTED_CATEGORIES:
        raise RealEvaluationError("invalid_cases")
    return tuple(cases)


def _counter(result: Mapping[str, object], name: str) -> int:
    value = result.get(name)
    if type(value) is not int or value < 0:
        raise RealEvaluationError("execution_error")
    return value


def _public_case(case: RealEvaluationCase, result: Mapping[str, object]) -> dict[str, object]:
    """Păstrează numai datele necesare verdictului uman local, nu datele interne de retrieval."""
    status = result.get("status")
    answer = result.get("answer")
    citations = result.get("citations")
    if not isinstance(status, str) or not isinstance(answer, str) or not isinstance(citations, list):
        raise RealEvaluationError("execution_error")
    return {
        "id": case.id,
        "category": case.category,
        "question": case.question,
        "status": status,
        "answer": answer,
        "citations": citations,
    }


def _write_report_atomically(report_path: Path, report: Mapping[str, object]) -> None:
    """Face raportul vizibil numai după ce toate cazurile au fost terminate cu succes."""
    if report_path.exists():
        raise RealEvaluationError("report_exists")
    temporary = report_path.with_name(f".{report_path.name}.tmp")
    try:
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, report_path)
    except OSError as error:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise RealEvaluationError("report_error") from error


def run_isolated_evaluation(
    manifest_path: Path,
    report_path: Path,
    *,
    connection_factory: Callable[[], object],
    execute_case: Callable[[RealEvaluationCase, object], Mapping[str, object]],
) -> dict[str, object]:
    """Rulează fail-fast pilotul cu o singură conexiune care nu poate persista schimbări."""
    cases = load_cases(manifest_path)
    connection: object | None = None
    public_cases: list[dict[str, object]] = []
    embedding_calls = 0
    generation_calls = 0
    try:
        connection = connection_factory()
        connection.set_session(readonly=True, autocommit=False)
        for case in cases:
            try:
                result = execute_case(case, connection)
                if not isinstance(result, Mapping):
                    raise RealEvaluationError("execution_error")
                current_embeddings = _counter(result, "embedding_calls")
                current_generations = _counter(result, "generation_calls")
                if embedding_calls + current_embeddings > MAX_EMBEDDING_CALLS or generation_calls + current_generations > MAX_GENERATION_CALLS:
                    raise RealEvaluationError("cost_limit")
                public_cases.append(_public_case(case, result))
                embedding_calls += current_embeddings
                generation_calls += current_generations
            except RealEvaluationError:
                raise
            except Exception as error:
                raise RealEvaluationError("execution_error") from error
    finally:
        if connection is not None:
            try:
                connection.rollback()
            finally:
                connection.close()

    report: dict[str, object] = {
        "cases": public_cases,
        "summary": {
            "cases": len(public_cases),
            "embedding_calls": embedding_calls,
            "generation_calls": generation_calls,
        },
    }
    _write_report_atomically(Path(report_path), report)
    return report
