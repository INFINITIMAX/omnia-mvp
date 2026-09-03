"""Corecteaza textul extras din formule culese cu fonturi CID fara /ToUnicode.

Problema: documente_noi/i9_2022/source.pdf (si, punctual, p118_1_2025) contin
formule culese cu fontul CambriaMath, incorporat ca subset CIDFontType0 sub
codificare Identity-H, FARA dictionar /ToUnicode. PyMuPDF (page.get_text())
recurge atunci la un euristic intern care produce code point-uri fara nicio
legatura cu sensul real al glifului (silabe etiopiene, litere siriace, cifre
tamile, semne malayalam etc.).

Solutia: sub Identity-H + CIDFontType0, codul CID scris in fluxul de continut
al paginii este chiar GID-ul din fontul original (verificat empiric: CID 1848
se rezolva, in fontul Windows "Cambria Math", la U+1D449 MATHEMATICAL ITALIC
CAPITAL V — exact litera "V" din formula de debit V-punct a art. 14.6).
page.get_texttrace() expune acest GID adevarat per caracter (spre deosebire de
get_text(), care foloseste euristicul stricat). Avem asadar, per span scris cu
fontul CambriaMath:
  - GID-urile reale ale caracterelor (din get_texttrace())
  - un dreptunghi (bbox) exact al span-ului

Folosim acest bbox pentru a extrage, prin page.get_text("text", clip=bbox),
exact acelasi text "stricat" pe care l-ar produce extragerea normala pentru
acea zona (aceeasi cale de rezolutie ca page.get_text() pe intreaga pagina),
apoi il inlocuim cu textul corect calculat din tabela de glife.

Tabela GID -> caracter e in font_maps/cambria_math_glyph_map.json (vezi
font_maps/README.md pentru metoda completa de constructie si verificare).

Indici si exponenti: Word (si deci fontul) marcheaza subscript/superscript
doar prin marime + pozitie verticala mai mica/mai mare fata de linia de baza,
nu printr-un caracter distinct. Ii detectam comparand marimea (size) fiecarui
span CambriaMath cu marimea "normala" cea mai recenta de pe pagina si pozitia
verticala a originii primului caracter fata de linia de baza normala, apoi ii
marcam explicit in text ca "_{...}" (indice) sau "^{...}" (exponent) - o
conventie stil LaTeX, usor de citit de un inginer fara sa deschida PDF-ul.

Glifele care nu exista in tabela (niciun cmap, nicio identificare vizuala) NU
sunt niciodata ghicite: sunt marcate explicit ca "<?glifNNNN?>" in text, ca sa
fie usor de gasit si de raportat.

Normalizare stilistica (bold/italic -> litera simpla): caracterele rezolvate
prin cmap sunt adesea din blocul Unicode "Mathematical Alphanumeric Symbols"
(U+1D400-U+1D7FF) - fontul Cambria Math foloseste acele code point-uri pentru
variantele stilizate (italic, bold, bold-italic etc.) ale literelor si
cifrelor, in loc sa aplice pur si simplu stilul vizual peste litera obisnuita.
Aceste code point-uri NU sunt continut matematic, sunt doar stilizare: 'V'
italic-bold ramane semantic litera 'V'. Daca le-am lasa asa:
  - fonturile aplicatiei (subset latin/latin-ext) nu le acopera -> patrate goale
  - o cautare exacta dupa 'V' nu s-ar potrivi cu '𝑽'
  - embeddingurile Voyage tokenizeaza prost caractere atat de rare
De aceea, la incarcarea tabelei, orice caracter din acest bloc e trecut prin
unicodedata.normalize('NFKC', ...) — verificat manual ca toate cele 996 de
code point-uri asignate din bloc (litere latine si grecesti in orice stil:
italic, bold, bold-italic, script, fraktur, bold-fraktur, double-struck,
sans-serif, sans-serif-bold, monospace, plus toate cifrele stilizate) se
descompun curat la EXACT un singur caracter simplu in afara blocului (e.g.
U+1D449 '𝑉' -> 'V', U+1D706 '𝜆' -> 'λ', U+1D7CE '𝟎' -> '0'). Simbolurile
matematice reale (√, ×, ≤, ≥, punctul suprapus combinat U+0307, literele
grecesti simple neaflate in acest bloc) NU sunt afectate: nu au descompunere
de compatibilitate, deci normalize() le lasa neschimbate.

In plus, un mic set de caractere din blocul "Letterlike Symbols"
(U+2100-214F) sunt folosite tot ca litera stilizata, nu ca simbol distinct —
ex. U+210E PLANCK CONSTANT, folosit in art. 12.1 ca litera italica "h"
generica pentru pierderea de sarcina locala, nu ca simbolul fizic al
constantei lui Planck. Spre deosebire de blocul Mathematical Alphanumeric
Symbols (unde ORICE caracter e garantat doar stilizare), acest bloc contine
si simboluri cu sens propriu real (ex. ℂ/ℝ/ℕ/ℤ/ℚ/ℙ pentru multimi de numere,
abrevieri ca ℅/℀), deci NU normalizam tot blocul orbeste — doar codpoint-urile
verificate individual, adaugate explicit in ALFANUMERICE_STILIZATE_SUPLIMENTAR
mai jos, dupa ce s-a confirmat ca in document apar ca litera stilizata, nu ca
simbol cu sens propriu.
"""

import json
import re
import unicodedata
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parent
CALE_TABELA_CAMBRIA_MATH = ROOT / "font_maps" / "cambria_math_glyph_map.json"

# substring cautat in numele fontului span-ului (numele complet are de obicei
# un prefix de subset, ex. "HBOCMB+CambriaMath")
FONTURI_TINTA = ("CambriaMath",)

# sub acest raport fata de marimea "normala" cea mai recenta, un span e
# considerat indice/exponent, nu text de baza
PRAG_RAPORT_SUBSCRIPT = 0.85

# toleranta (in puncte) pentru a decide daca originea unui span mai mic e sub
# sau deasupra liniei de baza a textului normal anterior
TOLERANTA_BASELINE = 0.5

# distanta verticala (in puncte) sub care un span dict e considerat "pe
# aceeasi linie" cu un candidat get_texttrace(), la asocierea prin centru de
# bbox - suficient de mare cat sa acopere un indice/exponent normal (cateva
# puncte fata de linia de baza), dar mai mic decat distanta tipica intre doua
# randuri diferite ale unei formule (10-14pt la marimile folosite in document)
PRAG_Y_ACEEASI_LINIE = 6.0

# spatiu lipit de o paranteza deschisa/inchisa - artefact de formatare din
# documentul sursa (ex. numerotarea ecuatiei "(14.2 )"), fara sens semantic
_CURATA_SPATII_LANGA_PARANTEZE = re.compile(r"([(\[]) +| +([)\]])")

# Mathematical Alphanumeric Symbols: intervalul Unicode folosit de fonturi
# matematice pentru variante STILIZATE (italic/bold/script/fraktur/
# double-struck/sans-serif/monospace) ale literelor si cifrelor. Nu e continut
# semantic, doar stil vizual - il normalizam la litera/cifra simpla.
INCEPUT_BLOC_MATH_ALFANUMERIC = 0x1D400
SFARSIT_BLOC_MATH_ALFANUMERIC = 0x1D7FF

# Letterlike Symbols (U+2100-214F): bloc mixt - unele codpoint-uri sunt doar
# litere stilizate, altele sunt simboluri cu sens propriu (ℂ/ℝ/ℕ/ℤ/ℚ/ℙ etc.).
# Normalizam DOAR pe cele verificate individual, aparute efectiv in tabela cu
# rol de litera stilizata, nu blocul intreg.
ALFANUMERICE_STILIZATE_SUPLIMENTAR = frozenset(
    {
        0x210E,  # PLANCK CONSTANT - folosit in art. 12.1 ca litera italica "h" generica
    }
)


def _normalizeaza_stil(caracter):
    """Reduce o litera/cifra stilizata (Mathematical Alphanumeric Symbols, sau
    un codpoint din ALFANUMERICE_STILIZATE_SUPLIMENTAR) la varianta ei simpla
    prin NFKC. Simbolurile matematice reale (radical, operatori, litere
    grecesti simple, diacritice combinate, ℂ/ℝ/ℕ etc.) nu sunt vizate, deci
    raman neatinse."""
    if caracter and len(caracter) == 1:
        cod = ord(caracter)
        e_stilizat = (
            INCEPUT_BLOC_MATH_ALFANUMERIC <= cod <= SFARSIT_BLOC_MATH_ALFANUMERIC
            or cod in ALFANUMERICE_STILIZATE_SUPLIMENTAR
        )
        if e_stilizat:
            return unicodedata.normalize("NFKC", caracter)
    return caracter


def incarca_tabela(cale=CALE_TABELA_CAMBRIA_MATH):
    """Incarca tabela GID -> caracter, cu cheile convertite la int si
    caracterele stilizate (bold/italic/etc.) normalizate la litera simpla."""
    with open(cale, encoding="utf-8") as fisier:
        date = json.load(fisier)
    tabela = {}
    for gid, intrare in date["entries"].items():
        intrare = dict(intrare)
        intrare["char"] = _normalizeaza_stil(intrare.get("char"))
        tabela[int(gid)] = intrare
    return tabela


def _este_font_tinta(nume_font):
    return any(tinta in nume_font for tinta in FONTURI_TINTA)


def _gid_la_caracter(tabela, gid):
    """Traduce un GID in caracterul real. Nu ghiceste niciodata: daca GID-ul
    nu e in tabela (sau e marcat explicit 'unresolved'), intoarce un marcaj
    vizibil, usor de gasit prin cautare."""
    intrare = tabela.get(gid)
    if intrare is None or intrare.get("char") is None:
        return "<?glif%d?>" % gid
    return intrare["char"]


def _stil_pentru_span(marime, origine_y, referinta):
    """Actualizeaza starea `referinta` si intoarce None (text normal),
    'sub' (indice) sau 'sup' (exponent) pentru span-ul curent."""
    if referinta["marime"] is None or marime >= referinta["marime"] * PRAG_RAPORT_SUBSCRIPT:
        referinta["marime"] = marime
        referinta["baseline_y"] = origine_y
        return None
    if referinta["baseline_y"] is None:
        return None
    if origine_y > referinta["baseline_y"] + TOLERANTA_BASELINE:
        return "sub"
    if origine_y < referinta["baseline_y"] - TOLERANTA_BASELINE:
        return "sup"
    return None


def _centru(bbox):
    return ((bbox.x0 + bbox.x1) / 2.0, (bbox.y0 + bbox.y1) / 2.0)


def _distanta2(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def _distanta2_la_bbox(punct, bbox):
    """Distanta (la patrat) de la un punct la cel mai apropiat punct DIN
    bbox (0 daca punctul e deja in interior). Spre deosebire de distanta
    centru-la-centru, asta nu penalizeaza un candidat doar pentru ca e "lat"
    (bbox mult mai mare decat un vecin mic) — un span dict al carui centru
    cade in interiorul unui candidat larg (ex. o coada lunga de formula:
    spatii + unitate + numar de ecuatie) trebuie sa mearga la ACEL candidat,
    nu la un vecin mic doar pentru ca centrele lor intamplator sunt apropiate."""
    px, py = punct
    cx = min(max(px, bbox.x0), bbox.x1)
    cy = min(max(py, bbox.y0), bbox.y1)
    return (px - cx) ** 2 + (py - cy) ** 2


def invata_proxy_glife(document, tabela):
    """Scaneaza tot documentul si invata, per GID, ce caracter "stricat"
    produce page.get_text("dict") pentru el, din orice potrivire de
    incredere gasita (acelasi mecanism de asociere ca in
    construieste_inlocuiri_pagina) a carei lungime totala corespunde exact
    numarului de GID-uri al candidatului - in acel caz stim, pozitie cu
    pozitie, ce caracter stricat corespunde fiecarui GID.

    De ce e nevoie de asta: am verificat ca page.get_text("dict") elimina
    sistematic anumite glife cu latime zero din propria segmentare — pe o
    pagina cu 8 aparitii ale literei "V" (gid 1848) din notatia V-punct, dict
    raporteaza span propriu pentru UNA singura; celelalte 7 nu exista deloc ca
    span in dict, desi page.get_text() simplu chiar le contine ca text (deci
    nu e o eroare de potrivire de-a noastra, e o inconsistenta intre cele doua
    cai de extragere ale PyMuPDF). Fallback-ul stricat pare insa determinist
    per GID (verificat pe zeci de aparitii in acest document: gid 1848 produce
    mereu U+0738, gid 4662 mereu U+1236) — folosim acest fapt empiric ca sa
    reconstruim needle-ul si pentru span-urile pe care dict le omite, in loc
    sa le lasam needit. Daca acelasi GID produce caractere DIFERITE in doua
    locuri (contrazice ipoteza de determinism), il scoatem din tabela — nu
    ghicim intre variante contradictorii."""
    proxy = {}
    contradictorii = set()

    for pagina in document:
        candidati = []  # (gids, bbox)
        for span in pagina.get_texttrace():
            if not _este_font_tinta(span.get("font", "")):
                continue
            caractere = span.get("chars") or []
            if caractere:
                candidati.append(([c[1] for c in caractere], fitz.Rect(span["bbox"])))
        if not candidati:
            continue

        grupuri = [[] for _ in candidati]
        for block in pagina.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                for span_dict in line.get("spans", []):
                    if not _este_font_tinta(span_dict.get("font", "")):
                        continue
                    text = span_dict.get("text", "")
                    if not text:
                        continue
                    bbox_dict = fitz.Rect(span_dict["bbox"])
                    centru_dict = _centru(bbox_dict)
                    index_apropiat = min(
                        range(len(candidati)),
                        key=lambda i: (
                            _distanta2_la_bbox(centru_dict, candidati[i][1]),
                            _distanta2(centru_dict, _centru(candidati[i][1])),
                        ),
                    )
                    grupuri[index_apropiat].append((bbox_dict.x0, text))

        for (gids, _bbox), grup in zip(candidati, grupuri):
            # invatam DOAR dintr-un singur span dict contiguu (nu din mai
            # multe span-uri concatenate): am verificat un caz real in care
            # lungimea totala concatenata coincidea cu numarul de GID-uri
            # (10==10), dar corespondenta pozitie-cu-pozitie era decalata cu
            # unu (un span dict lipsea undeva la mijloc, compensat de un alt
            # span mai lung in alta parte) - ar fi invatat gid 1848 -> 'ሶ' in
            # loc de 'ܸ', contrazicand toate celelalte observatii corecte. Un
            # singur span dict, cu lungime exacta, nu are aceasta ambiguitate.
            if len(grup) != 1:
                continue
            text_vechi = grup[0][1]
            if len(text_vechi) != len(gids):
                continue
            for gid, caracter in zip(gids, text_vechi):
                if gid in contradictorii:
                    continue
                existent = proxy.get(gid)
                if existent is not None and existent != caracter:
                    contradictorii.add(gid)
                    del proxy[gid]
                    continue
                proxy[gid] = caracter

    return proxy


def construieste_inlocuiri_pagina(pagina, tabela, proxy=None):
    """Intoarce o lista de (text_vechi, text_corectat), in ordinea aparitiei
    pe pagina, pentru toate span-urile scrise cu un font din FONTURI_TINTA.

    De ce nu folosim page.get_text(clip=bbox-ul din get_texttrace()): am
    verificat empiric ca get_texttrace() si page.get_text() calculeaza bbox-ul
    unui glif dupa metrici DIFERITE (nu doar rotunjiri) — un clip de 0.1pt
    latime, plasat exact la originea unui indice, tot "prinde" litera de baza
    vecina prin bbox-ul ei din get_texttrace(), in timp ce insusi indicele nu
    e prins deloc. Asadar bbox-ul din get_texttrace() nu e o baza de incredere
    pentru clip(). In schimb, page.get_text("dict") isi segmenteaza singur
    textul in span-uri (uneori exact 1 caracter, cand glifele se suprapun
    optic) cu bbox-uri consistente cu propria lui geometrie interna — exact
    ce va aparea, literal, in page.get_text() simplu.

    Asociem fiecare span dict de fontul tinta cu span-ul get_texttrace() al
    carui centru de bbox e cel mai apropiat (nu ordinea de parcurgere, care
    poate diferi intre cele doua API-uri pe randuri cu reordonare bidi).
    Span-urile dict asociate aceluiasi span get_texttrace() sunt apoi
    concatenate in ordinea lor pe orizontala (x0) ca sa formeze text_vechi."""
    referinta = {"marime": None, "baseline_y": None}

    candidati = []
    for span in pagina.get_texttrace():
        nume_font = span.get("font", "")
        if not _este_font_tinta(nume_font):
            continue
        caractere = span.get("chars") or []
        if not caractere:
            continue

        marime = span.get("size")
        origine_y = caractere[0][2][1]
        stil = _stil_pentru_span(marime, origine_y, referinta)

        gids = [caracter[1] for caracter in caractere]
        text_corectat = "".join(_gid_la_caracter(tabela, gid) for gid in gids)
        # spatii parazite lipite de o paranteza/paranteza dreapta - artefact de
        # formatare din documentul sursa (ex. "(14.2 )" in loc de "(14.2)"),
        # nu continut semantic
        text_corectat = _CURATA_SPATII_LANGA_PARANTEZE.sub(r"\1\2", text_corectat)
        if not text_corectat.strip():
            # span compus doar din spatii: nu are sens semantic de corectat
            continue
        if stil == "sub":
            text_corectat = "_{%s}" % text_corectat
        elif stil == "sup":
            text_corectat = "^{%s}" % text_corectat

        bbox = fitz.Rect(span["bbox"])
        candidati.append({
            "bbox": bbox,
            "centru": _centru(bbox),
            "text_corectat": text_corectat,
            "gids": gids,
        })

    if not candidati:
        return []

    # span-urile "vazute" de page.get_text("dict") pentru fontul tinta -
    # aceasta e chiar segmentarea pe care o va folosi page.get_text() simplu
    grupuri = [[] for _ in candidati]
    for block in pagina.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            for span_dict in line.get("spans", []):
                if not _este_font_tinta(span_dict.get("font", "")):
                    continue
                text = span_dict.get("text", "")
                if not text:
                    continue
                bbox_dict = fitz.Rect(span_dict["bbox"])
                centru_dict = _centru(bbox_dict)
                # candidatii "pe aceeasi linie" (Y apropiat) - fara aceasta
                # limita, un span dict de pe o alta formula (alta linie, alt
                # rand al unei formule stivuite) poate fi din greseala mai
                # aproape ca centru de un candidat gresit decat de al lui
                # propriu, mai ales cand candidatul e un indice minuscul.
                pe_aceeasi_linie = [
                    i
                    for i, cand in enumerate(candidati)
                    if abs(centru_dict[1] - cand["centru"][1]) <= PRAG_Y_ACEEASI_LINIE
                ]
                grup_de_cautat = pe_aceeasi_linie or range(len(candidati))
                # distanta la bbox (nu centru-la-centru): un span dict lat
                # (ex. spatii + unitate + numar de ecuatie) al carui centru
                # cade in interiorul unui candidat lat trebuie sa mearga la
                # ACEL candidat, nu la un vecin mic doar pt. ca centrele sunt
                # intamplator apropiate (vezi _distanta2_la_bbox). Cand
                # punctul cade in interiorul mai multor bbox-uri suprapuse
                # (distanta 0 la toate - glife optic suprapuse), departajam
                # prin distanta centru-la-centru.
                index_apropiat = min(
                    grup_de_cautat,
                    key=lambda i: (
                        _distanta2_la_bbox(centru_dict, candidati[i]["bbox"]),
                        _distanta2(centru_dict, candidati[i]["centru"]),
                    ),
                )
                grupuri[index_apropiat].append((bbox_dict.x0, text))

    inlocuiri = []
    for candidat, grup in zip(candidati, grupuri):
        grup.sort(key=lambda item: item[0])
        text_vechi = "".join(text for _, text in grup)
        text_corectat = candidat["text_corectat"]

        if len(text_vechi) < len(candidat["gids"]):
            # dict a dat MAI PUTINE caractere decat GID-uri are candidatul -
            # cel putin unul dintre glife a fost omis din segmentarea lui
            # (vezi invata_proxy_glife: pe o pagina cu 8 aparitii ale unei
            # litere, dict raporteaza span propriu pentru UNA singura).
            # Textul dat de dict e deci incomplet, nu doar imprecis - il
            # inlocuim integral cu reconstructia din proxy, GID cu GID, DOAR
            # daca avem un proxy cunoscut pentru FIECARE GID al candidatului
            # (altfel am amesteca text real din dict cu litere ghicite).
            #
            # Cand dict da MAI MULTE caractere decat GID-uri (poate combina
            # span-uri vecine sau normaliza spatii), il folosim asa cum e: nu
            # e o omisiune, iar empiric functioneaza pentru marea majoritate
            # a cazurilor - proxy-ul ar fi mai putin precis aici, nu mai mult.
            if proxy is not None:
                proxy_chars = [proxy.get(gid) for gid in candidat["gids"]]
                if all(ch is not None for ch in proxy_chars):
                    text_vechi = "".join(proxy_chars)
                elif not text_vechi:
                    continue
            elif not text_vechi:
                continue

        if not text_vechi or text_vechi == text_corectat:
            continue
        inlocuiri.append((text_vechi, text_corectat))

    return inlocuiri


def _regex_pentru_needle(text_vechi):
    """Compileaza text_vechi intr-un regex care accepta spatiu alb suplimentar
    sau lipsa intre caracterele consecutive.

    De ce: page.get_text() pe toata pagina si page.get_text(clip=...) pe
    bbox-ul strans al unui singur span pot linia-riza diferit exact aceeasi
    secventa de caractere — de exemplu, un simbol de baza urmat imediat de un
    accent combinat (litera + punct suprapus) poate primi un "\\n" intre ele
    in textul intregii pagini quando formeaza inceputul unui rand nou dupa o
    intrerupere de linie, desi clip()-ul acelui span singur nu insereaza
    niciun separator. Needle-ul literal nu s-ar mai gasi in text si corectia
    ar fi sarita silentios. Tratam orice pozitie dintre doua caractere ale
    needle-ului ca putand contine spatiu alb suplimentar (sau deloc)."""
    bucati = [re.escape(text_vechi[0])] if text_vechi else []
    for caracter in text_vechi[1:]:
        bucati.append(r"\s*")
        bucati.append(re.escape(caracter))
    return re.compile("".join(bucati))


def aplica_inlocuiri(text, inlocuiri):
    """Inlocuieste fiecare (text_vechi -> text_corectat) cu prima aparitie a
    lui text_vechi in text care nu se suprapune cu o inlocuire deja facuta.

    Cautarea e tolerantа la spatiu alb suplimentar/lipsa intre caracterele
    needle-ului (vezi _regex_pentru_needle) si nu presupune ca get_texttrace()
    enumera span-urile in exact aceeasi ordine in care page.get_text() le
    adauga in textul simplu (layout-uri pe mai multe coloane sau segmente
    bidi pot reordona); de aceea cautam fiecare needle independent, nu cu un
    cursor care avanseaza mereu inainte.

    Procesam needle-urile de la cel mai lung la cel mai scurt (nu in ordinea
    din pagina): un needle scurt si generic (ex. un singur indice "i", care
    apare identic de zeci de ori pe pagina) poate "fura" prima aparitie
    libera inainte ca un needle mai lung si mult mai specific (ex. un indice
    intreg "izolație", 8 caractere, care incepe cu acelasi caracter "i") sa
    apuce sa-si gaseasca propria pozitie — needle-ul lung ramane apoi fara
    nicio aparitie libera si e sarit, desi textul lui exista, neatins, in
    pagina. Reasamblarea finala e oricum in ordinea pozitiei din text (vezi
    sortarea lui `gasite` mai jos), deci ordinea de procesare aici nu
    afecteaza rezultatul in alt fel decat prin care needle "castiga" o
    suprapunere posibila."""
    ocupate = []  # (start, end) deja folosite pentru o inlocuire
    gasite = []  # (start, end, text_corectat)
    for text_vechi, text_corectat in sorted(inlocuiri, key=lambda item: -len(item[0])):
        model = _regex_pentru_needle(text_vechi)
        cautare_de_la = 0
        loc = None
        while True:
            potrivire = model.search(text, cautare_de_la)
            if potrivire is None:
                break
            idx, capat = potrivire.start(), potrivire.end()
            se_suprapune = any(idx < u_capat and capat > u_start for u_start, u_capat in ocupate)
            if not se_suprapune:
                loc = (idx, capat)
                break
            cautare_de_la = idx + 1
        if loc is None:
            # nicio aparitie libera a textului vechi: nu stricam restul
            # textului, doar sarim peste aceasta corectie.
            continue
        ocupate.append(loc)
        gasite.append((loc[0], loc[1], text_corectat))

    gasite.sort(key=lambda item: item[0])
    bucati = []
    pos = 0
    for start, capat, text_corectat in gasite:
        bucati.append(text[pos:start])
        bucati.append(text_corectat)
        pos = capat
    bucati.append(text[pos:])
    return "".join(bucati)


def corecteaza_text_pagina(pagina, tabela, proxy=None):
    """Textul complet al paginii (page.get_text()), cu formulele CambriaMath
    corectate folosind tabela de glife. `proxy` (optional) e tabela GID ->
    caracter stricat invatata pe tot documentul cu invata_proxy_glife() -
    folosita ca rezerva pentru span-urile pe care page.get_text("dict") le
    omite din propria segmentare (vezi invata_proxy_glife)."""
    text = pagina.get_text()
    inlocuiri = construieste_inlocuiri_pagina(pagina, tabela, proxy=proxy)
    return aplica_inlocuiri(text, inlocuiri)
