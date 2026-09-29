"""Teste sintetice R28: suportul `ANEXA NR.`/`ANEXA Nr.` din `PATTERN_TITLU_ANEXA`
(regresia reală P 118/2, MO 595 bis). Fiecare test reproduce un punct din
`docs/handoff/R28-tester.md`; fără dependențe de documente reale.
"""

from chunking_core import PATTERN_TITLU_ANEXA, creeaza_chunkuri


# --- 1: PATTERN_TITLU_ANEXA prinde variantele „NR.”/„Nr.” ----------------------


def test_pattern_titlu_anexa_prinde_variantele_nr_si_bis():
    """Ar pica dacă regex-ul nu ar recunoaște vreuna dintre formele „ANEXA NR. 1”,
    „ANEXA NR.2” (fără spațiu), „ANEXA Nr. 3” sau „ANEXA NR.14bis”, sau dacă
    grupul capturat ar include „NR”/„Nr” în loc de doar identificatorul numeric
    (respectiv „14bis”)."""
    cazuri = {
        "\nANEXA NR. 1\n": "1",
        "\nANEXA NR.2\n": "2",
        "\nANEXA Nr. 3\n": "3",
        "\nANEXA NR.14bis\n": "14bis",
    }
    for text, identificator_asteptat in cazuri.items():
        potrivire = PATTERN_TITLU_ANEXA.search(text)
        assert potrivire is not None, text
        assert potrivire.group(1) == identificator_asteptat, text
        assert "NR" not in potrivire.group(1) and "Nr" not in potrivire.group(1)


# --- 2: nu prinde trimiterile din corp sau formele deja excluse de R21 ---------


def test_pattern_titlu_anexa_nu_prinde_trimiteri_din_corp_sau_forme_excluse():
    """Ar pica dacă regex-ul ar prinde o trimitere din corp scrisă cu literă mică
    („anexa nr. 8, la clădirile...”), sau dacă noul suport pentru „NR.”/„Nr.” ar
    slăbi excluderile deja existente din R21 (virgulă sau literă mică imediat
    după număr, semn că e o trimitere, nu un titlu real)."""
    cazuri = [
        "\nanexa nr. 8, la cladirile inalte trebuie respectate normele tehnice.\n",
        "\nANEXA NR. 2, la cladirile inalte se aplica prevederile actuale.\n",
        "\nANEXA NR. 2 au caracter de recomandare pentru proiectantii care aplica.\n",
    ]
    for text in cazuri:
        assert PATTERN_TITLU_ANEXA.search(text) is None, text


# --- 3: regresia reală P 118/2 — capitol omonim în corp vs. anexă „NR.” --------


def test_anexa_nr_cu_capitol_omonim_in_corp_nu_se_confunda_regresie_p118_2():
    """Regresia reală P 118/2: un capitol „33.x.” din corp și o anexă introdusă prin
    „ANEXA NR.33” cu articole interne „33.1.”…„33.3.” nu trebuie să se confunde —
    articolele anexei devin „ANEXA 33.33.1.” etc., iar capitolul din corp rămâne
    „33.1.” neschimbat, fără text pierdut. Ar pica dacă „ANEXA NR.33” nu ar fi
    recunoscută ca titlu de anexă (articolele anexei ar rămâne „33.1.” neprefixate
    și s-ar contopi cu cele din corp), sau dacă vreun fragment de conținut ar
    lipsi din chunk-urile rezultate."""
    text = (
        "\n33.1. Articol de corp care apartine capitolului treizecisitrei din "
        "documentul de baza, cu text suficient de lung pentru a fi un chunk valid.\n"
        "ANEXA NR.33\n"
        "Introducere anexa treizecisitrei cu text detaliat suficient de lung pentru "
        "a fi un chunk valid complet corect stabilit pentru acest exemplu de test.\n"
        "33.1. Primul articol al anexei treizecisitrei cu text suficient de lung "
        "pentru a fi un chunk valid complet si corect pentru acest exemplu de test.\n"
        "33.2. Al doilea articol al anexei treizecisitrei cu text suficient pentru "
        "a fi un chunk valid complet si corect pentru acest exemplu de test scris.\n"
        "33.3. Al treilea articol al anexei treizecisitrei cu text suficient pentru "
        "a fi un chunk valid complet si corect pentru acest exemplu de test scris.\n"
    )

    rezultat = creeaza_chunkuri(text)

    articole = {c["articol"]: c["text"] for c in rezultat}
    assert "33.1." in articole
    assert "Articol de corp care apartine capitolului" in articole["33.1."]
    assert {"ANEXA 33.", "ANEXA 33.33.1.", "ANEXA 33.33.2.", "ANEXA 33.33.3."} <= set(articole)
    assert "Introducere anexa treizecisitrei" in articole["ANEXA 33."]
    assert "Primul articol al anexei" in articole["ANEXA 33.33.1."]
    assert "Al doilea articol al anexei" in articole["ANEXA 33.33.2."]
    assert "Al treilea articol al anexei" in articole["ANEXA 33.33.3."]


# --- 4: formele vechi (fără „NR.”) rămân neschimbate ---------------------------


def test_forme_vechi_de_anexa_fara_nr_raman_neschimbate():
    """Ar pica dacă adăugarea suportului pentru „NR.”/„Nr.” ar altera în vreun fel
    recunoașterea formelor vechi „ANEXA 3” (identificator simplu) sau „ANEXA 3.1.”
    (identificator cu subnivel zecimal), care nu conțin „NR.”/„Nr.”."""
    text = (
        "\nANEXA 3 - TITLU TREI\n"
        "Continut anexa trei cu text detaliat suficient de lung pentru a fi un chunk "
        "valid complet corect pentru acest exemplu sintetic de test automatizat scris.\n"
        "ANEXA 3.1. - SUBSECTIUNE\n"
        "Continut subsectiune anexa cu text suficient de lung pentru a fi un chunk "
        "valid complet corect pentru acest exemplu sintetic de test automatizat scris.\n"
    )

    rezultat = creeaza_chunkuri(text)

    articole = {c["articol"]: c["text"] for c in rezultat}
    assert "ANEXA 3." in articole
    assert "Continut anexa trei" in articole["ANEXA 3."]
    assert "ANEXA 3.1." in articole
    assert "Continut subsectiune anexa" in articole["ANEXA 3.1."]
