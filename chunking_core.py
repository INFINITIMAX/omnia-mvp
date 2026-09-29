"""Chunking determinist unificat pentru ingestia normativelor RO.

Aceeași logică servește atât importul real (`populare_db.py`), cât și
preflight-ul local (`manual_ingestion_preflight.py`): fără I/O, fără DB, fără
rețea. Curăță antetele de pagină ale Monitorului Oficial și cuprinsul,
tratează titlurile de secțiune ca simplu context pentru articolele-copil
directe și deduplichează variantele, numărând tot ce elimină.
"""

from __future__ import annotations

import re

from diacritice import corecteaza_substituiri_pdf

# Regex-ul pentru structura articolelor din normativele deja validate. „?"
# opțional gestionează actele modificatoare, unde numărul articolului din
# normativul modificat stă imediat după ghilimeaua de deschidere a citatului
# (ex: „1.2. Domeniul de aplicare...”), nu la început de rând ca în normativele
# de bază. Ghilimeaua nu intră în grupul capturat, deci nu strică normalizarea.
# Titlurile de anexă (ex. „ANEXA 3.1.”) nu mai sunt tratate aici (Runda R21):
# `PATTERN_TITLU_ANEXA` le detectează pe toate, cu o singură logică de regiune.
PATTERN_ARTICOL = re.compile(
    r"\n\s*„?\s*(\d+\.\d+\.\s*\([A-Za-z]\)\.\s*(?:[IVXLl]\.|\d+\.)?(?:\d+\.)?|"
    r"\d+\.\d+\.(?:\d+\.){0,4})"
)
# Format alternativ folosit doar de P 118/1: articolele încep cu „Art. N.N....”, nu direct
# cu numărul. Cerem explicit spațiu + majusculă/paranteză după număr, altfel rândul e o
# trimitere ruptă pe rând nou ("Art. 2.4.5.4.. ", "Art. 2.4.5.4., …") și rămâne text.
PATTERN_ARTICOL_ART = re.compile(
    r"\n\s*„?\s*Art\.\s*(\d+\.\d+\.(?:\d+\.){0,4})\s*(?=[A-ZĂÂÎȘȚŞŢ]|\()"
)
# Format folosit de I7/I5/NP 057: articole de adâncime >=3 fără punct după ultima
# componentă ("3.1.5.7 Amplasarea...", "3.2.1 Generalități"). Cerem explicit cel puțin
# un spațiu apoi majusculă/„/( — nu și cifră sau sfârșit de rând, ca să nu confundăm
# valori zecimale ("0.4 kV", "2.5 m") cu articole noi.
PATTERN_ARTICOL_FARA_PUNCT = re.compile(
    r"\n\s*„?\s*(\d+\.\d+(?:\.\d+){0,4})[ \t  ]+(?=[A-ZĂÂÎȘȚŞŢ„(])"
)
# Titlu de anexă (Runda R21): rând care începe cu „ANEXA N”, opțional „.M”, opțional
# un sufix „.(X)” sau o literă lipită, urmat de sfârșit de rând, cratimă/en dash sau un
# titlu cu majuscule. O virgulă sau text cu literă mică după număr e o trimitere din
# corp („ANEXA 2.1, au caracter de recomandare...”, I9), nu un titlu — niciuna dintre
# variantele de continuare acceptate mai jos nu se potrivește cu ele, deci rămân excluse
# fără nicio verificare suplimentară.
PATTERN_TITLU_ANEXA = re.compile(
    r"\n[ \t]*ANEXA[ \t]+(\d+(?:\.\d+)?(?:\.?\([A-Za-z]\))?[A-Za-z]?)\.?[ \t]*"
    r"(?=[\-–]|[A-ZĂÂÎȘȚŞŢ]|$)",
    re.MULTILINE,
)
# Marcaj intern de anexă (Runda R21, P 118/1/Anexa 10 „Construcții existente”):
# „A.10. 2.7.7. Pentru intervenția...” repetă numărul anexei curente ca prefix literal;
# grupul capturat e numărul propriu-zis, cu punctul final inclus (ca la PATTERN_ARTICOL_ART),
# ca să nu se dubleze punctul la compunerea identificatorului cu prefixul anexei.
PATTERN_MARCAJ_ANEXA_INTERN = re.compile(
    r"\n[ \t]*A\.\d+\.[ \t]*(\d+(?:\.\d+){1,4}\.)[ \t]+(?=[A-ZĂÂÎȘȚŞŢ„(])"
)
# Titlu de capitol cu un singur nivel de numerotare ("4. Elemente generale de calcul"),
# nerecunoscut de PATTERN_ARTICOL (cere >=2 componente). Grupul 1 include punctul final,
# ca la celelalte marcaje; grupul 2 e textul titlului, validat separat în
# `_este_titlu_capitol_simplu_valid` (lungime, punctuație finală, copil direct următor) —
# altfel orice enumerare simplă din corpul unui articol ("1. text... 2. text...") ar fi
# confundată cu un titlu de capitol.
PATTERN_TITLU_CAPITOL_SIMPLU = re.compile(r"\n\s*(\d{1,2}\.)[ \t]+([A-ZĂÂÎȘȚŞŢ].*)")
PATTERN_LINIE_CUPRINS = re.compile(r"\.{4,}\s*\d{1,4}\s*(?=\n|$)")
PATTERN_TITLU_CUPRINS = re.compile(r"^\s*\d+(?:\.\d+)*\.\s+\S.*$")
PATTERN_NUMAR_PAGINA = re.compile(r"^\d{1,4}$")
PATTERN_SUBPUNCT = re.compile(r"\n\s*\((\d+)\)\s+")
PATTERN_ANTET_MO = re.compile(
    r"^\s*MONITORUL\s+OFICIAL\s+AL\s+ROM[ÂA]NIEI,\s*PARTEA\s+I,\s*Nr\.\s*.+$"
)
PATTERN_TITLU_ROMAN = re.compile(r"^\s*[IVXLC]{1,6}\.\s+(.+?)\s*$")
# Colofonul de tipar de la finalul fiecărui fascicul MO: fie fraza de tiraj/abonament,
# fie antetul editurii, fie mențiunea explicită "Tiparul: ...". Toate trei apar identic
# în fiecare fascicul, deci ancorarea pe oricare din ele prinde blocul complet.
PATTERN_COLOFON_MO = re.compile(
    r"^\s*(?:„Monitorul Oficial” R\.A\.,"
    r"|Tiparul:\s*„Monitorul Oficial” R\.A\.\s*$"
    r"|Acest număr al Monitorului Oficial al României a fost tipărit în afara abonamentului\.)",
    re.MULTILINE,
)
PATTERN_DATA_ZI_LUNA_AN = re.compile(r"^(0[1-9]|[12]\d|3[01])\.(0[1-9]|1[0-2])\.$")
_PATTERN_SPATIERE_ARTICOL = re.compile(r"[ \t\n\r\f\v  ]+")
_PATTERN_ARTICOL_NORMALIZAT = re.compile(r"^[a-z0-9().-]+$")

# Folosite doar de acoperire_text_brut, pentru a compara textul brut cu textul
# concatenat al chunk-urilor fără marcajele de articol/subpunct pe care
# extragerea le consumă ca delimitatoare (nu mai apar în chunk-uri).
_PATTERN_MARCAJ_ARTICOL_ACOPERIRE = re.compile(r"(?:Art\.\s*)?\d+(?:\.\d+){1,6}\.?")
# Runda R21/3: marcajul intern de anexă („A.10. 2.7.7.”) e mutat de chunker în
# identificator (ca și marcajele obișnuite) și nu mai apare în textul chunk-urilor —
# trebuie eliminat și din textul brut, altfel liniile din Anexa 10 P 118/1 raportează
# fals acoperire scăzută.
_PATTERN_MARCAJ_ANEXA_INTERN_ACOPERIRE = re.compile(r"A\.\d+\.")
_PATTERN_SUBPUNCT_PARANTEZA_ACOPERIRE = re.compile(r"\(\d+\)")
LUNGIME_MINIMA_LINIE_ACOPERIRE = 50

# Runda R21: sub acest prag de marcaje „Art.” recunoscute, documentul nu folosește
# convenția P 118/1 — PATTERN_ARTICOL_FARA_PUNCT rămâne activ ca până acum (I7 etc.).
PRAG_MARCAJE_ART = 50

LUNGIME_MINIMA_CHUNK = 15
LUNGIME_PENTRU_SPLIT_SECUNDAR = 2000
MAX_CHUNK_CHARS = 1000
# D27: marcajul de proveniență din normativele consolidate (vezi consolidare_normative.py).
# Recunoaște atât forma originală, pusă de consolidare direct pe textul afectat („Text
# modificat”/„Text introdus”/„Abrogat”), cât și forma la nivel de articol propagată de
# `_propaga_marcaj_provenienta` la celelalte bucăți ale aceluiași articol de bază
# („Articol cu text modificat/introdus/abrogat”) — necesar ca tăietura la 1000 de
# caractere (`_aplica_limita_caractere`) să nu rupă nici forma nouă în două.
PATTERN_MARCAJ_PROVENIENTA = re.compile(
    r"\[(?:Articol cu text )?(Text modificat|Text introdus|Abrogat|modificat|introdus|abrogat) "
    r"(prin Ordinul nr\. [^\]\n]{1,150})\]"
)
LUNGIME_MAXIMA_MARCAJ = 200
PROCENT_MAXIM_CAUTARE_CUPRINS = 0.20
DISTANTA_MAXIMA_ANTET = 3
NUMAR_MINIM_INTRARI_CUPRINS = 5
DISTANTA_MAXIMA_INTRARE_CUPRINS = 3
LUNGIME_MAXIMA_TITLU = 200
LUNGIME_MAXIMA_TITLU_CAPITOL_SIMPLU = 120
LUNGIME_FEREASTRA_COLOFON = 4000

_ultimele_statistici = {
    "antete_eliminate": 0,
    "titluri_contopite": 0,
    "duplicate_eliminate": 0,
    "titluri_cuprins_eliminate": 0,
}


def ultimele_statistici() -> dict[str, int]:
    """Întoarce statisticile ultimei rulări a creeaza_chunkuri (nu e thread-safe)."""
    return dict(_ultimele_statistici)


def creeaza_chunkuri(text: str) -> list[dict[str, str]]:
    """Transformă textul unui normativ în chunk-uri deterministe, fără I/O."""
    text = corecteaza_substituiri_pdf(text)
    continut, antete_eliminate = _elimina_antete_mo(text)
    continut = _elimina_colofon_mo(continut)
    continut = _elimina_cuprins(continut)
    continut = _elimina_titluri_capitol_roman(continut)

    segmente = _extrage_segmente(continut)
    _propaga_titluri_capitol_simplu(segmente)
    titluri_contopite, titluri_cuprins_eliminate = _contopeste_titluri(segmente)
    articole_cu_context_parinte = {
        segment["articol"] for segment in segmente if segment["are_context_parinte"]
    }

    chunkuri_dupa_articol: dict[str, dict[str, str]] = {}
    duplicate_eliminate = 0
    for segment in segmente:
        if segment["este_titlu"]:
            continue
        text_segment = segment["text"]
        if len(text_segment) < LUNGIME_MINIMA_CHUNK:
            continue
        articol = segment["articol"]
        cheie = _normalizeaza_pentru_dedup(articol)
        existent = chunkuri_dupa_articol.get(cheie)
        if existent is None:
            chunkuri_dupa_articol[cheie] = {"articol": articol, "text": text_segment}
        elif len(text_segment) > len(existent["text"]):
            chunkuri_dupa_articol[cheie] = {"articol": articol, "text": text_segment}
            duplicate_eliminate += 1
        else:
            duplicate_eliminate += 1

    chunkuri, titluri_contopite_din_split = _aplica_split_secundar(
        list(chunkuri_dupa_articol.values()), articole_cu_context_parinte
    )
    titluri_contopite += titluri_contopite_din_split
    chunkuri = _aplica_limita_caractere(chunkuri)
    chunkuri = _propaga_marcaj_provenienta(chunkuri)

    _ultimele_statistici["antete_eliminate"] = antete_eliminate
    _ultimele_statistici["titluri_contopite"] = titluri_contopite
    _ultimele_statistici["duplicate_eliminate"] = duplicate_eliminate
    _ultimele_statistici["titluri_cuprins_eliminate"] = titluri_cuprins_eliminate
    return chunkuri


def _elimina_antete_mo(text: str) -> tuple[str, int]:
    """Șterge rândul de antet MO și numerele de pagină alăturate lui.

    Un rând doar-cifre e eliminat numai dacă e la cel mult 3 rânduri de un
    antet, cu doar rânduri goale sau doar-cifre între ele — altfel rămâne,
    fiindcă poate fi o celulă de tabel.
    """
    linii = text.split("\n")
    de_eliminat: set[int] = set()
    nr_antete = 0
    for index, linie in enumerate(linii):
        if not PATTERN_ANTET_MO.match(linie):
            continue
        nr_antete += 1
        de_eliminat.add(index)
        for directie in (-1, 1):
            vecin = index + directie
            pasi = 0
            while pasi < DISTANTA_MAXIMA_ANTET and 0 <= vecin < len(linii):
                candidat = linii[vecin].strip()
                if candidat == "":
                    vecin += directie
                    pasi += 1
                    continue
                if PATTERN_NUMAR_PAGINA.match(candidat):
                    de_eliminat.add(vecin)
                    vecin += directie
                    pasi += 1
                    continue
                break
    linii_ramase = [linie for index, linie in enumerate(linii) if index not in de_eliminat]
    return "\n".join(linii_ramase), nr_antete


def _elimina_cuprins(text: str) -> str:
    """Sare peste cuprins: fie linii cu puncte de conducere, fie titlu + pagină pe rândul următor.

    Ambele stiluri se recunosc numai ca BLOC (minimum `NUMAR_MINIM_INTRARI_CUPRINS`
    intrări, la cel mult `DISTANTA_MAXIMA_INTRARE_CUPRINS` rânduri nevide una de alta),
    nu la prima/ultima potrivire izolată — altfel un interval numeric întâmplător din
    corpul textului („...între 150...500 ms...”) ar fi confundat cu finalul cuprinsului
    și ar arunca tot ce e înainte de el (bug real găsit în I7).
    """
    limita = int(len(text) * PROCENT_MAXIM_CAUTARE_CUPRINS)
    linii = text.split("\n")
    offsets = []
    offset = 0
    for linie in linii:
        offsets.append(offset)
        offset += len(linie) + 1

    indici_puncte = [
        index for index, linie in enumerate(linii)
        if offsets[index] < limita and PATTERN_LINIE_CUPRINS.search(linie)
    ]
    taietura_puncte = _capatul_primului_bloc_cuprins(linii, offsets, indici_puncte, lungime_intrare=1)

    indici_pagini = [
        index for index in range(len(linii) - 1)
        if offsets[index] < limita
        and PATTERN_TITLU_CUPRINS.match(linii[index])
        and PATTERN_NUMAR_PAGINA.match(linii[index + 1].strip())
    ]
    taietura_pagini = _capatul_primului_bloc_cuprins(linii, offsets, indici_pagini, lungime_intrare=2)

    taietura = max(taietura_puncte, taietura_pagini)
    return text[taietura:] if taietura else text


def _capatul_primului_bloc_cuprins(
    linii: list[str], offsets: list[int], indici_intrari: list[int], lungime_intrare: int
) -> int:
    """Primul bloc de minimum `NUMAR_MINIM_INTRARI_CUPRINS` intrări consecutive, unde
    fiecare intrare ocupă `lungime_intrare` rânduri începând la un index din
    `indici_intrari`, iar între finalul unei intrări și începutul următoarei sunt cel
    mult `DISTANTA_MAXIMA_INTRARE_CUPRINS` rânduri nevide (titlurile lungi se pot rupe
    pe 2-3 rânduri fără să întrerupă blocul). Întoarce offset-ul de sfârșit al ultimei
    intrări din primul bloc care atinge pragul, sau 0 dacă nu există un asemenea bloc.
    """
    bloc: list[int] = []
    for index in indici_intrari:
        if bloc:
            gap = linii[bloc[-1] + lungime_intrare:index]
            nr_nevide = sum(1 for linie in gap if linie.strip())
            if nr_nevide > DISTANTA_MAXIMA_INTRARE_CUPRINS:
                if len(bloc) >= NUMAR_MINIM_INTRARI_CUPRINS:
                    return _sfarsit_intrare_cuprins(linii, offsets, bloc[-1], lungime_intrare)
                bloc = []
        bloc.append(index)
    if len(bloc) >= NUMAR_MINIM_INTRARI_CUPRINS:
        return _sfarsit_intrare_cuprins(linii, offsets, bloc[-1], lungime_intrare)
    return 0


def _sfarsit_intrare_cuprins(linii: list[str], offsets: list[int], index_start: int, lungime_intrare: int) -> int:
    ultima_linie = index_start + lungime_intrare - 1
    return offsets[ultima_linie] + len(linii[ultima_linie]) + 1


def _elimina_titluri_capitol_roman(text: str) -> str:
    """Închide articolul curent la un titlu de capitol cu cifre romane; titlul nu intră în text."""
    linii_pastrate = []
    for linie in text.split("\n"):
        potrivire = PATTERN_TITLU_ROMAN.match(linie)
        if potrivire and _este_majoritar_majuscul(potrivire.group(1)):
            continue
        linii_pastrate.append(linie)
    return "\n".join(linii_pastrate)


def _elimina_colofon_mo(text: str) -> str:
    """Taie colofonul de tipar de la finalul fasciculului, căutat doar spre finalul textului.

    Referințele din corp ("publicat în Monitorul Oficial al României...") nu ancorează
    pe niciunul dintre cele trei tipare, deci rămân neatinse.
    """
    limita = max(0, len(text) - LUNGIME_FEREASTRA_COLOFON)
    inceput_linie = text.find("\n", limita)
    fereastra_start = inceput_linie + 1 if inceput_linie != -1 else limita
    potrivire = PATTERN_COLOFON_MO.search(text, fereastra_start)
    if potrivire is None:
        return text
    return text[:potrivire.start()].rstrip("\n")


def _este_titlu(text: str) -> bool:
    """Un rând unic, nevid, scurt, fără punctuație finală de continuare — potrivit ca titlu."""
    return (
        bool(text)
        and "\n" not in text
        and len(text) <= LUNGIME_MAXIMA_TITLU
        and not text.endswith((".", ";", ":"))
    )


def _este_majoritar_majuscul(text: str) -> bool:
    litere = [caracter for caracter in text if caracter.isalpha()]
    if not litere:
        return False
    majuscule = sum(1 for caracter in litere if caracter.isupper())
    return majuscule > len(litere) / 2


def _normalizeaza_pentru_dedup(articol: str) -> str:
    """Cheia de dedup: același contract ca `normalizeaza_articol`/`_normalizeaza_articol`
    (spațiere colapsată, minuscule, fără puncte finale), fără validarea caracterelor —
    validarea rămâne responsabilitatea importerului la scriere în DB."""
    return _PATTERN_SPATIERE_ARTICOL.sub("", articol).lower().rstrip(".")


def _este_articol_normalizabil(articol: str) -> bool:
    return bool(_PATTERN_ARTICOL_NORMALIZAT.fullmatch(_normalizeaza_pentru_dedup(articol)))


def _baza_articol(potrivire: re.Match[str]) -> str:
    """Numărul normalizat al marcajului, cu punct final garantat.

    Marcajele fără punct pe ultima componentă (Runda 6, ex. `3.1.5.7`) nu au
    punctul inclus în grupul capturat; îl adăugăm aici, o singură dată, ca
    identificatorul rezultat să fie identic cu forma cu punct (`3.1.5.7.`) și
    ca toate verificările (trimitere ruptă, dată, contopire titluri) să
    lucreze pe același format, indiferent care marcaj a produs potrivirea.
    """
    baza = potrivire.group(1).strip()
    return baza if baza.endswith(".") else baza + "."


def _este_data_zi_luna_an(potrivire: re.Match[str], sursa: str) -> bool:
    """O secvență `ZZ.LL.` urmată imediat de un an pe 4 cifre e o dată, nu un articol."""
    if not PATTERN_DATA_ZI_LUNA_AN.fullmatch(_baza_articol(potrivire)):
        return False
    return re.match(r"\d{4}(?!\d)", sursa[potrivire.end(1):]) is not None


_PATTERN_SPATII_INLINE = re.compile(r"[ \t  ]*")
_PATTERN_CARACTER_VALID_DUPA_NUMAR = re.compile(r"^[A-ZĂÂÎȘȚŞŢ„(0-9]")
# Runda R27 (P 118/3, P 118/2 Anexa 33): definițiile de terminologie încep cu literă
# mică ("2.56. semnal de confirmare alarmă - semnal de la..."), caz altfel identic cu o
# trimitere ruptă (literă mică nevalidă după număr). Le distingem prin prezența unei
# cratime/en dash aproape de începutul rândului (separatorul termen-definiție); fereastra
# de căutare acoperă și variantele cu cratimă lipită de termen, cu paranteze înainte de
# cratimă și cu cratima mutată pe rândul următor (2.16, 2.30, 2.61 etc.).
_PATTERN_LITERA_MICA_DUPA_NUMAR = re.compile(r"^[a-zăâîșțşţ]")
_PATTERN_CRATIMA_DEFINITIE = re.compile(r"[-–]")
_LUNGIME_FEREASTRA_CRATIMA_DEFINITIE = 120
# Runda 2 (I7/NP 057): extragerea PDF lipește uneori cuvântul de primul articol,
# fără spațiu ("3.0.1.CondiĠii", "3.1.2.3.3.Mentenanța"). Când primul caracter
# lipit e o majusculă (inclusiv diacritice), acel caracter deschide un cuvânt
# real, nu un sufix de articol — cuvântul întreg rămâne text, nu se lipește de
# identificator. Verificăm doar primul caracter lipit; eventuale caractere
# corupte de OCR (ex. „Ġ”, „ú”) mai departe în același cuvânt nu contează aici,
# fiindcă acel cuvânt nu mai ajunge deloc în `articol`.
_PATTERN_MAJUSCULA_LIPITA = re.compile(r"[A-ZĂÂÎȘȚŞŢ]")
# Cuvintele care, la finalul ultimului rând nevid dinaintea marcajului, arată că
# numărul de pe rândul următor e continuarea unei trimiteri rupte de extragerea PDF
# ("...prevederile Art.\n2.1.3.5. (1) alin. a);"), nu un articol nou. Comparate cu
# rândul anterior integral, minuscule — acoperă și "Art."/"Articolul" cu majusculă.
_CUVINTE_TRIMITERE_RUPTA = (
    "art.", "articolul", "alin.", "pct.", "lit.", "conform",
    "punctele", "punctul", "punctelor", "articolele", "articolelor", "prevederile", "prevederilor",
)


# Runda R21/5: ultimul cuvânt întreg al unui rând (precedat de început de rând sau de
# un caracter care nu e literă) — folosit ca să nu se mai confunde un sufix de cuvânt
# ("...stabilit." conține "lit.") cu un cuvânt de trimitere/legătură real.
_PATTERN_ULTIMUL_CUVANT_RAND = re.compile(r"(?:^|[^A-Za-zĂÂÎȘȚăâîșț])([A-Za-zĂÂÎȘȚăâîșț]+\.?)$")


def _ultimul_cuvant(linie: str) -> str:
    potrivire = _PATTERN_ULTIMUL_CUVANT_RAND.search(linie)
    return potrivire.group(1).lower() if potrivire else ""


def _linia_anterioara_se_termina_cu_trimitere(sursa: str, pozitie_marcaj: int) -> bool:
    """Caută înapoi, sărind rândurile goale, ultimul rând nevid dinaintea marcajului."""
    capat = pozitie_marcaj
    while capat >= 0:
        inceput = sursa.rfind("\n", 0, capat) + 1
        linie = sursa[inceput:capat].strip()
        if linie:
            return _ultimul_cuvant(linie) in _CUVINTE_TRIMITERE_RUPTA
        if inceput == 0:
            return False
        capat = inceput - 1
    return False


# Runda R21/2: cuvinte de legătură care, la finalul rândului anterior unui titlu de
# anexă, arată o frază întreruptă pe rând nou ("...utilizând standardul SR EN 12056-2 și
# ↵ ANEXA 5.3.", I9), nu un titlu real — pe lângă lista deja existentă de trimiteri rupte.
_CUVINTE_CONTINUARE_ANEXA = ("și", "sau", "din", "la", "în")


def _linia_anterioara_indica_continuare_anexa(sursa: str, pozitie_marcaj: int) -> bool:
    """Rândul nevid anterior arată că marcajul „ANEXA…” e o continuare de frază ruptă pe
    rând nou, nu un titlu: se termină cu virgulă sau cu unul dintre cuvintele din
    `_CUVINTE_CONTINUARE_ANEXA`/`_CUVINTE_TRIMITERE_RUPTA`. Runda R21/4: nu mai respinge
    doar pentru că se termină cu literă mică — legendele de figuri („Figura 173 - Stație
    de pompare - Acces pe scara verticală”) se termină așa și precedă titluri reale."""
    capat = pozitie_marcaj
    while capat >= 0:
        inceput = sursa.rfind("\n", 0, capat) + 1
        linie = sursa[inceput:capat].strip()
        if linie:
            if linie[-1] == ",":
                return True
            cuvant = _ultimul_cuvant(linie)
            return cuvant in _CUVINTE_TRIMITERE_RUPTA or cuvant in _CUVINTE_CONTINUARE_ANEXA
        if inceput == 0:
            return False
        capat = inceput - 1
    return False


def _urmatorul_rand_nevid(sursa: str, pozitie: int) -> str | None:
    """Textul (fără spații) al primului rând nevid care începe după `pozitie`, sau
    `None` dacă textul se termină înainte de un asemenea rând."""
    inceput = sursa.find("\n", pozitie)
    while inceput != -1:
        sfarsit = sursa.find("\n", inceput + 1)
        capat_linie = sfarsit if sfarsit != -1 else len(sursa)
        linie = sursa[inceput + 1:capat_linie].strip()
        if linie:
            return linie
        inceput = sfarsit
    return None


def _este_titlu_anexa_de_cuprins(potrivire: re.Match[str], sursa: str) -> bool:
    """Un titlu de anexă e o intrare de cuprins, nu un titlu real din corp, dacă
    rândul nevid următor e tot un titlu de anexă sau doar un număr de pagină (bloc de
    minimum 2 intrări de cuprins consecutive)."""
    urmator = _urmatorul_rand_nevid(sursa, potrivire.end())
    if urmator is None:
        return False
    if PATTERN_NUMAR_PAGINA.match(urmator):
        return True
    return PATTERN_TITLU_ANEXA.match("\n" + urmator) is not None


def _este_referinta_rupta(potrivire: re.Match[str], sursa: str) -> bool:
    """Un marcaj numeric simplu (sau „Art. N.N....”) e o trimitere ruptă pe rând nou
    (D18 + P 118/1), nu un articol nou, dacă:

    - rândul anterior nevid se termină cu un cuvânt de trimitere
      (`_linia_anterioara_se_termina_cu_trimitere`), sau
    - imediat după număr (după eventuale spații) nu urmează majusculă (inclusiv
      diacritice), `„`, `(`, cifră sau sfârșitul rândului/textului.

    Excepție D18: o virgulă e delimitator valid (se elimină, ca acum, prin sufixul de
    citat) numai dacă e urmată doar de spații până la capătul rândului; altfel
    (`1.1.,text`) rămâne trimitere ruptă. Literele mici (ex. `lit. a)` din P 118/1) nu
    sunt niciodată un început valid de articol — cu excepția definițiilor de terminologie
    (Runda R27, P 118/3 „2.56. semnal de confirmare alarmă - ...”, P 118/2 Anexa 33
    „33.5. instalație cu preacționare – ...”), recunoscute după cratima/en dash care
    separă termenul de definiție, aproape de începutul rândului.
    """
    baza = _baza_articol(potrivire)
    if not re.fullmatch(r"\d+(?:\.\d+)*\.", baza):
        return False
    if _linia_anterioara_se_termina_cu_trimitere(sursa, potrivire.start()):
        return True
    urmator = sursa[potrivire.end(1):]

    if urmator[:1] == ",":
        dupa_virgula = urmator[1:]
        pas = _PATTERN_SPATII_INLINE.match(dupa_virgula).end()
        return dupa_virgula[pas:pas + 1] not in ("", "\n")

    pas = _PATTERN_SPATII_INLINE.match(urmator).end()
    rest = urmator[pas:]
    if rest[:1] in ("", "\n"):
        return False
    # O cifră lipită imediat (fără spațiu) de marcaj e prefixul unui număr mai lung
    # (ex. „4.2.4.” + „5 și 4.2.4.6” din text continuu), nu un articol nou — spre
    # deosebire de o cifră după spațiu real, care rămâne caracter valid ca până acum.
    if pas == 0 and rest[:1].isdigit():
        return True
    if _PATTERN_CARACTER_VALID_DUPA_NUMAR.match(rest):
        return False
    # Cratima trebuie să fie pe același rând: în I7, „4.1.4.2.2.2. sau” e urmat pe rândul
    # următor de „-” (enumerare), nu e o definiție.
    if _PATTERN_LITERA_MICA_DUPA_NUMAR.match(rest) and _PATTERN_CRATIMA_DEFINITIE.search(
        urmator.split("\n", 1)[0][:_LUNGIME_FEREASTRA_CRATIMA_DEFINITIE]
    ):
        return False
    return True


def _este_titlu_capitol_simplu_valid(
    potrivire: re.Match[str], candidate: list[re.Match[str]], index: int
) -> bool:
    """Un rând `N. Titlu` e titlu de capitol numai dacă respectă formatul (titlu scurt,
    fără punctuație finală de continuare) și marcajul recunoscut imediat următor e un
    copil direct al lui — altfel e o enumerare obișnuită din corpul unui articol
    (ex. „1. text… 2. text…”, fără „1.1.”), nu un separator de capitol.
    """
    titlu = potrivire.group(2).rstrip()
    if len(titlu) > LUNGIME_MAXIMA_TITLU_CAPITOL_SIMPLU or titlu.endswith((".", ";", ":")):
        return False
    if index + 1 >= len(candidate):
        return False
    prefix = _baza_articol(potrivire)
    baza_urmator = _baza_articol(candidate[index + 1])
    if not baza_urmator.startswith(prefix) or baza_urmator == prefix:
        return False
    return baza_urmator[len(prefix):].count(".") == 1


def _extrage_segmente(continut: str) -> list[dict[str, object]]:
    """Parsează articolele în ordinea din text, cu numărul brut și cel cu sufix.

    Combină marcajul numeric obișnuit, marcajul „Art. N.N....” (P 118/1), marcajul
    fără punct pe ultima componentă (I7/I5/NP 057) și titlurile/marcajele interne de
    anexă (Runda R21). Când două marcaje pornesc din exact aceeași poziție (ex.
    varianta cu punct prinde doar `3.1.5.`, cea fără punct prinde `3.1.5.7` întreg),
    câștigă potrivirea cu numărul mai lung — cealaltă e doar un prefix parțial al
    aceleiași cifre.

    Runda R21: în documentele care folosesc convenția „Art. N.N....” ca marcaj
    principal (≥ `PRAG_MARCAJE_ART` marcaje), `PATTERN_ARTICOL_FARA_PUNCT` nu mai
    produce începuturi de articol — sursa falșilor identificatori din P 118/1
    („27.3”, „48.6” etc., numere sau valori rupte pe rând nou în anexe). În restul
    documentelor (I7) rămâne activ ca până acum.
    """
    sursa = "\n" + continut
    marcaje_art = list(PATTERN_ARTICOL_ART.finditer(sursa))
    fara_punct_activ = len(marcaje_art) < PRAG_MARCAJE_ART
    # Runda R21/4: în documentele cu convenția „Art. N.N....” (≥ prag), tot ce precede
    # primul marcaj „Art.” ACCEPTAT (nu trimitere ruptă/dată) e cuprins/front-matter —
    # inclusiv titlurile de anexă rupte pe două rânduri din cuprins, pe care regulile de
    # continuare de frază nu le prind (ex. rândul 414 P 118/1). Nu „ultimul” marcaj: în
    # regiunea reală a anexelor apar și trimiteri „Art.” (ex. rândurile 26351, 29484,
    # 35900), care ar împinge greșit limita până la sfârșitul documentului.
    prim_art_acceptat = next(
        (
            potrivire for potrivire in marcaje_art
            if not (_este_data_zi_luna_an(potrivire, sursa) or _este_referinta_rupta(potrivire, sursa))
        ),
        None,
    ) if not fara_punct_activ else None
    prim_art_start = prim_art_acceptat.start() if prim_art_acceptat is not None else None
    toate = sorted(
        (
            *PATTERN_ARTICOL.finditer(sursa),
            *marcaje_art,
            *(PATTERN_ARTICOL_FARA_PUNCT.finditer(sursa) if fara_punct_activ else ()),
            *PATTERN_TITLU_CAPITOL_SIMPLU.finditer(sursa),
            *PATTERN_TITLU_ANEXA.finditer(sursa),
            *PATTERN_MARCAJ_ANEXA_INTERN.finditer(sursa),
        ),
        key=lambda potrivire: (potrivire.start(), -(potrivire.end(1) - potrivire.start(1))),
    )
    candidate = []
    ultimul_start = None
    for potrivire in toate:
        if potrivire.start() == ultimul_start:
            continue
        candidate.append(potrivire)
        ultimul_start = potrivire.start()

    potriviri = []
    for index, potrivire in enumerate(candidate):
        # Runda R21/2: un titlu de anexă e o intrare de cuprins (bloc de titluri
        # consecutive/pagini) sau o continuare de frază ruptă pe rând nou — niciuna
        # dintre ele nu deschide o regiune de anexă reală.
        if potrivire.re is PATTERN_TITLU_ANEXA and (
            _este_titlu_anexa_de_cuprins(potrivire, sursa)
            or _linia_anterioara_indica_continuare_anexa(sursa, potrivire.start())
            or (prim_art_start is not None and potrivire.start() < prim_art_start)
        ):
            continue
        # Marcajele interne de anexă au propria validare (lookahead-ul din regex),
        # independentă de trimiterile rupte pe rând nou sau de datele calendaristice
        # specifice marcajelor numerice obișnuite.
        if potrivire.re in (PATTERN_TITLU_ANEXA, PATTERN_MARCAJ_ANEXA_INTERN):
            potriviri.append(potrivire)
            continue
        if _este_data_zi_luna_an(potrivire, sursa) or _este_referinta_rupta(potrivire, sursa):
            continue
        if potrivire.re is PATTERN_TITLU_CAPITOL_SIMPLU and not _este_titlu_capitol_simplu_valid(
            potrivire, candidate, index
        ):
            continue
        potriviri.append(potrivire)
    segmente = []
    anexa_curenta: str | None = None
    for index, potrivire in enumerate(potriviri):
        este_titlu_anexa = potrivire.re is PATTERN_TITLU_ANEXA
        if este_titlu_anexa:
            anexa_curenta = potrivire.group(1)
            articol = articol_baza = f"ANEXA {anexa_curenta}."
            titlu_capitol = None
        else:
            articol_baza = _baza_articol(potrivire)
            if anexa_curenta is not None:
                # Marcajele interne dintr-o anexă (numere simple sau „A.N. X.Y.Z.”)
                # devin copii ai anexei curente, ca să nu mai poată coincide cu
                # articolele din corp (regula copiilor din `find_exact`/R14).
                articol_baza = f"ANEXA {anexa_curenta}.{articol_baza}"
            articol = articol_baza
            titlu_capitol = (
                potrivire.group(2).rstrip() if potrivire.re is PATTERN_TITLU_CAPITOL_SIMPLU else None
            )
            urmator_direct = sursa[potrivire.end(1):potrivire.end(1) + 1]
            if not _PATTERN_MAJUSCULA_LIPITA.match(urmator_direct):
                sufix = re.match(r"[^\s]+", sursa[potrivire.end(1):])
                if sufix is not None:
                    candidat = articol + sufix.group(0)
                    if candidat.endswith(","):
                        articol = candidat[:-1] if _este_articol_normalizabil(candidat[:-1]) else candidat
                    else:
                        articol = candidat
        inceput_text = potrivire.end()
        sfarsit_text = potriviri[index + 1].start() if index + 1 < len(potriviri) else len(sursa)
        text_segment = sursa[inceput_text:sfarsit_text].strip()
        segmente.append(
            {
                "articol": articol,
                "articol_baza": articol_baza,
                "titlu_capitol": titlu_capitol,
                "text": text_segment,
                "este_titlu": False,
                "are_context_parinte": False,
            }
        )
    return segmente


def _propaga_titluri_capitol_simplu(segmente: list[dict[str, object]]) -> None:
    """Pune textul titlurilor de capitol cu un singur nivel (`titlu_capitol`) ca prim
    rând la copiii lor direcți, ca la titlurile din `_contopeste_titluri` — dar
    segmentul-titlu însuși rămâne un chunk normal (introducerea capitolului), nu e
    marcat `este_titlu`, fiindcă validarea din `_este_titlu_capitol_simplu_valid` a
    confirmat deja că are un copil direct, indiferent de forma textului rămas.
    """
    for index, segment in enumerate(segmente):
        titlu = segment["titlu_capitol"]
        if titlu is None:
            continue
        prefix = segment["articol_baza"]
        context = f"{prefix} {titlu}"
        pas = index + 1
        while pas < len(segmente) and segmente[pas]["articol_baza"].startswith(prefix):
            rest = segmente[pas]["articol_baza"][len(prefix):]
            if rest.count(".") == 1:
                segmente[pas]["text"] = f"{context}\n{segmente[pas]['text']}"
                segmente[pas]["are_context_parinte"] = True
            pas += 1


def _contopeste_titluri(segmente: list[dict[str, object]]) -> tuple[int, int]:
    """Marchează titlurile de secțiune și pune textul lor ca prim rând la copiii direcți.

    Un segment care arată a titlu, dar al cărui număr are copii undeva în document, nu
    devine niciodată chunk separat: dacă segmentul imediat următor e chiar copilul lui,
    se contopește ca până acum; altfel e o intrare de cuprins duplicat (fără pagini,
    ex. P 118/1) și e eliminată direct, fără propagare de context.
    """
    contopite = 0
    cuprins_eliminate = 0
    bazele = [segment["articol_baza"] for segment in segmente]
    for index, segment in enumerate(segmente):
        if segment["titlu_capitol"] is not None:
            continue
        text = segment["text"]
        if not _este_titlu(text):
            continue
        prefix = segment["articol_baza"]
        are_copil_undeva = any(
            baza != prefix and baza.startswith(prefix) for baza in bazele
        )
        if not are_copil_undeva:
            continue

        urmator = segmente[index + 1] if index + 1 < len(segmente) else None
        este_copil_imediat = (
            urmator is not None
            and urmator["articol_baza"] != prefix
            and urmator["articol_baza"].startswith(prefix)
        )
        if not este_copil_imediat:
            segment["este_titlu"] = True
            cuprins_eliminate += 1
            continue

        segment["este_titlu"] = True
        contopite += 1
        context = f"{prefix} {text}"
        pas = index + 1
        while pas < len(segmente) and segmente[pas]["articol_baza"].startswith(prefix):
            rest = segmente[pas]["articol_baza"][len(prefix):]
            if rest.count(".") == 1:
                segmente[pas]["text"] = f"{context}\n{segmente[pas]['text']}"
                segmente[pas]["are_context_parinte"] = True
            pas += 1
    return contopite, cuprins_eliminate


def _aplica_split_secundar(
    chunkuri: list[dict[str, str]], articole_cu_context_parinte: set[str]
) -> tuple[list[dict[str, str]], int]:
    rezultat = []
    titluri_contopite = 0
    for chunk in chunkuri:
        if len(chunk["text"]) < LUNGIME_PENTRU_SPLIT_SECUNDAR:
            rezultat.append(chunk)
            continue
        subpuncte = PATTERN_SUBPUNCT.split(chunk["text"])
        if len(subpuncte) == 1:
            rezultat.append(chunk)
            continue
        numere_subpunct = [int(subpuncte[index]) for index in range(1, len(subpuncte), 2)]
        # Numerotare care reîncepe sau se repetă (ex. „(1)…(3)” de mai multe ori în
        # același articol, la sub-secțiuni nenumerotate) nu poate fi despărțită pe
        # subpuncte — ar suprapune identificatori. Articolul rămâne o unitate, tăiată
        # apoi doar de `_aplica_limita_caractere`.
        if any(numere_subpunct[index] <= numere_subpunct[index - 1] for index in range(1, len(numere_subpunct))):
            rezultat.append(chunk)
            continue
        introducere = subpuncte[0].strip()
        # O introducere care e ea însăși un titlu (ex. "1.1." -> "Obiect și domeniul de
        # aplicare", urmat direct de subpunctele (1), (2)...) nu devine chunk separat;
        # devine context, la fel ca la titlurile de secțiune din _contopeste_titluri.
        # Dacă introducerea e chiar titlul părintelui deja contopit de _contopeste_titluri
        # (chunk-ul are_context_parinte), rămâne ca atare — fără să mai adăugăm și
        # articolul curent în față, ca să nu apară un prefix dublat.
        context = None
        if _este_titlu(introducere):
            if chunk["articol"] in articole_cu_context_parinte:
                context = introducere
            else:
                context = f"{chunk['articol']} {introducere}"
                titluri_contopite += 1
        elif len(introducere) >= LUNGIME_MINIMA_CHUNK:
            rezultat.append({"articol": chunk["articol"], "text": introducere})
        for index in range(1, len(subpuncte), 2):
            numar = subpuncte[index]
            text_subpunct = subpuncte[index + 1].strip() if index + 1 < len(subpuncte) else ""
            if context is not None and text_subpunct:
                text_subpunct = f"{context}\n{text_subpunct}"
            if len(text_subpunct) >= LUNGIME_MINIMA_CHUNK:
                rezultat.append({"articol": f"{chunk['articol']}({numar})", "text": text_subpunct})
    return rezultat, titluri_contopite


def _normalizeaza_pentru_acoperire(text: str) -> str:
    """Elimină marcajele de articol și (N), colapsează spațiile — ca linia brută
    din document să fie comparabilă cu textul concatenat al chunk-urilor, care nu
    mai conține marcajul consumat ca delimitator."""
    text = _PATTERN_MARCAJ_ANEXA_INTERN_ACOPERIRE.sub("", text)
    text = _PATTERN_MARCAJ_ARTICOL_ACOPERIRE.sub("", text)
    text = _PATTERN_SUBPUNCT_PARANTEZA_ACOPERIRE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def acoperire_text_brut(text: str, chunkuri: list[dict[str, str]]) -> float:
    """Procentul de rânduri brute (≥50 caractere, fără antete MO) regăsite
    (normalizat) în textul concatenat al chunk-urilor. Folosită atât de testul
    de regresie `test_acoperirea_continutului_brut_ramane_peste_prag`, cât și
    de poarta automată de reimport (D24) — aceeași metrică în ambele locuri.

    Textul brut e trecut prin `corecteaza_substituiri_pdf` (Runda R22) înainte
    de comparație, ca substituirile din PDF-uri precum I7 să nu producă
    diferențe false între linia brută și textul deja normalizat al
    chunk-urilor."""
    text = corecteaza_substituiri_pdf(text)
    text_concatenat = _normalizeaza_pentru_acoperire(" ".join(chunk["text"] for chunk in chunkuri))
    total = 0
    gasite = 0
    for linie in text.split("\n"):
        linie = linie.strip()
        if len(linie) < LUNGIME_MINIMA_LINIE_ACOPERIRE or "MONITORUL OFICIAL" in linie:
            continue
        total += 1
        prefix = _normalizeaza_pentru_acoperire(linie)[:45]
        if prefix and prefix in text_concatenat:
            gasite += 1
    return gasite / total if total else 1.0


def _aplica_limita_caractere(chunkuri: list[dict[str, str]], limita: int = MAX_CHUNK_CHARS) -> list[dict[str, str]]:
    rezultat = []
    for chunk in chunkuri:
        text = chunk["text"]
        while len(text) > limita:
            boundary = max(text.rfind("\n", 0, limita + 1), text.rfind(" ", 0, limita + 1))
            if boundary < LUNGIME_MINIMA_CHUNK:
                boundary = limita
            # D27: marcajul de proveniență nu se taie în două — tăietura se mută înaintea lui;
            # bucata anterioară primește apoi marcajul la nivel de articol (propagare).
            for marcaj in PATTERN_MARCAJ_PROVENIENTA.finditer(text, 0, boundary + LUNGIME_MAXIMA_MARCAJ):
                if marcaj.start() < boundary < marcaj.end() and marcaj.start() >= LUNGIME_MINIMA_CHUNK:
                    boundary = marcaj.start()
            piece, text = text[:boundary].strip(), text[boundary:].strip()
            if piece:
                rezultat.append({"articol": chunk["articol"], "text": piece})
        if text:
            rezultat.append({"articol": chunk["articol"], "text": text})
    return rezultat


# D27: sufixul de alineat pus de `_aplica_split_secundar` ("3.3.1.(1)" -> baza "3.3.1.").
# Bucățile cu aceeași bază aparțin aceluiași articol, indiferent care dintre ele conține
# efectiv marcajul de proveniență pus de consolidare pe textul afectat.
_PATTERN_SUFIX_ALINEAT_PROVENIENTA = re.compile(r"(?:\(\d+\))+$")


def _baza_articol_provenienta(articol: str) -> str:
    return _PATTERN_SUFIX_ALINEAT_PROVENIENTA.sub("", articol)


def _adjectiv_provenienta(tip: str) -> str:
    """Normalizează tipul capturat de `PATTERN_MARCAJ_PROVENIENTA` la adjectivul folosit
    în marcajul la nivel de articol: „Text modificat”/„modificat” -> „modificat”,
    „Abrogat”/„abrogat” -> „abrogat” etc."""
    return tip.rsplit(" ", 1)[-1].lower()


def _propaga_marcaj_provenienta(chunkuri: list[dict[str, str]]) -> list[dict[str, str]]:
    """Pas final (D27): dacă o bucată a unui articol conține un marcaj de proveniență,
    toate celelalte bucăți ale aceluiași articol de bază primesc, pe un rând propriu,
    marcajul echivalent la nivel de articol, exceptând bucățile care au deja un marcaj
    pentru același ordin/tip. Articolele fără niciun marcaj rămân neatinse (text identic
    byte cu byte)."""
    indici_pe_articol: dict[str, list[int]] = {}
    for index, chunk in enumerate(chunkuri):
        indici_pe_articol.setdefault(_baza_articol_provenienta(chunk["articol"]), []).append(index)

    rezultat = [dict(chunk) for chunk in chunkuri]
    for indici in indici_pe_articol.values():
        marcaje_distincte: list[tuple[str, str]] = []
        chei_vazute: set[tuple[str, str]] = set()
        for index in indici:
            for potrivire in PATTERN_MARCAJ_PROVENIENTA.finditer(chunkuri[index]["text"]):
                cheie = (_adjectiv_provenienta(potrivire.group(1)), potrivire.group(2))
                if cheie not in chei_vazute:
                    chei_vazute.add(cheie)
                    marcaje_distincte.append(cheie)
        if not marcaje_distincte:
            continue
        for index in indici:
            text = rezultat[index]["text"]
            chei_prezente = {
                (_adjectiv_provenienta(potrivire.group(1)), potrivire.group(2))
                for potrivire in PATTERN_MARCAJ_PROVENIENTA.finditer(text)
            }
            adaugari = [
                f"[Articol cu text {adjectiv} {rest}]"
                for adjectiv, rest in marcaje_distincte
                if (adjectiv, rest) not in chei_prezente
            ]
            if adaugari:
                rezultat[index]["text"] = text + "\n" + "\n".join(adaugari)
    return _respecta_limita_cu_marcaje(rezultat)


def _respecta_limita_cu_marcaje(chunkuri: list[dict[str, str]]) -> list[dict[str, str]]:
    """Bucățile care depășesc limita după adăugarea marcajelor la nivel de articol se
    împart din nou, astfel încât fiecare parte, cu marcajele ei, să rămână ≤ MAX_CHUNK_CHARS."""
    rezultat = []
    for chunk in chunkuri:
        if len(chunk["text"]) <= MAX_CHUNK_CHARS:
            rezultat.append(chunk)
            continue
        text = chunk["text"]
        adaugate = [m.group(0) for m in PATTERN_MARCAJ_PROVENIENTA.finditer(text) if m.group(0).startswith("[Articol cu text ")]
        corp = text
        for marcaj in adaugate:
            corp = corp.replace("\n" + marcaj, "")
        sufix = "\n" + "\n".join(adaugate)
        for bucata in _aplica_limita_caractere([{"articol": chunk["articol"], "text": corp}], MAX_CHUNK_CHARS - len(sufix)):
            text_bucata = bucata["text"]
            if not any(marcaj in text_bucata for marcaj in adaugate):
                text_bucata += sufix
            rezultat.append({"articol": chunk["articol"], "text": text_bucata})
    return rezultat
