"""Consolidarea normativelor de bază cu ordinele de modificare (Runda 26/B).

Fără I/O implicit (în afara CLI-ului de mai jos), fără rețea, fără DB. Segmentează
Art. I al unui ordin de modificare în itemi numerotați consecutiv, verifică că un
manifest JSON scris de om declară exact aceleași operații, localizează fiecare
țintă în textul de bază al normativului (fail-closed: exact o potrivire), aplică
înlocuirile/inserările/abrogările de la sfârșit spre început și adaugă, după
fiecare fragment modificat/introdus/abrogat, marcajul de proveniență din
`R26-C-coder.md` (regex de referință):

    \\[(Text modificat|Text introdus|Abrogat) prin Ordinul nr\\. [0-9.]+/\\d{4},
    publicat în Monitorul Oficial nr\\. \\d+ din \\d{2}\\.\\d{2}\\.\\d{4}\\]

Reutilizează câteva constante publice din `chunking_core` (antete MO, numere de
pagină, linii de cuprins) ca să nu dubleze acea logică — nu îl modifică.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from dataclasses import dataclass

from chunking_core import PATTERN_ANTET_MO, PATTERN_LINIE_CUPRINS, PATTERN_NUMAR_PAGINA

MARCAJ_MODIFICAT = "[Text modificat prin Ordinul nr. {ordin}, publicat în Monitorul Oficial nr. {mo} din {data}]"
MARCAJ_INTRODUS = "[Text introdus prin Ordinul nr. {ordin}, publicat în Monitorul Oficial nr. {mo} din {data}]"
MARCAJ_ABROGAT = "[Abrogat prin Ordinul nr. {ordin}, publicat în Monitorul Oficial nr. {mo} din {data}]"

PATTERN_NUMARARE_MARCAJE = re.compile(
    r"\[(?:Text modificat|Text introdus|Abrogat) prin Ordinul nr\. [0-9.]+/\d{4}, "
    r"publicat în Monitorul Oficial nr\. \d+ din \d{2}\.\d{2}\.\d{4}\]"
)

PATTERN_START_ART_I = re.compile(r"Art(?:\.|icolul)\s*I\b")
PATTERN_START_ART_II = re.compile(r"Art(?:\.|icolul)\s*II\b")
PATTERN_CUPRINS_MARKER = re.compile(r"cuprins\s*:", re.IGNORECASE)
PATTERN_ABROGA_PROPOZITIE = re.compile(r"se abrog[ăa]\s*\.")
# Runda 2: item „La tabelele X—Y, sintagma «...» se înlocuiește cu sintagma «...».” —
# nu are nici „cuprins:”, nici „se abrogă.”; X/Y pot fi rupte pe rând de extragerea din MO,
# de-aici DOTALL (spațiile interne se normalizează oricum la aplicare).
PATTERN_SINTAGMA = re.compile(
    r"sintagm[ăa]\s*„(?P<veche>.+?)”\s*se înlocuie[șs]te\s*cu sintagm[ăa]\s*„(?P<noua>.+?)”\s*\.",
    re.DOTALL,
)
PATTERN_LINIE_DOAR_PUNCTE = re.compile(r"^[ \t]*\.{2,}[ \t]*$")

# Următorul început de punct/titlu de capitol/anexă — bornează întinderea unui
# punct localizat în textul de bază (nu doar imediat-următorul nivel al lui).
PATTERN_URMATOR_MARCAJ = re.compile(
    r"(?m)^[ \t]*(?:\d+(?:\.\d+){1,4}\.?(?=[ \t]|$)|ANEXA\b|\d{1,2}\.[ \t]+[A-ZĂÂÎȘȚŞŢ])"
)
# Runda 2: fără a cere spațiu după `)` — „3.8.2.5 (1)Sunetul...” nu are spațiu între
# paranteză și cuvântul următor; doar poziția de start a următoarei subunități contează,
# ca să bornăm întinderea celei curente.
PATTERN_URMATOARE_SUBUNITATE = re.compile(r"(?m)^[ \t]*(?:\(\d+\)|[a-z]\))")

TIPURI_CUVINTE_CHEIE = {
    # „cuprins” e mereu prezent (segmentarea îl folosește ca delimitator instrucțiune/text_nou),
    # dar 6025 formulează exclusiv „va avea următorul cuprins”, fără „se modifică” — acceptăm
    # oricare dintre cele două formulări ca dovadă a tipului de operație.
    "inlocuieste_punct": (r"se modific[ăa]", r"cuprins"),
    "inlocuieste_subunitate": (r"alineat", r"liter[ăa]", r"partea introductiv[ăa]", r"cuprins"),
    "insereaza_dupa": (r"se introduce",),
    "abroga_punct": (r"se abrog[ăa]",),
    "abroga_subunitate": (r"se abrog[ăa]",),
    "renumeroteaza_inlocuieste": (r"se renumeroteaz[ăa]",),
    "inlocuieste_bloc": (r"tabelul", r"anexa", r"observa[țt]i"),
    "inlocuieste_sintagma_in_bloc": (r"sintagm[ăa]", r"se înlocuie[șs]te"),
}


@dataclass
class ItemOrdin:
    nr: int
    instructiune: str
    text_nou: str  # brut, netăiat pe marcaje, necurățat
    sintagma_veche: str | None = None
    sintagma_noua: str | None = None


# ---------------------------------------------------------------------------
# Segmentarea ordinului
# ---------------------------------------------------------------------------

def segmenteaza_ordin(text: str) -> list[ItemOrdin]:
    """Segmentează itemii 1..N din Art. I, până la Art. II."""
    start_match = PATTERN_START_ART_I.search(text)
    if start_match is None:
        raise ValueError("Art. I nu a fost găsit în ordin")
    end_match = PATTERN_START_ART_II.search(text, start_match.end())
    if end_match is None:
        raise ValueError("Art. II nu a fost găsit în ordin")
    corp = text[start_match.end():end_match.start()]

    itemi: list[ItemOrdin] = []
    cursor = 0
    nr = 1
    while True:
        pattern_curent = re.compile(rf"(?m)^[ \t]*{nr}\.(?=\s)")
        marcaj = pattern_curent.search(corp, cursor)
        if marcaj is None:
            break
        continut_start = marcaj.end()
        while continut_start < len(corp) and corp[continut_start] in " \t\n\r":
            continut_start += 1
        pattern_urmator = re.compile(rf"(?m)^[ \t]*{nr + 1}\.(?=\s)")
        urmator = pattern_urmator.search(corp, continut_start)
        continut_end = urmator.start() if urmator else len(corp)
        bloc = corp[continut_start:continut_end]
        itemi.append(_parseaza_item(nr, bloc))
        cursor = continut_end
        nr += 1

    if not itemi:
        raise ValueError("nu s-a găsit niciun item numerotat (1., 2., ...) în Art. I")
    return itemi


def _parseaza_item(nr: int, bloc: str) -> ItemOrdin:
    cuprins_match = PATTERN_CUPRINS_MARKER.search(bloc)
    if cuprins_match is not None:
        instructiune = bloc[:cuprins_match.end()]
        text_nou_brut = bloc[cuprins_match.end():]
        return ItemOrdin(nr=nr, instructiune=instructiune.strip(), text_nou=text_nou_brut)

    abroga_match = PATTERN_ABROGA_PROPOZITIE.search(bloc)
    if abroga_match is not None:
        instructiune = bloc[:abroga_match.end()]
        return ItemOrdin(nr=nr, instructiune=instructiune.strip(), text_nou="")

    sintagma_match = PATTERN_SINTAGMA.search(bloc)
    if sintagma_match is not None:
        instructiune = bloc[:sintagma_match.end()]
        veche = _normalizeaza_spatii(sintagma_match.group("veche"))
        noua = _normalizeaza_spatii(sintagma_match.group("noua"))
        return ItemOrdin(
            nr=nr, instructiune=instructiune.strip(), text_nou="",
            sintagma_veche=veche, sintagma_noua=noua,
        )

    raise ValueError(
        f"itemul {nr}: nu conține nici „cuprins:”, nici propoziția „se abrogă.”, "
        f"nici tiparul „sintagma «...» se înlocuiește cu sintagma «...».”"
    )


# ---------------------------------------------------------------------------
# Curățarea și tăierea pe marcaje a textului nou din ordin
# ---------------------------------------------------------------------------

def _curata_segment(segment: str) -> str:
    linii_pastrate = []
    for linie in segment.split("\n"):
        if PATTERN_ANTET_MO.match(linie):
            continue
        stripped = linie.strip()
        if PATTERN_NUMAR_PAGINA.match(stripped):
            continue
        if PATTERN_LINIE_DOAR_PUNCTE.match(linie):
            continue
        linii_pastrate.append(linie)
    text = "\n".join(linii_pastrate).strip()
    if text.startswith("„"):
        text = text[1:].lstrip()
    if text.endswith("”"):
        text = text[:-1].rstrip()
    return text


def _imparte_pe_marcaje(text_nou_brut: str, marcaje: list[str]) -> list[str]:
    pozitii = []
    for marcaj in marcaje:
        pattern = re.compile(r"(?m)^[ \t]*" + re.escape(marcaj))
        potriviri = list(pattern.finditer(text_nou_brut))
        if len(potriviri) != 1:
            raise ValueError(
                f"marcajul de tăiere {marcaj!r} are {len(potriviri)} potriviri în text_nou (necesar exact 1)"
            )
        pozitii.append(potriviri[0].start())
    segmente = []
    for index, start in enumerate(pozitii):
        sfarsit = pozitii[index + 1] if index + 1 < len(pozitii) else len(text_nou_brut)
        segmente.append(_curata_segment(text_nou_brut[start:sfarsit]))
    return segmente


def _segmenteaza_text_nou(item: ItemOrdin, tinte: list[dict], marcaj_implicit) -> list[str]:
    if len(tinte) == 1:
        return [_curata_segment(item.text_nou)]
    marcaje = [tinta.get("marcaj_text_nou") or marcaj_implicit(tinta) for tinta in tinte]
    return _imparte_pe_marcaje(item.text_nou, marcaje)


# ---------------------------------------------------------------------------
# Localizarea țintelor în textul de bază
# ---------------------------------------------------------------------------

def _linia(text: str, pozitie: int) -> str:
    inceput = text.rfind("\n", 0, pozitie) + 1
    sfarsit = text.find("\n", pozitie)
    if sfarsit == -1:
        sfarsit = len(text)
    return text[inceput:sfarsit]


def _localizeaza_punct(baza: str, punct: str, aparitie: int | None = None) -> tuple[int, int]:
    """`aparitie` (Runda 3, 1-based) alege a n-a potrivire când sursa MO are numărul de
    punct duplicat real (ex. 23.51 apare de două ori în P 118/2) — permis numai când
    există efectiv mai multe potriviri; altfel (o singură potrivire, dar `aparitie` dat)
    e eroare, ca să nu ascundem tacit o schimbare de sursă."""
    pattern = re.compile(r"(?m)^[ \t]*" + re.escape(punct) + r"(?:\.|[ \t])")
    potriviri = [
        m for m in pattern.finditer(baza)
        if not PATTERN_LINIE_CUPRINS.search(_linia(baza, m.start()))
    ]
    if aparitie is not None:
        if len(potriviri) < 2:
            raise ValueError(
                f"punctul {punct!r} are {len(potriviri)} potriviri; 'aparitie' e permisă doar când "
                f"există mai multe potriviri (nu ascundem o potrivire unică sub un număr de apariție)"
            )
        if not 1 <= aparitie <= len(potriviri):
            raise ValueError(f"'aparitie' {aparitie} invalidă pentru punctul {punct!r} ({len(potriviri)} potriviri)")
        ales = potriviri[aparitie - 1]
    else:
        if len(potriviri) != 1:
            raise ValueError(f"punctul {punct!r} are {len(potriviri)} potriviri în bază (necesar exact 1)")
        ales = potriviri[0]
    start = ales.start()
    urmator = PATTERN_URMATOR_MARCAJ.search(baza, ales.end())
    sfarsit = urmator.start() if urmator else len(baza)
    return start, sfarsit


def _numara_punct(baza: str, punct: str) -> int:
    pattern = re.compile(r"(?m)^[ \t]*" + re.escape(punct) + r"(?:\.|[ \t])")
    return sum(
        1 for m in pattern.finditer(baza)
        if not PATTERN_LINIE_CUPRINS.search(_linia(baza, m.start()))
    )


def _cauta_marcaj_dupa_prefix(regiune: str, prefix_regex: str, marcaj_regex: str) -> tuple[int, int] | None:
    """Runda 2: prima subunitate a unui punct/alineat poate sta pe chiar rândul
    numărului/etichetei-părinte, imediat după el, cu sau fără spațiu înainte de textul
    propriu-zis (ex. „3.8.2.5 (1)Sunetul...”, „5.3.5 (1)Cablurile...”). `prefix_regex`
    descrie exact acel prefix (numărul punctului/alineatului + delimitatorul lui);
    dacă regiunea nu începe cu el, sau marcajul nu urmează imediat, nu e o potrivire."""
    prefix_match = re.match(prefix_regex, regiune)
    if prefix_match is None:
        return None
    rest = regiune[prefix_match.end():]
    marcaj_match = re.match(marcaj_regex, rest)
    if marcaj_match is None:
        return None
    return prefix_match.end() + marcaj_match.start(), prefix_match.end() + marcaj_match.end()


# Runda 3: întinderea unui ALINEAT se oprește doar la următorul „(n)” sau la finalul
# punctului — literele (a), b), c)…) sunt în interiorul lui, nu îl închid (ex. P 118/3
# 5.3.5 alin. (2): „(2) Aceste cabluri sunt cele care asigură: a)... b)... c)... d)...”).
PATTERN_URMATOR_ALINEAT = re.compile(r"(?m)^[ \t]*\(\d+\)")


def _localizeaza_marcaj_in_regiune(
    regiune: str, marcaj_regex: str, prefix_regex: str | None = None,
    urmator_pattern: re.Pattern[str] | None = None,
) -> tuple[int, int]:
    pattern = re.compile(r"(?m)^[ \t]*" + marcaj_regex)
    candidati = [(m.start(), m.end()) for m in pattern.finditer(regiune)]
    if prefix_regex is not None:
        gasit = _cauta_marcaj_dupa_prefix(regiune, prefix_regex, marcaj_regex)
        if gasit is not None:
            candidati.append(gasit)
    if len(candidati) != 1:
        raise ValueError(f"marcajul /{marcaj_regex}/ are {len(candidati)} potriviri în regiune (necesar exact 1)")
    start, sfarsit_marcaj = candidati[0]
    urmator_pattern = urmator_pattern or PATTERN_URMATOARE_SUBUNITATE
    urmator = urmator_pattern.search(regiune, sfarsit_marcaj)
    sfarsit = urmator.start() if urmator else len(regiune)
    return start, sfarsit


def _localizeaza_subunitate(
    baza: str, punct: str, alineat: str | None = None, litera: str | None = None,
    introductiva: bool = False,
) -> tuple[int, int]:
    p_start, p_sfarsit = _localizeaza_punct(baza, punct)
    regiune = baza[p_start:p_sfarsit]
    prefix_punct = r"[ \t]*" + re.escape(punct) + r"(?:\.|[ \t])[ \t]*"

    if introductiva:
        urmator = PATTERN_URMATOARE_SUBUNITATE.search(regiune)
        sfarsit = urmator.start() if urmator else len(regiune)
        return p_start, p_start + sfarsit

    if alineat is not None and litera is not None:
        a_start, a_sfarsit = _localizeaza_marcaj_in_regiune(
            regiune, rf"\({re.escape(alineat)}\)", prefix_punct, urmator_pattern=PATTERN_URMATOR_ALINEAT,
        )
        sub_regiune = regiune[a_start:a_sfarsit]
        prefix_alineat = r"[ \t]*\(" + re.escape(alineat) + r"\)[ \t]*"
        l_start, l_sfarsit = _localizeaza_marcaj_in_regiune(sub_regiune, rf"{re.escape(litera)}\)", prefix_alineat)
        return p_start + a_start + l_start, p_start + a_start + l_sfarsit

    if alineat is not None:
        start, sfarsit = _localizeaza_marcaj_in_regiune(
            regiune, rf"\({re.escape(alineat)}\)", prefix_punct, urmator_pattern=PATTERN_URMATOR_ALINEAT,
        )
        return p_start + start, p_start + sfarsit

    if litera is not None:
        start, sfarsit = _localizeaza_marcaj_in_regiune(regiune, rf"{re.escape(litera)}\)", prefix_punct)
        return p_start + start, p_start + sfarsit

    raise ValueError("subunitatea nu specifică alineat/litera/introductiva")


def _gaseste_unic_start_linie(baza: str, ancora: str) -> int:
    pattern = re.compile(r"(?m)^[ \t]*" + re.escape(ancora))
    potriviri = list(pattern.finditer(baza))
    if len(potriviri) != 1:
        raise ValueError(f"ancora {ancora!r} are {len(potriviri)} potriviri în bază (necesar exact 1)")
    return potriviri[0].start()


def _localizeaza_bloc(baza: str, ancora_inceput: str, ancora_sfarsit: str) -> tuple[int, int]:
    start = _gaseste_unic_start_linie(baza, ancora_inceput)
    sfarsit = _gaseste_unic_start_linie(baza, ancora_sfarsit)
    if sfarsit <= start:
        raise ValueError(f"ancora de sfârșit {ancora_sfarsit!r} apare înaintea celei de început {ancora_inceput!r}")
    return start, sfarsit


# ---------------------------------------------------------------------------
# Validarea manifestului față de segmentare
# ---------------------------------------------------------------------------

def _tuplu_numeric(numar: str) -> tuple[int, ...]:
    return tuple(int(parte) for parte in numar.split("."))


def _instructiune_contine_punctul(instructiune: str, punct: str) -> bool:
    if punct in instructiune:
        return True
    # Ordinul citează uneori punctul-părinte în text, deși ținta reală e singurul lui
    # copil direct din baza.txt (ex. „punctul 3.7.13” în ordin, dar conținutul e sub
    # „3.7.13.1” în P 118/3) — acceptăm și această relație, nu doar egalitatea literală.
    tokeni = re.findall(r"\d+(?:\.\d+)*", instructiune)
    if any(punct.startswith(token + ".") for token in tokeni):
        return True
    for capat_a, capat_b in re.findall(r"(\d+(?:\.\d+)*)\s*[—–-]\s*(\d+(?:\.\d+)*)", instructiune):
        tup_a, tup_b = _tuplu_numeric(capat_a), _tuplu_numeric(capat_b)
        try:
            tup_p = _tuplu_numeric(punct)
        except ValueError:
            continue
        if len(tup_a) == len(tup_b) == len(tup_p) and tup_a <= tup_p <= tup_b:
            return True
    return False


def _valideaza_operatie(item: ItemOrdin, operatie: dict) -> None:
    tip = operatie["tip"]
    cuvinte = TIPURI_CUVINTE_CHEIE.get(tip)
    if cuvinte is None:
        raise ValueError(f"tip de operație necunoscut: {tip!r}")
    if not any(re.search(cuvant, item.instructiune, re.IGNORECASE) for cuvant in cuvinte):
        raise ValueError(f"itemul {item.nr}: instrucțiunea nu conține cuvântul-cheie pentru {tip!r}")
    for tinta in operatie.get("tinte", []):
        punct = tinta.get("punct") or tinta.get("punct_vechi")
        if punct and not _instructiune_contine_punctul(item.instructiune, punct):
            raise ValueError(f"itemul {item.nr}: instrucțiunea nu conține punctul {punct!r}")
        # Runda 3: „aparitie” (număr de punct duplicat real în sursă) cere justificare
        # scrisă în manifest — nu alegem tacit o apariție fără o explicație verificabilă.
        if "aparitie" in tinta and not tinta.get("justificare"):
            raise ValueError(f"itemul {item.nr}: ținta cu 'aparitie' trebuie să aibă și 'justificare'")


# ---------------------------------------------------------------------------
# Aplicarea operațiilor
# ---------------------------------------------------------------------------

def _marcaj(sablon: str, ordin_info: dict) -> str:
    return sablon.format(ordin=ordin_info["ordin"], mo=ordin_info["monitorul_oficial"], data=ordin_info["data_mo"])


def _normalizeaza_spatii(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _localizeaza_ancora_insereaza(baza: str, tinta: dict) -> tuple[int, bool]:
    """Poziția (în bază) după care se inserează o subunitate nouă + dacă alineatul-ancoră
    a fost implicit (Runda 3: un punct fără nicio etichetă „(n)” tratează tot conținutul
    lui ca alineatul (1) — inserarea „după alineatul (1)” cade atunci la finalul punctului)."""
    punct, dupa_alineat, dupa_litera = tinta["punct"], tinta.get("dupa_alineat"), tinta.get("dupa_litera")
    if dupa_alineat is not None and dupa_litera is None:
        p_start, p_sfarsit = _localizeaza_punct(baza, punct)
        are_etichete = re.search(r"(?m)^[ \t]*\(\d+\)", baza[p_start:p_sfarsit]) is not None
        if not are_etichete and dupa_alineat == "1":
            return p_sfarsit, True
    _, sfarsit_ancora = _localizeaza_subunitate(baza, punct, alineat=dupa_alineat, litera=dupa_litera)
    return sfarsit_ancora, False


def _adauga_aparitie(intrare: dict, tinta: dict) -> None:
    if "aparitie" in tinta:
        intrare["aparitie"] = tinta["aparitie"]
        intrare["justificare"] = tinta["justificare"]


def _proceseaza_operatie(baza: str, item: ItemOrdin, operatie: dict, ordin_info: dict) -> list[dict]:
    tip = operatie["tip"]
    tinte = operatie.get("tinte", [])
    rezultate = []

    if tip == "inlocuieste_punct":
        segmente = _segmenteaza_text_nou(item, tinte, lambda t: f"{t['punct']}.")
        for tinta, segment in zip(tinte, segmente):
            start, sfarsit = _localizeaza_punct(baza, tinta["punct"])
            text_final = segment + "\n" + _marcaj(MARCAJ_MODIFICAT, ordin_info)
            rezultate.append(_intrare(item.nr, tip, f"punct {tinta['punct']}", start, sfarsit, baza, text_final, segment))

    elif tip == "inlocuieste_subunitate":
        def marcaj_implicit(tinta):
            if tinta.get("introductiva"):
                return tinta["punct"]
            if tinta.get("litera") and tinta.get("alineat"):
                return f"{tinta['litera']})"
            if tinta.get("alineat"):
                return f"({tinta['alineat']})"
            return f"{tinta['litera']})"

        segmente = _segmenteaza_text_nou(item, tinte, marcaj_implicit)
        for tinta, segment in zip(tinte, segmente):
            start, sfarsit = _localizeaza_subunitate(
                baza, tinta["punct"], alineat=tinta.get("alineat"), litera=tinta.get("litera"),
                introductiva=bool(tinta.get("introductiva")),
            )
            eticheta = _eticheta_subunitate(tinta)
            text_final = segment + "\n" + _marcaj(MARCAJ_MODIFICAT, ordin_info)
            rezultate.append(_intrare(item.nr, tip, f"{eticheta} al punctului {tinta['punct']}", start, sfarsit, baza, text_final, segment))

    elif tip == "abroga_punct":
        for tinta in tinte:
            punct = tinta["punct"]
            start, sfarsit = _localizeaza_punct(baza, punct, aparitie=tinta.get("aparitie"))
            text_final = f"{punct}. Abrogat.\n" + _marcaj(MARCAJ_ABROGAT, ordin_info)
            intrare = _intrare(item.nr, tip, f"punct {punct}", start, sfarsit, baza, text_final, None)
            _adauga_aparitie(intrare, tinta)
            rezultate.append(intrare)

    elif tip == "abroga_subunitate":
        for tinta in tinte:
            start, sfarsit = _localizeaza_subunitate(
                baza, tinta["punct"], alineat=tinta.get("alineat"), litera=tinta.get("litera"),
            )
            eticheta = _eticheta_subunitate(tinta)
            eticheta_text = f"({tinta['alineat']})" if tinta.get("alineat") else f"{tinta['litera']})"
            text_final = f"{eticheta_text} Abrogat.\n" + _marcaj(MARCAJ_ABROGAT, ordin_info)
            rezultate.append(_intrare(item.nr, tip, f"{eticheta} al punctului {tinta['punct']}", start, sfarsit, baza, text_final, None))

    elif tip == "insereaza_dupa":
        segmente = _segmenteaza_text_nou(item, tinte, lambda t: t.get("marcaj_text_nou", ""))
        for tinta, segment in zip(tinte, segmente):
            sfarsit_ancora, alineat_implicit = _localizeaza_ancora_insereaza(baza, tinta)
            text_final = "\n" + segment + "\n" + _marcaj(MARCAJ_INTRODUS, ordin_info)
            intrare = _intrare(
                item.nr, tip, f"nouă subunitate a punctului {tinta['punct']}",
                sfarsit_ancora, sfarsit_ancora, baza, text_final, segment,
            )
            if alineat_implicit:
                intrare["alineat_implicit"] = True
            rezultate.append(intrare)

    elif tip == "renumeroteaza_inlocuieste":
        for tinta in tinte:
            punct_vechi, punct_nou = tinta["punct_vechi"], tinta["punct_nou"]
            if _numara_punct(baza, punct_nou) != 0:
                raise ValueError(f"itemul {item.nr}: numărul nou {punct_nou!r} există deja în bază")
            start, sfarsit = _localizeaza_punct(baza, punct_vechi, aparitie=tinta.get("aparitie"))
            segment = _curata_segment(item.text_nou)
            text_final = segment + "\n" + _marcaj(MARCAJ_MODIFICAT, ordin_info)
            intrare = _intrare(
                item.nr, tip, f"punct {punct_vechi} → {punct_nou}", start, sfarsit, baza, text_final, segment,
            )
            _adauga_aparitie(intrare, tinta)
            rezultate.append(intrare)

    elif tip == "inlocuieste_bloc":
        for tinta in tinte:
            start, sfarsit = _localizeaza_bloc(baza, tinta["ancora_inceput"], tinta["ancora_sfarsit"])
            segment = _curata_segment(item.text_nou)
            text_final = segment + "\n" + _marcaj(MARCAJ_MODIFICAT, ordin_info)
            rezultate.append(_intrare(
                item.nr, tip, f"bloc {tinta['ancora_inceput']!r}…{tinta['ancora_sfarsit']!r}",
                start, sfarsit, baza, text_final, segment,
            ))

    elif tip == "inlocuieste_sintagma_in_bloc":
        # Runda 2: sintagmă înlocuită doar în interiorul unui bloc ancorat (ex. tabelele
        # 7.10—7.12), nu în tot documentul. Ca la înlocuirile globale: fără marcaj per
        # apariție, dar numărul de înlocuiri se raportează; ≥1 obligatoriu (fail-closed).
        for tinta in tinte:
            start, sfarsit = _localizeaza_bloc(baza, tinta["ancora_inceput"], tinta["ancora_sfarsit"])
            regiune = baza[start:sfarsit]
            regiune_noua, numar = _aplica_inlocuire_globala(regiune, item.sintagma_veche, item.sintagma_noua)
            if numar < 1:
                raise ValueError(
                    f"itemul {item.nr}: sintagma {item.sintagma_veche!r} nu a fost găsită în blocul "
                    f"{tinta['ancora_inceput']!r}…{tinta['ancora_sfarsit']!r}"
                )
            intrare = _intrare(
                item.nr, tip, f"bloc {tinta['ancora_inceput']!r}…{tinta['ancora_sfarsit']!r}",
                start, sfarsit, baza, regiune_noua, None,
            )
            intrare["numar_inlocuiri"] = numar
            intrare["_fara_marcaj"] = True
            rezultate.append(intrare)

    else:
        raise ValueError(f"tip de operație necunoscut: {tip!r}")

    return rezultate


def _eticheta_subunitate(tinta: dict) -> str:
    if tinta.get("introductiva"):
        return "partea introductivă"
    if tinta.get("litera") and tinta.get("alineat"):
        return f"litera {tinta['litera']}) a alineatului ({tinta['alineat']})"
    if tinta.get("alineat"):
        return f"alineatul ({tinta['alineat']})"
    return f"litera {tinta['litera']})"


def _intrare(nr, tip, tinta_descriere, start, sfarsit, baza, text_final, text_nou_segment):
    text_vechi = baza[start:sfarsit]
    return {
        "nr": nr,
        "tip": tip,
        "tinta": tinta_descriere,
        "status": "aplicat",
        "lungime_veche": len(text_vechi),
        "lungime_noua": len(text_final),
        "_start": start,
        "_sfarsit": sfarsit,
        "_text_final": text_final,
        "_text_vechi_norm": _normalizeaza_spatii(text_vechi) if text_vechi.strip() else "",
        "_text_nou_norm": _normalizeaza_spatii(text_nou_segment) if text_nou_segment else "",
        "_fara_marcaj": False,
    }


def _aplica_inlocuire_globala(text: str, veche: str, noua: str) -> tuple[str, int]:
    tokeni = [re.escape(cuvant) for cuvant in veche.split()]
    pattern = re.compile(r"\s+".join(tokeni))
    rezultat, numar = pattern.subn(noua, text)
    return rezultat, numar


def aplica_operatii(baza: str, itemi: list[ItemOrdin], manifest: dict) -> tuple[str, list[dict]]:
    ordin_info = {
        "ordin": manifest["ordin"],
        "monitorul_oficial": manifest["monitorul_oficial"],
        "data_mo": manifest["data_mo"],
    }
    itemi_dict = {item.nr: item for item in itemi}
    nrs_ordin = set(itemi_dict)
    nrs_manifest = {operatie["nr"] for operatie in manifest["operatii"]}
    if nrs_ordin != nrs_manifest:
        raise ValueError(
            f"manifestul (nr. {sorted(nrs_manifest)}) nu coincide cu segmentarea ordinului "
            f"(nr. {sorted(nrs_ordin)})"
        )

    intrari: list[dict] = []
    for operatie in sorted(manifest["operatii"], key=lambda o: o["nr"]):
        item = itemi_dict[operatie["nr"]]
        if operatie.get("manual"):
            intrari.append({
                "nr": operatie["nr"], "tip": operatie.get("tip", "manual"), "tinta": operatie.get("nota", ""),
                "status": "manual", "lungime_veche": None, "lungime_noua": None,
            })
            continue
        _valideaza_operatie(item, operatie)
        intrari.extend(_proceseaza_operatie(baza, item, operatie, ordin_info))

    tinte_ordonate = sorted(
        (i for i in intrari if "_start" in i), key=lambda i: i["_start"],
    )
    for index in range(1, len(tinte_ordonate)):
        if tinte_ordonate[index]["_start"] < tinte_ordonate[index - 1]["_sfarsit"]:
            raise ValueError("ținte suprapuse la aplicare")

    rezultat = baza
    for intrare in sorted(tinte_ordonate, key=lambda i: i["_start"], reverse=True):
        text_final = intrare["_text_final"]
        rest = rezultat[intrare["_sfarsit"]:]
        # Marcajul rămâne pe rând propriu: fără `\n`, începutul punctului următor s-ar lipi de el
        # și chunker-ul nu l-ar mai recunoaște ca articol nou.
        if rest and not text_final.endswith("\n") and not rest.startswith("\n"):
            text_final += "\n"
        rezultat = rezultat[:intrare["_start"]] + text_final + rest

    raport = []
    for intrare in intrari:
        public = {k: v for k, v in intrare.items() if not k.startswith("_")}
        raport.append(public)

    for sintagma in manifest.get("inlocuiri_globale", []):
        rezultat, numar = _aplica_inlocuire_globala(rezultat, sintagma["veche"], sintagma["noua"])
        raport.append({
            "nr": None, "tip": "inlocuire_globala", "tinta": f"{sintagma['veche']!r} → {sintagma['noua']!r}",
            "status": "aplicat" if numar else "nicio_potrivire",
            "lungime_veche": None, "lungime_noua": None, "numar_inlocuiri": numar,
        })

    _verifica_final(rezultat, tinte_ordonate, manifest.get("inlocuiri_globale", []))
    return rezultat, raport


def _verifica_final(rezultat: str, tinte_ordonate: list[dict], inlocuiri_globale: list[dict] = ()) -> None:
    normalizat_rezultat = _normalizeaza_spatii(rezultat)

    def _dupa_inlocuiri_globale(text: str) -> str:
        # Înlocuirea globală din ordin (ex. Art. II din 6.025/2018) se aplică în tot
        # normativul, inclusiv în textul nou adus de celelalte operații ale aceluiași ordin.
        for sintagma in inlocuiri_globale:
            text, _ = _aplica_inlocuire_globala(text, sintagma["veche"], sintagma["noua"])
        return text

    # Runda 2: operațiile „fără marcaj” (ex. inlocuieste_sintagma_in_bloc) nu adaugă
    # niciun marcaj de proveniență — nu intră în numărătoarea așteptată.
    tinte_cu_marcaj = [i for i in tinte_ordonate if not i.get("_fara_marcaj")]
    numar_marcaje = len(PATTERN_NUMARARE_MARCAJE.findall(rezultat))
    if numar_marcaje != len(tinte_cu_marcaj):
        raise ValueError(
            f"numărul de marcaje din rezultat ({numar_marcaje}) diferă de numărul de operații "
            f"nemodificate global și cu marcaj ({len(tinte_cu_marcaj)})"
        )

    for intrare in tinte_ordonate:
        text_nou_norm = _dupa_inlocuiri_globale(intrare["_text_nou_norm"])
        if text_nou_norm and text_nou_norm not in normalizat_rezultat:
            raise ValueError(f"itemul {intrare['nr']} ({intrare['tinta']}): text_nou nu apare literal în rezultat")
        text_vechi_norm = _dupa_inlocuiri_globale(intrare["_text_vechi_norm"])
        if text_vechi_norm and text_vechi_norm not in text_nou_norm and text_vechi_norm in normalizat_rezultat:
            raise ValueError(f"itemul {intrare['nr']} ({intrare['tinta']}): textul vechi mai există în rezultat")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def consolideaza(baza: str, ordin: str, manifest: dict) -> tuple[str, list[dict]]:
    itemi = segmenteaza_ordin(ordin)
    return aplica_operatii(baza, itemi, manifest)


def _scrie_atomic(cale: str, continut: str) -> None:
    director = os.path.dirname(cale) or "."
    descriptor, cale_temporara = tempfile.mkstemp(dir=director, prefix=".tmp-consolidare-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as fisier:
            fisier.write(continut)
        os.replace(cale_temporara, cale)
    except BaseException:
        if os.path.exists(cale_temporara):
            os.remove(cale_temporara)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baza", required=True)
    parser.add_argument("--ordin", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--iesire", required=True)
    parser.add_argument("--raport", required=True)
    argumente = parser.parse_args()

    with open(argumente.baza, encoding="utf-8") as fisier:
        baza = fisier.read()
    with open(argumente.ordin, encoding="utf-8") as fisier:
        ordin = fisier.read()
    with open(argumente.manifest, encoding="utf-8") as fisier:
        manifest = json.load(fisier)

    rezultat, raport = consolideaza(baza, ordin, manifest)

    _scrie_atomic(argumente.iesire, rezultat)
    _scrie_atomic(argumente.raport, json.dumps(raport, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
