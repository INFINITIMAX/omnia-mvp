"""Harness de evaluare: masoara criteriile MVP din docs/HYBRID_SEARCH_SPEC.md sectiunea 10.

Ruleaza fiecare caz din eval_set_data prin RetrievalService real, cu un repository
controlat (fara DB) care intoarce exact dovada asteptata pentru cazul respectiv.
Procentele sunt calculate din rezultate, nu copiate din spec.
"""

from dataclasses import dataclass

from retrieval_core import ArticleParser, Evidence, RetrievalService

from eval_set_data import ALIASES, ALL_CASES, EXACT_CASES, KNOWN_ARTICLES, NOT_FOUND_CASES, SEMANTIC_CASES


def _evidence_for(case):
    return Evidence(
        chunk_id=abs(hash(case.id)) % 100000,
        document_id=case.document_id,
        cod_document="COD TEST",
        titlu_document="Titlu sintetic",
        articol=case.articol_normalizat,
        articol_normalizat=case.articol_normalizat,
        content="fragment sintetic pentru " + case.id,
        content_hash="hash-" + case.id,
        score=0.9,
    )


@dataclass
class _RepositoryForCase:
    """Intoarce exact dovada asteptata pentru cazul curent; nu ghiceste raspunsul."""

    case: object
    exact_calls: int = 0
    semantic_calls: int = 0

    def find_exact(self, document_id, article_normalized):
        self.exact_calls += 1
        if self.case.tip == "not_found":
            return []
        if self.case.document_id == document_id and self.case.articol_normalizat == article_normalized:
            return [_evidence_for(self.case)]
        return []

    def find_semantic(self, _embedding, _top_k):
        self.semantic_calls += 1
        if self.case.tip != "semantic":
            return []
        return [_evidence_for(self.case)]


class _EmbedderStub:
    def embed_query(self, _question):
        return (0.1, 0.2, 0.3)


def _run_case(case):
    parser = ArticleParser(ALIASES, KNOWN_ARTICLES)
    service = RetrievalService(parser, _RepositoryForCase(case), _EmbedderStub())
    return service.retrieve(case.intrebare)


def test_fiecare_caz_de_evaluare_are_forma_valida():
    assert ALL_CASES, "setul de evaluare nu poate fi gol"
    for case in ALL_CASES:
        assert case.intrebare.strip(), f"{case.id}: intrebarea nu poate fi goala"
        assert case.tip in {"exact", "semantic", "not_found"}, f"{case.id}: tip necunoscut"
        if case.tip != "not_found":
            assert case.document_id and case.articol_normalizat, f"{case.id}: lipseste document/articol asteptat"


def test_setul_de_evaluare_respecta_criteriile_mvp_din_spec():
    assert EXACT_CASES and NOT_FOUND_CASES and SEMANTIC_CASES, "trebuie toate cele 3 categorii, nu doar una"

    exact_results = [(case, _run_case(case)) for case in EXACT_CASES]
    not_found_results = [(case, _run_case(case)) for case in NOT_FOUND_CASES]
    semantic_results = [(case, _run_case(case)) for case in SEMANTIC_CASES]

    exact_ok = sum(1 for _, result in exact_results if result.status == "found")
    not_found_ok = sum(1 for _, result in not_found_results if result.status == "not_found")
    semantic_ok = sum(1 for _, result in semantic_results if result.status == "found")

    exact_rate = exact_ok / len(EXACT_CASES)
    not_found_rate = not_found_ok / len(NOT_FOUND_CASES)
    semantic_rate = semantic_ok / len(SEMANTIC_CASES)

    failed_exact = [case.id for case, result in exact_results if result.status != "found"]
    assert exact_rate == 1.0, f"exact lookup {exact_ok}/{len(EXACT_CASES)}; esuate: {failed_exact}"

    failed_not_found = [case.id for case, result in not_found_results if result.status != "not_found"]
    assert not_found_rate == 1.0, f"refuz articole inventate {not_found_ok}/{len(NOT_FOUND_CASES)}; esuate: {failed_not_found}"

    failed_semantic = [case.id for case, result in semantic_results if result.status != "found"]
    assert semantic_rate >= 0.90, f"semantic {semantic_ok}/{len(SEMANTIC_CASES)} = {semantic_rate:.0%}; esuate: {failed_semantic}"


def test_articol_inventat_nu_are_fallback_semantic_in_setul_de_evaluare():
    """Confirma ca refuzul e real: find_semantic nu e apelat deloc pentru articole explicite inventate."""
    for case in NOT_FOUND_CASES:
        repository = _RepositoryForCase(case)
        parser = ArticleParser(ALIASES, KNOWN_ARTICLES)
        service = RetrievalService(parser, repository, _EmbedderStub())
        result = service.retrieve(case.intrebare)

        assert result.status == "not_found", f"{case.id}: asteptat not_found, primit {result.status}"
        assert repository.exact_calls == 1, f"{case.id}: exact lookup trebuie apelat exact o data"
        assert repository.semantic_calls == 0, f"{case.id}: nu trebuie sa existe fallback semantic"
