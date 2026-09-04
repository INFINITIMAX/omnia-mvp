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
