"""Teste pentru evaluatorul local, nu o cerință ca produsul să rămână vulnerabil."""

import json
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

import grounding_eval as evaluation
from generation_core import (
    GenerationResult,
    GenerationService,
    GenerationValidationError,
    PublicCitation,
)


def case_by_id(case_id):
    return next(case for case in evaluation.build_cases() if case.id == case_id)


def published(candidate, evidence):
    return GenerationResult(
        "answered",
        candidate,
        tuple(
            PublicCitation(
                f"C{index}", item.cod_document, item.titlu_document,
                item.articol, item.content,
            )
            for index, item in enumerate(evidence, start=1)
        ),
    )


class AcceptAll:
    """Control intenționat permisiv; nu primește gold-ul cazurilor."""

    def __init__(self, generator):
        self.generator = generator

    def generate(self, question, evidence):
        payload = json.loads(self.generator.generate(question, max_tokens=1200))
        return published(payload["raspuns"], evidence)


class RejectAll(AcceptAll):
    def generate(self, question, evidence):
        self.generator.generate(question, max_tokens=1200)
        raise GenerationValidationError("refuz sintetic tipat")


class ExecutionFailure(AcceptAll):
    def generate(self, question, evidence):
        self.generator.generate(question, max_tokens=1200)
        raise RuntimeError("defecțiune sintetică")


class ImprovedControl(AcceptAll):
    """Script de test pentru G07/G18, NU validator propus sau detecție semantică."""

    def generate(self, question, evidence):
        result = super().generate(question, evidence)
        if result.raspuns == "Lungimea tijei fictive Zori este 19 mm. [C1]":
            raise GenerationValidationError("refuz fix pentru controlul G07")
        return result


def assert_derived_summary(report):
    cases = report["cases"]
    summary = report["summary"]
    findings = [finding for case in cases for finding in case["findings"]]
    assert summary["total_cases"] == len(cases)
    assert summary["cases_with_findings"] == len([case for case in cases if case["findings"]])
    assert summary["total_findings"] == len(findings)
    assert summary["fake_calls"] == sum(case["fake_calls"] for case in cases)
    for kind in evaluation.FINDING_KINDS:
        assert summary[kind] == len([finding for finding in findings if finding["kind"] == kind])
    for counter, outcome in (("published", "published"), ("typed_refusals", "rejected"), ("not_found", "not_found")):
        assert summary[counter] == len([case for case in cases if case["observation"]["outcome"] == outcome])
    assert report["has_findings"] is bool(findings)
    assert summary["total_cases"] == (
        summary["published"] + summary["typed_refusals"] + summary["not_found"] + summary["execution_error"]
    )


def test_grounding_eval_fixtures_have_unique_ids_explicit_gold_and_fictional_sources():
    cases = evaluation.build_cases()
    assert len(cases) >= 16
    assert len({case.id for case in cases}) == len(cases)
    assert {case.expected_publishable for case in cases} == {True, False}
    for case in cases:
        assert case.id and case.category and case.question and case.candidate
        assert "fictiv" in case.question
        assert type(case.expected_publishable) is bool
        assert len(case.justification.strip()) > 30
        assert "C1" in case.justification or "C2" in case.justification
        assert case.evidence
        for item in case.evidence:
            assert item.cod_document.startswith("FICTIV-")
            assert "fictiv" in item.titlu_document
            assert item.content.startswith("[TEXT FICTIV PENTRU EVALUARE]")
        for passage in case.required_passages:
            assert passage.text
            evidence_by_id = {f"C{index}": item for index, item in enumerate(case.evidence, start=1)}
            assert passage.citation_id in evidence_by_id
            assert passage.text in evidence_by_id[passage.citation_id].content


def test_grounding_eval_model_passages_are_explicit_literal_inputs_not_semantic_verdicts():
    cases = evaluation.build_cases()
    assert [case.id for case in cases] == [f"G{index:02d}" for index in range(1, 20)]
    for case in cases:
        by_id = {f"C{index}": item for index, item in enumerate(case.evidence, start=1)}
        used_ids = set(re.findall(r"\[(C[1-9][0-9]*)\]", case.candidate))
        assert {passage.id for passage in case.model_passages} == used_ids
        assert len(case.model_passages) == len(used_ids)
        for passage in case.model_passages:
            assert isinstance(passage, evaluation.ModelPassage)
            assert isinstance(passage.citat, str) and passage.citat.strip()
            assert len(passage.citat) <= 600
            if case.id == "G16":
                assert passage.id == "C99" and passage.citat in case.evidence[0].content
            else:
                assert passage.citat in by_id[passage.id].content
    for case_id in [f"G{index:02d}" for index in range(7, 16)] + ["G19"]:
        case = case_by_id(case_id)
        assert case.expected_publishable is False and case.model_passages
    for case_id in ("G18", "G19"):
        passage = case_by_id(case_id).model_passages[0]
        assert passage.id == "C2"
        assert case_by_id(case_id).evidence[1].content.index(passage.citat) > 600


def test_grounding_eval_changing_gold_never_changes_generator_payload():
    case = case_by_id("G18")
    payloads = []

    def capture(generator):
        assert set(vars(generator)) == {"payload", "calls"}
        payloads.append(json.loads(generator.payload))
        return AcceptAll(generator)

    evaluation.evaluate_case(case, service_factory=capture)
    evaluation.evaluate_case(replace(
        case, expected_publishable=False, justification="Gold modificat numai pentru test.",
        required_passages=(evaluation.PassageRequirement("C1", "gold care nu intră în generator"),),
    ), service_factory=capture)

    assert payloads[0] == payloads[1] == {
        "raspuns": case.candidate,
        "pasaje": [{"id": "C2", "citat": "Presiunea admisă în globul fictiv Sora este 17 kPa."}],
    }


def test_grounding_eval_r06_real_service_has_no_missing_passages_false_refusals_or_execution_errors():
    report = evaluation.run_evaluation()
    assert report["summary"]["relevant_passage_missing"] == 0
    assert report["summary"]["publishable_rejected"] == 0
    assert report["summary"]["execution_error"] == 0
    # Nu fixăm non_publishable_published: o remediere R05 poate reduce acel contor.
    for case_id, error_type in (("G16", "UnknownCitationError"), ("G17", "MissingCitationError")):
        case = next(item for item in report["cases"] if item["id"] == case_id)
        assert case["observation"]["outcome"] == "rejected"
        assert case["observation"]["error_type"] == error_type
        assert case["fake_calls"] == 1


def test_grounding_eval_fixture_categories_cover_semantic_and_structural_controls():
    gold_by_category = {case.category: case.expected_publishable for case in evaluation.build_cases()}
    correct = {"literal", "paraphrase", "negation_preserved", "condition_preserved", "multiple_citations", "exception_preserved", "late_relevant_passage"}
    incorrect = {"wrong_number", "wrong_unit", "wrong_polarity", "condition_removed", "minimum_maximum", "exception_omitted", "unsupported_second_claim", "wrong_evidence_link", "number_in_irrelevant_evidence", "structural_unknown_citation", "structural_missing_citation"}
    assert all(gold_by_category[category] is True for category in correct)
    assert all(gold_by_category[category] is False for category in incorrect)
    assert "[C99]" in case_by_id("G16").candidate
    assert "[C" not in case_by_id("G17").candidate


def test_grounding_eval_irrelevant_number_and_wrong_citation_are_explicit_controls():
    number = case_by_id("G15")
    assert "19" in number.candidate and "19" in number.evidence[1].content
    assert "19" not in number.evidence[0].content
    wrong_link = case_by_id("G14")
    assert "[C1]" in wrong_link.candidate and "[C2]" not in wrong_link.candidate
    assert "turcoaz" not in wrong_link.evidence[0].content
    assert "turcoaz" in wrong_link.evidence[1].content


@pytest.mark.parametrize("case_id", ["G18", "G19"])
def test_grounding_eval_late_gold_is_after_600_characters_in_corresponding_evidence(case_id):
    case = case_by_id(case_id)
    passage = case.required_passages[0]
    assert passage.citation_id == "C2"
    assert case.evidence[1].content.index(passage.text) > 600
    assert passage.text not in case.evidence[0].content


def test_grounding_eval_fake_gets_only_candidate_and_counts_every_call():
    payload = json.dumps({
        "raspuns": "candidat fictiv fix [C1]",
        "pasaje": [{"id": "C1", "citat": "pasaj fictiv fix"}],
    })
    generator = evaluation.FixedGenerator(payload)
    assert vars(generator) == {"payload": payload, "calls": 0}
    assert generator.generate("prompt fictiv unu", max_tokens=4) == generator.payload
    assert generator.generate("prompt fictiv doi", max_tokens=8) == generator.payload
    assert generator.calls == 2


def test_grounding_eval_default_runner_uses_real_service_without_gold(monkeypatch):
    case = case_by_id("G01")
    calls = []
    original = GenerationService.generate

    def spy(self, question, evidence):
        calls.append((question, evidence))
        return original(self, question, evidence)

    monkeypatch.setattr(GenerationService, "generate", spy)
    result = evaluation.evaluate_case(case)
    assert calls == [(case.question, case.evidence)]
    assert result["observation"]["outcome"] != "execution_error"
    assert type(result["fake_calls"]) is int


def test_grounding_eval_gold_does_not_depend_on_observed_output():
    case = case_by_id("G07")
    accepted = evaluation.evaluate_case(case, service_factory=AcceptAll)
    rejected = evaluation.evaluate_case(case, service_factory=RejectAll)
    assert accepted["expected_publishable"] is rejected["expected_publishable"] is False
    assert accepted["justification"] == rejected["justification"] == case.justification
    assert accepted["findings"] == [{"kind": "non_publishable_published"}]
    assert rejected["findings"] == []


@pytest.mark.parametrize("factory", [None, AcceptAll, RejectAll, ExecutionFailure])
def test_grounding_eval_summary_is_derived_and_report_is_deterministic(factory):
    first = evaluation.run_evaluation(service_factory=factory)
    second = evaluation.run_evaluation(service_factory=factory)
    assert first == second
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["kind"] == "synthetic_fixed_output_grounding"
    assert first["notice"] == "candidati fixi sintetici, nu acuratete model live"
    assert_derived_summary(first)


def test_grounding_eval_accept_all_detects_false_publications_not_false_refusals():
    cases = evaluation.build_cases()
    report = evaluation.run_evaluation(cases, service_factory=AcceptAll)
    assert report["summary"]["non_publishable_published"] == sum(not case.expected_publishable for case in cases)
    assert report["summary"]["publishable_rejected"] == 0
    assert report["summary"]["relevant_passage_missing"] == 0
    assert report["summary"]["fake_calls"] == len(cases)
    assert evaluation.exit_code(report) == 1


def test_grounding_eval_reject_all_detects_false_refusals_not_missing_unpublished_passages():
    cases = evaluation.build_cases()
    report = evaluation.run_evaluation(cases, service_factory=RejectAll)
    assert report["summary"]["publishable_rejected"] == sum(case.expected_publishable for case in cases)
    assert report["summary"]["non_publishable_published"] == 0
    assert report["summary"]["relevant_passage_missing"] == 0
    assert report["summary"]["typed_refusals"] == len(cases)
    for result in report["cases"]:
        assert result["passage_status"] == ("not_observed" if result["required_passages"] else "not_applicable")


def test_grounding_eval_improved_results_can_be_green_without_changing_evaluator():
    cases = (case_by_id("G07"), case_by_id("G18"))
    permissive = evaluation.run_evaluation(cases, service_factory=AcceptAll)
    improved = evaluation.run_evaluation(cases, service_factory=ImprovedControl)
    assert permissive["has_findings"] is True
    assert improved["has_findings"] is False
    assert improved["summary"]["total_findings"] == 0
    assert improved["summary"]["execution_error"] == 0
    assert evaluation.exit_code(improved) == 0
    assert_derived_summary(improved)


@pytest.mark.parametrize("case_id", ["G01", "G07"])
def test_grounding_eval_unexpected_errors_are_never_correct_refusals(case_id):
    report = evaluation.run_evaluation((case_by_id(case_id),), service_factory=ExecutionFailure)
    result = report["cases"][0]
    assert result["observation"]["outcome"] == "execution_error"
    assert result["observation"]["error_type"] == "RuntimeError"
    assert result["findings"] == [{"kind": "execution_error"}]
    assert report["summary"]["typed_refusals"] == 0
    assert report["summary"]["publishable_rejected"] == 0
    assert report["summary"]["non_publishable_published"] == 0
    assert evaluation.exit_code(report) == 2


def test_grounding_eval_factory_failure_is_execution_error():
    def broken_factory(generator):
        raise OSError("defecțiune locală fictivă")

    result = evaluation.evaluate_case(case_by_id("G07"), service_factory=broken_factory)
    assert result["observation"]["outcome"] == "execution_error"
    assert result["fake_calls"] == 0
    assert result["findings"] == [{"kind": "execution_error"}]


def test_grounding_eval_not_found_is_not_a_typed_refusal():
    class NotFound(AcceptAll):
        def generate(self, question, evidence):
            return GenerationResult("not_found", "Lipsă sintetică de dovezi.", ())

    report = evaluation.run_evaluation((case_by_id("G01"), case_by_id("G07")), service_factory=NotFound)
    assert report["summary"]["not_found"] == 2
    assert report["summary"]["typed_refusals"] == 0
    assert report["summary"]["publishable_rejected"] == 1
    assert report["cases"][1]["findings"] == []
    assert_derived_summary(report)


def test_grounding_eval_invalid_service_status_is_execution_error():
    class InvalidStatus(AcceptAll):
        def generate(self, question, evidence):
            return GenerationResult("invalid", "răspuns fictiv", ())

    result = evaluation.evaluate_case(case_by_id("G07"), service_factory=InvalidStatus)
    assert result["observation"]["outcome"] == "execution_error"
    assert result["observation"]["error_type"] == "ValueError"


@pytest.mark.parametrize("case_id", ["G18", "G19"])
def test_grounding_eval_passage_in_wrong_citation_does_not_count(case_id):
    case = case_by_id(case_id)
    passage = case.required_passages[0]

    class WrongCitation(AcceptAll):
        def generate(self, question, evidence):
            result = super().generate(question, evidence)
            return replace(result, citari=(
                replace(result.citari[0], citat=passage.text),
                replace(result.citari[1], citat="Fragment fictiv fără regula cerută."),
            ))

    report = evaluation.run_evaluation((case,), service_factory=WrongCitation)
    result = report["cases"][0]
    assert result["passage_status"] == "missing"
    assert result["passage_checks"][0]["status"] == "missing"
    assert {"kind": "relevant_passage_missing", "citation_id": "C2", "text": passage.text} in result["findings"]
    assert report["summary"]["cases_with_findings"] == 1
    assert report["summary"]["total_findings"] == (1 if case.expected_publishable else 2)
    assert_derived_summary(report)


def test_grounding_eval_missing_corresponding_citation_is_missing_passage():
    class NoCitations(AcceptAll):
        def generate(self, question, evidence):
            return replace(super().generate(question, evidence), citari=())

    result = evaluation.evaluate_case(case_by_id("G18"), service_factory=NoCitations)
    assert result["passage_status"] == "missing"
    assert result["findings"][0]["citation_id"] == "C2"


def test_grounding_eval_multiple_missing_passages_are_separate_findings():
    class EmptyQuotes(AcceptAll):
        def generate(self, question, evidence):
            result = super().generate(question, evidence)
            return replace(result, citari=tuple(replace(citation, citat="") for citation in result.citari))

    report = evaluation.run_evaluation((case_by_id("G05"),), service_factory=EmptyQuotes)
    assert report["summary"]["cases_with_findings"] == 1
    assert report["summary"]["total_findings"] == 2
    assert report["summary"]["relevant_passage_missing"] == 2
    assert {finding["citation_id"] for finding in report["cases"][0]["findings"]} == {"C1", "C2"}


def test_grounding_eval_no_passage_requirement_is_not_applicable():
    result = evaluation.evaluate_case(case_by_id("G07"), service_factory=AcceptAll)
    assert result["passage_status"] == "not_applicable"
    assert result["passage_checks"] == []
    assert not any(finding["kind"] == "relevant_passage_missing" for finding in result["findings"])


@pytest.mark.parametrize("factory, expected_exit", [(AcceptAll, 1), (ImprovedControl, 0), (ExecutionFailure, 2)])
def test_grounding_eval_cli_writes_json_and_exit_codes(tmp_path, monkeypatch, capsys, factory, expected_exit):
    cases = (case_by_id("G07"), case_by_id("G18"))
    monkeypatch.setattr(evaluation, "build_cases", lambda: cases)
    monkeypatch.setattr(evaluation, "GenerationService", factory)
    output = tmp_path / "diagnostic.json"
    assert evaluation.main(["--output", str(output)]) == expected_exit
    first_bytes = output.read_bytes()
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["kind"] == evaluation.KIND
    assert isinstance(report["has_findings"], bool)
    assert isinstance(report["cases"], list)
    assert evaluation.exit_code(report) == expected_exit
    assert_derived_summary(report)
    assert evaluation.main(["--output", str(output)]) == expected_exit
    assert output.read_bytes() == first_bytes
    stdout = capsys.readouterr().out
    assert evaluation.NOTICE in stdout and '"fake_calls"' in stdout


def test_grounding_eval_cli_write_failure_is_infrastructure_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(evaluation, "GenerationService", AcceptAll)
    assert evaluation.main(["--output", str(tmp_path)]) == 2
    assert "Eroare de infrastructura" in capsys.readouterr().err


def test_grounding_eval_cli_runner_failure_is_infrastructure_error(tmp_path, monkeypatch, capsys):
    def broken_runner():
        raise RuntimeError("defecțiune evaluator fictivă")

    monkeypatch.setattr(evaluation, "run_evaluation", broken_runner)
    output = tmp_path / "diagnostic.json"
    assert evaluation.main(["--output", str(output)]) == 2
    assert not output.exists()
    assert "RuntimeError" in capsys.readouterr().err


def test_grounding_eval_cli_requires_explicit_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as error:
        evaluation.main([])
    assert error.value.code == 2
    assert list(tmp_path.iterdir()) == []


def test_grounding_eval_cli_real_service_exit_matches_diagnostic_not_frozen_score(tmp_path):
    script = Path(evaluation.__file__).resolve()
    output = tmp_path / "real-service-synthetic.json"
    process = subprocess.run(
        [sys.executable, "-B", str(script), "--output", str(output)],
        cwd=tmp_path, capture_output=True, timeout=30,
    )
    assert output.exists(), process.stderr.decode(errors="replace")
    report = json.loads(output.read_text(encoding="utf-8"))
    assert_derived_summary(report)
    assert report["summary"]["execution_error"] == 0
    assert process.returncode == (1 if report["has_findings"] else 0)


def test_grounding_eval_import_has_no_output_files_or_generation(tmp_path):
    module_dir = str(Path(evaluation.__file__).resolve().parent)
    code = (
        f"import sys; sys.path.insert(0, {module_dir!r}); "
        "import generation_core; "
        "generation_core.GenerationService.__init__ = lambda *a, **k: sys.exit(91); "
        "import grounding_eval"
    )
    process = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=tmp_path, capture_output=True, timeout=30,
    )
    assert process.returncode == 0, process.stderr.decode(errors="replace")
    assert process.stdout == b"" and process.stderr == b""
    assert list(tmp_path.iterdir()) == []


def test_grounding_eval_execution_error_takes_priority_over_diagnostic_findings():
    class MixedControl(AcceptAll):
        def generate(self, question, evidence):
            result = super().generate(question, evidence)
            if result.raspuns == "Lungimea tijei fictive Zori este 19 mm. [C1]":
                raise RuntimeError("defecțiune sintetică pentru G07")
            return result

    report = evaluation.run_evaluation(
        (case_by_id("G07"), case_by_id("G08")), service_factory=MixedControl,
    )
    assert report["summary"]["execution_error"] == 1
    assert report["summary"]["non_publishable_published"] == 1
    assert report["summary"]["total_findings"] == 2
    assert evaluation.exit_code(report) == 2
    assert_derived_summary(report)
