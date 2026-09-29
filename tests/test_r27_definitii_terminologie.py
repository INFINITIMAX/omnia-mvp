"""Teste pentru R27: definițiile de terminologie cu literă mică + cratimă/en dash
(same-line) devin articol propriu în `chunking_core._este_referinta_rupta`.
Cazuri reale din P 118/3 (CAPITOLUL 2 - TERMINOLOGIE SPECIFICĂ) și P 118/2
(Anexa 33 „TERMINOLOGIE”, 33.5), reproduse sintetic. Vezi `docs/handoff/R27-tester.md`
și `R27-coder-raport.md`.
"""

import pytest

from chunking_core import creeaza_chunkuri


# --- Definiții cu literă mică + cratimă pe același rând -> articol propriu ------


def test_definitie_cu_cratima_cu_spatii_devine_articol_propriu():
    """Ar pica dacă „2.56. semnal de confirmare alarmă - semnal...” ar rămâne lipit
    de articolul anterior (regresia P1183-03: citarea ar arăta greșit „Art. 1.7”)."""
    text = (
        "\n1.7. Capitolul de fata contine prevederi generale introductive pentru sistemul de alarmare la incendiu.\n"
        "2.56. semnal de confirmare alarmă - semnal de la centrala de semnalizare care confirma alarma reala detectata.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["1.7.", "2.56."]
    assert "semnal de confirmare alarmă" in rezultat[1]["text"]
    assert "semnal de confirmare alarmă" not in rezultat[0]["text"]


def test_definitie_cu_cratima_lipita_de_cuvant_devine_articol_propriu():
    """Ar pica dacă o cratimă lipită imediat de cuvântul următor (fără spațiu, ex.
    „-conexiune”) nu ar fi recunoscută ca marcaj de definiție."""
    text = (
        "\n2.7. Introducere generala suficienta pentru a forma un chunk valid corect complet aici clar bine.\n"
        "2.8. cale de transmisie -conexiune fizica intre elementele componente ale sistemului de semnalizare incendiu.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["2.7.", "2.8."]
    assert "cale de transmisie" in rezultat[1]["text"]


def test_definitie_cu_paranteza_inaintea_cratimei_devine_articol_propriu():
    """Ar pica dacă o paranteză de abreviere plasată chiar înaintea cratimei (ex.
    „(PIF) -”) ar bloca detectarea definiției."""
    text = (
        "\n2.49. Introducere generala suficienta pentru a forma un chunk valid corect complet aici clar bine.\n"
        "2.50. punere în funcțiune(PIF) -proces prin care se verifica functionarea corecta a instalatiei montate.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["2.49.", "2.50."]
    assert "punere în funcțiune" in rezultat[1]["text"]


def test_definitie_cu_en_dash_devine_articol_propriu():
    """Ar pica dacă en dash-ul („–”, nu cratima obișnuită „-”) nu ar fi recunoscut ca
    marcaj de definiție (regresia P 118/2, Anexa 33, 33.5)."""
    text = (
        "\n33.4. Introducere terminologica suficienta pentru a forma un chunk valid corect complet aici clar.\n"
        "33.5. instalație cu preacționare – una sau mai multe zone de detectie care preced actionarea reala a instalatiei.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["33.4.", "33.5."]
    assert "instalație cu preacționare" in rezultat[1]["text"]


def test_definitie_cu_subnivel_devine_articol_propriu():
    """Ar pica dacă un sub-nivel de numerotare (ex. „2.19.18.1.”) nu ar fi recunoscut
    ca definiție proprie doar din cauza adâncimii numerotării."""
    text = (
        "\n2.19.18. Introducere suficienta pentru a forma un chunk valid corect complet aici clar bine sigur.\n"
        "2.19.18.1. termen tehnic special - definitie detaliata a acestui termen conform reglementarii actuale in vigoare.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["2.19.18.", "2.19.18.1."]
    assert "termen tehnic special" in rezultat[1]["text"]


# --- Fără cratimă pe același rând -> rămâne trimitere/continuare ---------------


def test_litera_mica_fara_cratima_pe_acelasi_rand_ramane_atasata():
    """Ar pica dacă un rând cu literă mică fără nicio cratimă/en dash (nu e o
    definiție, doar text de continuare) ar deveni totuși articol propriu."""
    text = (
        "\n2.9. Introducere suficienta pentru a forma un chunk valid corect complet aici clar bine sigur exact.\n"
        "2.10. conform planului tehnic aprobat de autoritatea competenta in domeniul situatiilor de urgenta reale.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["2.9."]
    assert "conform planului tehnic aprobat" in rezultat[0]["text"]


def test_i7_cratima_doar_pe_randul_urmator_nu_devine_articol():
    """Regresia I7: „4.1.4.2.2.2. sau” urmat pe rândul fizic următor de „-”
    (enumerare, nu definiție) trebuie să rămână atașat articolului anterior. Ar
    pica dacă fereastra de căutare a cratimei ar depăși rândul curent."""
    text = (
        "\n4.1.4.2.2.1. Prevederile tehnice urmatoare se aplica instalatiilor descrise in continuare in acest capitol.\n"
        "4.1.4.2.2.2. sau\n"
        "-enumerare cu prima valoare mentionata mai jos in continuarea textului tehnic prezentat anterior aici.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["4.1.4.2.2.1."]
    assert "4.1.4.2.2.2. sau" in rezultat[0]["text"]
    assert "-enumerare cu prima valoare" in rezultat[0]["text"]


# --- Majusculă: comportament neschimbat (regresie) ------------------------------


def test_majuscula_dupa_numar_ramane_articol_indiferent_de_cratima_apropiata():
    """Ar pica dacă adăugarea ramurii de definiție ar interfera cu ramura deja
    existentă pentru majusculă (care trebuie să rămână articol propriu necondiționat,
    chiar dacă întâmplător apare o cratimă în apropiere pe rândul următor)."""
    text = (
        "\n2.11. Introducere suficienta pentru a forma un chunk valid corect complet aici clar bine sigur exact.\n"
        "2.12. Sistemul de detectie - alarmare functioneaza conform specificatiilor tehnice din prezentul capitol.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["2.11.", "2.12."]
    assert "Sistemul de detectie" in rezultat[1]["text"]
