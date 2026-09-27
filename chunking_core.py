"""Chunking determinist unificat pentru ingestia normativelor RO.

Aceeași logică servește atât importul real (`populare_db.py`), cât și
preflight-ul local (`manual_ingestion_preflight.py`): fără I/O, fără DB, fără
rețea. Curăță antetele de pagină ale Monitorului Oficial și cuprinsul,
tratează titlurile de secțiune ca simplu context pentru articolele-copil
directe și deduplichează variantele, numărând tot ce elimină.
"""

from __future__ import annotations

import re

# Regex-ul pentru structura articolelor din normativele deja validate. „?"
# opțional gestionează actele modificatoare, unde numărul articolului din
# normativul modificat stă imediat după ghilimeaua de deschidere a citatului
# (ex: „1.2. Domeniul de aplicare...”), nu la început de rând ca în normativele
# de bază. Ghilimeaua nu intră în grupul capturat, deci nu strică normalizarea.
PATTERN_ARTICOL = re.compile(
    r"\n\s*„?\s*(\d+\.\d+\.\s*\([A-Za-z]\)\.\s*(?:[IVXLl]\.|\d+\.)?(?:\d+\.)?|"
    r"ANEXA\s+\d+\.\d+\.|\d+\.\d+\.(?:\d+\.){0,4})"
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

LUNGIME_MINIMA_CHUNK = 15
LUNGIME_PENTRU_SPLIT_SECUNDAR = 2000
MAX_CHUNK_CHARS = 1000
PROCENT_MAXIM_CAUTARE_CUPRINS = 0.20
DISTANTA_MAXIMA_ANTET = 3
NUMAR_MINIM_INTRARI_CUPRINS = 5
DISTANTA_MAXIMA_INTRARE_CUPRINS = 3
LUNGIME_MAXIMA_TITLU = 200
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
    continut, antete_eliminate = _elimina_antete_mo(text)
    continut = _elimina_colofon_mo(continut)
    continut = _elimina_cuprins(continut)
    continut = _elimina_titluri_capitol_roman(continut)

    segmente = _extrage_segmente(continut)
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
        existent = chunkuri_dupa_articol.get(articol)
        if existent is None:
            chunkuri_dupa_articol[articol] = {"articol": articol, "text": text_segment}
        elif len(text_segment) > len(existent["text"]):
            chunkuri_dupa_articol[articol] = {"articol": articol, "text": text_segment}
            duplicate_eliminate += 1
        else:
            duplicate_eliminate += 1

    chunkuri, titluri_contopite_din_split = _aplica_split_secundar(
        list(chunkuri_dupa_articol.values()), articole_cu_context_parinte
    )
    titluri_contopite += titluri_contopite_din_split
    chunkuri = _aplica_limita_caractere(chunkuri)

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


def _este_articol_normalizabil(articol: str) -> bool:
    normalizat = _PATTERN_SPATIERE_ARTICOL.sub("", articol).lower().rstrip(".")
    return bool(_PATTERN_ARTICOL_NORMALIZAT.fullmatch(normalizat))


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
# Cuvintele care, la finalul ultimului rând nevid dinaintea marcajului, arată că
# numărul de pe rândul următor e continuarea unei trimiteri rupte de extragerea PDF
# ("...prevederile Art.\n2.1.3.5. (1) alin. a);"), nu un articol nou. Comparate cu
# rândul anterior integral, minuscule — acoperă și "Art."/"Articolul" cu majusculă.
_CUVINTE_TRIMITERE_RUPTA = ("art.", "articolul", "alin.", "pct.", "lit.", "conform")


def _linia_anterioara_se_termina_cu_trimitere(sursa: str, pozitie_marcaj: int) -> bool:
    """Caută înapoi, sărind rândurile goale, ultimul rând nevid dinaintea marcajului."""
    capat = pozitie_marcaj
    while capat >= 0:
        inceput = sursa.rfind("\n", 0, capat) + 1
        linie = sursa[inceput:capat].strip()
        if linie:
            cuvant = linie.lower()
            return any(cuvant.endswith(sufix) for sufix in _CUVINTE_TRIMITERE_RUPTA)
        if inceput == 0:
            return False
        capat = inceput - 1
    return False


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
    sunt niciodată un început valid de articol.
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
    return not _PATTERN_CARACTER_VALID_DUPA_NUMAR.match(rest)


def _extrage_segmente(continut: str) -> list[dict[str, object]]:
    """Parsează articolele în ordinea din text, cu numărul brut și cel cu sufix.

    Combină marcajul numeric obișnuit, marcajul „Art. N.N....” (P 118/1) și
    marcajul fără punct pe ultima componentă (I7/I5/NP 057). Când două marcaje
    pornesc din exact aceeași poziție (ex. varianta cu punct prinde doar
    `3.1.5.`, cea fără punct prinde `3.1.5.7` întreg), câștigă potrivirea cu
    numărul mai lung — cealaltă e doar un prefix parțial al aceleiași cifre.
    """
    sursa = "\n" + continut
    toate = sorted(
        (
            *PATTERN_ARTICOL.finditer(sursa),
            *PATTERN_ARTICOL_ART.finditer(sursa),
            *PATTERN_ARTICOL_FARA_PUNCT.finditer(sursa),
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

    potriviri = [
        potrivire
        for potrivire in candidate
        if not _este_data_zi_luna_an(potrivire, sursa) and not _este_referinta_rupta(potrivire, sursa)
    ]
    segmente = []
    for index, potrivire in enumerate(potriviri):
        articol_baza = _baza_articol(potrivire)
        articol = articol_baza
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
                "text": text_segment,
                "este_titlu": False,
                "are_context_parinte": False,
            }
        )
    return segmente


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


def _aplica_limita_caractere(chunkuri: list[dict[str, str]]) -> list[dict[str, str]]:
    rezultat = []
    for chunk in chunkuri:
        text = chunk["text"]
        while len(text) > MAX_CHUNK_CHARS:
            boundary = max(text.rfind("\n", 0, MAX_CHUNK_CHARS + 1), text.rfind(" ", 0, MAX_CHUNK_CHARS + 1))
            if boundary < LUNGIME_MINIMA_CHUNK:
                boundary = MAX_CHUNK_CHARS
            piece, text = text[:boundary].strip(), text[boundary:].strip()
            if piece:
                rezultat.append({"articol": chunk["articol"], "text": piece})
        if text:
            rezultat.append({"articol": chunk["articol"], "text": text})
    return rezultat
