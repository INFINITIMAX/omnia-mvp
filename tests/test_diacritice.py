"""Teste pentru diacritice.py — corectarea sedila -> virgula pentru ț/ș."""

import pytest

from diacritice import normalizeaza_diacritice


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
