"""Teste deterministe pentru refuzul local al calculelor de proiectare."""

import pytest

from scope_core import is_engineering_calculation_request, normalize_scope_text


@pytest.mark.parametrize(
    "question",
    [
        "Calculează sarcina termică pentru o hală.",
        "Estimează consumul necesar pentru proiect.",
        "Dimensionează instalația de răcire.",
        "Câți kW îmi trebuie pentru clădire?",
        "Hală de 200 kW, 4000 mp, 7 m, 28°C, Buzău: ce sarcină de răcire este necesară?",
    ],
)
def test_cererile_de_executie_sunt_in_afara_scopeului(question):
    assert is_engineering_calculation_request(question) is True


def test_calculul_cerut_conform_normativului_este_diferit_de_metoda_intrebata():
    assert is_engineering_calculation_request(
        "Cum se calculează sarcina termică potrivit I5?"
    ) is False
    assert is_engineering_calculation_request(
        "Calculează conform I5 sarcina termică pentru hală."
    ) is True


@pytest.mark.parametrize(
    "question",
    [
        "Cum se calculează sarcina termică potrivit I5?",
        "Ce formulă prevede normativul pentru sarcina termică?",
        "Ce metodă de calcul prevede normativul pentru sarcina termică?",
        "Care este debitul minim pentru grupuri sanitare?",
        "Care sunt pragurile și valorile prescrise de normativ?",
        "Ce articol din I5 descrie metodologia?",
    ],
)
def test_intrebarile_normative_sau_metodologice_nu_sunt_blocate(question):
    assert is_engineering_calculation_request(question) is False


def test_normalizarea_este_sigura_pentru_diacritice_si_capitalizare():
    assert normalize_scope_text("  CÂȚI kW ÎMI   TREBUIE? ") == "cati kw imi trebuie?"
    assert is_engineering_calculation_request("CÂȚI kW ÎMI TREBUIE?") is True
