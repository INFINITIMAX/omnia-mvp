"""Teste sintetice pentru formatul NP 127:2009 (Runda R29): marcajul „Articolul N”,
titlurile „Capitolul <roman>”/„Secţiunea <n>” și separatorul „+”. Texte mici,
deterministe, fără dependențe de documente_noi.
"""

from chunking_core import acoperire_text_brut, creeaza_chunkuri


# --- 1: „Articolul N” la început de rând devine articol -----------------------


def test_articolul_n_la_inceput_de_rand_devine_articol_cu_punct():
    """Ar pica dacă `Articolul 117` nu ar deschide un articol propriu cu
    identificatorul „117.” (contractul cerut de importer/retrieval)."""
    text = (
        "\nArticolul 117 Evacuarea fumului trebuie realizata printr-un sistem mecanic "
        "cu un debit minim de 600 mc/h pe autoturism conform prezentei reglementari.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["117."]
    assert "Evacuarea fumului" in rezultat[0]["text"]
    assert "Articolul" not in rezultat[0]["text"]


def test_articolul_urmat_de_litera_mica_nu_devine_articol_nou():
    """„Articolul 117 evacuarea...” (literă mică imediat după număr) nu respectă
    lookahead-ul cerut și trebuie să rămână text atașat articolului anterior, nu
    un articol „117.” separat. Ar pica dacă regexul ar accepta și litera mică."""
    text = (
        "\nArticolul 5 Aceasta sectiune defineste domeniul de aplicare al prezentei "
        "reglementari tehnice pentru constructii de acest tip.\n"
        "Articolul 117 evacuarea fumului trebuie sa respecte prevederile tehnice ale "
        "sistemelor de desfumare montate in parcajele subterane auto.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["5."]
    assert "evacuarea fumului" in rezultat[0]["text"]


def test_articolul_in_mijlocul_frazei_nu_deschide_articol_nou():
    """„Articolul 6” apărut în mijlocul unui rând (nu la început de rând) nu
    trebuie tratat ca marcaj — rămâne text simplu, atașat articolului curent.
    Ar pica dacă regexul nu ar cere strict începutul de rând."""
    text = (
        "\nArticolul 5 Se aplica cerintele tehnice mentionate si in Articolul 6 din "
        "alta reglementare conexa care nu se aplica direct in acest context tehnic.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["5."]
    assert "Articolul 6" in rezultat[0]["text"]


# --- 2: titluri „Capitolul”/„Secţiunea” nu devin articole și nu apar în text ---


def test_titluri_capitol_si_sectiune_np127_elimina_dar_secretiune_fraza_ramane():
    """Titlurile de capitol/secțiune (formatul Portalului Legislativ) trebuie
    eliminate integral, fără să devină articole proprii; o frază care începe cu
    „Secțiunea” dar nu e urmată de un număr (i5-style) rămâne text normal, atașat
    articolului anterior. Ar pica dacă titlurile ar deveni chunk-uri/articole
    separate sau dacă fraza obișnuită ar fi eliminată din greșeală."""
    text = (
        "\nCapitolul I Dispozitii generale\n"
        "Secțiunea 1 Obiect si domeniu de aplicare\n"
        "Articolul 1 Prezentul normativ stabileste conditiile tehnice minime "
        "obligatorii pentru proiectarea parcajelor subterane pentru autoturisme.\n"
        "Secțiunea a 2-a Terminologie si definitii\n"
        "Articolul 2 Termenii folositi in acest document au intelesul stabilit prin "
        "prezenta reglementare tehnica de specialitate pentru domeniul constructiilor.\n"
        "Secțiunea conductelor se dimensioneaza conform tabelelor de calcul prezentate "
        "in anexa tehnica atasata la finalul prezentului document normativ.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["1.", "2."]
    text_complet = " ".join(c["text"] for c in rezultat)
    assert "Capitolul I" not in text_complet
    assert "Dispozitii generale" not in text_complet
    assert "Secțiunea 1" not in text_complet
    assert "Secțiunea a 2-a" not in text_complet
    # Fraza obișnuită „Secțiunea conductelor...” nu e un titlu (nu e urmată de
    # număr) și trebuie păstrată, atașată ultimului articol.
    assert "Secțiunea conductelor se dimensioneaza" in text_complet


# --- 3: separatorul „+” ---------------------------------------------------------


def test_plus_eliminat_inaintea_articolului_urmator():
    """Un rând „+” urmat (după linii goale) de „Articolul N” e separatorul
    Portalului Legislativ și trebuie eliminat. Ar pica dacă „+” ar rămâne în
    textul unui chunk."""
    text = (
        "\nArticolul 1 Primul articol contine prevederi tehnice suficient de lungi "
        "pentru a forma un chunk valid in acest test sintetic de verificare.\n"
        "+\n"
        "Articolul 2 Al doilea articol contine de asemenea prevederi tehnice "
        "suficient de lungi pentru a forma un chunk valid separat corect.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["1.", "2."]
    text_complet = " ".join(c["text"] for c in rezultat)
    assert "+" not in text_complet


def test_plus_pastrat_cand_e_parte_dintr_o_formula():
    """Regresie pentru corectura planner (punctul 1): un „+” pe rând propriu care
    NU e urmat de „Articolul”/„Capitolul”/„Secțiunea” (ex. o formulă „a / + / b”,
    ca în I7, P 118/3, NP 015) trebuie păstrat în text, nu eliminat orbește.
    Ar pica dacă implementarea ar elimina toate rândurile „+”, indiferent de
    context (varianta inițială a coder-ului, respinsă de planner)."""
    text = (
        "\nArticolul 1 Formula de calcul a debitului este urmatoarea, conform "
        "relatiei tehnice de mai jos prezentate in cuprinsul prezentului normativ.\n"
        "a\n"
        "+\n"
        "b\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["1."]
    assert "+" in rezultat[0]["text"]


# --- 4: acoperire pentru textul sintetic în format NP 127 ----------------------


def test_acoperire_text_sintetic_format_np127_este_aproape_completa():
    """Regresie pentru corectura planner (punctul 2): `_normalizeaza_pentru_acoperire`
    trebuie să scoată și prefixul „Articolul N” de la început de rând din textul
    brut, altfel liniile de articol raportează fals acoperire scăzută (motivul
    pentru care acoperirea NP 127 era 11% înainte de corectură). Ar pica dacă
    prefixul „Articolul N” nu ar fi eliminat la normalizarea liniei brute."""
    text = (
        "\nArticolul 117 Evacuarea fumului trebuie realizata printr-un sistem mecanic "
        "cu un debit minim de sase sute de metri cubi pe ora pe autoturism instalat.\n"
        "+\n"
        "Articolul 129 Distanta dintre gurile de evacuare a fumului si orice "
        "constructie suprateran va fi de minimum opt metri fata de aceasta cladire.\n"
        "+\n"
        "Articolul 130 Prizele de aer proaspat vor fi amplasate la o distanta minima "
        "de opt metri fata de sursele de poluare identificate in vecinatate directa.\n"
    )

    rezultat = creeaza_chunkuri(text)
    acoperire = acoperire_text_brut(text, rezultat)

    assert acoperire >= 0.99
