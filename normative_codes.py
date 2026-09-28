"""Detecția pozițiilor referințelor normative dintr-un text oarecare.

Modul independent (fără import din `retrieval_core` sau `generation_core`), ca
ambele module să îl poată folosi fără risc de import circular.
"""

from __future__ import annotations

import re

# Coada numerică a unui cod normativ: cifre, eventual grupate cu punct, cratimă sau bară
# (`52016-1`, `118/2-2013`, `6648/1-82`). Un separator trebuie urmat obligatoriu de cifră,
# deci punctul de la finalul frazei nu intră niciodată în referință.
_CODE_TAIL = r"\d+(?:\s?[./-]\s?\d+)*"

_NORMATIVE_REFERENCE_PATTERNS = (
    # `STAS 6648`, `STAS 6648/1-82`, `STAS-1907-1`.
    re.compile(rf"\bSTAS\s*-?\s*{_CODE_TAIL}", re.IGNORECASE),
    # `SR EN ISO 52016-1`, `SR EN 12831`, `SR ISO 9001`, `SR 1907-1`.
    re.compile(rf"\bSR(?:\s+EN)?(?:\s+ISO)?(?:\s+IEC)?\s+{_CODE_TAIL}", re.IGNORECASE),
    # `EN 12831`, `EN ISO 52016-1` — variantele fără prefixul `SR`.
    re.compile(rf"\bEN(?:\s+ISO)?(?:\s+IEC)?\s+{_CODE_TAIL}", re.IGNORECASE),
    # `NP 133-2013`, `NP133/2013`.
    re.compile(rf"\bNP\s*-?\s*{_CODE_TAIL}", re.IGNORECASE),
    # `P 118/2-2013`, `P100-1/2013`. Litera `P` apare des în text obișnuit („p. 12"),
    # deci cerem obligatoriu forma compusă (număr + separator + număr) și numai majusculă,
    # ca „p. 12-14" să nu fie confundat cu un normativ.
    re.compile(rf"\bP\s*-?\s*\d+\s?[./-]\s?{_CODE_TAIL}"),
    # `I5-2022`, `I 13-2015`. Aceeași prudență ca la `P`, dar mai strictă: cerem forma
    # compusă (număr + separator + număr), nu doar un număr. Fără asta, tiparul prindea
    # numerotarea cu cifre romane din text obișnuit — „ANEXA I 5" și „CAPITOLUL I 2" erau
    # raportate ca referințe normative, iar costul unui asemenea fals pozitiv e o
    # reîncercare plătită degeaba, urmată de refuzul unui răspuns corect.
    # Compromis asumat: o referință scrisă fără an („I 13" simplu) nu mai e detectată.
    # E acceptabil — codurile oficiale din corpus poartă toate anul (`I5-2022`, `I7-2011`,
    # `I9-2022`, `I 13-2015`), iar o referință inventată de model include aproape mereu anul.
    re.compile(rf"\bI\s*-?\s*\d+\s?[./-]\s?{_CODE_TAIL}"),
    # `C 107-2005`, `C 56-2002` (termotehnică, verificarea calității). Literă singură, deci
    # aceeași regulă ca la `P` și `I`: numai majusculă și obligatoriu formă compusă. E
    # esențial aici: fără cerința de formă compusă, tiparul ar prinde chiar identificatorii
    # de citare `[C1]`, `[C2]` pe care îi conține fiecare răspuns corect.
    re.compile(rf"\bC\s*-?\s*\d+\s?[./-]\s?{_CODE_TAIL}"),
    # `NE 012-2007` (execuția betonului), `NE 001-1996`.
    re.compile(rf"\bNE\s*-?\s*{_CODE_TAIL}", re.IGNORECASE),
    # `GP 051-2000`, `GT 039-2002` — ghiduri de proiectare, respectiv tehnice.
    re.compile(rf"\bG[PT]\s*-?\s*{_CODE_TAIL}", re.IGNORECASE),
    # `Mc 001-2006` — metodologii de calcul.
    re.compile(rf"\bMc\s*-?\s*{_CODE_TAIL}", re.IGNORECASE),
)

# Cuvinte de structură care, imediat înaintea unei litere urmate de cifre, arată că e vorba
# de numerotarea internă a unui document, nu de un cod de normativ („ANEXA I 5-2",
# „CAPITOLUL C 1-2"). Apărare în adâncime peste cerința de formă compusă de mai sus:
# lista tiparelor nu poate acoperi singură orice context.
_CUVINTE_DE_STRUCTURA = frozenset(
    {"ANEXA", "ANEXE", "CAPITOLUL", "CAPITOL", "TABELUL", "TABEL", "FIGURA", "PARTEA",
     "SECTIUNEA", "SECȚIUNEA", "PUNCTUL", "LITERA", "POZITIA", "POZIȚIA"}
)

_ULTIMUL_CUVANT = re.compile(r"([A-Za-zĂÂÎȘȚăâîșț]+)\s*$")


def _precedat_de_cuvant_de_structura(text: str, start: int) -> bool:
    """Spune dacă potrivirea e precedată imediat de un cuvânt de structură.

    „ANEXA I 5-2" e numerotarea internă a unui document, nu normativul `I 5-2`; la fel
    „CAPITOLUL C 1-2". Comparația e insensibilă la majuscule și acceptă și scrierea fără
    diacritice, fiindcă modelul le folosește pe amândouă.
    """
    potrivire = _ULTIMUL_CUVANT.search(text[:start])
    if potrivire is None:
        return False
    return potrivire.group(1).upper() in _CUVINTE_DE_STRUCTURA


def gaseste_referinte_normative(text: str) -> list[tuple[int, int]]:
    """Pozițiile (start, end) ale referințelor normative dintr-un text.

    Filtrul de incluziune evită raportarea dublă: în `SR EN 12831` se potrivesc atât
    tiparul `SR ...`, cât și tiparul `EN ...`; păstrăm numai potrivirea cea mai lungă.
    """
    matches = [
        (match.start(), match.end())
        for pattern in _NORMATIVE_REFERENCE_PATTERNS
        for match in pattern.finditer(text)
        if not _precedat_de_cuvant_de_structura(text, match.start())
    ]
    matches.sort(key=lambda item: (item[0], -item[1]))
    kept: list[tuple[int, int]] = []
    for start, end in matches:
        if any(previous_start <= start and end <= previous_end for previous_start, previous_end in kept):
            continue
        kept.append((start, end))
    return kept
