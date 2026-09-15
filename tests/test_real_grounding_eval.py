"""Contract mock-first pentru evaluatorul R05 real, izolat de ruta publică."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import real_grounding_eval as evaluation


CAZURI_VALIDE = [
    *[
        {"id": f"E{index:02d}", "category": "exact", "question": f"Întrebare exactă {index}?"}
        for index in range(1, 9)
    ],
    *[
        {"id": f"S{index:02d}", "category": "semantic", "question": f"Întrebare semantică {index}?"}
        for index in range(1, 9)
    ],
    *[
        {"id": f"N{index:02d}", "category": "negative", "question": f"Întrebare negativă {index}?"}
        for index in range(1, 5)
    ],
]


class ConnectionFake:
    def __init__(self):
        self.sessions = []
        self.rollbacks = 0
        self.closes = 0

    def set_session(self, **kwargs):
        self.sessions.append(kwargs)

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closes += 1


def scrie_manifest(tmp_path: Path, cases=CAZURI_VALIDE) -> Path:
    cale = tmp_path / "r05-cases.json"
    cale.write_text(json.dumps({"cases": cases}, ensure_ascii=False), encoding="utf-8")
    return cale


def rezultat_public(case, *, embeddings=0, generations=1):
    return {
        "status": "answered",
        "answer": f"Răspuns de revizuire pentru {case.id}.",
        "citations": [{"cod_document": "NORMATIV-TEST", "articol": "1.1."}],
        "embedding_calls": embeddings,
        "generation_calls": generations,
        "embedding": [0.1, 0.2],
        "chunk_text": "Text intern care nu poate intra în raport.",
    }


def test_manifest_accepta_numai_pilotul_aprobat_de_20_de_cazuri(tmp_path):
    manifest = scrie_manifest(tmp_path)

    cases = evaluation.load_cases(manifest)

    assert len(cases) == 20
    assert [case.category for case in cases].count("exact") == 8
    assert [case.category for case in cases].count("semantic") == 8
    assert [case.category for case in cases].count("negative") == 4
    assert len({case.id for case in cases}) == 20

    with pytest.raises(evaluation.RealEvaluationError, match="invalid_cases"):
        evaluation.load_cases(scrie_manifest(tmp_path, CAZURI_VALIDE[:-1]))


def test_runner_foloseste_numai_o_conexiune_readonly_si_inchide_prin_rollback(tmp_path):
    connection = ConnectionFake()
    report = tmp_path / "r05-report.json"

    rezultat = evaluation.run_isolated_evaluation(
        scrie_manifest(tmp_path),
        report,
        connection_factory=lambda: connection,
        execute_case=lambda case, _connection: rezultat_public(
            case, embeddings=int(case.category == "semantic"), generations=int(case.category != "negative")
        ),
    )

    assert connection.sessions == [{"readonly": True, "autocommit": False}]
    assert connection.rollbacks == connection.closes == 1
    assert rezultat == json.loads(report.read_text(encoding="utf-8"))
    assert rezultat["summary"] == {"cases": 20, "embedding_calls": 8, "generation_calls": 16}


def test_runner_opreste_la_eroare_fara_retry_si_fara_raport_partial(tmp_path):
    connection = ConnectionFake()
    report = tmp_path / "r05-report.json"
    calls = []

    def failure(case, _connection):
        calls.append(case.id)
        raise RuntimeError("provider indisponibil")

    with pytest.raises(evaluation.RealEvaluationError, match="execution_error"):
        evaluation.run_isolated_evaluation(
            scrie_manifest(tmp_path), report, connection_factory=lambda: connection, execute_case=failure
        )

    assert calls == ["E01"]
    assert not report.exists()
    assert connection.rollbacks == connection.closes == 1


def test_runner_aplica_limitele_inainte_de_publicare_si_omite_datele_interne(tmp_path):
    connection = ConnectionFake()
    report = tmp_path / "r05-report.json"

    def prea_multe_embeddinguri(case, _connection):
        return rezultat_public(case, embeddings=9 if case.id == "E01" else 0, generations=0)

    with pytest.raises(evaluation.RealEvaluationError, match="cost_limit"):
        evaluation.run_isolated_evaluation(
            scrie_manifest(tmp_path), report, connection_factory=lambda: connection, execute_case=prea_multe_embeddinguri
        )

    assert not report.exists()

    result = evaluation.run_isolated_evaluation(
        scrie_manifest(tmp_path),
        report,
        connection_factory=ConnectionFake,
        execute_case=lambda case, _connection: rezultat_public(
            case, embeddings=int(case.category == "semantic"), generations=int(case.category != "negative")
        ),
    )
    serialized = json.dumps(result, ensure_ascii=False)
    assert "chunk_text" not in serialized
    assert '"embedding"' not in serialized
    assert "Răspuns de revizuire" in serialized
    assert result["cases"][0] == {
        "id": "E01",
        "category": "exact",
        "question": "Întrebare exactă 1?",
        "status": "answered",
        "answer": "Răspuns de revizuire pentru E01.",
        "citations": [{"cod_document": "NORMATIV-TEST", "articol": "1.1."}],
    }


def test_runner_nu_importa_sau_apeleaza_ruta_fastapi_si_nu_cunoaste_bugete_live():
    source = Path(evaluation.__file__).read_text(encoding="utf-8")

    forbidden = ("FastAPI", "TestClient", "POST /intreaba", "paid_call_budget", "reserve_paid_call")
    assert all(value not in source for value in forbidden)


class EmbedderCounter:
    def __init__(self):
        self.calls = 0

    def embed_query(self, _question):
        self.calls += 1
        return (0.1, 0.2)


class GeneratorCounter:
    def __init__(self):
        self.calls = 0

    def generate(self, _prompt, *, max_tokens):
        self.calls += 1
        assert max_tokens == 1200
        return '{"raspuns":"pachet controlat","pasaje":[]}'


class CatalogFake:
    def create_parser(self):
        return "parser-controlat"


class RetrievalFake:
    def __init__(self, _parser, _repository, embedder, result):
        self.embedder = embedder
        self.result = result

    def retrieve(self, question, _context=()):
        if question.startswith("semantic"):
            self.embedder.embed_query(question)
        return self.result


class GenerationServiceFake:
    def __init__(self, generator):
        self.generator = generator

    def generate(self, _question, _evidence):
        self.generator.generate("prompt-controlat", max_tokens=1200)
        return SimpleNamespace(
            raspuns="Răspuns real controlat.",
            citari=(
                SimpleNamespace(
                    id="C1",
                    cod_document="NP TEST-1",
                    titlu_document="Titlu public",
                    articol="1.1.",
                    citat="Pasaj public controlat.",
                    source_key="nu-este-public",
                ),
            ),
        )


def executor_real_controlat(result, embedder, generator):
    return evaluation.build_real_case_executor(
        catalog_factory=lambda _connection: CatalogFake(),
        repository_factory=lambda _connection: object(),
        retrieval_service_factory=lambda parser, repository, injected_embedder: RetrievalFake(
            parser, repository, injected_embedder, result
        ),
        embedder_factory=lambda: embedder,
        generator_factory=lambda: generator,
        generation_service_factory=GenerationServiceFake,
    )


def test_adaptor_real_numara_apelurile_din_wrapuri_si_publica_numai_citarea_publica():
    embedder = EmbedderCounter()
    generator = GeneratorCounter()
    executor = executor_real_controlat(SimpleNamespace(status="found", evidence=(object(),)), embedder, generator)

    rezultat = executor(evaluation.RealEvaluationCase("S01", "semantic", "semantic controlat?"), ConnectionFake())

    assert rezultat["embedding_calls"] == 1
    assert rezultat["generation_calls"] == 1
    assert rezultat["citations"] == [
        {
            "id": "C1",
            "cod_document": "NP TEST-1",
            "titlu_document": "Titlu public",
            "articol": "1.1.",
            "citat": "Pasaj public controlat.",
        }
    ]
    assert "source_key" not in json.dumps(rezultat, ensure_ascii=False)


@pytest.mark.parametrize("status", ("not_found", "ambiguous_article", "ambiguous_reference", "unsupported_answer"))
def test_adaptor_real_nu_genereaza_pentru_status_fara_dovezi(status):
    embedder = EmbedderCounter()
    generator = GeneratorCounter()
    executor = executor_real_controlat(SimpleNamespace(status=status, evidence=()), embedder, generator)

    rezultat = executor(evaluation.RealEvaluationCase("N01", "negative", "întrebare negativă?"), ConnectionFake())

    assert rezultat["status"] == status
    assert rezultat["answer"] == ""
    assert rezultat["citations"] == []
    assert rezultat["generation_calls"] == generator.calls == 0


def test_cli_refuza_rularea_fara_run_fara_sa_construiasca_provider(monkeypatch, tmp_path):
    manifest = scrie_manifest(tmp_path)
    report = tmp_path / "r05-report.json"
    invoked = []
    monkeypatch.setattr(evaluation, "build_runtime_executor", lambda: invoked.append(True))

    assert evaluation.main(["--manifest", str(manifest), "--report", str(report)]) == 2
    assert invoked == []
    assert not report.exists()


def test_adaptor_refuza_al_noualea_embedding_inainte_de_delegate():
    embedder = EmbedderCounter()
    executor = executor_real_controlat(SimpleNamespace(status="found", evidence=(object(),)), embedder, GeneratorCounter())

    for index in range(8):
        executor(evaluation.RealEvaluationCase(f"S{index:02d}", "semantic", "semantic controlat?"), ConnectionFake())

    with pytest.raises(evaluation.RealEvaluationError, match="cost_limit"):
        executor(evaluation.RealEvaluationCase("S09", "semantic", "semantic controlat?"), ConnectionFake())

    assert embedder.calls == 8


def test_adaptor_refuza_a_saptesprezecea_generare_inainte_de_delegate():
    generator = GeneratorCounter()
    executor = executor_real_controlat(SimpleNamespace(status="found", evidence=(object(),)), EmbedderCounter(), generator)

    for index in range(16):
        executor(evaluation.RealEvaluationCase(f"E{index:02d}", "exact", "exact controlat?"), ConnectionFake())

    with pytest.raises(evaluation.RealEvaluationError, match="cost_limit"):
        executor(evaluation.RealEvaluationCase("E17", "exact", "exact controlat?"), ConnectionFake())

    assert generator.calls == 16


def test_runtime_generator_r05_forteaza_toolul_d22_si_refuza_text_liber():
    calls = []

    class MessagesFake:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                content=[SimpleNamespace(
                    type="tool_use", name="return_grounded_answer",
                    input={"raspuns": "Răspuns [C1]", "pasaje": [{"id": "C1", "citat": "literal"}]},
                )],
                stop_reason="tool_use",
            )

    generated = evaluation._RuntimeGenerator(SimpleNamespace(messages=MessagesFake())).generate("prompt", max_tokens=1200)

    assert json.loads(generated.text)["raspuns"] == "Răspuns [C1]"
    assert calls[0]["tool_choice"] == {"type": "tool", "name": "return_grounded_answer"}

    invalid_responses = [
        SimpleNamespace(content=[SimpleNamespace(type="text", text="nu accept")], stop_reason="end_turn"),
        SimpleNamespace(content=[SimpleNamespace(type="tool_use", name="alt_tool", input={})], stop_reason="tool_use"),
        SimpleNamespace(content=[SimpleNamespace(type="tool_use", name="return_grounded_answer", input="invalid")], stop_reason="tool_use"),
        SimpleNamespace(content=[SimpleNamespace(type="tool_use", name="return_grounded_answer", input={}), SimpleNamespace(type="text", text="extra")], stop_reason="tool_use"),
        SimpleNamespace(content=[SimpleNamespace(type="tool_use", name="return_grounded_answer", input={})], stop_reason="max_tokens"),
    ]
    for invalid_response in invalid_responses:
        class InvalidMessagesFake:
            def create(self, **_kwargs):
                return invalid_response

        with pytest.raises(evaluation.RealEvaluationError, match="invalid_generation"):
            evaluation._RuntimeGenerator(SimpleNamespace(messages=InvalidMessagesFake())).generate("prompt", max_tokens=1200)


def test_factory_runtime_construieste_clienti_fara_retry_si_cu_timeout(monkeypatch):
    voyage_calls = []
    anthropic_calls = []
    voyage_client = object()
    anthropic_client = object()

    def voyage_factory(**kwargs):
        voyage_calls.append(kwargs)
        return voyage_client

    def anthropic_factory(**kwargs):
        anthropic_calls.append(kwargs)
        return anthropic_client

    monkeypatch.setattr(evaluation, "VoyageClient", voyage_factory)
    monkeypatch.setattr(evaluation, "AnthropicClient", anthropic_factory)
    monkeypatch.setattr(evaluation, "_required_environment", lambda name: f"fake-{name}")

    embedder = evaluation._build_runtime_embedder()
    generator = evaluation._build_runtime_generator()

    assert embedder._client is voyage_client
    assert generator._client is anthropic_client
    assert voyage_calls == [{"api_key": "fake-VOYAGE_API_KEY", "timeout": 30, "max_retries": 0}]
    assert anthropic_calls == [{"api_key": "fake-ANTHROPIC_API_KEY", "timeout": 30, "max_retries": 0}]
