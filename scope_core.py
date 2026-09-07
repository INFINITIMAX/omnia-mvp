"""Clasificare locală și deterministă a cererilor care cer calcule de proiectare."""

from __future__ import annotations

import re
import unicodedata


# Verbele cer o execuție din partea produsului. Nu sunt suficiente singure pentru a
# bloca întrebarea despre metoda descrisă într-un normativ.
_EXECUTION_VERBS = re.compile(r"\b(calcul\w*|estim\w*|dimension\w*)\b")
# Formele imperative/persoana întâi indică acțiunea cerută produsului chiar când
# utilizatorul menționează și un normativ („calculează conform I5”).
_EXECUTION_REQUEST = re.compile(
    r"\b(calculeaza|calculati|calculez|calculam|estimeaza|estimati|estimez|estimam|"
    r"dimensioneaza|dimensionati|dimensionez|dimensionam)\b"
)
_METHOD_REQUEST = re.compile(r"\b(cum|metod\w*|formula|formul\w*|prevede|conform)\b")
# „cum se calculează” cere explicarea metodei (diateză reflexivă), nu executarea ei.
_METHOD_EXECUTION_FORM = re.compile(
    r"\bcum\s+se\s+(?:calculeaza|estimeaza|dimensioneaza)\b"
)
_POWER_NEED = re.compile(r"\b(cati|cata|cat)\s+kw\b.*\b(imi|ne)\s+trebuie\b")
_COOLING_LOAD = re.compile(r"\b(sarcina|necesar\w*)\b.*\b(racire|termic\w*)\b")
_PROJECT_INPUT = re.compile(
    r"\b(\d+(?:[.,]\d+)?\s*(?:kw|w|mp|m2|m³|m3|°c|c)|hala|cladire|spatiu|inaltime|"
    r"temperatur\w*|oras|localitate|buzau)\b"
)
# Un singur literal complet: nu compunem fragmente de regex, deoarece un grup deschis
# într-un fragment ar face modulul neimportabil înainte ca testele să poată rula.
_PRESCRIBED_VALUE = re.compile(
    r"\b(?:debit\w*\s+minim|prag\w*|valo\w*\s+prescris\w*)\b"
)


def normalize_scope_text(text: str) -> str:
    """Normalizează doar pentru comparare: diacritice, capitalizare și spații."""
    if not isinstance(text, str):
        return ""
    decomposed = unicodedata.normalize("NFD", text.casefold())
    without_diacritics = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return " ".join(without_diacritics.split())


def is_engineering_calculation_request(question: str) -> bool:
    """Returnează True numai pentru cereri de execuție, nu pentru întrebări normative.

    Clasificarea nu folosește servicii externe și se bazează pe semnale explicite: un
    verb de execuție, necesarul de putere, ori sarcina termică cerută cu date de proiect.
    """
    normalized = normalize_scope_text(question)
    if not normalized or _PRESCRIBED_VALUE.search(normalized):
        return False
    if _METHOD_EXECUTION_FORM.search(normalized):
        return False
    if _METHOD_REQUEST.search(normalized):
        return bool(_EXECUTION_REQUEST.search(normalized))
    if _EXECUTION_VERBS.search(normalized):
        return True
    if _POWER_NEED.search(normalized):
        return True
    return bool(_COOLING_LOAD.search(normalized) and _PROJECT_INPUT.search(normalized))
