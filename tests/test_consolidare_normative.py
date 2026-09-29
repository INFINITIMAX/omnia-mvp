"""Teste sintetice pentru consolidare_normative (R26/B), fără fișierele reale
(documente_noi/p118_*). Fiecare test reproduce o singură regulă din
docs/handoff/R26-B-coder-raport.md / R26-spec.md.
"""

import pytest

from consolidare_normative import (
    ItemOrdin,
    PATTERN_NUMARARE_MARCAJE,
    _localizeaza_punct,
    _verifica_final,
    aplica_operatii,
    segmenteaza_ordin,
)

ORDIN_INFO = {"ordin": "6.025/2018", "monitorul_oficial": "977", "data_mo": "19.11.2018"}


def _manifest(operatii, inlocuiri_globale=None):
    manifest = {**ORDIN_INFO, "operatii": operatii}
    if inlocuiri_globale is not None:
        manifest["inlocuiri_globale"] = inlocuiri_globale
    return manifest


def _ordin(corp_itemi: str) -> str:
    return (
        "Art. I. Se modifică prezentul act normativ după cum urmează:\n"
        + corp_itemi
        + "\nArt. II. Prezentul ordin intră în vigoare la data publicării lui.\n"
    )


@pytest.fixture
def baza_simpla() -> str:
    return (
        "1.1. Domeniul de aplicare\n"
        "Text alfa despre domeniul de aplicare al prezentului normativ tehnic aici.\n"
        "1.2. Definitii generale\n"
        "(1) Primul alineat cu definitii importante pentru intelegerea textului aici prezent.\n"
        "(2) Al doilea alineat cu subdiviziuni:\n"
        "a) primul continut prezent aici insusi.\n"
        "b) al doilea continut prezent aici insusi.\n"
        "c) al treilea continut prezent aici insusi.\n"
        "1.3. Domeniul urmator al textului\n"
        "Text final pentru ultimul punct al acestui exemplu sintetic.\n"
    )


# ---------------------------------------------------------------------------
# 1. Segmentare
# ---------------------------------------------------------------------------


def test_segmenteaza_ambele_stiluri_de_numerotare():
    """Ar pica dacă stilul 'N. text pe același rând' sau stilul 'N.\\ntext pe rândul
    următor' nu ar fi recunoscute deopotrivă."""
    ordin = _ordin(
        "1. La punctul 1.1., alineatul (1) se modifică și va avea următorul cuprins:\n"
        "„(1) Text nou pentru primul alineat introdus prin prezentul ordin aici.”\n"
        "2.\n"
        "La punctul 1.2. se modifică și va avea următorul cuprins:\n"
        "„1.2. Text nou pentru al doilea punct introdus prin prezentul ordin.”\n"
    )

    itemi = segmenteaza_ordin(ordin)

    assert [item.nr for item in itemi] == [1, 2]
    assert "cuprins" in itemi[0].instructiune.lower()
    assert "1.2. Text nou pentru al doilea punct" in itemi[1].text_nou


def test_segmenteaza_se_opreste_la_articolul_ii():
    """Ar pica dacă textul de după Art. II ('Articolul II', forma lungă) ar fi
    citit ca un item suplimentar."""
    ordin = (
        "Art. I. Se modifică prezentul act normativ după cum urmează:\n"
        "1. La punctul 1.1. se modifică și va avea următorul cuprins:\n"
        "„1.1. Text nou complet.”\n"
        "Articolul II. Prezentul ordin intră în vigoare la data publicării lui în Monitorul Oficial.\n"
        "2. Acest text nu trebuie citit deloc pentru că e după Art. II al ordinului aici prezent.\n"
    )

    itemi = segmenteaza_ordin(ordin)

    assert len(itemi) == 1
    assert itemi[0].nr == 1
    assert "nu trebuie citit" not in itemi[0].text_nou


def test_segmenteaza_elimina_antet_mo_numar_pagina_si_linie_de_puncte():
    """Ar pica dacă antetul MO, numărul de pagină singur pe rând sau o linie doar-puncte
    ar rămâne în text_nou după curățare (verificat prin rezultatul aplicării)."""
    baza = "1.1. Domeniul de aplicare\nText vechi original prezent complet aici bine stabilit corect.\n"
    item = ItemOrdin(
        nr=1,
        instructiune="La punctul 1.1. se modifică și va avea următorul cuprins:",
        text_nou=(
            "1.1. Domeniul de aplicare noua varianta introdusa complet.\n"
            "MONITORUL OFICIAL AL ROMÂNIEI, PARTEA I, Nr. 977\n"
            "12\n"
            "Text continuat dupa antet care trebuie pastrat complet corect aici bine stabilit.\n"
            "....\n"
            "Ultima propozitie a textului nou introdus complet corect stabilit aici bine.\n"
        ),
    )
    manifest = _manifest([{"nr": 1, "tip": "inlocuieste_punct", "tinte": [{"punct": "1.1"}]}])

    rezultat, _ = aplica_operatii(baza, [item], manifest)

    assert "MONITORUL OFICIAL" not in rezultat
    assert "\n12\n" not in rezultat
    assert "...." not in rezultat
    assert "Text continuat dupa antet" in rezultat
    assert "Ultima propozitie a textului nou" in rezultat


def test_segmenteaza_numerotare_neconsecutiva_esueaza_la_segmentare():
    """Ar pica dacă un ordin care sare direct de la itemul 1 la itemul 5 (fără 2-4)
    ar fi acceptat tacit — itemul 1 ar înghiți instrucțiunea itemului 5 ca text nou."""
    ordin = _ordin(
        "1. La punctul 1.1. se modifică și va avea următorul cuprins:\n„1.1. Text nou.”\n"
        "5. La punctul 1.3. se modifică și va avea următorul cuprins:\n„1.3. Text nou al doilea.”\n"
    )

    with pytest.raises(ValueError, match="numerotare neconsecutivă"):
        segmenteaza_ordin(ordin)


def test_segmenteaza_item_nerecunoscut_ridica_eroare():
    """Ar pica dacă un item fără 'cuprins:', fără 'se abrogă.' și fără tiparul de
    sintagmă ar fi acceptat în loc să oprească segmentarea."""
    ordin = _ordin(
        "1. Se modifică prezentul act normativ fara nicio precizare clara asupra "
        "continutului nou introdus aici deloc.\n"
    )

    with pytest.raises(ValueError, match="nu conține nici"):
        segmenteaza_ordin(ordin)


def test_segmenteaza_item_sintagma_se_inlocuieste_cu_sintagma():
    """Ar pica dacă tiparul „sintagma «X» se înlocuiește cu sintagma «Y».” nu ar fi
    recunoscut, sau dacă X/Y rupte pe rând (DOTALL) nu ar fi capturate corect."""
    ordin = _ordin(
        "1. La tabelele 7.10-7.12, sintagma „forma\nveche a textului” se înlocuiește "
        "cu sintagma „forma noua a textului”.\n"
    )

    itemi = segmenteaza_ordin(ordin)

    assert len(itemi) == 1
    assert itemi[0].sintagma_veche == "forma veche a textului"
    assert itemi[0].sintagma_noua == "forma noua a textului"
    assert itemi[0].text_nou == ""


# ---------------------------------------------------------------------------
# 2. Fiecare tip de operație
# ---------------------------------------------------------------------------


def test_inlocuieste_punct_simplu(baza_simpla):
    """Ar pica dacă localizarea punctului 1.1 ar rata, sau dacă textul vechi ar
    supraviețui alături de cel nou."""
    item = ItemOrdin(
        nr=1,
        instructiune="La punctul 1.1. se modifică și va avea următorul cuprins:",
        text_nou="1.1. Domeniul de aplicare (versiune noua)\nText nou complet diferit fata de cel vechi.\n",
    )
    manifest = _manifest([{"nr": 1, "tip": "inlocuieste_punct", "tinte": [{"punct": "1.1"}]}])

    rezultat, raport = aplica_operatii(baza_simpla, [item], manifest)

    assert "Text nou complet diferit fata de cel vechi" in rezultat
    assert "Text alfa despre domeniul de aplicare" not in rezultat
    assert len(PATTERN_NUMARARE_MARCAJE.findall(rezultat)) == 1
    assert raport[0]["status"] == "aplicat"


def test_inlocuieste_subunitate_imbricata_alineat_cu_litere_interioare(baza_simpla):
    """Regresie Runda 3: un alineat cu litere imbricate nu trebuie să-și taie
    propria întindere la prima literă — altfel localizarea literei 'c' în
    subregiunea (deja goală) eșuează mereu."""
    item = ItemOrdin(
        nr=2,
        instructiune="La punctul 1.2., litera c) a alineatului (2) se modifică și va avea următorul cuprins:",
        text_nou="c) al treilea continut nou introdus prin prezentul ordin aici insusi.\n",
    )
    manifest = _manifest([
        {"nr": 2, "tip": "inlocuieste_subunitate", "tinte": [{"punct": "1.2", "alineat": "2", "litera": "c"}]}
    ])

    rezultat, _ = aplica_operatii(baza_simpla, [item], manifest)

    assert "c) al treilea continut nou introdus" in rezultat
    assert "c) al treilea continut prezent aici insusi" not in rezultat
    assert "a) primul continut prezent aici insusi" in rezultat
    assert "b) al doilea continut prezent aici insusi" in rezultat


def test_prima_subunitate_pe_randul_punctului_fara_spatiu():
    """Regresie Runda 2: '3.8.2.5 (1)Sunetul...' — alineatul (1) lipit imediat de
    numărul punctului, fără spațiu, trebuie localizat (nu 0 potriviri)."""
    baza = (
        "3.8.2.5 (1)Sunetul alarmei trebuie sa fie perceptibil in toate zonele protejate ale cladirii.\n"
        "3.8.2.6 Urmatorul punct simplu prezent dupa cel precedent verificat aici bine.\n"
    )
    item = ItemOrdin(
        nr=1,
        instructiune="La punctul 3.8.2.5, alineatul (1) se modifică și va avea următorul cuprins:",
        text_nou="(1)Sunetul nou al alarmei introdus prin prezentul ordin aici bine stabilit.\n",
    )
    manifest = _manifest([
        {"nr": 1, "tip": "inlocuieste_subunitate", "tinte": [{"punct": "3.8.2.5", "alineat": "1"}]}
    ])

    rezultat, _ = aplica_operatii(baza, [item], manifest)

    assert "Sunetul nou al alarmei" in rezultat
    assert "3.8.2.6 Urmatorul punct simplu" in rezultat


def test_prima_subunitate_pe_randul_punctului_cu_spatiu_si_punct_fara_punct_final():
    """'3.3.1 (1) ...' — punctul nu se termină cu punct, ci cu spațiu, iar alineatul
    e pe rândul punctului, cu spațiu de data asta."""
    baza = (
        "3.3.1 (1) Echiparea cladirii cu instalatii se face conform prevederilor tehnice prezentate mai jos.\n"
        "3.3.2 Urmatorul punct prezent imediat dupa cel verificat mai sus corect aici.\n"
    )
    item = ItemOrdin(
        nr=1,
        instructiune="La punctul 3.3.1, alineatul (1) se modifică și va avea următorul cuprins:",
        text_nou="(1) Echiparea noua a cladirii introdusa prin prezentul ordin aici bine stabilit.\n",
    )
    manifest = _manifest([
        {"nr": 1, "tip": "inlocuieste_subunitate", "tinte": [{"punct": "3.3.1", "alineat": "1"}]}
    ])

    rezultat, _ = aplica_operatii(baza, [item], manifest)

    assert "Echiparea noua a cladirii" in rezultat
    assert "3.3.2 Urmatorul punct prezent" in rezultat


def test_insereaza_dupa_alineat_implicit_cand_punctul_nu_are_etichete():
    """Runda 3: dacă punctul nu conține nicio etichetă '(n)', alineatul (1) e
    implicit tot conținutul punctului — inserarea 'după alineatul (1)' cade la
    finalul punctului, iar intrarea din raport marchează 'alineat_implicit'."""
    baza = (
        "2.1. Un punct fara nicio eticheta de alineat prezent aici deloc niciodata complet.\n"
        "2.2. Urmatorul punct simplu prezent imediat dupa cel dintai verificat aici bine.\n"
    )
    item = ItemOrdin(
        nr=3,
        instructiune="După punctul 2.1., alineatul (1), se introduce un nou alineat (2), cu următorul cuprins:",
        text_nou="(2) Alineat nou introdus prin prezentul ordin dupa primul, aici bine stabilit complet.",
    )
    manifest = _manifest([
        {"nr": 3, "tip": "insereaza_dupa", "tinte": [{"punct": "2.1", "dupa_alineat": "1"}]}
    ])

    rezultat, raport = aplica_operatii(baza, [item], manifest)

    assert raport[0].get("alineat_implicit") is True
    pozitie_nou = rezultat.index("Alineat nou introdus")
    pozitie_2_2 = rezultat.index("2.2. Urmatorul punct")
    assert pozitie_nou < pozitie_2_2


def test_aparitie_permisa_doar_cand_exista_cu_adevarat_doua_potriviri():
    """Runda 3: 'aparitie' alege a n-a potrivire când numărul de punct e duplicat
    real în sursă — abrogă doar prima apariție, a doua rămâne intactă."""
    baza = (
        "23.51. Primul continut original la prima aparitie a acestui numar de punct in sursa.\n"
        "23.52. Punct intermediar prezent intre cele doua aparitii ale numarului duplicat.\n"
        "23.51. Al doilea continut original la a doua aparitie a acestui numar de punct in sursa.\n"
        "23.53. Punct final dupa cele doua aparitii verificate complet mai sus bine stabilit.\n"
    )
    item = ItemOrdin(nr=1, instructiune="Punctul 23.51 se abrogă.", text_nou="")
    manifest = _manifest([{
        "nr": 1, "tip": "abroga_punct",
        "tinte": [{"punct": "23.51", "aparitie": 1, "justificare": "prima aparitie e cea vizata de ordin"}],
    }])

    rezultat, raport = aplica_operatii(baza, [item], manifest)

    assert "Primul continut original la prima aparitie" not in rezultat
    assert "Al doilea continut original la a doua aparitie" in rezultat
    assert raport[0]["aparitie"] == 1
    assert raport[0]["justificare"]


def test_aparitie_pe_punct_unic_ridica_eroare(baza_simpla):
    """'aparitie' nu poate fi folosită pentru a ascunde tacit o potrivire unică —
    trebuie să existe efectiv >=2 potriviri."""
    with pytest.raises(ValueError, match="permisă doar"):
        _localizeaza_punct(baza_simpla, "1.1", aparitie=1)


def test_aparitie_fara_justificare_ridica_eroare():
    """'aparitie' fără 'justificare' trebuie respinsă la validare, înainte de
    localizare."""
    from consolidare_normative import _valideaza_operatie

    item = ItemOrdin(nr=1, instructiune="Punctul 23.51 se abrogă.", text_nou="")
    operatie = {"nr": 1, "tip": "abroga_punct", "tinte": [{"punct": "23.51", "aparitie": 1}]}

    with pytest.raises(ValueError, match="justificare"):
        _valideaza_operatie(item, operatie)


def test_renumeroteaza_cu_numar_nou_deja_existent_ridica_eroare():
    """Ar pica dacă renumerotarea ar accepta un număr nou care există deja în bază
    (ar produce un duplicat silențios)."""
    baza = (
        "24.31. Continut existent la numarul curent deja prezent in sursa mai jos.\n"
        "24.32. Continut existent la numarul urmator deja prezent in sursa verificat bine.\n"
    )
    item = ItemOrdin(
        nr=1,
        instructiune="Punctul 24.32 se renumerotează și devine punctul 24.31, cu următorul cuprins:",
        text_nou="24.31. Text nou dupa renumerotare introdus complet.\n",
    )
    manifest = _manifest([{
        "nr": 1, "tip": "renumeroteaza_inlocuieste",
        "tinte": [{"punct_vechi": "24.32", "punct_nou": "24.31"}],
    }])

    with pytest.raises(ValueError, match="există deja"):
        aplica_operatii(baza, [item], manifest)


def test_cuprins_ignorat_la_localizarea_punctului():
    """O linie de cuprins ('1.2 ... 5') cu același număr de punct nu trebuie
    confundată cu punctul real — altfel localizarea ar eșua cu '2 potriviri'."""
    baza = (
        "1.2 Definitii generale .......... 5\n"
        "1.1. Domeniul de aplicare\n"
        "Text prim continut real prezent complet aici bine stabilit corect major.\n"
        "1.2. Definitii generale\n"
        "Text al doilea continut real prezent complet aici bine stabilit corect major.\n"
        "1.3. Domeniul urmator\n"
        "Text final continut real prezent complet aici bine stabilit corect major.\n"
    )

    start, sfarsit = _localizeaza_punct(baza, "1.2")

    assert baza[start:sfarsit].startswith("1.2. Definitii generale")
    assert "..........  5" not in baza[start:sfarsit]


def test_inlocuieste_bloc_intre_ancore():
    """Ar pica dacă blocul dintre cele două ancore n-ar fi înlocuit integral, sau
    dacă textul de dincolo de ancora de sfârșit ar fi atins."""
    baza = (
        "TABEL X\n"
        "rand vechi 1 al tabelului original prezent complet aici bine stabilit corect.\n"
        "rand vechi 2 al tabelului original prezent complet aici bine stabilit corect.\n"
        "TABEL Y\n"
        "Urmatoarea sectiune independenta de tabel prezenta imediat dupa aici bine.\n"
    )
    item = ItemOrdin(
        nr=1,
        instructiune="La tabelul X, textul se modifică și va avea următorul cuprins:",
        text_nou="TABEL X\nrand nou 1 introdus complet diferit prezent aici bine stabilit corect major.\n",
    )
    manifest = _manifest([{
        "nr": 1, "tip": "inlocuieste_bloc",
        "tinte": [{"ancora_inceput": "TABEL X", "ancora_sfarsit": "TABEL Y"}],
    }])

    rezultat, _ = aplica_operatii(baza, [item], manifest)

    assert "rand nou 1 introdus" in rezultat
    assert "rand vechi 1" not in rezultat
    assert "rand vechi 2" not in rezultat
    assert "Urmatoarea sectiune independenta de tabel" in rezultat


def test_inlocuieste_sintagma_in_bloc_nu_adauga_marcaj():
    """Ar pica dacă înlocuirea de sintagmă în interiorul unui bloc ancorat ar
    adăuga marcaj de proveniență (ca la înlocuirile globale, nu trebuie), sau
    dacă ar atinge textul din afara blocului."""
    ordin = _ordin(
        "1. La tabelele X şi Y, sintagma „forma veche” se înlocuiește cu sintagma „forma noua”.\n"
    )
    itemi = segmenteaza_ordin(ordin)
    baza = (
        "BLOC START\n"
        "Text cu forma veche mentionata prima data complet aici bine stabilit corect major.\n"
        "Alt rand cu forma veche mentionata a doua oara complet aici bine stabilit corect.\n"
        "BLOC END\n"
        "Text de dupa care nu trebuie atins deloc complet aici bine stabilit corect major.\n"
    )
    manifest = _manifest([{
        "nr": 1, "tip": "inlocuieste_sintagma_in_bloc",
        "tinte": [{"ancora_inceput": "BLOC START", "ancora_sfarsit": "BLOC END"}],
    }])

    rezultat, raport = aplica_operatii(baza, itemi, manifest)

    assert rezultat.count("forma noua") == 2
    assert "forma veche" not in rezultat.split("BLOC END")[0]
    assert "Text de dupa care nu trebuie atins" in rezultat
    assert len(PATTERN_NUMARARE_MARCAJE.findall(rezultat)) == 0
    intrare = next(i for i in raport if i["tip"] == "inlocuieste_sintagma_in_bloc")
    assert intrare["numar_inlocuiri"] == 2


# ---------------------------------------------------------------------------
# 3. Fail-closed
# ---------------------------------------------------------------------------


def test_localizare_punct_cu_zero_potriviri_ridica_eroare(baza_simpla):
    with pytest.raises(ValueError, match="0 potriviri"):
        _localizeaza_punct(baza_simpla, "9.9")


def test_localizare_punct_cu_doua_potriviri_fara_aparitie_ridica_eroare():
    baza = (
        "5.5. Primul continut duplicat prezent la prima aparitie a acestui punct.\n"
        "5.6. Punct intermediar diferit prezent intre cele doua aparitii verificate bine.\n"
        "5.5. Al doilea continut duplicat prezent la a doua aparitie a acestui punct verificat.\n"
    )
    with pytest.raises(ValueError, match="2 potriviri"):
        _localizeaza_punct(baza, "5.5")


def test_tinte_suprapuse_ridica_eroare(baza_simpla):
    """Două operații care țintesc exact același punct trebuie respinse — nu se
    aplică nicio ordine implicită de rezolvare a suprapunerii."""
    item1 = ItemOrdin(
        nr=10,
        instructiune="La punctul 1.1. se modifică și va avea următorul cuprins:",
        text_nou="1.1. Domeniul de aplicare nou introdus complet diferit fata de vechi.\n",
    )
    item2 = ItemOrdin(nr=11, instructiune="Punctul 1.1 se abrogă.", text_nou="")
    manifest = _manifest([
        {"nr": 10, "tip": "inlocuieste_punct", "tinte": [{"punct": "1.1"}]},
        {"nr": 11, "tip": "abroga_punct", "tinte": [{"punct": "1.1"}]},
    ])

    with pytest.raises(ValueError, match="suprapuse"):
        aplica_operatii(baza_simpla, [item1, item2], manifest)


def test_instructiune_care_nu_mentioneaza_punctul_ridica_eroare():
    from consolidare_normative import _valideaza_operatie

    item = ItemOrdin(
        nr=1,
        instructiune="La punctul 9.9. se modifică și va avea următorul cuprins:",
        text_nou="text nou",
    )
    operatie = {"nr": 1, "tip": "inlocuieste_punct", "tinte": [{"punct": "1.1"}]}

    with pytest.raises(ValueError, match="nu conține punctul"):
        _valideaza_operatie(item, operatie)


def test_verifica_final_text_nou_absent_ridica_eroare():
    rezultat = (
        "Text oarecare complet diferit.\n"
        "[Text modificat prin Ordinul nr. 6.025/2018, publicat în Monitorul Oficial nr. 977 din 19.11.2018]\n"
    )
    tinte = [{
        "nr": 1, "tinta": "punct 1.1",
        "_text_nou_norm": "text nou care nu exista deloc in rezultat",
        "_text_vechi_norm": "", "_fara_marcaj": False,
    }]

    with pytest.raises(ValueError, match="text_nou nu apare literal"):
        _verifica_final(rezultat, tinte)


def test_verifica_final_text_vechi_ramas_ridica_eroare():
    """text_nou trebuie să fie prezent (nu declanșează prima verificare), dar
    textul vechi supraviețuiește pe lângă el — a doua verificare trebuie să
    prindă exact acest caz."""
    rezultat = (
        "Text nou introdus corect prezent in rezultat.\n"
        "Text vechi original inca prezent din greseala aici.\n"
        "[Text modificat prin Ordinul nr. 6.025/2018, publicat în Monitorul Oficial nr. 977 din 19.11.2018]\n"
    )
    tinte = [{
        "nr": 1, "tinta": "punct 1.1",
        "_text_nou_norm": "Text nou introdus corect prezent in rezultat.",
        "_text_vechi_norm": "Text vechi original inca prezent din greseala aici.",
        "_fara_marcaj": False,
    }]

    with pytest.raises(ValueError, match="textul vechi mai există"):
        _verifica_final(rezultat, tinte)


def test_verifica_final_numar_de_marcaje_gresit_ridica_eroare():
    rezultat = "Text fara niciun marcaj de provenienta prezent aici.\n"
    tinte = [{"nr": 1, "tinta": "punct 1.1", "_text_nou_norm": "", "_text_vechi_norm": "", "_fara_marcaj": False}]

    with pytest.raises(ValueError, match="numărul de marcaje"):
        _verifica_final(rezultat, tinte)


# ---------------------------------------------------------------------------
# 4. Marcajul
# ---------------------------------------------------------------------------


def test_marcaj_are_formatul_exact(baza_simpla):
    item = ItemOrdin(
        nr=1,
        instructiune="La punctul 1.1. se modifică și va avea următorul cuprins:",
        text_nou="1.1. Domeniul de aplicare nou introdus complet diferit fata de vechi.\n",
    )
    manifest = _manifest([{"nr": 1, "tip": "inlocuieste_punct", "tinte": [{"punct": "1.1"}]}])

    rezultat, _ = aplica_operatii(baza_simpla, [item], manifest)

    marcaje = PATTERN_NUMARARE_MARCAJE.findall(rezultat)
    assert marcaje == [
        "[Text modificat prin Ordinul nr. 6.025/2018, publicat în Monitorul Oficial nr. 977 din 19.11.2018]"
    ]


def test_marcaj_niciodata_lipit_de_punctul_urmator(baza_simpla):
    """Regresie corectura 1 (planner): dacă textul nou nu se termină cu '\\n' și
    restul nu începe cu '\\n', punctul următor s-ar lipi de marcaj și ar dispărea
    ca articol distinct pentru chunker."""
    item = ItemOrdin(
        nr=1,
        instructiune="La punctul 1.2. se modifică și va avea următorul cuprins:",
        text_nou="1.2. Definitii noi introduse prin prezentul ordin fara linie noua la final",
    )
    manifest = _manifest([{"nr": 1, "tip": "inlocuieste_punct", "tinte": [{"punct": "1.2"}]}])

    rezultat, _ = aplica_operatii(baza_simpla, [item], manifest)

    assert "]\n1.3. Domeniul urmator" in rezultat
    assert "]1.3. Domeniul urmator" not in rezultat


def test_inlocuiri_globale_se_aplica_si_in_textul_nou(baza_simpla):
    """Regresie corectura 2 (planner): înlocuirea globală a ordinului (Art. II)
    trebuie aplicată și în textul nou adus de celelalte operații ale aceluiași
    ordin, nu doar în restul bazei — altfel verificarea finală ar compara greșit
    textul nebrut cu rezultatul deja înlocuit global și ar eșua fals."""
    item = ItemOrdin(
        nr=1,
        instructiune="La punctul 1.1. se modifică și va avea următorul cuprins:",
        text_nou=(
            "1.1. Domeniul de aplicare\n"
            "Sistemul de detectare, semnalizare și avertizare trebuie sa functioneze corect.\n"
        ),
    )
    manifest = _manifest(
        [{"nr": 1, "tip": "inlocuieste_punct", "tinte": [{"punct": "1.1"}]}],
        inlocuiri_globale=[{"veche": "detectare, semnalizare și avertizare", "noua": "detectare, semnalizare și alarmare"}],
    )

    rezultat, _ = aplica_operatii(baza_simpla, [item], manifest)

    assert "detectare, semnalizare și alarmare" in rezultat
    assert "detectare, semnalizare și avertizare" not in rezultat
