"""Diagnostic local pe candidați ficși sintetici, nu acuratețe model live.

Etichetele sunt definite explicit din dovezile fictive, nu din verdictul runtime.
Etichetele se aplică candidaților ficși; dacă un serviciu viitor îi rescrie înainte de publicare,
trebuie reevaluate pentru textul rezultat, pe care evaluatorul nu îl verifică semantic.
Nu modifică GenerationService și nu configurează provideri, DB sau fișiere la import.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Sequence

from generation_core import GenerationService, GenerationValidationError
from retrieval_core import Evidence

KIND = "synthetic_fixed_output_grounding"
NOTICE = "candidati fixi sintetici, nu acuratete model live"
FINDING_KINDS = (
    "non_publishable_published",
    "publishable_rejected",
    "relevant_passage_missing",
    "execution_error",
)


@dataclass(frozen=True)
class PassageRequirement:
    """Pasaj gold literal, verificat numai în citarea cu acest ID."""

    citation_id: str
    text: str


@dataclass(frozen=True)
class ModelPassage:
    """Intrare explicită furnizată de modelul fix, separată de cerințele gold."""

    id: str
    citat: str


@dataclass(frozen=True)
class GroundingCase:
    id: str
    category: str
    question: str
    evidence: tuple[Evidence, ...]
    candidate: str
    expected_publishable: bool
    justification: str
    required_passages: tuple[PassageRequirement, ...] = ()
    model_passages: tuple[ModelPassage, ...] = ()


class FixedGenerator:
    """Primește numai payloadul candidatului și pasajelor, niciodată datele gold."""

    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.calls = 0

    def generate(self, prompt: str, *, max_tokens: int) -> str:
        self.calls += 1
        return self.payload


def _evidence(index: int, text: str) -> Evidence:
    return Evidence(
        chunk_id=index,
        document_id=f"document-fictiv-{index}",
        cod_document=f"FICTIV-LAB-{index}",
        titlu_document=f"Document fictiv de laborator {index}",
        articol=f"articol-fictiv-{index}",
        articol_normalizat=f"articol-fictiv-{index}",
        content="[TEXT FICTIV PENTRU EVALUARE] " + text,
        content_hash=f"hash-fictiv-{index}",
    )


def build_cases() -> tuple[GroundingCase, ...]:
    """Fixture-uri inventate integral; verdictul nu se deduce din serviciu."""
    length = "Lungimea tijei fictive Zori este 12 mm."
    negative = "Clapeta fictivă Nori nu se deschide în modul violet."
    condition = "Lampa fictivă Mira se aprinde numai dacă sigiliul este verde."
    minimum = "Lățimea minimă a benzii fictive Luma este 8 mm."
    exception = "Toate capsulele fictive se marchează, cu excepția capsulelor opace."
    colour = "Carcasa fictivă Vela este turcoaz."
    late = "Presiunea admisă în globul fictiv Sora este 17 kPa."
    long_text = (
        "Notă fictivă de decor, fără reguli despre presiune. " * 18 + late
    )
    return (
        GroundingCase(
            "G01", "literal", "Ce lungime are tija fictivă Zori?",
            (_evidence(1, length),), "Lungimea tijei fictive Zori este 12 mm. [C1]",
            True, "C1 spune explicit 12 mm pentru Zori; candidatul redă literal valoarea și unitatea.",
            (PassageRequirement("C1", length),),
            model_passages=(ModelPassage("C1", length),),
        ),
        GroundingCase(
            "G02", "paraphrase", "Ce culoare are carcasa fictivă Vela?",
            (_evidence(1, colour),), "Turcoaz este culoarea carcasei fictive Vela. [C1]",
            True, "C1 atribuie culoarea turcoaz carcasei Vela; se schimbă doar ordinea cuvintelor.",
            model_passages=(ModelPassage("C1", colour),),
        ),
        GroundingCase(
            "G03", "negation_preserved", "Se deschide clapeta fictivă Nori în modul violet?",
            (_evidence(1, negative),), "În modul violet, clapeta fictivă Nori nu se deschide. [C1]",
            True, "C1 interzice deschiderea în modul violet; negația și modul sunt păstrate.",
            model_passages=(ModelPassage("C1", negative),),
        ),
        GroundingCase(
            "G04", "condition_preserved", "În ce condiție se aprinde lampa fictivă Mira?",
            (_evidence(1, condition),), "Lampa fictivă Mira se aprinde numai dacă sigiliul este verde. [C1]",
            True, "C1 impune sigiliul verde ca o condiție necesară; candidatul păstrează «numai dacă».",
            model_passages=(ModelPassage("C1", condition),),
        ),
        GroundingCase(
            "G05", "multiple_citations", "Descrie tija fictivă Zori și carcasa fictivă Vela.",
            (_evidence(1, length), _evidence(2, colour)),
            "Tija fictivă Zori are lungimea de 12 mm. [C1] Carcasa fictivă Vela este turcoaz. [C2]",
            True, "Lungimea este dată de C1, culoarea de C2; fiecare afirmație citează propria dovadă.",
            (PassageRequirement("C1", length), PassageRequirement("C2", colour)),
            model_passages=(ModelPassage("C1", length), ModelPassage("C2", colour)),
        ),
        GroundingCase(
            "G06", "exception_preserved", "Ce capsule fictive se marchează?",
            (_evidence(1, exception),), "Se marchează toate capsulele fictive, exceptând capsulele opace. [C1]",
            True, "C1 exclude capsulele opace; parafraza păstrează exact excepția.",
            model_passages=(ModelPassage("C1", exception),),
        ),
        GroundingCase(
            "G07", "wrong_number", "Ce lungime are tija fictivă Zori?",
            (_evidence(1, length),), "Lungimea tijei fictive Zori este 19 mm. [C1]",
            False, "C1 dă 12 mm, nu 19 mm; ID-ul valid nu susține numărul schimbat.",
            model_passages=(ModelPassage("C1", length),),
        ),
        GroundingCase(
            "G08", "wrong_unit", "Ce lungime are tija fictivă Zori?",
            (_evidence(1, length),), "Lungimea tijei fictive Zori este 12 cm. [C1]",
            False, "C1 folosește mm, nu cm; păstrarea numărului nu justifică schimbarea unității.",
            model_passages=(ModelPassage("C1", length),),
        ),
        GroundingCase(
            "G09", "wrong_polarity", "Se deschide clapeta fictivă Nori în modul violet?",
            (_evidence(1, negative),), "Clapeta fictivă Nori se deschide în modul violet. [C1]",
            False, "C1 spune «nu se deschide»; candidatul afirmă opusul în același mod.",
            model_passages=(ModelPassage("C1", negative),),
        ),
        GroundingCase(
            "G10", "condition_removed", "În ce condiție se aprinde lampa fictivă Mira?",
            (_evidence(1, condition),), "Lampa fictivă Mira se aprinde indiferent de culoarea sigiliului. [C1]",
            False, "C1 cere sigiliul verde; eliminarea condiției extinde nejustificat regula.",
            model_passages=(ModelPassage("C1", condition),),
        ),
        GroundingCase(
            "G11", "minimum_maximum", "Care este limita lățimii benzii fictive Luma?",
            (_evidence(1, minimum),), "Lățimea maximă a benzii fictive Luma este 8 mm. [C1]",
            False, "C1 stabilește un minim de 8 mm, nu un maxim; sensul limitei este inversat.",
            model_passages=(ModelPassage("C1", minimum),),
        ),
        GroundingCase(
            "G12", "exception_omitted", "Ce capsule fictive se marchează?",
            (_evidence(1, exception),), "Toate capsulele fictive se marchează. [C1]",
            False, "C1 exclude capsulele opace; afirmația universală omite excepția explicită.",
            model_passages=(ModelPassage("C1", exception),),
        ),
        GroundingCase(
            "G13", "unsupported_second_claim", "Descrie tija fictivă Zori.",
            (_evidence(1, length),), "Tija fictivă Zori are 12 mm și este ignifugă. [C1]",
            False, "C1 susține lungimea, dar nu conține nicio proprietate privind rezistența la foc.",
            model_passages=(ModelPassage("C1", length),),
        ),
        GroundingCase(
            "G14", "wrong_evidence_link", "Ce culoare are carcasa fictivă Vela?",
            (_evidence(1, length), _evidence(2, colour)),
            "Carcasa fictivă Vela este turcoaz. [C1]",
            False, "Numai C2 susține culoarea Vela; C1 este despre lungimea Zori și este citată greșit.",
            # Citat autentic din C1, dar irelevant pentru afirmație: limita R05, nu JSON invalid.
            model_passages=(ModelPassage("C1", length),),
        ),
        GroundingCase(
            "G15", "number_in_irrelevant_evidence", "Ce lungime are tija fictivă Zori?",
            (_evidence(1, length), _evidence(2, "Cutia fictivă Pufi conține 19 bile.")),
            "Lungimea tijei fictive Zori este 19 mm. [C1]",
            False, "C1 dă 12 mm; 19 din C2 numără bile Pufi. Scanarea globală a numerelor nu dovedește lungimea.",
            model_passages=(ModelPassage("C1", length),),
        ),
        GroundingCase(
            "G16", "structural_unknown_citation", "Ce lungime are tija fictivă Zori?",
            (_evidence(1, length),), "Lungimea tijei fictive Zori este 12 mm. [C99]",
            False, "Afirmația corespunde lui C1, dar C99 nu există: control structural, nu eroare semantică.",
            model_passages=(ModelPassage("C99", length),),
        ),
        GroundingCase(
            "G17", "structural_missing_citation", "Ce lungime are tija fictivă Zori?",
            (_evidence(1, length),), "Lungimea tijei fictive Zori este 12 mm.",
            False, "Afirmația este în C1, dar candidatul nu citează nimic: control structural separat de suport.",
            model_passages=(),
        ),
        GroundingCase(
            "G18", "late_relevant_passage", "Ce presiune este admisă în globul fictiv Sora?",
            (_evidence(1, colour), _evidence(2, long_text)),
            "Presiunea admisă în globul fictiv Sora este 17 kPa. [C2]",
            True, "C2 dă explicit 17 kPa după primele 600 de caractere; citarea C2 trebuie să arate acel pasaj.",
            (PassageRequirement("C2", late),),
            model_passages=(ModelPassage("C2", late),),
        ),
        GroundingCase(
            "G19", "wrong_number_and_late_passage", "Ce presiune este admisă în globul fictiv Sora?",
            (_evidence(1, colour), _evidence(2, long_text)),
            "Presiunea admisă în globul fictiv Sora este 29 kPa. [C2]",
            False, "C2 dă 17 kPa, nu 29; independent, pasajul cu regula trebuie vizibil în citarea C2 dacă se publică.",
            (PassageRequirement("C2", late),),
            model_passages=(ModelPassage("C2", late),),
        ),
    )


def evaluate_case(
    case: GroundingCase,
    *,
    service_factory: Callable[[FixedGenerator], GenerationService] | None = None,
) -> dict:
    """Observă runtime-ul real implicit; fabrica este doar un seam local pentru teste."""
    generator = FixedGenerator(json.dumps({
        "raspuns": case.candidate,
        "pasaje": [asdict(passage) for passage in case.model_passages],
    }, ensure_ascii=False))
    findings = []
    observation = {"outcome": "execution_error", "result": None, "error_type": None}
    passage_checks = [
        {**asdict(passage), "status": "not_observed"}
        for passage in case.required_passages
    ]
    try:
        service = (service_factory or GenerationService)(generator)
        result = service.generate(case.question, case.evidence)
        if result.status not in ("answered", "not_found"):
            raise ValueError("status de generare necunoscut")
        observation["result"] = asdict(result)
        observation["outcome"] = "published" if result.status == "answered" else "not_found"
        if result.status == "answered":
            for check in passage_checks:
                present = any(
                    citation.id == check["citation_id"] and check["text"] in citation.citat
                    for citation in result.citari
                )
                check["status"] = "present" if present else "missing"
    except GenerationValidationError as error:
        observation["outcome"] = "rejected"
        observation["error_type"] = type(error).__name__
    except Exception as error:
        # O eroare de execuție nu este dovadă că runtime-ul a refuzat corect.
        observation = {"outcome": "execution_error", "result": None, "error_type": type(error).__name__}
        for check in passage_checks:
            check["status"] = "not_observed"

    outcome = observation["outcome"]
    if outcome == "execution_error":
        findings.append({"kind": "execution_error"})
    elif outcome == "published" and not case.expected_publishable:
        findings.append({"kind": "non_publishable_published"})
    elif outcome != "published" and case.expected_publishable:
        findings.append({"kind": "publishable_rejected"})
    for check in passage_checks:
        if check["status"] == "missing":
            findings.append({"kind": "relevant_passage_missing", "citation_id": check["citation_id"], "text": check["text"]})

    passage_status = "not_applicable"
    if passage_checks:
        passage_status = (
            "not_observed" if outcome != "published"
            else "missing" if any(check["status"] == "missing" for check in passage_checks)
            else "present"
        )
    return {
        **asdict(case),
        "observation": observation,
        "fake_calls": generator.calls,
        "passage_status": passage_status,
        "passage_checks": passage_checks,
        "findings": findings,
    }


def summarize(cases: Sequence[dict]) -> dict:
    """Toate contoarele provin din rezultate, nu dintr-un scor așteptat hardcodat."""
    findings = [finding for case in cases for finding in case["findings"]]
    return {
        "total_cases": len(cases),
        "cases_with_findings": sum(bool(case["findings"]) for case in cases),
        "total_findings": len(findings),
        "fake_calls": sum(case["fake_calls"] for case in cases),
        "published": sum(case["observation"]["outcome"] == "published" for case in cases),
        "typed_refusals": sum(case["observation"]["outcome"] == "rejected" for case in cases),
        "not_found": sum(case["observation"]["outcome"] == "not_found" for case in cases),
        **{kind: sum(finding["kind"] == kind for finding in findings) for kind in FINDING_KINDS},
    }


def run_evaluation(
    cases: Sequence[GroundingCase] | None = None,
    *,
    service_factory: Callable[[FixedGenerator], GenerationService] | None = None,
) -> dict:
    results = [
        evaluate_case(case, service_factory=service_factory)
        for case in (build_cases() if cases is None else cases)
    ]
    summary = summarize(results)
    return {
        "kind": KIND,
        "notice": NOTICE,
        "has_findings": bool(summary["total_findings"]),
        "cases": results,
        "summary": summary,
    }


def exit_code(report: dict) -> int:
    if report["summary"]["execution_error"]:
        return 2
    return 1 if report["has_findings"] else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=NOTICE)
    parser.add_argument("--output", required=True, type=Path, help="Fișier JSON local explicit")
    args = parser.parse_args(argv)
    print(NOTICE)
    try:
        report = run_evaluation()
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except Exception as error:
        print(f"Eroare de infrastructura evaluator: {type(error).__name__}", file=sys.stderr)
        return 2
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    return exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
