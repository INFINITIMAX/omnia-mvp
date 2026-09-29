"""Extrage text din PDF-urile "MO bis" (P 118/2-2013, P 118/3-2015).

Problema: fonturile Type1 subset din aceste PDF-uri folosesc /Encoding cu
/Differences care numesc glifele /gNNN = GID din fontul Windows original, iar
/ToUnicode e inutil pentru ele. PyMuPDF pierde ă/ș/ț/Ă/Ș/Ț, iar pdfplumber
raportează acele caractere ca text "(cid:N)", unde N e codul din /Differences.

Solutia: tabela font_maps/mo_bis_glyph_map.json (generata offline de planner
din fonturile Windows cu fontTools) mapeaza direct GID -> caracter, per font.
Pentru fiecare PDF, harta_coduri() parcurge /Differences din fiecare font
(citite cu PyMuPDF) si construieste cod -> caracter prin GID -> tabela; apoi
extrage_text() foloseste acea harta pentru a inlocui fiecare "(cid:N)" produs
de pdfplumber cu caracterul corect.
"""

import argparse
import collections
import json
import re
from pathlib import Path

import fitz
import pdfplumber
from pdfplumber.utils import extract_text

from diacritice import normalizeaza_diacritice

ROOT_PROIECT = Path(__file__).resolve().parent
CALE_TABELA_MO_BIS = ROOT_PROIECT / "font_maps" / "mo_bis_glyph_map.json"

_PATTERN_SUBSET = re.compile(r"^[A-Z]{6}\+")
_PATTERN_ENCODING = re.compile(r"/Encoding\s+(\d+) 0 R")
_PATTERN_DIFFERENCES = re.compile(r"/Differences\s*\[(.*?)\]", re.S)
_PATTERN_GLIF = re.compile(r"/g(\d+)")
_PATTERN_CID = re.compile(r"\(cid:(\d+)\)")
_PATTERN_PAGINA_LIPITA_DE_ANTET = re.compile(
    r"(?m)^(\d{1,4})[ \t]+(MONITORUL OFICIAL AL ROMÂNIEI, PARTEA I, Nr\. .+)$"
)


def incarca_tabela(cale=CALE_TABELA_MO_BIS):
    """Incarca tabela font (fara prefix de subset) -> {GID: caracter}."""
    with open(cale, encoding="utf-8") as fisier:
        date = json.load(fisier)
    return {
        font: {int(gid): caracter for gid, caracter in intrari.items()}
        for font, intrari in date["fonturi"].items()
    }


def harta_coduri(pdf_path, tabela):
    """Pentru fiecare font din PDF (nume complet, cu prefixul de subset),
    construieste cod /Differences -> caracter, prin /gNNN -> tabela.

    Un numar din /Differences seteaza codul curent; fiecare nume de glifa
    care urmeaza foloseste acel cod si il incrementeaza (semantica PDF)."""
    harta = {}
    document = fitz.open(pdf_path)
    try:
        for pagina in document:
            for font in pagina.get_fonts(full=True):
                nume_complet = font[3]
                if nume_complet in harta:
                    continue
                obiect = document.xref_object(font[0])
                referinta_encoding = _PATTERN_ENCODING.search(obiect)
                encoding = (
                    document.xref_object(int(referinta_encoding.group(1)))
                    if referinta_encoding
                    else obiect
                )
                differences = _PATTERN_DIFFERENCES.search(encoding)
                coduri = {}
                if differences:
                    nume_baza = _PATTERN_SUBSET.sub("", nume_complet)
                    tabela_font = tabela.get(nume_baza, {})
                    cod = None
                    for token in differences.group(1).split():
                        if token.isdigit():
                            cod = int(token)
                            continue
                        glif = _PATTERN_GLIF.fullmatch(token)
                        if glif and cod is not None:
                            gid = int(glif.group(1))
                            if gid in tabela_font:
                                coduri[cod] = tabela_font[gid]
                        if cod is not None:
                            cod += 1
                harta[nume_complet] = coduri
    finally:
        document.close()
    return harta


def extrage_text(pdf_path, tabela=None):
    """Extrage textul din PDF, rezolvand fiecare "(cid:N)" prin harta de fonturi.

    Intoarce (text, raport), cu raport = {"nerezolvate": {"font:cod": n},
    "pagini": n}. Caracterele nerezolvate sunt eliminate din text, nu ghicite.
    Textul final trece prin diacritice.normalizeaza_diacritice."""
    if tabela is None:
        tabela = incarca_tabela()
    harta = harta_coduri(pdf_path, tabela)
    nerezolvate = collections.Counter()
    pagini_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for pagina in pdf.pages:
            caractere = []
            for caracter in pagina.chars:
                potrivire = _PATTERN_CID.fullmatch(caracter["text"])
                if potrivire is None:
                    caractere.append(caracter)
                    continue
                cod = int(potrivire.group(1))
                inlocuire = harta.get(caracter["fontname"], {}).get(cod)
                if inlocuire is None:
                    nerezolvate[f"{caracter['fontname']}:{cod}"] += 1
                    continue
                caracter = dict(caracter)
                caracter["text"] = inlocuire
                caractere.append(caracter)
            pagini_text.append(extract_text(caractere, layout=False, x_tolerance=1.5))
    text = normalizeaza_diacritice("\n".join(pagini_text))
    # pdfplumber pune numărul paginii pare pe același rând cu antetul MO („2 MONITORUL
    # OFICIAL…”); pe rând propriu, antetul e recunoscut și eliminat de chunker.
    text = _PATTERN_PAGINA_LIPITA_DE_ANTET.sub(r"\1\n\2", text)
    raport = {"nerezolvate": dict(nerezolvate), "pagini": len(pagini_text)}
    return text, raport


def _scrie_atomic(cale, continut):
    cale = Path(cale)
    fisier_temporar = cale.with_name(cale.name + ".tmp")
    fisier_temporar.write_text(continut, encoding="utf-8")
    fisier_temporar.replace(cale)


def main():
    parser = argparse.ArgumentParser(description="Extrage text din PDF-uri MO bis (P 118/2, P 118/3)")
    parser.add_argument("pdf", help="calea catre PDF-ul sursa")
    parser.add_argument("iesire", help="calea fisierului text de iesire")
    parser.add_argument("--raport", help="calea fisierului JSON cu raportul de extragere")
    args = parser.parse_args()

    text, raport = extrage_text(args.pdf)
    _scrie_atomic(args.iesire, text)
    if args.raport:
        _scrie_atomic(args.raport, json.dumps(raport, ensure_ascii=False, indent=2))
    print(f"Extras: {raport['pagini']} pagini, {len(text)} caractere, "
          f"{sum(raport['nerezolvate'].values())} nerezolvate")


if __name__ == "__main__":
    main()
