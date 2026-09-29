"""Teste sintetice pentru chunking_core.creeaza_chunkuri; texte mici, deterministe,
fără dependențe de documente_noi. Fiecare test reproduce o singură regulă din R14.
"""

import pytest

from chunking_core import (
    acoperire_text_brut,
    creeaza_chunkuri,
    ultimele_statistici,
    _propaga_marcaj_provenienta,
    _respecta_limita_cu_marcaje,
)


# --- 1a: antete MO ----------------------------------------------------------


def test_antet_mo_si_paginile_alaturate_sunt_eliminate():
    """Ar pica dacă antetul MO sau numărul de pagină alăturat ar rămâne în text,
    sau dacă statistica antete_eliminate nu ar reflecta antetul real eliminat."""
    text = (
        "\n1.1. Primul articol contine text detaliat inainte de antetul de pagina care urmeaza mai jos aici.\n"
        "MONITORUL OFICIAL AL ROMÂNIEI, PARTEA I, Nr. 100\n"
        "99\n"
        "1.2. Al doilea articol cu text suplimentar dupa eliminarea antetului de mai sus in mod corect.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["1.1.", "1.2."]
    text_complet = " ".join(c["text"] for c in rezultat)
    assert "MONITORUL OFICIAL" not in text_complet
    assert "99" not in text_complet
    assert ultimele_statistici()["antete_eliminate"] == 1


def test_numar_singur_fara_antet_in_apropiere_ramane_neatins():
    """Un rând doar-cifre fără antet MO în apropiere e o celulă de tabel și trebuie
    păstrat. Ar pica dacă implementarea ar elimina orice rând numeric scurt, indiferent
    de distanța față de un antet real."""
    text = (
        "\n1.1. Tabel cu valori conform prezentei sectiuni pentru control intern al documentatiei aici.\n"
        "Coloana A valoare\n"
        "42\n"
        "Coloana B valoare suplimentara pentru completarea tabelului curent prezentat mai sus.\n"
        "1.2. Al doilea articol contine antetul de pagina alaturat direct mai jos in acest exemplu.\n"
        "MONITORUL OFICIAL AL ROMÂNIEI, PARTEA I, Nr. 100\n"
        "77\n"
        "1.3. Al treilea articol cu text suficient de lung pentru a deveni chunk valid complet aici.\n"
    )

    rezultat = creeaza_chunkuri(text)

    text_articol_1_1 = next(c["text"] for c in rezultat if c["articol"] == "1.1.")
    assert "42" in text_articol_1_1
    text_complet = " ".join(c["text"] for c in rezultat)
    assert "77" not in text_complet


def test_referinta_la_monitorul_oficial_in_text_ramane():
    """O referință din corpul textului la Monitorul Oficial nu e un antet de pagină
    și trebuie păstrată. Ar pica dacă regex-ul de antet ar prinde și fraze narative."""
    text = (
        "\n1.1. Prezentul act a fost publicat in Monitorul Oficial al Romaniei, Partea I, nr. 34 "
        "din data mentionata in preambul si contine prevederi tehnice relevante pentru domeniu.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert len(rezultat) == 1
    assert "publicat in Monitorul Oficial al Romaniei, Partea I, nr. 34" in rezultat[0]["text"]
    assert ultimele_statistici()["antete_eliminate"] == 0


# --- Colofon MO de final -----------------------------------------------------


def test_colofonul_mo_de_final_este_eliminat():
    """Ar pica dacă blocul de colofon de la finalul fasciculului ar rămâne atașat
    ultimului articol."""
    text = (
        "\n1.1. Primul articol cu text detaliat inainte de colofonul final al documentului prezentat mai jos.\n"
        "Acest număr al Monitorului Oficial al României a fost tipărit în afara abonamentului.\n"
        "Alte informatii de tiraj care nu ar trebui sa mai apara in niciun chunk final generat aici.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert len(rezultat) == 1
    assert "Acest număr" not in rezultat[0]["text"]
    assert "Alte informatii de tiraj" not in rezultat[0]["text"]


# --- 1b: cuprins -------------------------------------------------------------


def test_cuprins_cu_puncte_de_conducere_ca_bloc_este_eliminat():
    """Un bloc real de ≥5 intrări de cuprins (puncte de conducere) trebuie sărit
    integral. Ar pica dacă intrările de cuprins ar rămâne ca articole/chunk-uri."""
    # Intrări scurte, dar destule ca bloc (≥5) — restul textului e amplu, ca blocul
    # de cuprins să rămână comod în primele 20% din documentul total.
    intrari_cuprins = "\n".join(
        f"{i}.1. T{i} .......... {i}" for i in range(1, 6)
    )
    corp_real = "9.1. " + (
        "Primul articol real din corpul documentului cu text detaliat suficient pentru "
        "validarea corecta a acestui exemplu sintetic de test automatizat extins clar bine. "
    ) * 4
    text = "\n" + intrari_cuprins + "\n" + corp_real.strip() + "\n"

    rezultat = creeaza_chunkuri(text)

    assert len(rezultat) == 1
    assert rezultat[0]["articol"] == "9.1."
    assert ".........." not in rezultat[0]["text"]
    assert "T1" not in rezultat[0]["text"]


def test_interval_numeric_izolat_cu_puncte_nu_taie_nimic():
    """Regresia I7: un interval numeric izolat cu puncte de conducere (ex. „150....500”)
    nu trebuie confundat cu finalul cuprinsului. Ar pica dacă textul dinaintea acestei
    linii ar fi aruncat."""
    text = (
        "\n1.1. Introducere reala a documentului cu text amplu descriind domeniul de aplicare "
        "al prezentei reglementari tehnice in detaliu suficient pentru validare corecta aici.\n"
        "Valori tipice cu timpi de declansare intre 150....500 utilizate in sistemele de protectie electrica.\n"
        "1.2. Al doilea articol contine informatii suplimentare tehnice relevante pentru domeniul studiat complet.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["1.1.", "1.2."]
    assert "150....500" in rezultat[0]["text"]


def test_cuprins_cu_numar_de_pagina_pe_randul_urmator_este_eliminat():
    """Stilul NP 010 (titlu pe un rând, pagina pe rândul următor), ca bloc de ≥5
    intrări, trebuie sărit. Ar pica dacă intrările ar rămâne ca articole separate."""
    # Intrări scurte (titlu + pagină pe rând separat), destule ca bloc (≥5) — restul
    # textului e amplu, ca blocul de cuprins să rămână comod în primele 20% din total.
    linii = []
    for i in range(1, 6):
        linii.append(f"{i}.1. T{i} titlu")
        linii.append(str(i + 2))
    corp_real = "9.1. " + (
        "Continut real dupa cuprins cu numerotare pagini separat pe randul urmator, "
        "detaliat suficient pentru validarea corecta a acestui exemplu de test automatizat. "
    ) * 4
    text = "\n" + "\n".join(linii) + "\n" + corp_real.strip() + "\n"

    rezultat = creeaza_chunkuri(text)

    assert len(rezultat) == 1
    assert rezultat[0]["articol"] == "9.1."


# --- 1c: titluri de capitol romane -------------------------------------------


def test_titlu_de_capitol_roman_nu_intra_in_textul_articolului_anterior():
    """Ar pica dacă titlul roman ar rămâne atașat la finalul articolului anterior,
    sau dacă ar dispărea și articolul următor."""
    text = (
        "\n1.1. Primul articol cu text detaliat inainte de titlul de capitol roman care urmeaza mai jos in document.\n"
        "II. POMPELE DE DISTRIBUTIE A CARBURANTILOR\n"
        "1.2. Al doilea articol cu text suplimentar dupa titlul de capitol eliminat corect din continutul precedent.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["1.1.", "1.2."]
    assert "POMPELE" not in rezultat[0]["text"]
    assert "II." not in rezultat[0]["text"]


# --- 1d: titluri de secțiune ca și context ------------------------------------


def test_titlu_de_sectiune_se_contopeste_ca_prim_rand_in_copiii_directi():
    """Ar pica dacă titlul ar rămâne chunk separat, sau dacă textul lui nu ar
    ajunge ca prefix pe copiii direcți."""
    text = (
        "\n4.4. Dimensionarea conductelor de aer\n"
        "4.4.1. Debitul de aer trebuie calculat conform metodologiei prezentate in capitolul anterior de referinta.\n"
        "4.4.2. Viteza aerului in conducte nu trebuie sa depaseasca valorile maxime admise prin prezenta norma.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["4.4.1.", "4.4.2."]
    for chunk in rezultat:
        assert chunk["text"].startswith("4.4. Dimensionarea conductelor de aer")
    assert ultimele_statistici()["titluri_contopite"] == 1


def test_titlu_fara_copii_ramane_chunk_normal():
    """Un segment care arată a titlu, dar nu are niciun copil în document, nu
    trebuie eliminat. Ar pica dacă ar dispărea conținutul acelui segment."""
    text = (
        "\n5.5. Titlu independent scurt\n"
        "6.1. Alt articol independent cu text suficient de lung pentru a forma un chunk valid complet si corect aici.\n"
    )

    rezultat = creeaza_chunkuri(text)

    articole = {c["articol"]: c["text"] for c in rezultat}
    assert "5.5." in articole
    assert articole["5.5."] == "Titlu independent scurt"


def test_titlu_fara_pagini_in_cuprins_este_eliminat_ca_duplicat():
    """O intrare de cuprins fără numere de pagină (titlu repetat, fără copil imediat),
    dar al cărei număr are copii reali în alt loc din document, trebuie eliminată —
    nu contopită, ca să nu introducă context greșit. Ar pica dacă ar rămâne chunk
    separat sau dacă titlul real (cu copil imediat) nu s-ar mai contopi."""
    text = (
        "\n2.3.2.1. Pereti antifoc rezistenta la foc\n"
        "2.3.2.2. Alta sectiune diferita neinrudita cu titlul anterior mentionat mai sus in cuprins simulat.\n"
        "2.3.2.1. Pereti antifoc rezistenta la foc\n"
        "2.3.2.1.1. Inchiderile perimetrale trebuie sa respecte urmatoarele conditii tehnice stabilite clar bine.\n"
    )

    rezultat = creeaza_chunkuri(text)

    articole = {c["articol"] for c in rezultat}
    assert "2.3.2.1." not in articole
    assert "2.3.2.1.1." in articole
    text_copil = next(c["text"] for c in rezultat if c["articol"] == "2.3.2.1.1.")
    assert text_copil.startswith("2.3.2.1. Pereti antifoc rezistenta la foc")
    stats = ultimele_statistici()
    assert stats["titluri_cuprins_eliminate"] == 1
    assert stats["titluri_contopite"] == 1


# --- Split secundar și introducere-titlu --------------------------------------


def _text_lung(propozitie, repetari):
    return (propozitie + " ") * repetari


def test_introducere_titlu_la_split_nu_devine_chunk_separat():
    """Ar pica dacă introducerea-titlu a unui articol lung, împărțit pe subpuncte,
    ar apărea ca propriul ei chunk, în loc să devină context pe fiecare subpunct.

    Folosește 3 subpuncte (nu 2), ca segmentul total să depășească pragul de 2000 de
    caractere de la care se aplică split-ul secundar, în timp ce fiecare subpunct
    individual (cu contextul titlului prepend-uit) rămâne sub limita de 1000, ca să nu
    fie el însuși tăiat de limita de caractere pe chunk."""
    subpunct = _text_lung(
        "Subpunct cu text detaliat privind domeniul de aplicare al prezentei "
        "reglementari tehnice extinse pentru completarea cerintelor necesare validarii.",
        5,
    )
    text = (
        f"\n1.1. Obiect si domeniu de aplicare\n"
        f"(1) {subpunct}\n(2) {subpunct}\n(3) {subpunct}\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["1.1.(1)", "1.1.(2)", "1.1.(3)"]
    assert all(len(c["text"]) <= 1000 for c in rezultat)
    assert all(c["text"].startswith("1.1. Obiect si domeniu de aplicare") for c in rezultat)
    assert ultimele_statistici()["titluri_contopite"] == 1


def test_split_secundar_nu_dubleaza_prefixul_titlului_deja_contopit():
    """Regresia „2.3.2.1.6. 2.3.2.1. Pereți antifoc…”: dacă introducerea unui subpunct
    e chiar titlul părintelui deja injectat de _contopeste_titluri, nu trebuie
    re-adăugat articolul curent în față. Ar pica dacă textul ar conține titlul dublat.

    3 subpuncte (nu 2), din același motiv de lungime ca la testul anterior: segmentul
    merge-uit (titlu părinte + subpuncte) trebuie să depășească 2000 de caractere, dar
    fiecare subpunct final (cu contextul prepend-uit) trebuie să rămână sub 1000."""
    subpunct = _text_lung(
        "Subpunct cu detalii tehnice privind calculul debitului de aer necesar pentru "
        "dimensionarea corecta a conductelor conform normativului actual in vigoare.",
        5,
    )
    text = (
        "\n4.4. Dimensionarea conductelor de aer\n"
        f"4.4.1.\n(1) {subpunct}\n(2) {subpunct}\n(3) {subpunct}\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["4.4.1.(1)", "4.4.1.(2)", "4.4.1.(3)"]
    assert all(len(c["text"]) <= 1000 for c in rezultat)
    for chunk in rezultat:
        assert chunk["text"].count("Dimensionarea conductelor de aer") == 1
        assert "4.4.1. 4.4." not in chunk["text"]
        assert chunk["text"].startswith("4.4. Dimensionarea conductelor de aer\n")


# --- Marcajul „Art.” (P 118/1) -----------------------------------------------


def test_marcaj_art_cu_trei_componente_este_recunoscut():
    """Ar pica dacă marcajul „Art. N.N.N.” urmat de majusculă nu ar deveni articol
    propriu."""
    text = (
        "\nArt. 2.3.6.1. La constructiile prevazute in prezenta reglementare trebuie respectate normele tehnice.\n"
        "Art. 2.3.6.2. Peretii antifoc trebuie sa indeplineasca urmatoarele conditii tehnice speciale aici.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["2.3.6.1.", "2.3.6.2."]
    assert "La constructiile" in rezultat[0]["text"]


def test_marcaj_art_urmat_de_litera_mica_sau_punctuatie_ramane_trimitere():
    """Un „Art. N.N.” urmat de literă mică sau de punctuație nu e un articol nou —
    rămâne text al articolului curent. Ar pica dacă ar apărea ca articol separat sau
    dacă textul respectiv s-ar pierde."""
    text = (
        "\n1.1. Primul articol cu suficient text initial pentru a fi valid chunk aici clar bine sigur.\n"
        "Art. 2.4.5.4.. text ce ramane atasat articolului anterior deoarece punctuatia invalideaza marcajul.\n"
        "Art. 2.4.5.4. mai jos se gasesc prevederi suplimentare care raman tot atasate primului articol.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["1.1."]
    assert "Art. 2.4.5.4.. text ce ramane atasat" in rezultat[0]["text"]
    assert "Art. 2.4.5.4. mai jos se gasesc" in rezultat[0]["text"]


# --- Trimiteri rupte (numar simplu) ------------------------------------------


def test_numar_urmat_de_litera_mica_e_trimitere_articolul_real_nu_se_pierde():
    """Regresia P 118/1 „2.3.2.1.2. lit. a)”: o repetiție a numărului de articol
    urmată de literă mică e o trimitere ruptă, nu un articol nou — nu trebuie să
    provoace pierderea articolului real prin dedup. Ar pica dacă ar apărea un al
    doilea chunk „2.3.2.1.2.” sau dacă textul real ar dispărea."""
    text = (
        "\n2.3.2.1.2. Peretii antifoc trebuie sa indeplineasca conditii speciale definite mai jos exact aici.\n"
        "a) minimum valoarea structurii de rezistenta la foc conform tabelului anexat prezentei reglementari.\n"
        "Alte prevederi generale mentionate in continuare pentru edificare completa a cerintelor tehnice reale.\n"
        "2.3.2.1.2. lit. a); trimitere gresita care nu trebuie sa devina articol nou separat aici in mod clar.\n"
        "Text suplimentar dupa trimitere care ramane atasat articolului real de mai sus in mod corect pastrat.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["2.3.2.1.2."]
    assert "Peretii antifoc trebuie sa indeplineasca" in rezultat[0]["text"]
    assert "lit. a); trimitere gresita" in rezultat[0]["text"]


def test_rand_anterior_terminat_in_conform_face_marcajul_urmator_trimitere():
    """Regresia P 118/1 3.2.11.20: dacă rândul anterior nevid se termină cu „conform”,
    marcajul numeric de pe rândul următor e o trimitere ruptă, nu un articol nou. Ar
    pica dacă „2.1.3.5.” ar apărea ca articol separat, aruncând restul textului real."""
    text = (
        "\n3.2.11.20. Prevederile privind parcajele subterane sunt urmatoarele in continuare detaliate mai jos.\n"
        "a) accesul autovehiculelor se face conform\n"
        "2.1.3.5. (1) alin. a); parcajele trebuie sa respecte normele tehnice stabilite prin prezentul act legal.\n"
        "b) alte cerinte tehnice suplimentare mentionate in continuare pentru edificarea completa a normei tehnice.\n"
        "c) cerinte finale suplimentare necesare pentru conformitate totala cu prezenta reglementare tehnica aici.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["3.2.11.20."]
    assert "2.1.3.5. (1) alin. a); parcajele trebuie" in rezultat[0]["text"]
    assert "c) cerinte finale suplimentare" in rezultat[0]["text"]


# --- D18: virgula la final de rand -------------------------------------------


def test_d18_virgula_la_final_de_rand_e_articol_valid_fara_virgula():
    """Ar pica dacă „1.1.,” urmat de sfârșit de rând ar fi respins ca trimitere
    ruptă (regresia D18)."""
    text = "\n1.1.,\nText articol valid cu virgula eliminata la final de rand pentru conformitate cu decizia D18 aprobata.\n"

    rezultat = creeaza_chunkuri(text)

    assert len(rezultat) == 1
    assert rezultat[0]["articol"] == "1.1."
    assert "Text articol valid cu virgula eliminata" in rezultat[0]["text"]


def test_d18_virgula_urmata_de_text_pe_acelasi_rand_nu_e_articol():
    """Ar pica dacă „1.1.,text” (virgulă urmată direct de conținut, nu de sfârșit de
    rând) ar deveni totuși articol propriu."""
    text = (
        "\n2.1. Introducere initiala cu suficient text pentru a forma un chunk valid corect aici sigur bine.\n"
        "1.1.,text imediat dupa virgula ceea ce face ca marcajul sa ramana trimitere nu articol nou aici clar.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["2.1."]
    assert "1.1.,text imediat dupa virgula" in rezultat[0]["text"]


# --- Numere fara punct final (I7) --------------------------------------------


def test_numar_fara_punct_final_urmat_de_majuscula_e_articol():
    """Ar pica dacă „3.1.5.7 Amplasarea…” (fără punct după ultima componentă) nu ar
    fi recunoscut ca articol nou."""
    text = "\n3.1.5.7 Amplasarea contoarelor trebuie sa respecte normele tehnice stabilite in prezentul capitol clar.\n"

    rezultat = creeaza_chunkuri(text)

    assert len(rezultat) == 1
    assert rezultat[0]["articol"] == "3.1.5.7."
    assert "Amplasarea contoarelor" in rezultat[0]["text"]


def test_zecimal_cu_litera_mica_dupa_nu_e_articol():
    """Ar pica dacă o valoare zecimală de tip „0.4 kV” ar fi confundată cu un
    articol fără punct final."""
    text = (
        "\n2.1. Sectiune introductiva cu suficient continut pentru a fi validata drept chunk complet corect aici.\n"
        "Valoarea tensiunii nominale utilizate in instalatie este de\n"
        "0.4 kV pentru retelele electrice interne curente ale cladirii analizate in acest exemplu.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["2.1."]
    assert "0.4 kV pentru retelele" in rezultat[0]["text"]


# --- Date tratate ca articole -------------------------------------------------


def test_data_zi_luna_an_nu_e_articol():
    """Ar pica dacă o dată de forma „15.01.2024” ar fi tratată ca articol nou."""
    text = (
        "\n2.1. Preambul cu text initial suficient de lung pentru a forma chunk valid corect si complet aici bine.\n"
        "Emis la data de\n"
        "15.01.2024 in conformitate cu prevederile legale in vigoare la momentul aprobarii prezentei norme.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["2.1."]
    assert "15.01.2024 in conformitate" in rezultat[0]["text"]


# --- Limita de 1000 caractere si statistici -----------------------------------


def test_limita_de_1000_caractere_pe_chunk():
    """Ar pica dacă un chunk unic ar depăși 1000 de caractere, sau dacă split-ul ar
    pierde conținut."""
    propozitie = (
        "Text foarte lung repetat de multe ori pentru a depasi limita de o mie de caractere impusa "
        "fiecarui chunk individual conform regulilor stabilite anterior in acest document tehnic de "
        "test sintetic automatizat pentru validarea corecta a comportamentului implementat aici. "
    )
    text = "\n1.1. " + propozitie * 6 + "\n"

    rezultat = creeaza_chunkuri(text)

    assert len(rezultat) >= 2
    assert all(chunk["articol"] == "1.1." for chunk in rezultat)
    assert all(len(chunk["text"]) <= 1000 for chunk in rezultat)
    assert rezultat[0]["text"].startswith("Text foarte lung repetat")


# --- D27: marcajul de proveniență nu se taie la limita de 1000 caractere ------


def test_marcaj_de_provenienta_nu_este_taiat_la_limita_de_1000_caractere():
    """D27 (consolidare_normative.py): dacă tăietura la 1000 de caractere ar cădea
    în interiorul marcajului de proveniență, acesta ar apărea trunchiat într-o
    bucată și cu resturi în cealaltă. Ar pica dacă marcajul nu ar rămâne întreg
    într-o singură bucată."""
    marcaj = "[Text modificat prin Ordinul nr. 6.025/2018, publicat în Monitorul Oficial nr. 977 din 19.11.2018]"
    text = "\n1.1. " + "A" * 940 + marcaj + "B" * 100 + "\n"

    rezultat = creeaza_chunkuri(text)

    assert all(chunk["articol"] == "1.1." for chunk in rezultat)
    chunkuri_cu_marcaj_intreg = [c for c in rezultat if marcaj in c["text"]]
    assert len(chunkuri_cu_marcaj_intreg) == 1
    chunkuri_cu_marcaj_trunchiat = [
        c for c in rezultat if "[Text modificat prin Ordinul" in c["text"] and marcaj not in c["text"]
    ]
    assert chunkuri_cu_marcaj_trunchiat == []
    assert "B" * 100 in "".join(c["text"] for c in rezultat)


def test_text_fara_marcaj_de_provenienta_se_taie_la_limita_ca_inainte():
    """Regresie: fără niciun marcaj de proveniență, tăietura la limita de 1000 de
    caractere trebuie să rămână neschimbată (la ultimul spațiu găsit, neextinsă
    artificial ca în testul de mai sus)."""
    text = "\n1.1. " + "A" * 940 + " " + "C" * 200 + "\n"

    rezultat = creeaza_chunkuri(text)

    assert len(rezultat) == 2
    assert all(len(chunk["text"]) <= 1000 for chunk in rezultat)
    assert rezultat[0]["text"] == "A" * 940
    assert rezultat[1]["text"] == "C" * 200


def test_ultimele_statistici_numara_corect_pe_exemplu_mic():
    """Ar pica dacă oricare dintre cele patru statistici nu ar reflecta exact
    operațiile aplicate pe acest exemplu mic și controlat."""
    text = (
        "\nMONITORUL OFICIAL AL ROMÂNIEI, PARTEA I, Nr. 50\n"
        "1.1. Titlu de sectiune scurt\n"
        "1.1.1. Primul copil cu text suficient de lung pentru a fi un chunk valid complet si corect stabilit aici bine.\n"
        "2.1. Primul text al doilea articol independent scurt insuficient\n"
        "2.1. Al doilea text pentru acelasi articol independent, mai lung, care ar trebui sa castige la deduplicare pentru acest test.\n"
    )

    rezultat = creeaza_chunkuri(text)
    stats = ultimele_statistici()

    assert stats == {
        "antete_eliminate": 1,
        "titluri_contopite": 1,
        "duplicate_eliminate": 1,
        "titluri_cuprins_eliminate": 0,
    }
    articole = {c["articol"] for c in rezultat}
    assert articole == {"1.1.1.", "2.1."}
    assert len([c for c in rezultat if c["articol"] == "2.1."]) == 1


# --- D27 Runda 2: _propaga_marcaj_provenienta (goluri semnalate de reviewer) --
#
# Testate direct pe funcțiile private (nu prin creeaza_chunkuri): scenariul din
# spec — un punct despărțit pe alineate de _aplica_split_secundar — cere un
# chunk de bază de minimum 2000 caractere ca să declanșeze split-ul secundar;
# construirea acelui text ar face testele fragile și greu de citit fără să
# aducă vreo garanție suplimentară față de a apela direct funcția care conține
# logica cerută (aceleași chei de articol "3.3.1.(1)"/"(2)"/"(4)" pe care le-ar
# produce _aplica_split_secundar).

MARCAJ_MODIFICAT_1 = "[Text modificat prin Ordinul nr. 6.025/2018, publicat în Monitorul Oficial nr. 977 din 19.11.2018]"
MARCAJ_ABROGAT_1 = "[Abrogat prin Ordinul nr. 6.026/2018, publicat în Monitorul Oficial nr. 966 din 15.11.2018]"


def test_propaga_marcaj_pe_punct_despartit_in_mai_multe_alineate():
    """Scenariul din spec (P 118/3, 3.3.1): un punct împărțit pe alineate în mai
    multe bucăți, unde doar una conține marcajul original. Ar pica dacă
    propagarea nu ar grupa corect după articolul de bază, sau dacă bucata cu
    marcajul original ar primi și ea dublura la nivel de articol."""
    chunkuri = [
        {"articol": "3.3.1.(1)", "text": "Primul alineat fara niciun marcaj propriu."},
        {"articol": "3.3.1.(2)", "text": f"Al doilea alineat, chiar cel modificat.\n{MARCAJ_MODIFICAT_1}"},
        {"articol": "3.3.1.(4)", "text": "Al patrulea alineat, tot fara marcaj propriu."},
    ]

    rezultat = _propaga_marcaj_provenienta(chunkuri)

    marcaj_articol = "[Articol cu text modificat prin Ordinul nr. 6.025/2018, publicat în Monitorul Oficial nr. 977 din 19.11.2018]"
    text_1 = next(c["text"] for c in rezultat if c["articol"] == "3.3.1.(1)")
    text_2 = next(c["text"] for c in rezultat if c["articol"] == "3.3.1.(2)")
    text_4 = next(c["text"] for c in rezultat if c["articol"] == "3.3.1.(4)")

    assert text_1 == f"Primul alineat fara niciun marcaj propriu.\n{marcaj_articol}"
    assert text_4 == f"Al patrulea alineat, tot fara marcaj propriu.\n{marcaj_articol}"
    # Bucata cu marcajul original nu primește dublura la nivel de articol.
    assert text_2 == f"Al doilea alineat, chiar cel modificat.\n{MARCAJ_MODIFICAT_1}"
    assert text_2.count("[") == 1


def test_propaga_marcaj_articol_fara_niciun_marcaj_ramane_byte_identic():
    """Regresie explicit cerută: un articol ale cărui bucăți nu conțin niciun
    marcaj de proveniență trebuie să rămână complet neatins. Ar pica dacă
    propagarea ar adăuga vreun rând suplimentar în absența oricărui marcaj."""
    chunkuri = [
        {"articol": "4.1.(1)", "text": "Primul alineat, complet normal, fara nicio modificare."},
        {"articol": "4.1.(2)", "text": "Al doilea alineat, la fel de normal, fara nicio modificare."},
    ]

    rezultat = _propaga_marcaj_provenienta(chunkuri)

    assert rezultat == chunkuri


def test_propaga_doua_marcaje_diferite_deduplicat_in_ordinea_primei_aparitii():
    """Mai multe ordine/tipuri de marcaj pe același articol: fiecare altă bucată
    primește câte un rând per marcaj distinct, în ordinea primei apariții în
    listă (nu ordinea alfabetică), fără duplicate. Ar pica dacă deduplicarea nu
    ar respecta ordinea primei apariții sau ar produce rânduri duplicate."""
    chunkuri = [
        {"articol": "5.1.(1)", "text": f"Primul alineat.\n{MARCAJ_ABROGAT_1}"},
        {"articol": "5.1.(2)", "text": f"Al doilea alineat.\n{MARCAJ_MODIFICAT_1}"},
        {"articol": "5.1.(3)", "text": "Al treilea alineat, fara marcaj propriu."},
    ]

    rezultat = _propaga_marcaj_provenienta(chunkuri)

    marcaj_articol_abrogat = "[Articol cu text abrogat prin Ordinul nr. 6.026/2018, publicat în Monitorul Oficial nr. 966 din 15.11.2018]"
    marcaj_articol_modificat = "[Articol cu text modificat prin Ordinul nr. 6.025/2018, publicat în Monitorul Oficial nr. 977 din 19.11.2018]"

    text_1 = next(c["text"] for c in rezultat if c["articol"] == "5.1.(1)")
    text_2 = next(c["text"] for c in rezultat if c["articol"] == "5.1.(2)")
    text_3 = next(c["text"] for c in rezultat if c["articol"] == "5.1.(3)")

    # Bucata (1) are deja marcajul abrogat original, primește doar dublura modificat.
    assert text_1 == f"Primul alineat.\n{MARCAJ_ABROGAT_1}\n{marcaj_articol_modificat}"
    # Bucata (2) are deja marcajul modificat original, primește doar dublura abrogat.
    assert text_2 == f"Al doilea alineat.\n{MARCAJ_MODIFICAT_1}\n{marcaj_articol_abrogat}"
    # Bucata (3), fara niciun marcaj propriu, primește ambele, in ordinea primei
    # aparitii in lista (abrogat inaintea lui modificat).
    assert text_3 == (
        "Al treilea alineat, fara marcaj propriu.\n"
        f"{marcaj_articol_abrogat}\n{marcaj_articol_modificat}"
    )


def test_respecta_limita_cu_marcaje_reimparte_bucata_care_depaseste_1000():
    """O bucată de ~990 de caractere care primește un marcaj propagat depășește
    1000 de caractere; trebuie re-împărțită astfel încât fiecare parte, cu
    marcajul ei, să rămână ≤1000, fără să se piardă niciun cuvânt. Ar pica dacă
    rezultatul ar depăși limita sau ar pierde conținut la re-împărțire."""
    text_lung = ("Cuvant " * 141) + "Ultim."
    assert len(text_lung) <= 1000  # ~990 caractere, sub limita, inainte de marcaj
    chunkuri = [
        {"articol": "6.1.(1)", "text": text_lung},
        {"articol": "6.1.(2)", "text": f"Alineat scurt cu marcajul original.\n{MARCAJ_MODIFICAT_1}"},
    ]

    rezultat = _propaga_marcaj_provenienta(chunkuri)

    marcaj_articol = "[Articol cu text modificat prin Ordinul nr. 6.025/2018, publicat în Monitorul Oficial nr. 977 din 19.11.2018]"
    bucati_articolului_1 = [c for c in rezultat if c["articol"] == "6.1.(1)"]

    assert len(bucati_articolului_1) >= 2
    assert all(len(c["text"]) <= 1000 for c in bucati_articolului_1)
    assert all(marcaj_articol in c["text"] for c in bucati_articolului_1)
    # Niciun cuvant din textul original nu s-a pierdut la re-impartire.
    text_recompus = " ".join(
        c["text"].replace("\n" + marcaj_articol, "") for c in bucati_articolului_1
    )
    for cuvant in text_lung.split():
        assert cuvant in text_recompus


# --- Runda 2: numar lipit de majuscula (I7/NP 057) -----------------------------


def test_numar_lipit_de_majuscula_nu_se_lipeste_de_articol():
    """Ar pica dacă „3.0.1.Condiții…” (extras de PDF fără spațiu între marcaj și
    cuvânt) ar produce articolul invalid „3.0.1.Condiții” în loc să separe numărul
    curat de cuvântul lipit, care trebuie să rămână începutul textului (bug real
    găsit de planner pe I7/NP 057, runda 2)."""
    text = (
        "\n3.0.1.Condiții generale suficient de lungi pentru a forma un chunk valid conform regulilor stabilite clar.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert len(rezultat) == 1
    assert rezultat[0]["articol"] == "3.0.1."
    assert rezultat[0]["text"].startswith("Condiții")


# --- R16: dedup pe identificatorul normalizat ---------------------------------


def test_dedup_pe_forma_normalizata_variante_care_difera_doar_prin_majuscula():
    """Regresia R16 (I5): două variante ale aceluiași articol care diferă doar prin
    litera din paranteză (majusculă/minusculă) trebuie deduplicate ca o singură
    cheie normalizată — dedup-ul pe identificatorul brut (case-sensitiv) le-ar fi
    tratat ca articole diferite. Ar pica dacă dedup-ul ar reveni la cheia brută."""
    text = (
        "\n3.2.(B). Titlu scurt neinformativ.\n"
        "3.2.(b). Textul real, mult mai detaliat, cu prevederi tehnice suplimentare complete pentru acest articol.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert len(rezultat) == 1
    assert "Textul real, mult mai detaliat" in rezultat[0]["text"]
    assert ultimele_statistici()["duplicate_eliminate"] == 1


def test_dedup_forme_diferite_dar_neechivalente_normalizat_raman_separate():
    """Control negativ: litere diferite în paranteză (nu doar caz diferit) rămân
    chei diferite. Ar pica dacă normalizarea le-ar confunda greșit."""
    text = (
        "\n3.2.(b). Primul articol cu litera b, text suficient de lung pentru a fi un chunk valid complet aici.\n"
        "3.2.(c). Al doilea articol cu litera c, text suficient de lung pentru a fi un chunk valid complet aici.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert {c["articol"] for c in rezultat} == {"3.2.(b).", "3.2.(c)."}


def test_dedup_exemplul_din_handoff_varianta_fara_punct_si_cu_punct():
    """Exemplul literal din handoff R16: „6.1.1 Titlu…” și „6.1.1. Text real…” trebuie
    să rămână un singur articol, cu varianta mai lungă câștigând. Ar pica dacă
    vreuna dintre variante ar rămâne chunk separat sau dacă textul scurt ar câștiga."""
    text = (
        "\n6.1.1 Titlu scurt neinformativ aici.\n"
        "6.1.1. Text real mult mai lung, cu detalii tehnice suplimentare importante pentru acest articol complet aici.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert len(rezultat) == 1
    assert "Text real mult mai lung" in rezultat[0]["text"]


# --- R16: titlu de capitol cu un singur nivel de numerotare --------------------


def test_titlu_capitol_simplu_cu_copil_direct_devine_context_iar_introducerea_nu_se_lipeste():
    """Regresia I5: „4. Elemente generale de calcul” urmat de introducere „(1)…” și
    apoi „4.1. …” — introducerea nu trebuie să se lipească de articolul anterior
    (3.2.5.2.), titlul devine context pentru 4.1., iar introducerea rămâne chunk
    propriu cu articolul „4.”. Ar pica dacă „4.” nu ar fi recunoscut ca marcaj, dacă
    introducerea s-ar lipi de 3.2.5.2., sau dacă titlul nu s-ar propaga la 4.1."""
    text = (
        "\n3.2.5.2. Ultimul subpunct al capitolului anterior cu text suficient de lung pentru a fi valid complet clar.\n"
        "4. Elemente generale de calcul\n"
        "(1) Introducerea capitolului patru cu text detaliat suficient pentru a forma un chunk valid complet corect.\n"
        "4.1. Parametrii interiori trebuie stabiliti conform normelor tehnice in vigoare pentru acest tip de cladire.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["3.2.5.2.", "4.", "4.1."]

    chunk_325 = next(c for c in rezultat if c["articol"] == "3.2.5.2.")
    assert "Elemente generale de calcul" not in chunk_325["text"]
    assert "Introducerea capitolului patru" not in chunk_325["text"]

    chunk_4 = next(c for c in rezultat if c["articol"] == "4.")
    assert chunk_4["text"].startswith("(1) Introducerea capitolului patru")

    chunk_41 = next(c for c in rezultat if c["articol"] == "4.1.")
    assert chunk_41["text"].startswith("4. Elemente generale de calcul")
    assert "Parametrii interiori" in chunk_41["text"]


def test_enumerare_simpla_fara_copil_1_1_nu_e_tratata_ca_titlu_de_capitol():
    """O enumerare „1. text… 2. text…” din corpul unui articol, fără un copil de
    tip „1.1.”, nu trebuie tratată ca titlu de capitol cu un singur nivel. Ar pica
    dacă implementarea ar recunoaște orice „N. Majusculă…” ca titlu, indiferent
    dacă are sau nu un copil direct imediat următor."""
    text = (
        "\n2.1. Introducere articol cu text suficient de lung pentru a forma un chunk valid complet corect aici bine.\n"
        "1. Primul element enumerat in corpul articolului fara copil de tip subpunct sau alt nivel afisat\n"
        "2. Al doilea element enumerat continuand lista fara sa formeze un titlu nou de capitol distinct\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["2.1."]
    assert "1. Primul element enumerat" in rezultat[0]["text"]
    assert "2. Al doilea element enumerat" in rezultat[0]["text"]


# --- R16 (task 3b): subpuncte care reîncep nu se mai împart -------------------


def test_subpuncte_care_reincep_nu_se_imparte_pe_subpuncte():
    """Regresia NP 010/P 118/1/NP 015/I7: dacă numerotarea „(1)(2)…” reîncepe în
    același articol (sub-secțiuni nenumerotate), articolul nu se mai împarte pe
    subpuncte — rămâne o unitate, tăiată doar de limita de 1000 caractere. Ar pica
    dacă split-ul secundar ar continua să taie pe „(1)”/„(2)” chiar și cu reluare."""
    subpunct = _text_lung(
        "Text de subpunct detaliat pentru testarea renumerotarii care se repeta in acelasi articol lung de test.",
        6,
    )
    text = (
        "\n5.1. Sectiune cu subpuncte care se renumeroteaza\n"
        f"(1) {subpunct}\n(2) {subpunct}\n(1) {subpunct}\n(2) {subpunct}\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert len(rezultat) >= 2
    assert all(c["articol"] == "5.1." for c in rezultat)
    assert all(len(c["text"]) <= 1000 for c in rezultat)


def test_subpuncte_strict_crescatoare_neconsecutive_se_impart_normal():
    """Control pozitiv: o numerotare strict crescătoare, chiar dacă nu e consecutivă
    (1, 2, 4, 7), tot se împarte pe subpuncte ca înainte — regula respinge doar
    reluarea/repetarea, nu salturile. Ar pica dacă implementarea ar cere pași de
    exact +1 între subpuncte, sau dacă nu ar mai împărți deloc."""
    subpunct = _text_lung(
        "Text de subpunct detaliat privind cerintele tehnice aplicabile acestei sectiuni a normativului curent.",
        6,
    )
    text = (
        "\n6.1. Titlu sectiune diverse cerinte tehnice\n"
        f"(1) {subpunct}\n(2) {subpunct}\n(4) {subpunct}\n(7) {subpunct}\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["6.1.(1)", "6.1.(2)", "6.1.(4)", "6.1.(7)"]
    assert all(len(c["text"]) <= 1000 for c in rezultat)


# --- R16 Runda 2: cifră lipită după marcaj nu e articol -------------------------


def test_cifra_lipita_dupa_marcaj_precedat_de_punctele_nu_e_articol():
    """Regresia NP 010: „…de la punctele\\n4.2.4.5 și 4.2.4.6” nu trebuie să producă
    un articol fals „4.2.4.5”, care ar fura, prin dedup normalizat, articolul real
    „4.2.4.5.”. Ar pica dacă un al doilea chunk „4.2.4.5.” ar apărea, sau dacă
    textul real ar fi înlocuit de „Tabelul 4.21…”."""
    text = (
        "\n4.2.4.5. Prevederi specifice de siguranta pentru zonele de recreatie la exterior trebuie respectate clar.\n"
        "Detalii suplimentare importante pentru aceasta sectiune tehnica continua mai jos in text detaliat complet.\n"
        "Masuri generale cu respectarea prevederilor de la punctele\n"
        "4.2.4.5 si 4.2.4.6 Tabelul 4.21 prezinta valorile de referinta pentru acest tip de instalatie tehnica.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["4.2.4.5."]
    assert "Prevederi specifice de siguranta" in rezultat[0]["text"]
    assert "Tabelul 4.21 prezinta valorile" in rezultat[0]["text"]


def test_cifra_lipita_dupa_marcaj_fara_cuvant_de_trimitere_tot_nu_e_articol():
    """Izolează regula generică (cifră lipită la distanță zero de marcaj), fără
    niciun cuvânt din lista de trimitere rupta pe rândul anterior — regăsit de coder
    pe NP 010 rândul 2817 („…la\\n4.2.2, (30)…”). Ar pica dacă doar lista de cuvinte
    ar respinge trimiterile rupte, fără regula generică pe cifra lipită."""
    text = (
        "\n4.2.4.5. Prevederi specifice de siguranta pentru zonele de joaca a copiilor trebuie respectate cu strictete.\n"
        "Alte detalii tehnice suplimentare relevante pentru aceasta sectiune continua in acest exemplu mai jos aici.\n"
        "Valorile stabilite sunt\n"
        "4.2.4.5 si 4.2.4.6 reprezinta limitele minime acceptate conform tabelului de referinta anexat prezentei norme.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["4.2.4.5."]
    assert "reprezinta limitele minime acceptate" in rezultat[0]["text"]


# --- R16 Runda 2: cuvinte noi de final de rând ----------------------------------


@pytest.mark.parametrize(
    "cuvant",
    ["punctele", "punctul", "punctelor", "articolele", "articolelor", "prevederile", "prevederilor"],
)
def test_cuvinte_noi_de_trimitere_rupta_fac_marcajul_urmator_trimitere(cuvant):
    """Fiecare cuvânt nou adăugat la lista de final de rând (Runda 2) trebuie să facă
    marcajul de pe rândul următor o trimitere ruptă, chiar dacă acel marcaj ar fi
    altfel valid (spațiu + majusculă după număr). Ar pica dacă vreunul dintre
    cuvinte ar lipsi din listă în implementare."""
    text = (
        f"\n2.1. Introducere initiala cu suficient text pentru a forma un chunk valid corect aici sigur bine clar.\n"
        f"Se aplica conform {cuvant}\n"
        "5.5. Text ce nu trebuie sa devina articol nou din cauza cuvantului anterior de trimitere rupta.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["2.1."]
    assert f"conform {cuvant}" in rezultat[0]["text"]
    assert "5.5. Text ce nu trebuie" in rezultat[0]["text"]


def test_numar_lipit_de_caracter_ne_majuscul_ramane_referinta_rupta():
    """Fix-ul de la runda 2 se aplică numai când primul caracter lipit e o
    majusculă. Ar pica dacă „1.1./…” (bară, nu majusculă) ar deveni totuși un
    articol propriu, în loc să rămână parte din textul articolului anterior —
    la fel cum rămâne și „1.1.,text” (deja acoperit de testele D18 de mai sus)."""
    text = (
        "\n2.1. Introducere initiala cu suficient text pentru a forma un chunk valid corect aici sigur bine.\n"
        "1.1./ceva trimitere rupta care nu trebuie sa devina articol propriu conform regulii clar aici.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["2.1."]
    assert "1.1./ceva trimitere rupta" in rezultat[0]["text"]


# --- R21: prag de marcaje „Art.” dezactivează numărul fără punct final ----------


def test_numar_fara_punct_final_nu_incepe_articol_in_document_cu_multe_art():
    """Regresia P 118/1: într-un document cu ≥50 marcaje „Art.” recunoscute, numerele
    fără punct final din text („48.6 Substrat…”, „27.3 Mj/kg…”) nu trebuie să mai
    deschidă articole proprii — trebuie să rămână text atașat articolului „Art.”
    curent. Ar pica dacă PATTERN_ARTICOL_FARA_PUNCT ar rămâne activ peste prag: ar
    apărea chunk-uri „48.6.”/„27.3.” separate, iar numărul total de chunk-uri ar
    depăși 50."""
    parti = []
    for i in range(1, 51):
        bloc = (
            f"\nArt. {i}.1. Continut articol numarul {i} cu text suficient pentru a fi "
            "valid complet aici clar bine sigur si corect stabilit.\n"
        )
        if i == 1:
            bloc += (
                "48.6 Substrat - material component al structurii, prevazut sa reziste "
                "la actiuni conform proiectului tehnic aprobat pentru aceasta lucrare.\n"
                "27.3 Mj/kg, in orice fel de conditii ramane parte a textului articolului "
                "curent fara sa il desparta in vreun fel de continutul principal real.\n"
            )
        parti.append(bloc)
    text = "".join(parti)

    rezultat = creeaza_chunkuri(text)

    assert len(rezultat) == 50
    assert not any(c["articol"] in ("48.6.", "27.3.") for c in rezultat)
    chunk_1_1 = next(c for c in rezultat if c["articol"] == "1.1.")
    assert "48.6 Substrat" in chunk_1_1["text"]
    assert "27.3 Mj/kg" in chunk_1_1["text"]


def test_cuprins_de_titluri_anexa_inaintea_primului_art_este_ignorat():
    """Regresia rundelor 2-3 (R21): într-un document cu ≥50 marcaje „Art.”, un bloc de
    titluri „ANEXA …” aflat înaintea primului articol „Art.” real (cuprinsul anexelor)
    nu trebuie să producă niciun chunk și nu trebuie să deschidă o regiune de anexă
    care să înghită tot corpul. Ar pica dacă vreun chunk „ANEXA …” ar apărea, sau dacă
    numărul total de chunk-uri „Art.” ar scădea sub 50 (regiune de anexă înghițind
    corpul, ca în runda 2)."""
    cuprins = "\nANEXA 1 - TITLU UNU\nANEXA 2 - TITLU DOI\nANEXA 3 - TITLU TREI\n"
    corp = "".join(
        f"\nArt. {i}.1. Continut articol numarul {i} cu text suficient pentru a fi "
        "valid complet aici clar bine sigur si corect stabilit pentru acest test.\n"
        for i in range(1, 51)
    )
    text = cuprins + corp

    rezultat = creeaza_chunkuri(text)

    assert len(rezultat) == 50
    assert not any(c["articol"].startswith("ANEXA") for c in rezultat)


# --- R21: regiuni de anexă ------------------------------------------------------


def test_titlu_de_anexa_urmat_de_continut_devine_chunk_propriu():
    """Ar pica dacă titlul „ANEXA 2.1 - TITLU” nu ar deschide o regiune de anexă, sau
    dacă textul care îl urmează nu ar deveni chunk-ul „ANEXA 2.1.”."""
    text = (
        "\nANEXA 2.1 - TITLU ANEXA\n"
        "Text continut anexa cu detalii tehnice suficiente pentru a forma un chunk "
        "complet valid pentru acest exemplu sintetic de test automatizat aici bine.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert len(rezultat) == 1
    assert rezultat[0]["articol"] == "ANEXA 2.1."
    assert "Text continut anexa" in rezultat[0]["text"]


def test_marcaj_intern_de_anexa_devine_copil_si_nu_coincide_cu_articol_din_corp():
    """Regresia P 118/1 (Anexa 10): marcajul intern „A.10. 2.7.7. Text…” trebuie să
    devină un copil al anexei curente („ANEXA 10.2.7.7.”), distinct de un articol
    real din corp cu același număr („2.7.7.”, în afara oricărei anexe). Ar pica dacă
    marcajul intern nu ar primi prefixul anexei, sau dacă cele două identificatoare
    (corp vs. copil de anexă) ar coincide și s-ar contopi prin dedup."""
    text = (
        "\n2.7.7. Articol real din corpul documentului cu text detaliat suficient "
        "pentru validare corecta a acestui exemplu de test automatizat scris aici.\n"
        "ANEXA 10\n"
        "A.10. 2.7.7. Pentru interventia la cladiri existente trebuie respectate "
        "urmatoarele conditii tehnice speciale stabilite prin prezenta reglementare.\n"
    )

    rezultat = creeaza_chunkuri(text)

    articole = {c["articol"]: c["text"] for c in rezultat}
    assert set(articole) == {"2.7.7.", "ANEXA 10.2.7.7."}
    assert "Articol real din corpul documentului" in articole["2.7.7."]
    assert "Pentru interventia la cladiri existente" in articole["ANEXA 10.2.7.7."]


def test_bloc_de_titluri_anexa_cu_pagina_intre_ele_e_cuprins_si_e_ignorat():
    """Regresia runda 2 (R21), stilul NP 010/I9 (fără prag de „Art.” atins): un titlu
    „ANEXA …” e o intrare de cuprins — deci ignorat — dacă rândul nevid următor e tot
    un titlu „ANEXA …” sau doar un număr de pagină. Aici al doilea titlu e urmat de un
    număr de pagină izolat, nu de conținut real. Ar pica dacă vreunul dintre cele două
    titluri ar deschide totuși o regiune de anexă reală."""
    text = (
        "\nANEXA 1 - TITLU UNU\n"
        "ANEXA 2 - TITLU DOI\n"
        "3\n"
        "1.1. Primul articol real al corpului cu text suficient de lung pentru a fi "
        "un chunk valid complet si corect stabilit pentru acest exemplu de test aici.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert not any(c["articol"].startswith("ANEXA") for c in rezultat)
    assert any(c["articol"] == "1.1." for c in rezultat)


def test_trimiteri_cu_virgula_sau_rupte_pe_rand_nou_nu_deschid_regiune_de_anexa():
    """Regresia I9 (R21, runda 2): o trimitere „ANEXA 2.1, au caracter…” (virgulă
    după număr) sau o frază ruptă pe rând nou care se termină cu „și” înaintea
    „ANEXA 5.3.” nu sunt titluri reale — nu trebuie să deschidă o regiune de anexă.
    Ar pica dacă vreunul dintre cele două ar produce un chunk „ANEXA 2.1.”/„ANEXA 5.3.”."""
    text = (
        "\n1.1. Introducere initiala cu suficient text pentru a forma un chunk valid "
        "corect aici sigur bine clar si complet pentru acest exemplu de test scris.\n"
        "Masurile conform ANEXA 2.1, au caracter de recomandare pentru proiectantii "
        "care aplica prezenta reglementare tehnica in activitatea curenta desfasurata.\n"
        "Cerintele tehnice se stabilesc utilizand standardul mentionat mai sus și\n"
        "ANEXA 5.3.\n"
        "Alte prevederi tehnice suplimentare raman atasate primului articol real de "
        "mai sus in acest exemplu de test scris pentru validarea corecta a regulii.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert [c["articol"] for c in rezultat] == ["1.1."]
    assert "ANEXA 2.1, au caracter" in rezultat[0]["text"]
    assert "ANEXA 5.3." in rezultat[0]["text"]


def test_titlu_de_anexa_precedat_de_legenda_terminata_in_litera_mica_deschide_regiune():
    """Regresia runda 4 (R21): o legendă de figură terminată cu literă mică
    („Figura 173 - Acces pe scara verticală”) nu trebuie să respingă titlul real de
    anexă care o urmează — doar virgula sau cuvintele de trimitere/continuare
    respectă respingerea. Ar pica dacă „ANEXA 4.5” ar rămâne text atașat articolului
    anterior în loc să devină chunk propriu."""
    text = (
        "\n1.1. Introducere cu text detaliat suficient pentru a forma un chunk valid "
        "corect si complet pentru acest exemplu de test automatizat scris aici bine.\n"
        "Figura 173 - Acces pe scara verticala\n"
        "ANEXA 4.5 - INCAPERI DE DEPOZITARE\n"
        "Continut anexa patru cinci cu detalii tehnice suficiente pentru validare "
        "completa a acestui exemplu sintetic de test automatizat scris pentru regula.\n"
    )

    rezultat = creeaza_chunkuri(text)

    articole = {c["articol"]: c["text"] for c in rezultat}
    assert "ANEXA 4.5." in articole
    assert "Continut anexa patru cinci" in articole["ANEXA 4.5."]
    assert "1.1." in articole
    assert "ANEXA 4.5" not in articole["1.1."]


def test_marcaj_art_in_interiorul_unei_anexe_nu_inchide_regiunea():
    """Regresia runda 4 (R21): un rând „Art. 2.4.9.4. (2).” în interiorul unei anexe
    reale e o trimitere internă, nu un semnal de ieșire din regiune — nu trebuie să
    închidă anexa curentă. Ar pica dacă acest marcaj ar produce un chunk „2.4.9.4.”
    fără prefixul anexei, sau dacă marcajul intern de după el nu ar mai fi recunoscut
    ca aparținând aceleiași anexe."""
    text = (
        "\nANEXA 6 - TITLU SASE\n"
        "Introducere anexa sase cu text detaliat suficient de lung pentru a fi valid "
        "complet corect pentru acest exemplu sintetic de test automatizat scris aici.\n"
        "Art. 2.4.9.4. (2). Text trimitere in interiorul anexei care nu trebuie sa "
        "inchida regiunea curenta a acestei anexe conform regulii stabilite prin R21.\n"
        "A.6. 3.1.1. Continutul final al anexei sase cu detalii tehnice suplimentare "
        "suficiente pentru validare completa a acestui exemplu de test scris aici bine.\n"
    )

    rezultat = creeaza_chunkuri(text)

    articole = {c["articol"] for c in rezultat}
    assert articole == {"ANEXA 6.", "ANEXA 6.2.4.9.4.", "ANEXA 6.3.1.1."}
    assert "2.4.9.4." not in articole


# --- R21: acoperire_text_brut elimină marcajele interne de anexă ----------------


def test_acoperire_text_brut_elimina_marcajul_intern_de_anexa():
    """Regresia P 118/1 (runda 3, R21): marcajul intern de anexă „A.<nr>.” trebuie
    eliminat și din textul brut la calculul acoperirii, la fel cum e mutat de chunker
    în identificator — altfel liniile din interiorul anexelor raportează fals
    acoperire scăzută. Ar pica dacă acoperirea nu ar fi 1.0 pe acest exemplu minim."""
    text = (
        "\nANEXA 10\n"
        "A.10. 2.2.9. Pentru limitarea propagarii fumului in caz de incendiu trebuie "
        "respectate urmatoarele conditii tehnice speciale stabilite prin normativ.\n"
    )

    rezultat = creeaza_chunkuri(text)
    acoperire = acoperire_text_brut(text, rezultat)

    assert acoperire == 1.0


# --- R22: substituiri PDF (I7) corectate la chunking și la acoperire -----------


def test_creeaza_chunkuri_corecteaza_substituirile_pdf_din_text():
    """Ar pica dacă `creeaza_chunkuri` nu ar aplica `corecteaza_substituiri_pdf`
    înainte de parsare — chunk-urile ar conține Ġ/ú/ğ/U+070A/U+0708 în loc de
    ț/ș/Ț, ca în extragerea reală a I7."""
    text = (
        "\n1.1. ProtecĠia úi securitatea instalaĠiilor electrice trebuie sa respecte "
        "prevederile prezentei norme tehnice in vigoare pentru acest tip de cladire.\n"
        "1.2. Construc܊ii ܈i instala܊ii trebuie verificate periodic conform "
        "programului de mentenanta stabilit prin prezenta reglementare tehnica aici.\n"
    )

    rezultat = creeaza_chunkuri(text)

    assert len(rezultat) == 2
    text_complet = " ".join(c["text"] for c in rezultat)
    for caracter_corupt in ("Ġ", "ú", "܊", "܈"):
        assert caracter_corupt not in text_complet
    assert "Protecția și securitatea instalațiilor" in text_complet
    assert "Construcții și instalații" in text_complet


def test_acoperire_text_brut_pe_text_corupt_ramane_simetrica():
    """Regresia I7: textul brut cu substituiri PDF și chunk-urile lui (deja
    corectate) trebuie să dea acoperire 1.0 — altfel poarta D24 ar vedea pierderi
    false, doar din cauza diferenței de codare între cele două forme comparate.
    Ar pica dacă `acoperire_text_brut` nu ar corecta și ea textul brut."""
    text = (
        "\n1.1. ProtecĠia úi securitatea instalaĠiilor electrice trebuie sa respecte "
        "prevederile prezentei norme tehnice in vigoare pentru acest tip de cladire.\n"
    )

    rezultat = creeaza_chunkuri(text)
    acoperire = acoperire_text_brut(text, rezultat)

    assert acoperire == 1.0
