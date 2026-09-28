"""Corectează exclusiv sedila greșită din diacriticele românești ț/ș.

Problema: o parte din documentele sursă (și unele tastaturi/sisteme mai
vechi) folosesc varianta greșită a literelor românești ț și ș - cu SEDILĂ
(ţ U+0163, ş U+015F, și majusculele Ţ U+0162, Ş U+015E) - în loc de varianta
corectă din standardul actual, cu VIRGULĂ dedesubt (ț U+021B, ș U+0219, Ț
U+021A, Ș U+0218). Sunt code point-uri Unicode diferite: o comparație de
șiruri sau o căutare exactă între cele două forme eșuează, chiar dacă un
cititor uman nu vede nicio diferență vizuală.

Soluția: o traducere caracter-cu-caracter, STRICT limitată la aceste patru
perechi. NU folosim unicodedata.normalize() sau altă normalizare Unicode
globală aici - o normalizare NFKC/NFKD generală ar atinge și code point-urile
din Mathematical Alphanumeric Symbols și alte blocuri folosite de formulele
reconstruite din PDF-uri CambriaMath (vezi glyph_mapping.py), lucru pe care
nu-l vrem în acest modul. Orice alt caracter (â, î, ă, radical, ×, litere
grecești, punctul suprapus combinat U+0307 etc.) rămâne complet neatins.

Folosit simetric: la ingestie, pe textul extras din documente (vezi
procesare_documente.py), și la interogare, pe întrebarea utilizatorului
(vezi retrieval_core.py) - altfel normalizarea unilaterală a documentelor
ar muta problema în loc s-o rezolve pentru utilizatorii ale căror tastatură
sau sistem produc tot sedilă.
"""

_SEDILA_LA_VIRGULA = str.maketrans({
    "ţ": "ț",  # ţ -> ț
    "ş": "ș",  # ş -> ș
    "Ţ": "Ț",  # Ţ -> Ț
    "Ş": "Ș",  # Ş -> Ș
})


def normalizeaza_diacritice(text: str) -> str:
    """Înlocuiește ţ/ş/Ţ/Ş (sedilă) cu ț/ș/Ț/Ș (virgulă). Nimic altceva."""
    if not isinstance(text, str):
        raise ValueError("textul trebuie să fie text")
    return text.translate(_SEDILA_LA_VIRGULA)


# Runda R22: extragerea PDF a normativului I7-2011 substituie sistematic ț/ș/Ț cu
# caractere din alte alfabete/blocuri Unicode, fără nicio legătură vizuală sau
# semantică cu litera înlocuită - font embedat cu tabelă de codare greșită, nu
# sedilă vs. virgulă. Fiecare mapare de mai jos e dovedită direct în
# documente_noi/i7_2011/extracted.txt (vezi docs/handoff/R22-coder.md):
# - Ġ (U+0120, literă latină) -> ț, ex. „protecĠia”
# - ú (U+00FA, u cu accent, alfabet spaniol/portughez) -> ș, ex. „úi”
# - ğ (U+011F, g cu breve, alfabet turc) -> Ț, doar în cuvinte cu majuscule
#   („INSTALAğIILOR”, „PROTECğII”)
# - ܊ (U+070A, alfabet siriac) -> ț, ex. „construc܊ii”
# - ܈ (U+0708, alfabet siriac) -> ș, ex. „܈i”
# Nu există (verificat în text) o formă majusculă coruptă separată a lui Ș -
# cuvintele cu majuscule care ar conține-o („ÎNTREȚINEREA”, „SECURITĂȚII”) au
# de fapt Ț corupt (ğ), nu Ș; nu se adaugă nicio mapare nedovedită.
# \x98 (simbol din formule matematice) NU se mapează - nu corespunde unei
# diacritice, ci unui simbol pierdut la extragere.
_SUBSTITUIRI_PDF_LA_DIACRITICE = str.maketrans({
    "Ġ": "ț",
    "ú": "ș",
    "ğ": "Ț",
    "܊": "ț",
    "܈": "ș",
})


def corecteaza_substituiri_pdf(text: str) -> str:
    """Înlocuiește Ġ/ú/ğ/܊/܈ cu ț/ș/Ț (vezi tabela de mai sus). Nimic altceva."""
    if not isinstance(text, str):
        raise ValueError("textul trebuie să fie text")
    return text.translate(_SUBSTITUIRI_PDF_LA_DIACRITICE)
