"""Teste directe pentru detecția pozițiilor referințelor normative (`normative_codes.py`).

Modul e folosit atât de `generation_core` (verificarea referințelor inventate), cât și
de `retrieval_core` (D25, refuzul codurilor necunoscute). Aici testăm doar funcția
publică `gaseste_referinte_normative`, independent de oricare dintre cei doi clienți.
"""

import pytest

from normative_codes import gaseste_referinte_normative


def _texts(text):
    return [text[start:end] for start, end in gaseste_referinte_normative(text)]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Se aplică NP 127-2010 pentru acest caz.", ["NP 127-2010"]),
        ("Conform I 13-2015, instalația trebuie verificată.", ["I 13-2015"]),
        ("Pereții antifoc respectă P 118/2-2013.", ["P 118/2-2013"]),
        ("Ventilația respectă SR EN 12831 pentru calculul sarcinii termice.", ["SR EN 12831"]),
        ("Piesele fictive poartă marcaj conform STAS 6648.", ["STAS 6648"]),
    ],
)
def test_detecteaza_codurile_normative_pozitive(text, expected):
    assert _texts(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        # Numerotare internă a documentului, nu un normativ ("I 5-2" e o poziție din anexă).
        "Vezi ANEXA I 5-2 pentru detalii.",
        # Identificator de citare intern, nu normativul C.
        "Conform dovezii [C1], marcajul este vizibil.",
        # Paginație, nu normativul P (fără majusculă și fără formă de cod).
        "Detaliile sunt la p. 12-14 din document.",
        # Numerotare de articol, nu un cod normativ (nu are literă de prefix).
        "Se aplică art. 4.4 din regulament.",
    ],
)
def test_nu_detecteaza_false_pozitive(text):
    assert gaseste_referinte_normative(text) == []


def test_filtrul_de_incluziune_pastreaza_doar_potrivirea_cea_mai_lunga():
    """`SR EN 12831` se potrivește atât cu tiparul `SR ...`, cât și cu `EN ...`;
    trebuie păstrată o singură potrivire (cea mai lungă, „SR EN 12831”), nu ambele."""
    text = "Se aplică SR EN 12831 pentru acest calcul."

    matches = gaseste_referinte_normative(text)

    assert len(matches) == 1
    start, end = matches[0]
    assert text[start:end] == "SR EN 12831"


def test_pozitiile_intoarse_permit_reconstructia_exacta_a_textului():
    text = "Marcajul respectă STAS 6648/1-82 conform pieselor fictive."

    matches = gaseste_referinte_normative(text)

    assert len(matches) == 1
    start, end = matches[0]
    assert text[start:end] == "STAS 6648/1-82"
