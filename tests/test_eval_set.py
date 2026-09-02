"""Harness de evaluare: masoara criteriile MVP din docs/HYBRID_SEARCH_SPEC.md sectiunea 10.

Regression eval sintetic, determinist, complet local/mockuit pentru un set controlat.
NU e o evaluare de calitate reala Voyage/Claude si nu inlocuieste testarea vizuala/
smoke pe trafic public (acelea raman restante, vezi TASKS.md).

Ruleaza fiecare caz din eval_set_data prin RetrievalService real, cu un repository
sintetic care NU primeste EvalCase/tip/expected: cauta exact strict dupa document+articol
in CORPUS, iar la semantic clasifica intregul CORPUS (inclusiv decoy-uri fara legatura)
prin similaritate cosinus reala intre vectorul intrebarii si vectorii continutului,
derivati determinist din text (bag-of-words peste un vocabular fix, cu un tezaur general
de sinonime/variante morfologice _SYNONYM_GROUPS - nu o mapare caz->dovada). Metricile
verifica identitatea document+articol asteptata, nu doar statusul "found", iar un caz de
control negativ dovedeste ca o intrebare fara semnal relevant nu primeste automat dovada.

SEMANTIC_CASES contine minimum 10 parafraze reale (alt vocabular/alta structura de fraza
decat propozitia-tinta din CORPUS); un test dedicat verifica literal ca nicio intrebare nu
reproduce un fragment lung din formularea corpusului (vezi _MAX_COPIED_TOKEN_RUN mai jos).
"""

import math
import re
from collections import Counter
from dataclasses import dataclass

from retrieval_core import SEMANTIC_MIN_SCORE, ArticleParser, Evidence, RetrievalService

from eval_set_data import (
    ALIASES,
    ALL_CASES,
    CORPUS,
    EXACT_CASES,
    KNOWN_ARTICLES,
    NEGATIVE_SEMANTIC_CASES,
    NOT_FOUND_CASES,
    SEMANTIC_CASES,
)

_TOKEN = re.compile(r"[a-zA-ZăâîșțĂÂÎȘȚ]+")


def _tokenize(text: str) -> tuple[str, ...]:
    """Tokenizare literala (fara normalizare); folosita si de verificarea anti-copiere."""
    return tuple(_TOKEN.findall(text.lower()))


# Tezaur general de variante morfologice/sinonime (nu per-caz, nu per-intrebare): permite
# embedderului sintetic sa recunoasca o parafraza reala ("ferestrele" vs "geamurile",
# "izolatie" vs "izolare", "salile" vs "sali") fara sa cunoasca vreodata raspunsul asteptat
# pentru un caz anume. Grupurile sunt derivate din vocabularul CORPUS-ului, nu din
# formularea vreunei intrebari din eval_set_data.
_SYNONYM_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"iluminatul", "iluminat", "iluminatului", "lumina", "luminii", "luminata", "luminate"}),
    frozenset({"natural", "naturala", "naturale", "naturali"}),
    frozenset({"scolilor", "scoala", "scolare", "scolar", "scoli", "scolara", "scolii"}),
    frozenset({"ferestrele", "ferestre", "fereastra", "geamurile", "geamuri", "geamul"}),
    frozenset({"dimensionate", "dimensiune", "dimensiuni", "dimensionarea", "dimensionarii", "dimensionat"}),
    frozenset({"suprafetei", "suprafata", "suprafete"}),
    frozenset({"salilor", "sala", "sali", "salile", "salii"}),
    frozenset({"clasa", "clase", "clasei", "clasele"}),
    frozenset({"siguranta", "sigure", "sigur", "sigura", "sigurantei"}),
    frozenset({"incendiu", "incendii", "foc", "incendiului"}),
    frozenset({"evacuare", "evacuarea", "evacuati", "evacuarii", "evacuate"}),
    frozenset({"cladiri", "cladirile", "cladire", "cladirilor", "blocurile", "blocuri", "bloc", "blocurilor"}),
    frozenset({"izolatie", "izolatia", "izolare", "izolarea", "izoleze", "izolarii", "izolatiei"}),
    frozenset({"fonica", "fonic", "acustica", "acustic", "sunet", "sunetul", "zgomotul", "zgomot"}),
    frozenset({"pereti", "peretii", "peretilor", "peretele"}),
    frozenset({"despartitori", "despartitoare", "despartitor"}),
    frozenset({"proiecteaza", "proiectarea", "proiectare", "proiectate", "proiectat"}),
    frozenset({"locuinte", "locuinta", "locuintelor", "locuibile", "locuintei"}),
    frozenset({"distante", "distanta", "distantele", "distantei"}),
    frozenset({"orientare", "orientarea", "orientate", "orientat"}),
    frozenset({"acces", "accesul", "accesibile", "accesibilitate"}),
    frozenset({"cai", "caile", "cailor", "calea"}),
    frozenset({"usi", "usile", "usilor", "usa"}),
    frozenset({"minime", "minima", "minim", "minimale"}),
    frozenset({"auto", "masina", "masini", "autovehicul", "autovehicule"}),
)

# Fiecare cuvant dintr-un grup e mapat la forma sa canonica (cea mai mica alfabetic, arbitrar
# dar determinist). Cuvintele din afara tezaurului raman neschimbate.
_CANONICAL_FORM: dict[str, str] = {
    word: min(group) for group in _SYNONYM_GROUPS for word in group
}


def _canonicalize(tokens: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(_CANONICAL_FORM.get(token, token) for token in tokens)


# Vocabular fix, derivat determinist din CORPUS (sortat -> reproductibil, fara hash()).
_VOCABULARY: tuple[str, ...] = tuple(
    sorted({token for entry in CORPUS for token in _canonicalize(_tokenize(entry.content))})
)


def _vectorize(text: str) -> tuple[float, ...]:
    """Vector bag-of-words peste _VOCABULARY (dupa canonicalizare); cuvinte in afara
    vocabularului sunt ignorate."""
    counts = Counter(_canonicalize(_tokenize(text)))
    return tuple(float(counts.get(term, 0)) for term in _VOCABULARY)


def _cosine_similarity(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


# Vectorii continutului sunt precalculati o singura data; identici indiferent de caz.
_CORPUS_VECTORS: tuple[tuple[float, ...], ...] = tuple(_vectorize(entry.content) for entry in CORPUS)


def _evidence_from_corpus(index: int, score: float | None = None) -> Evidence:
    entry = CORPUS[index]
    return Evidence(
        chunk_id=index + 1,
        document_id=entry.document_id,
        cod_document=entry.cod_document,
        titlu_document=entry.titlu_document,
        articol=entry.articol_normalizat,
        articol_normalizat=entry.articol_normalizat,
        content=entry.content,
        content_hash=f"hash-{entry.document_id}-{entry.articol_normalizat}",
        score=score,
    )


@dataclass
class _SyntheticCorpusRepository:
    """Cauta doar in CORPUS; nu primeste si nu citeste EvalCase/tip/expected niciodata."""

    exact_calls: int = 0
    semantic_calls: int = 0

    def find_exact(self, document_id, article_normalized):
        self.exact_calls += 1
        return [
            _evidence_from_corpus(index)
            for index, entry in enumerate(CORPUS)
            if entry.document_id == document_id and entry.articol_normalizat == article_normalized
        ]

    def find_semantic(self, embedding, top_k):
        self.semantic_calls += 1
        ranked = sorted(
            range(len(CORPUS)),
            key=lambda index: (-_cosine_similarity(embedding, _CORPUS_VECTORS[index]), index),
        )
        return [
            _evidence_from_corpus(index, score=_cosine_similarity(embedding, _CORPUS_VECTORS[index]))
            for index in ranked[:top_k]
        ]


class _DeterministicEmbedder:
    """Deriva vectorul intrebarii din text (token features); nu are acces la raspunsul asteptat."""

    def embed_query(self, question):
        return _vectorize(question)


def _run_case(case, repository=None):
    parser = ArticleParser(ALIASES, KNOWN_ARTICLES)
    service = RetrievalService(parser, repository or _SyntheticCorpusRepository(), _DeterministicEmbedder())
    return service.retrieve(case.intrebare)


def _matches_expected(case, result) -> bool:
    """Adevarat doar daca statusul e found SI dovada contine identitatea document+articol asteptata."""
    if result.status != "found":
        return False
    return any(
        item.document_id == case.document_id and item.articol_normalizat == case.articol_normalizat
        for item in result.evidence
    )


def test_fiecare_caz_de_evaluare_are_forma_valida():
    assert ALL_CASES, "setul de evaluare nu poate fi gol"
    for case in ALL_CASES:
        assert case.intrebare.strip(), f"{case.id}: intrebarea nu poate fi goala"
        assert case.tip in {"exact", "semantic", "not_found"}, f"{case.id}: tip necunoscut"
        if case.tip not in {"not_found"}:
            assert case.document_id and case.articol_normalizat, f"{case.id}: lipseste document/articol asteptat"


def test_corpusul_sintetic_are_o_singura_intrare_per_document_si_articol():
    """Garanteaza ca nu exista ambiguitate accidentala introdusa de corpus (chei duplicate)."""
    chei = [(entry.document_id, entry.articol_normalizat) for entry in CORPUS]
    assert len(chei) == len(set(chei)), "CORPUS contine duplicate document+articol"


def _corpus_content_for(case) -> str:
    for entry in CORPUS:
        if entry.document_id == case.document_id and entry.articol_normalizat == case.articol_normalizat:
            return entry.content
    raise AssertionError(f"{case.id}: nu exista in CORPUS o intrare pentru document/articol asteptat")


def _longest_common_token_run(a: tuple[str, ...], b: tuple[str, ...]) -> int:
    """Cel mai lung sir de cuvinte consecutive identice (literal, fara canonicalizare)."""
    best = 0
    for i in range(len(a)):
        for j in range(len(b)):
            run = 0
            while i + run < len(a) and j + run < len(b) and a[i + run] == b[j + run]:
                run += 1
            best = max(best, run)
    return best


# Peste acest prag, intrebarea nu mai e o parafraza: reproduce o bucata din formularea
# propozitiei-tinta din CORPUS. Sintagme uzuale de 2-3 cuvinte ("sali de clasa", "cai de
# evacuare") raman sub prag; o clauza intreaga copiata nu.
_MAX_COPIED_TOKEN_RUN = 3


def test_evaluarea_semantica_are_minimum_zece_cazuri_pentru_metrica_90():
    """Pragul de acceptare >=90% (vezi mai jos) trebuie masurat pe un esantion suficient."""
    assert len(SEMANTIC_CASES) >= 10, (
        f"SEMANTIC_CASES are {len(SEMANTIC_CASES)} cazuri; pragul de 90% nu e o metrica "
        "de incredere sub 10 cazuri"
    )


def test_intrebarile_semantice_sunt_parafraze_reale_nu_copii_ale_corpusului():
    """Fiecare intrebare semantica trebuie sa fie o reformulare, nu formularea din CORPUS.

    Verificare literala (fara sinonime/canonicalizare): daca intrebarea ar contine un sir
    lung de cuvinte identic cu propozitia-tinta, testul de similaritate cosinus ar reusi
    trivial prin copiere, nu prin recunoasterea reala a unei parafraze.
    """
    for case in SEMANTIC_CASES:
        target_content = _corpus_content_for(case)
        run = _longest_common_token_run(_tokenize(case.intrebare), _tokenize(target_content))
        assert run <= _MAX_COPIED_TOKEN_RUN, (
            f"{case.id}: intrebarea reproduce {run} cuvinte consecutive din propozitia-tinta "
            "din CORPUS (formulare copiata, nu parafraza reala)"
        )


def test_setul_de_evaluare_respecta_criteriile_mvp_din_spec():
    assert EXACT_CASES and NOT_FOUND_CASES and SEMANTIC_CASES, "trebuie toate cele 3 categorii, nu doar una"

    exact_results = [(case, _run_case(case)) for case in EXACT_CASES]
    not_found_results = [(case, _run_case(case)) for case in NOT_FOUND_CASES]
    semantic_results = [(case, _run_case(case)) for case in SEMANTIC_CASES]

    exact_ok = sum(1 for case, result in exact_results if _matches_expected(case, result))
    not_found_ok = sum(1 for _, result in not_found_results if result.status == "not_found")
    semantic_ok = sum(1 for case, result in semantic_results if _matches_expected(case, result))

    exact_rate = exact_ok / len(EXACT_CASES)
    not_found_rate = not_found_ok / len(NOT_FOUND_CASES)
    semantic_rate = semantic_ok / len(SEMANTIC_CASES)

    failed_exact = [case.id for case, result in exact_results if not _matches_expected(case, result)]
    assert exact_rate == 1.0, f"exact lookup {exact_ok}/{len(EXACT_CASES)}; esuate: {failed_exact}"

    failed_not_found = [case.id for case, result in not_found_results if result.status != "not_found"]
    assert not_found_rate == 1.0, f"refuz articole inventate {not_found_ok}/{len(NOT_FOUND_CASES)}; esuate: {failed_not_found}"

    failed_semantic = [case.id for case, result in semantic_results if not _matches_expected(case, result)]
    assert semantic_rate >= 0.90, f"semantic {semantic_ok}/{len(SEMANTIC_CASES)} = {semantic_rate:.0%}; esuate: {failed_semantic}"


def test_articol_inventat_nu_are_fallback_semantic_in_setul_de_evaluare():
    """Confirma ca refuzul e real: find_semantic nu e apelat deloc pentru articole explicite inventate."""
    for case in NOT_FOUND_CASES:
        repository = _SyntheticCorpusRepository()
        result = _run_case(case, repository)

        assert result.status == "not_found", f"{case.id}: asteptat not_found, primit {result.status}"
        assert repository.exact_calls == 1, f"{case.id}: exact lookup trebuie apelat exact o data"
        assert repository.semantic_calls == 0, f"{case.id}: nu trebuie sa existe fallback semantic"


def test_intrebare_semantica_fara_semnale_relevante_nu_primeste_automat_dovada():
    """Control negativ: fara suprapunere de vocabular cu CORPUS, similaritatea reala e 0.0.

    Dovedeste ca repository-ul nu returneaza "orice" ca dovada gasita: cautarea semantica
    e reala (e apelata si calculeaza scoruri), dar scorul ramane sub SEMANTIC_MIN_SCORE
    pentru toate intrarile din corpus, deci rezultatul e refuz, nu o potrivire ghicita.
    """
    assert NEGATIVE_SEMANTIC_CASES, "trebuie cel putin un caz de control negativ"
    for case in NEGATIVE_SEMANTIC_CASES:
        repository = _SyntheticCorpusRepository()
        result = _run_case(case, repository)

        vector = _DeterministicEmbedder().embed_query(case.intrebare)
        best_score = max(_cosine_similarity(vector, entry_vector) for entry_vector in _CORPUS_VECTORS)
        assert best_score == 0.0, f"{case.id}: intrebarea de control trebuie sa nu aiba nicio suprapunere de vocabular, scor obtinut {best_score}"
        assert best_score < SEMANTIC_MIN_SCORE

        assert repository.semantic_calls == 1, f"{case.id}: cautarea semantica reala trebuie totusi incercata"
        assert result.status == "not_found", f"{case.id}: fara semnal relevant, asteptat refuz, primit {result.status}"
        assert not result.evidence
