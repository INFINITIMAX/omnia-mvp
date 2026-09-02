"""Set de evaluare sintetic pentru criteriile MVP din docs/HYBRID_SEARCH_SPEC.md sectiunea 10.

Toate textele, articolele si documentele sunt fictive/de test; nu contin continut normativ
real, la fel ca fixture-urile din tests/test_retrieval_core.py.

CORPUS este comun tuturor cazurilor: contine identitate document/articol si continut cu
semnale semantice fictive (inclusiv decoy-uri pe teme diferite), independent de EvalCase.
Harness-ul din test_eval_set.py cauta in el prin lookup exact si prin similaritate
cosinus reala calculata din text, fara sa cunoasca dinainte raspunsul asteptat.
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


@dataclass(frozen=True)
class CorpusEntry:
    """O intrare fictiva de corpus: identitate document/articol + continut cu semnal semantic."""

    document_id: str
    articol_normalizat: str
    cod_document: str
    titlu_document: str
    content: str


ALIASES = {
    "doc-np010": ("NP010", "NP 010-2022"),
    "doc-np057": ("NP057", "NP 057-02"),
}

KNOWN_ARTICLES = {
    "doc-np010": ("4.4.7.2", "4.6.(1)", "3.2.(b).l"),
    "doc-np057": ("5.1.1",),
}

# Corpus sintetic comun, partajat de exact lookup si de rankingul semantic. Contine
# tintele reale pentru EXACT_CASES/SEMANTIC_CASES plus decoy-uri pe teme fara legatura,
# ca similaritatea cosinus sa aiba concurenta reala si sa nu "castige" din lipsa de rivali.
CORPUS: tuple[CorpusEntry, ...] = (
    CorpusEntry(
        "doc-np010", "4.4.7.2", "NP TEST010", "Titlu sintetic NP010",
        "Ce cerinte exista pentru iluminatul natural al scolilor: ferestrele trebuie "
        "dimensionate conform suprafetei utile a salilor de clasa.",
    ),
    CorpusEntry(
        "doc-np010", "4.6.(1)", "NP TEST010", "Titlu sintetic NP010",
        "Regulile de siguranta la incendiu pentru cladiri scolare impun cai de evacuare "
        "marcate si usi rezistente la foc.",
    ),
    CorpusEntry(
        "doc-np010", "3.2.(b).l", "NP TEST010", "Titlu sintetic NP010",
        "Peretii despartitori dintre salile de clasa asigura izolatie fonica adecvata, "
        "masurata prin indicele de atenuare acustica normat.",
    ),
    CorpusEntry(
        "doc-np057", "5.1.1", "NP TEST057", "Titlu sintetic NP057",
        "Cum se proiecteaza cladirile de locuinte conform normativului: distante minime "
        "intre blocuri, orientare corecta si acces auto pentru fiecare locuinta.",
    ),
    CorpusEntry(
        "doc-decoy-ventilatie", "2.1.1", "DECOY TEST", "Titlu decoy ventilatie",
        "Sistemele de ventilatie mecanica din birouri asigura un debit minim de aer "
        "proaspat pentru fiecare angajat prezent la birou.",
    ),
    CorpusEntry(
        "doc-decoy-acustica", "3.3.3", "DECOY TEST", "Titlu decoy acustica hoteluri",
        "Hotelurile limiteaza zgomotul dintre camere prin pereti dubli si usi cu "
        "garnituri de etansare acustica performanta.",
    ),
    CorpusEntry(
        "doc-decoy-structuri", "6.2.4", "DECOY TEST", "Titlu decoy structuri poduri",
        "Podurile metalice sunt calculate la incarcari dinamice provenite din trafic "
        "greu si variatii sezoniere de temperatura.",
    ),
    CorpusEntry(
        "doc-decoy-sanitare", "7.4.2", "DECOY TEST", "Titlu decoy instalatii spitale",
        "Instalatiile sanitare din spitale respecta cerinte stricte de igiena, cu "
        "robinete cu senzor si sifoane anti-reflux.",
    ),
    CorpusEntry(
        "doc-decoy-electrice", "8.1.5", "DECOY TEST", "Titlu decoy electrice parcari",
        "Tablourile electrice din parcari subterane sunt protejate la umiditate si "
        "dotate cu sisteme de detectie a supratensiunilor.",
    ),
)

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

# Intrebari fara referinta explicita de articol -> semantic search, rankuit prin
# similaritate cosinus reala fata de CORPUS (inclusiv decoy-urile de mai sus).
#
# Fiecare intrebare e o parafraza sintetica controlata a articolului-tinta: alt vocabular, alta ordine
# a cuvintelor, alta structura de fraza, NU formularea propozitiei din CORPUS. Harness-ul
# verifica acest lucru explicit (test_eval_set.py: test_intrebarile_semantice_sunt_parafraze...),
# iar embedderul sintetic recunoaste variantele morfologice/sinonimele printr-un tezaur
# general de cuvinte (_SYNONYM_GROUPS din test_eval_set.py), nu printr-o mapare
# caz -> dovada asteptata.
SEMANTIC_CASES: tuple[EvalCase, ...] = (
    EvalCase(
        "semantic-1", "semantic",
        "Cum trebuie dimensionate ferestrele unei sali de clasa, in functie de suprafata ei "
        "utila, pentru lumina naturala?",
        "doc-np010", "4.4.7.2",
    ),
    EvalCase(
        "semantic-2", "semantic",
        "Ce reguli exista pentru marimea geamurilor dintr-o sala de clasa, raportat la "
        "suprafata utila a incaperii?",
        "doc-np010", "4.4.7.2",
    ),
    EvalCase(
        "semantic-3", "semantic",
        "Ce cerinta de iluminat natural trebuie respectata pentru salile de clasa dintr-o "
        "scoala, avand in vedere suprafata ferestrelor?",
        "doc-np010", "4.4.7.2",
    ),
    EvalCase(
        "semantic-4", "semantic",
        "Ce prevede normativul despre caile de evacuare marcate dintr-o cladire scolara, "
        "in caz de incendiu?",
        "doc-np010", "4.6.(1)",
    ),
    EvalCase(
        "semantic-5", "semantic",
        "Cum trebuie sa fie usile unei scoli pentru a rezista la foc, conform regulilor de "
        "siguranta?",
        "doc-np010", "4.6.(1)",
    ),
    EvalCase(
        "semantic-6", "semantic",
        "Ce obligatii au cladirile scolare in privinta sigurantei la incendiu si a "
        "evacuarii elevilor?",
        "doc-np010", "4.6.(1)",
    ),
    EvalCase(
        "semantic-7", "semantic",
        "Ce nivel de izolatie fonica trebuie sa aiba peretele dintre doua sali de clasa "
        "alaturate?",
        "doc-np010", "3.2.(b).l",
    ),
    EvalCase(
        "semantic-8", "semantic",
        "Cum se asigura o izolare fonica buna intre doua sali de clasa vecine, la nivelul "
        "peretelui despartitor?",
        "doc-np010", "3.2.(b).l",
    ),
    EvalCase(
        "semantic-9", "semantic",
        "Ce cerinte de izolare fonica trebuie sa respecte peretele despartitor dintre doua "
        "sali de clasa?",
        "doc-np010", "3.2.(b).l",
    ),
    EvalCase(
        "semantic-10", "semantic",
        "Cat de mare trebuie sa fie distanta minima dintre doua blocuri de locuinte "
        "alaturate?",
        "doc-np057", "5.1.1",
    ),
    EvalCase(
        "semantic-11", "semantic",
        "Ce reguli de orientare si de acces cu masina se aplica atunci cand se proiecteaza "
        "un bloc de locuinte?",
        "doc-np057", "5.1.1",
    ),
    EvalCase(
        "semantic-12", "semantic",
        "La proiectarea unei cladiri rezidentiale, ce se cere in privinta accesului auto "
        "pentru fiecare apartament?",
        "doc-np057", "5.1.1",
    ),
)

# Control negativ: intrebare semantica fara nicio suprapunere de vocabular cu CORPUS.
# Dovedeste ca rankingul semantic e real (nu returneaza automat "ceva"): scorul cosinus
# fata de fiecare intrare din corpus trebuie sa fie 0.0, sub pragul de acceptare.
NEGATIVE_SEMANTIC_CASES: tuple[EvalCase, ...] = (
    EvalCase("negative-1", "not_found", "Pisicile prefera culori pastelate cand dorm pe canapele confortabile."),
)

ALL_CASES: tuple[EvalCase, ...] = EXACT_CASES + NOT_FOUND_CASES + SEMANTIC_CASES + NEGATIVE_SEMANTIC_CASES
