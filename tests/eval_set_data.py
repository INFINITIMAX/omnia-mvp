"""Set de evaluare sintetic pentru criteriile MVP din docs/HYBRID_SEARCH_SPEC.md sectiunea 10.

Toate textele si articolele sunt fictive/de test; nu contin continut normativ real,
la fel ca fixture-urile din tests/test_retrieval_core.py.
"""

from dataclasses import dataclass
from typing import Literal

TipCaz = Literal["exact", "semantic", "not_found"]


@dataclass(frozen=True)
class EvalCase:
    id: str
    tip: TipCaz
    intrebare: str
    document_id: str | None = None
    articol_normalizat: str | None = None


ALIASES = {
    "doc-np010": ("NP010", "NP 010-2022"),
    "doc-np057": ("NP057", "NP 057-02"),
}

KNOWN_ARTICLES = {
    "doc-np010": ("4.4.7.2", "4.6.(1)", "3.2.(b).l"),
    "doc-np057": ("5.1.1",),
}

# Articole cunoscute, referite explicit (marker "articolul"/"art.") -> exact lookup.
EXACT_CASES: tuple[EvalCase, ...] = (
    EvalCase("exact-1", "exact", "Ce prevede articolul 4.4.7.2 din NP 010-2022?", "doc-np010", "4.4.7.2"),
    EvalCase("exact-2", "exact", "Detaliaza art. 4.6.(1) NP010.", "doc-np010", "4.6.(1)"),
    EvalCase("exact-3", "exact", "Ce spune articolul 5.1.1 din NP 057-02?", "doc-np057", "5.1.1"),
)

# Articole explicit inventate, absente din KNOWN_ARTICLES -> refuz, fara fallback semantic.
NOT_FOUND_CASES: tuple[EvalCase, ...] = (
    EvalCase("invented-1", "not_found", "Ce prevede articolul 9.9.9 din NP 010-2022?"),
    EvalCase("invented-2", "not_found", "Detaliaza art. 8.8.(z) NP 057-02."),
)

# Intrebari fara referinta explicita de articol -> semantic search.
SEMANTIC_CASES: tuple[EvalCase, ...] = (
    EvalCase("semantic-1", "semantic", "Ce cerinte exista pentru iluminatul natural al scolilor?", "doc-np010", "4.4.7.2"),
    EvalCase("semantic-2", "semantic", "Cum se proiecteaza cladirile de locuinte conform normativului?", "doc-np057", "5.1.1"),
    EvalCase("semantic-3", "semantic", "Care sunt regulile de siguranta la incendiu pentru cladiri scolare?", "doc-np010", "4.6.(1)"),
)

ALL_CASES: tuple[EvalCase, ...] = EXACT_CASES + NOT_FOUND_CASES + SEMANTIC_CASES
