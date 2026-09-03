"""Teste pentru glyph_mapping.py — corectarea formulelor CambriaMath fara /ToUnicode.

Nu depinde de fitz/PDF-uri reale: construim obiecte minimale care imita doar
API-ul folosit din pagina.get_texttrace() / pagina.get_text().
"""

import json

import pytest

import glyph_mapping


class SpanFals:
    """Imita un span din page.get_texttrace(): are 'font', 'size', 'bbox', 'chars'."""

    def __init__(self, font, size, bbox, chars):
        self.font = font
        self.size = size
        self.bbox = bbox
        self.chars = chars

    def get(self, cheie, implicit=None):
        return getattr(self, cheie, implicit)

    def __getitem__(self, cheie):
        return getattr(self, cheie)


class PaginaFalsa:
    """Imita fitz.Page cat sa testam construieste_inlocuiri_pagina() fara PDF real.

    text_pagina - textul complet pe care l-ar intoarce page.get_text()
    spans - span-urile pe care le-ar intoarce page.get_texttrace()
    dict_spans - lista de (font, bbox, text) care imita span-urile pe care
    le-ar intoarce page.get_text("dict") (segmentarea proprie a PyMuPDF, de
    obicei diferita de bbox-urile din get_texttrace()); implicit, daca nu e
    dat, se construieste automat cate un span dict per span texttrace, cu
    acelasi bbox si font (cazul simplu, fara suprapuneri de testat)
    """

    def __init__(self, text_pagina, spans, dict_spans=None):
        self._text = text_pagina
        self._spans = spans
        if dict_spans is None:
            dict_spans = [(s.font, s.bbox, "X") for s in spans]
        self._dict_spans = dict_spans

    def get_texttrace(self):
        return self._spans

    def get_text(self, mod="text", clip=None):
        if mod == "dict":
            spans = [{"font": font, "bbox": bbox, "text": text} for font, bbox, text in self._dict_spans]
            return {"blocks": [{"lines": [{"spans": spans}]}]}
        return self._text


TABELA_TEST = {
    100: {"char": "V", "unicode": "U+0056", "method": "cmap", "glyph_name": "V", "note": "test"},
    101: {"char": "c", "unicode": "U+0063", "method": "visual", "glyph_name": None, "note": "test"},
    102: {"char": "s", "unicode": "U+0073", "method": "visual", "glyph_name": None, "note": "test"},
    3: {"char": " ", "unicode": "U+0020", "method": "cmap", "glyph_name": "space", "note": "test"},
}


def test_incarca_tabela_are_intrari_int_cheie(tmp_path):
    cale = tmp_path / "harta.json"
    cale.write_text(
        json.dumps({"entries": {"100": {"char": "V", "unicode": "U+0056", "method": "cmap"}}}),
        encoding="utf-8",
    )
    tabela = glyph_mapping.incarca_tabela(cale)
    assert tabela[100]["char"] == "V"
    assert isinstance(list(tabela.keys())[0], int)


def test_construieste_inlocuiri_corecteaza_span_normal():
    # dict raporteaza normal exact un caracter per GID - "ǡ" e un caracter
    # stricat oarecare (nu are nicio legatura cu litera reala "V")
    bbox = (10.0, 10.0, 20.0, 20.0)
    span = SpanFals("CambriaMath", 12.0, bbox, [(65533, 100, (10.0, 18.0), bbox)])
    pagina = PaginaFalsa(
        text_pagina="inainte ǡ după",
        spans=[span],
        dict_spans=[("CambriaMath", bbox, "ǡ")],
    )
    inlocuiri = glyph_mapping.construieste_inlocuiri_pagina(pagina, TABELA_TEST)
    assert inlocuiri == [("ǡ", "V")]


def test_font_neCambriaMath_e_ignorat_complet():
    bbox = (10.0, 10.0, 20.0, 20.0)
    span = SpanFals("TimesNewRomanPSMT", 12.0, bbox, [(97, 97, (10.0, 18.0), bbox)])
    pagina = PaginaFalsa(text_pagina="text normal", spans=[span], dict_spans=[])
    inlocuiri = glyph_mapping.construieste_inlocuiri_pagina(pagina, TABELA_TEST)
    assert inlocuiri == []


def test_glif_necunoscut_e_marcat_explicit_nu_ghicit():
    """GID-urile absente din tabela NU trebuie inlocuite cu o presupunere:
    trebuie sa apara un marcaj vizibil si cautabil."""
    bbox = (10.0, 10.0, 15.0, 20.0)
    span = SpanFals("CambriaMath", 12.0, bbox, [(65533, 9999, (10.0, 18.0), bbox)])
    pagina = PaginaFalsa(
        text_pagina="inainte X după",
        spans=[span],
        dict_spans=[("CambriaMath", bbox, "X")],
    )
    inlocuiri = glyph_mapping.construieste_inlocuiri_pagina(pagina, TABELA_TEST)
    assert inlocuiri == [("X", "<?glif9999?>")]


def test_indice_lipit_de_litera_de_baza_nu_se_pierde():
    """Regresie: un indice tucked sub litera de baza (bbox-urile din
    get_texttrace() se suprapun optic) trebuie asociat span-ului dict care
    contine EXACT indicele, nu celui care contine litera de baza, chiar daca
    bbox-urile din get_texttrace() se suprapun substantial. page.get_text
    ("dict") le segmenteaza deja separat - ne bazam pe centrul lor de bbox,
    nu pe cel din get_texttrace()."""
    bbox_v = (10.0, 10.0, 18.0, 22.0)  # litera de baza, bbox lat (metrica fontului)
    bbox_c = (15.0, 14.0, 20.0, 23.0)  # indice, se suprapune cu bbox_v din get_texttrace()
    span_v = SpanFals("CambriaMath", 12.0, bbox_v, [(65533, 100, (10.0, 20.0), bbox_v)])
    span_c = SpanFals("CambriaMath", 8.0, bbox_c, [(65533, 101, (15.0, 22.0), bbox_c)])
    pagina = PaginaFalsa(
        text_pagina="text babilon1 babilon2 final",
        spans=[span_v, span_c],
        # page.get_text("dict") segmenteaza corect, cu bbox-uri proprii, mult
        # mai inguste decat cele din get_texttrace() - cate un caracter stricat
        # per GID (ǡ pentru V, ǯ pentru c - fara nicio legatura cu litera reala)
        dict_spans=[
            ("CambriaMath", (10.1, 10.0, 10.1, 22.0), "ǡ"),
            ("CambriaMath", (15.5, 14.0, 19.5, 23.0), "ǯ"),
        ],
    )
    inlocuiri = glyph_mapping.construieste_inlocuiri_pagina(pagina, TABELA_TEST)
    assert inlocuiri == [("ǡ", "V"), ("ǯ", "_{c}")]


def test_subscript_e_marcat_cu_conventia_underscore_acolade():
    bbox_normal = (10.0, 10.0, 20.0, 22.0)
    bbox_mic = (20.0, 14.0, 26.0, 22.0)  # origine_y mai mare = mai jos pe pagina = indice
    span_normal = SpanFals("CambriaMath", 12.0, bbox_normal, [(65533, 100, (10.0, 20.0), bbox_normal)])
    span_indice = SpanFals("CambriaMath", 8.0, bbox_mic, [(65533, 101, (20.0, 21.0), bbox_mic)])
    pagina = PaginaFalsa(
        text_pagina="text alfa beta final",
        spans=[span_normal, span_indice],
        dict_spans=[
            ("CambriaMath", bbox_normal, "ǡ"),
            ("CambriaMath", bbox_mic, "ǯ"),
        ],
    )
    inlocuiri = glyph_mapping.construieste_inlocuiri_pagina(pagina, TABELA_TEST)
    assert inlocuiri == [("ǡ", "V"), ("ǯ", "_{c}")]


def test_superscript_e_marcat_cu_conventia_caret_acolade():
    bbox_normal = (10.0, 10.0, 20.0, 22.0)
    bbox_mic = (20.0, 6.0, 26.0, 14.0)  # origine_y mai mica = mai sus pe pagina = exponent
    span_normal = SpanFals("CambriaMath", 12.0, bbox_normal, [(65533, 100, (10.0, 20.0), bbox_normal)])
    span_exponent = SpanFals("CambriaMath", 8.0, bbox_mic, [(65533, 102, (20.0, 12.0), bbox_mic)])
    pagina = PaginaFalsa(
        text_pagina="text alfa gama final",
        spans=[span_normal, span_exponent],
        dict_spans=[
            ("CambriaMath", bbox_normal, "ǡ"),
            ("CambriaMath", bbox_mic, "ǰ"),
        ],
    )
    inlocuiri = glyph_mapping.construieste_inlocuiri_pagina(pagina, TABELA_TEST)
    assert inlocuiri == [("ǡ", "V"), ("ǰ", "^{s}")]


def test_aplica_inlocuiri_pastreaza_restul_textului():
    # cate o intrare per aparitie, asa cum le produce construieste_inlocuiri_pagina
    # (un span per aparitie in pagina, chiar daca textul stricat e identic)
    text = "inainte babilonă după babilonă final"
    rezultat = glyph_mapping.aplica_inlocuiri(text, [("babilonă", "V"), ("babilonă", "V")])
    assert rezultat == "inainte V după V final"


def test_aplica_inlocuiri_needle_negasit_nu_strica_textul():
    text = "text simplu fara nimic de corectat"
    rezultat = glyph_mapping.aplica_inlocuiri(text, [("nu există", "X")])
    assert rezultat == text


def test_aplica_inlocuiri_gestioneaza_reordonari_intre_span_uri():
    """Regresie: get_texttrace() nu garanteaza aceeasi ordine cu page.get_text()
    (ex. linii cu segmente bidi). Inlocuirea trebuie sa gaseasca fiecare needle
    oriunde apare in text, nu doar dupa cursorul ultimei inlocuiri."""
    text = "AAA BBB CCC"
    inlocuiri = [("CCC", "3"), ("AAA", "1"), ("BBB", "2")]
    rezultat = glyph_mapping.aplica_inlocuiri(text, inlocuiri)
    assert rezultat == "1 2 3"


def test_gid_la_caracter_marcheaza_intrare_unresolved_din_tabela():
    tabela = {5: {"char": None, "unicode": None, "method": "unresolved", "note": "de revizuit"}}
    assert glyph_mapping._gid_la_caracter(tabela, 5) == "<?glif5?>"
    assert glyph_mapping._gid_la_caracter(tabela, 999) == "<?glif999?>"


@pytest.mark.parametrize(
    "stilizat, simplu",
    [
        ("\U0001D449", "V"),  # MATHEMATICAL ITALIC CAPITAL V
        ("\U0001D48C", "k"),  # MATHEMATICAL BOLD ITALIC SMALL K
        ("\U0001D706", "λ"),  # MATHEMATICAL ITALIC SMALL LAMDA -> litera greaca simpla
        ("\U0001D7CE", "0"),  # MATHEMATICAL BOLD DIGIT ZERO
        ("\U0001D538", "A"),  # MATHEMATICAL DOUBLE-STRUCK CAPITAL A
        ("\U0001D504", "A"),  # MATHEMATICAL FRAKTUR CAPITAL A
        ("\U0001D49C", "A"),  # MATHEMATICAL SCRIPT CAPITAL A
        ("\U0001D5A0", "A"),  # MATHEMATICAL SANS-SERIF CAPITAL A
        ("\U0001D68A", "a"),  # MATHEMATICAL MONOSPACE SMALL A
    ],
)
def test_incarca_tabela_normalizeaza_litere_stilizate_la_simple(tmp_path, stilizat, simplu):
    """Blocul Mathematical Alphanumeric Symbols (bold/italic/script/fraktur/
    double-struck/sans-serif/monospace + cifre) nu e continut, e stilizare —
    trebuie redus la litera/cifra simpla ca sa fie acoperit de fonturile din
    UI si sa se potriveasca la cautare exacta."""
    cale = tmp_path / "harta.json"
    cale.write_text(
        json.dumps({"entries": {"1": {"char": stilizat, "unicode": None, "method": "cmap"}}}),
        encoding="utf-8",
    )
    tabela = glyph_mapping.incarca_tabela(cale)
    assert tabela[1]["char"] == simplu


@pytest.mark.parametrize(
    "simbol",
    ["√", "×", "≤", "≥", "̇", "α", "λ", "π", "Σ"],
)
def test_incarca_tabela_nu_atinge_simboluri_matematice_reale(tmp_path, simbol):
    """Radicalul, operatorii, diacriticul combinat si literele grecesti simple
    (in afara blocului Mathematical Alphanumeric Symbols) nu au descompunere
    de compatibilitate si nu trebuie modificate."""
    cale = tmp_path / "harta.json"
    cale.write_text(
        json.dumps({"entries": {"1": {"char": simbol, "unicode": None, "method": "cmap"}}}),
        encoding="utf-8",
    )
    tabela = glyph_mapping.incarca_tabela(cale)
    assert tabela[1]["char"] == simbol


def test_incarca_tabela_normalizeaza_planck_constant_folosit_ca_litera_h(tmp_path):
    """U+210E PLANCK CONSTANT apare in art. 12.1 ca litera italica 'h' generica
    (pierdere de sarcina locala), nu ca simbolul fizic - trebuie normalizat."""
    cale = tmp_path / "harta.json"
    cale.write_text(
        json.dumps({"entries": {"1": {"char": "ℎ", "unicode": None, "method": "cmap"}}}),
        encoding="utf-8",
    )
    tabela = glyph_mapping.incarca_tabela(cale)
    assert tabela[1]["char"] == "h"


def test_incarca_tabela_nu_normalizeaza_alte_simboluri_letterlike(tmp_path):
    """Restul blocului Letterlike Symbols (ex. ℂ - multimea numerelor complexe)
    nu e in lista curatata individual, deci nu trebuie atins orbeste."""
    cale = tmp_path / "harta.json"
    cale.write_text(
        json.dumps({"entries": {"1": {"char": "ℂ", "unicode": None, "method": "cmap"}}}),
        encoding="utf-8",
    )
    tabela = glyph_mapping.incarca_tabela(cale)
    assert tabela[1]["char"] == "ℂ"


def test_spatiu_parazit_langa_paranteza_e_curatat():
    """Regresie: documentul sursa are uneori un glif de spatiu lipit inainte
    de paranteza inchisa a numarului de ecuatie (ex. '(14.2 )' in loc de
    '(14.2)') - e artefact de formatare, nu continut."""
    bbox = (10.0, 10.0, 30.0, 20.0)
    # gid 3 = spatiu; simulam secventa "(14.2 )" cu un gid oarecare pt fiecare caracter deja mapat
    tabela = dict(TABELA_TEST)
    tabela[200] = {"char": "(", "method": "cmap"}
    tabela[201] = {"char": "1", "method": "cmap"}
    tabela[202] = {"char": ")", "method": "cmap"}
    span = SpanFals(
        "CambriaMath",
        12.0,
        bbox,
        [
            (65533, 200, (10.0, 18.0), bbox),
            (65533, 201, (10.0, 18.0), bbox),
            (65533, 3, (10.0, 18.0), bbox),
            (65533, 202, (10.0, 18.0), bbox),
        ],
    )
    pagina = PaginaFalsa(
        text_pagina="text (1 ) final",
        spans=[span],
        dict_spans=[("CambriaMath", bbox, "(1 )")],
    )
    inlocuiri = glyph_mapping.construieste_inlocuiri_pagina(pagina, tabela)
    assert inlocuiri == [("(1 )", "(1)")]


def test_span_doar_spatiu_nu_produce_o_corectie():
    """Un span care se mapeaza doar la spatiu(-i) nu are sens semantic de
    corectat, indiferent daca l-am putea localiza precis in dict_spans."""
    bbox = (10.0, 10.0, 12.0, 20.0)
    span = SpanFals("CambriaMath", 12.0, bbox, [(65533, 3, (10.0, 18.0), bbox)])
    pagina = PaginaFalsa(
        text_pagina="pentru conducte",
        spans=[span],
        dict_spans=[("CambriaMath", bbox, "\x03")],
    )
    inlocuiri = glyph_mapping.construieste_inlocuiri_pagina(pagina, TABELA_TEST)
    assert inlocuiri == []


# --- teste pentru invata_proxy_glife() / rezerva pentru span-uri omise de dict ---


def test_invata_proxy_glife_din_potriviri_certe():
    """Regresie: page.get_text("dict") omite complet unele span-uri de 1
    caracter din propria segmentare (verificat: pe o pagina reala cu 8
    aparitii ale gid-ului 1848 = litera 'V', dict raporteaza span propriu
    pentru UNA singura). Fallback-ul stricat al MuPDF e insa determinist per
    GID - invatam din potrivirile certe (span get_texttrace() de 1 caracter,
    foarte aproape de un span dict de 1 caracter) ca sa completam restul."""
    bbox = (10.0, 10.0, 20.0, 20.0)
    span = SpanFals("CambriaMath", 12.0, bbox, [(65533, 100, (10.0, 18.0), bbox)])
    pagina = PaginaFalsa(
        text_pagina="text ǡ final",
        spans=[span],
        dict_spans=[("CambriaMath", bbox, "ǡ")],
    )
    proxy = glyph_mapping.invata_proxy_glife([pagina], TABELA_TEST)
    assert proxy == {100: "ǡ"}


def test_invata_proxy_glife_scoate_gid_contradictoriu():
    """Daca acelasi GID pare sa produca DOUA caractere stricate diferite in
    doua locuri, ipoteza de determinism e contrazisa - nu ghicim intre
    variante, scoatem GID-ul din proxy cu totul."""
    bbox1 = (10.0, 10.0, 20.0, 20.0)
    bbox2 = (10.0, 50.0, 20.0, 60.0)
    span1 = SpanFals("CambriaMath", 12.0, bbox1, [(65533, 100, (10.0, 18.0), bbox1)])
    span2 = SpanFals("CambriaMath", 12.0, bbox2, [(65533, 100, (10.0, 58.0), bbox2)])
    pagina1 = PaginaFalsa(text_pagina="x", spans=[span1], dict_spans=[("CambriaMath", bbox1, "ǡ")])
    pagina2 = PaginaFalsa(text_pagina="x", spans=[span2], dict_spans=[("CambriaMath", bbox2, "ǯ")])
    proxy = glyph_mapping.invata_proxy_glife([pagina1, pagina2], TABELA_TEST)
    assert 100 not in proxy


def test_construieste_inlocuiri_foloseste_proxy_cand_dict_omite_span():
    """Cazul real gasit: span get_texttrace() cu GID cunoscut, dar NICIUN
    span dict in apropiere (dict l-a omis din segmentare) - cu un proxy
    invatat in prealabil, needle-ul se reconstruieste din proxy, nu din dict."""
    bbox = (100.0, 100.0, 108.0, 112.0)
    span = SpanFals("CambriaMath", 12.0, bbox, [(65533, 100, (100.0, 110.0), bbox)])
    pagina = PaginaFalsa(text_pagina="text ǡ final", spans=[span], dict_spans=[])
    proxy = {100: "ǡ"}
    inlocuiri = glyph_mapping.construieste_inlocuiri_pagina(pagina, TABELA_TEST, proxy=proxy)
    assert inlocuiri == [("ǡ", "V")]


def test_construieste_inlocuiri_prefera_dict_fata_de_proxy_cand_dict_reuseste():
    """Cand dict chiar da un caracter per GID asteptat, folosim needle-ul din
    dict (mai precis, legat de pozitia reala), nu proxy-ul generic — chiar
    daca proxy-ul ar da un raspuns diferit pentru acelasi GID."""
    bbox = (10.0, 10.0, 20.0, 20.0)
    span = SpanFals("CambriaMath", 12.0, bbox, [(65533, 100, (10.0, 18.0), bbox)])
    pagina = PaginaFalsa(
        text_pagina="text ǡ final",
        spans=[span],
        dict_spans=[("CambriaMath", bbox, "ǡ")],
    )
    proxy = {100: "cu totul alt text"}
    inlocuiri = glyph_mapping.construieste_inlocuiri_pagina(pagina, TABELA_TEST, proxy=proxy)
    assert inlocuiri == [("ǡ", "V")]


def test_construieste_inlocuiri_fara_proxy_nu_ghiceste_span_omis():
    """Fara un proxy invatat (proxy=None, comportamentul implicit) si fara
    niciun span dict in apropiere, corectia e sarita - nu ghicim."""
    bbox = (100.0, 100.0, 108.0, 112.0)
    span = SpanFals("CambriaMath", 12.0, bbox, [(65533, 100, (100.0, 110.0), bbox)])
    pagina = PaginaFalsa(text_pagina="text ǡ final", spans=[span], dict_spans=[])
    inlocuiri = glyph_mapping.construieste_inlocuiri_pagina(pagina, TABELA_TEST)
    assert inlocuiri == []
