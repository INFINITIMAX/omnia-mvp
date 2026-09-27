"""Teste sintetice pentru chunking_core.creeaza_chunkuri; texte mici, deterministe,
fără dependențe de documente_noi. Fiecare test reproduce o singură regulă din R14.
"""

from chunking_core import creeaza_chunkuri, ultimele_statistici


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
