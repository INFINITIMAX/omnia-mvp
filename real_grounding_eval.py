"""Runner local pentru pilotul R05; dependențele reale se injectează numai la rularea aprobată."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import Callable, Mapping, Sequence

from anthropic import Anthropic as AnthropicClient
from voyageai import Client as VoyageClient

from generation_core import GeneratedText, GenerationService
from main import AnthropicTextGenerator, _open_db_connection
from retrieval_core import (
    PostgresApprovedCatalogRepository,
    PostgresRetrievalRepository,
    RetrievalService,
)


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


class _CountingEmbedder:
    """Blochează apelul al nouălea înainte ca el să poată ajunge la Voyage."""

    def __init__(self, delegate: object) -> None:
        self._delegate = delegate
        self.calls = 0

    def embed_query(self, question: str) -> object:
        if self.calls >= MAX_EMBEDDING_CALLS:
            raise RealEvaluationError("cost_limit")
        self.calls += 1
        return self._delegate.embed_query(question)


class _CountingGenerator:
    """Blochează generarea a șaptesprezecea înainte ca ea să poată ajunge la Anthropic."""

    def __init__(self, delegate: object) -> None:
        self._delegate = delegate
        self.calls = 0

    def generate(self, prompt: str, *, max_tokens: int) -> object:
        if self.calls >= MAX_GENERATION_CALLS:
            raise RealEvaluationError("cost_limit")
        self.calls += 1
        return self._delegate.generate(prompt, max_tokens=max_tokens)


def _required_environment(name: str) -> str:
    """Citește o cheie numai când rularea reală a fost confirmată explicit."""
    value = os.getenv(name)
    if not value:
        raise RealEvaluationError("missing_environment")
    return value


class _RuntimeEmbedder:
    """Adaptor Voyage local: un singur embedding validat pentru întrebarea curentă."""

    model = "voyage-3.5"

    def __init__(self, client: object) -> None:
        self._client = client

    def embed_query(self, question: str) -> tuple[float, ...]:
        response = self._client.embed([question], model=self.model, input_type="query")
        embeddings = getattr(response, "embeddings", None)
        if not isinstance(embeddings, Sequence) or isinstance(embeddings, (str, bytes)) or len(embeddings) != 1:
            raise RealEvaluationError("invalid_embedding")
        vector = embeddings[0]
        if not isinstance(vector, Sequence) or isinstance(vector, (str, bytes)) or not vector:
            raise RealEvaluationError("invalid_embedding")
        try:
            return tuple(float(value) for value in vector)
        except (TypeError, ValueError) as error:
            raise RealEvaluationError("invalid_embedding") from error


class _RuntimeGenerator:
    """Adaptor R05 identic cu D22: acceptă exclusiv inputul toolului structurat."""

    model = AnthropicTextGenerator.model
    _TOOL_NAME = AnthropicTextGenerator._TOOL_NAME
    _TOOL = AnthropicTextGenerator._TOOL

    def __init__(self, client: object) -> None:
        self._client = client

    def generate(self, prompt: str, *, max_tokens: int) -> GeneratedText:
        response = self._client.messages.create(
            model=self.model, max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}],
            tools=[self._TOOL], tool_choice={"type": "tool", "name": self._TOOL_NAME},
        )
        content = getattr(response, "content", None)
        if getattr(response, "stop_reason", None) == "max_tokens":
            raise RealEvaluationError("invalid_generation")
        if not isinstance(content, Sequence) or isinstance(content, (str, bytes)) or len(content) != 1:
            raise RealEvaluationError("invalid_generation")
        block = content[0]
        payload = getattr(block, "input", None)
        if getattr(block, "type", None) != "tool_use" or getattr(block, "name", None) != self._TOOL_NAME or not isinstance(payload, dict):
            raise RealEvaluationError("invalid_generation")
        return GeneratedText(json.dumps(payload, ensure_ascii=False), truncated=False)


def _build_runtime_embedder() -> _RuntimeEmbedder:
    """Construiește clientul Voyage fără retry, doar după opt-in-ul `--run`."""
    return _RuntimeEmbedder(VoyageClient(api_key=_required_environment("VOYAGE_API_KEY"), timeout=30, max_retries=0))


def _build_runtime_generator() -> _RuntimeGenerator:
    """Construiește clientul Anthropic fără retry, doar după opt-in-ul `--run`."""
    return _RuntimeGenerator(AnthropicClient(api_key=_required_environment("ANTHROPIC_API_KEY"), timeout=30, max_retries=0))


def _citation_publica(citation: object) -> dict[str, str]:
    """Selectează explicit forma publică, fără identificatori interni de sursă."""
    fields = ("id", "cod_document", "titlu_document", "articol", "citat")
    values = {field: getattr(citation, field, None) for field in fields}
    if not all(isinstance(value, str) for value in values.values()):
        raise RealEvaluationError("execution_error")
    return values


def build_real_case_executor(
    *,
    catalog_factory: Callable[[object], object] = PostgresApprovedCatalogRepository,
    repository_factory: Callable[[object], object] = PostgresRetrievalRepository,
    retrieval_service_factory: Callable[[object, object, object], object] = RetrievalService,
    embedder_factory: Callable[[], object] = _build_runtime_embedder,
    generator_factory: Callable[[], object] = _build_runtime_generator,
    generation_service_factory: Callable[[object], object] = GenerationService,
) -> Callable[[RealEvaluationCase, object], Mapping[str, object]]:
    """Compune retrieval/generare direct, fără a folosi ruta publică sau contoare live."""
    embedder = _CountingEmbedder(embedder_factory())
    generator = _CountingGenerator(generator_factory())

    def execute(case: RealEvaluationCase, connection: object) -> Mapping[str, object]:
        embedding_before = embedder.calls
        generation_before = generator.calls
        catalog = catalog_factory(connection)
        catalog_complet = catalog.load() if hasattr(catalog, "load") else catalog
        parser = catalog_complet.create_parser()
        retrieval = retrieval_service_factory(parser, repository_factory(connection), embedder)
        result = retrieval.retrieve(case.question)
        status = getattr(result, "status", None)
        evidence = getattr(result, "evidence", ())
        if not isinstance(status, str) or not isinstance(evidence, Sequence):
            raise RealEvaluationError("execution_error")
        if status != "found" or not evidence:
            return {
                "status": status,
                "answer": "",
                "citations": [],
                "embedding_calls": embedder.calls - embedding_before,
                "generation_calls": generator.calls - generation_before,
            }

        generated = generation_service_factory(generator).generate(case.question, evidence)
        answer = getattr(generated, "raspuns", None)
        citations = getattr(generated, "citari", None)
        if not isinstance(answer, str) or not isinstance(citations, Sequence):
            raise RealEvaluationError("execution_error")
        return {
            "status": "answered",
            "answer": answer,
            "citations": [_citation_publica(citation) for citation in citations],
            "embedding_calls": embedder.calls - embedding_before,
            "generation_calls": generator.calls - generation_before,
        }

    return execute


def build_runtime_executor() -> Callable[[RealEvaluationCase, object], Mapping[str, object]]:
    """Construiește adaptorii cu cheile încărcate lazy numai după `--run` explicit."""
    return build_real_case_executor(embedder_factory=_build_runtime_embedder, generator_factory=_build_runtime_generator)


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


def main(argv: Sequence[str] | None = None) -> int:
    """Rulează costisitor numai cu opt-in explicit; fără acesta nu construiește provideri."""
    parser = argparse.ArgumentParser(description="Rulează pilotul R05 izolat.")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--run", action="store_true", help="Confirmă apelurile providerilor reali.")
    arguments = parser.parse_args(argv)
    if not arguments.run:
        print("run_required", file=sys.stderr)
        return 2
    try:
        report = run_isolated_evaluation(
            arguments.manifest,
            arguments.report,
            connection_factory=_open_db_connection,
            execute_case=build_runtime_executor(),
        )
    except RealEvaluationError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(report["summary"], ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
