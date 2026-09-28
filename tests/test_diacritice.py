"""Teste pentru diacritice.py — corectarea sedila -> virgula pentru ț/ș."""

import pytest

from diacritice import corecteaza_substituiri_pdf, normalizeaza_diacritice


def test_normalizeaza_cele_patru_perechi_sedila_la_virgula():
    text = "Rețeaua ştie despre Ţara aceasta şi despre acțiunea corectă"
    asteptat = "Rețeaua știe despre Țara aceasta și despre acțiunea corectă"
    assert normalizeaza_diacritice(text) == asteptat


@pytest.mark.parametrize(
    ("sedila", "virgula"),
    [("ţ", "ț"), ("ş", "ș"), ("Ţ", "Ț"), ("Ş", "Ș")],
)
def test_fiecare_pereche_individual(sedila, virgula):
    assert normalizeaza_diacritice(sedila) == virgula


def test_textul_deja_corect_ramane_neschimbat():
    text = "rețea, ușă, comunicație, Țara Românească"
    assert normalizeaza_diacritice(text) == text


def test_textul_fara_diacritice_ramane_neschimbat():
    text = "text simplu fara nicio problema 12345 (A).(b)."
    assert normalizeaza_diacritice(text) == text


def test_refuza_valori_non_text():
    with pytest.raises(ValueError):
        normalizeaza_diacritice(None)


def test_simbolurile_matematice_nu_sunt_afectate():
    """Simbolurile din formule (radical, inmultire, comparatii, punctul
    suprapus combinat folosit pentru V-punct) nu au nicio legatura cu
    sedila/virgula si trebuie sa ramana identice."""
    text = "√N-1 × 2 ≤ V̇ ≥ 0,83 h ℂ ℝ"
    assert normalizeaza_diacritice(text) == text


def test_literele_grecesti_nu_sunt_afectate():
    text = "Σ ψ θ ρ λ ζ Φ α ν Ω β γ δ"
    assert normalizeaza_diacritice(text) == text


def test_literele_stilizate_mathematical_alphanumeric_nu_sunt_afectate():
    """Blocul Mathematical Alphanumeric Symbols (reconstruit din CambriaMath,
    vezi glyph_mapping.py) nu contine ţ/ş/Ţ/Ş, deci trece nemodificat."""
    text = "\U0001D449 \U0001D706 \U0001D7CE"  # 𝑉, 𝜆, 𝟎
    assert normalizeaza_diacritice(text) == text


def test_alte_diacritice_romanesti_nu_sunt_afectate():
    """â, î, ă, Â, Î, Ă nu au nicio varianta sedila si nu trebuie atinse."""
    text = "câine, înalt, fărâmă, Â, Î, Ă"
    assert normalizeaza_diacritice(text) == text


# --- corecteaza_substituiri_pdf (Runda R22, I7) ------------------------------


@pytest.mark.parametrize(
    ("cuvant_corupt", "cuvant_asteptat"),
    [
        ("protecĠia", "protecția"),
        ("úi", "și"),
        ("INSTALAğIILOR", "INSTALAȚIILOR"),
        ("construc܊ii", "construcții"),
        ("܈i", "și"),
    ],
)
def test_corecteaza_substituiri_pdf_pe_cuvinte_reale_din_i7(cuvant_corupt, cuvant_asteptat):
    """Ar pica dacă vreuna dintre cele cinci substituiri validate pe I7
    (Ġ->ț, ú->ș, ğ->Ț, U+070A->ț, U+0708->ș) nu ar fi aplicată corect."""
    assert corecteaza_substituiri_pdf(cuvant_corupt) == cuvant_asteptat


def test_corecteaza_substituiri_pdf_x98_ramane_neschimbat():
    """\\x98 e un simbol pierdut la extragere, nu o diacritică — nu trebuie mapat.
    Ar pica dacă implementarea l-ar trata greșit ca substituire de diacritică."""
    text = "valoare\x98suplimentara"
    assert corecteaza_substituiri_pdf(text) == text


def test_corecteaza_substituiri_pdf_text_fara_caractere_corupte_ramane_identic():
    """Un text fără niciunul dintre cele cinci caractere corupte trece nemodificat.
    Ar pica dacă funcția ar altera accidental alte caractere."""
    text = "text normal romanesc fara nicio problema de extragere PDF"
    assert corecteaza_substituiri_pdf(text) == text


def test_corecteaza_substituiri_pdf_nu_atinge_sedila_sau_diacritice_corecte():
    """Sedila (ţ/ş/Ţ/Ş) rămâne treaba lui `normalizeaza_diacritice`, nu a acestei
    funcții — la fel diacriticele deja corecte cu virgulă. Ar pica dacă
    `corecteaza_substituiri_pdf` ar începe să acopere și acest caz."""
    text = "rețea, ușă, Țara, comunicaţie, ştie, Şase"
    assert corecteaza_substituiri_pdf(text) == text


def test_corecteaza_substituiri_pdf_refuza_valori_non_text():
    with pytest.raises(ValueError):
        corecteaza_substituiri_pdf(None)
