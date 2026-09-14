"""Contract mock-first pentru evaluatorul R05 real, izolat de ruta publică."""

from __future__ import annotations

import json
from pathlib import Path

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
