"""Teste sintetice pentru extragere_mo_bis.py (R26-A), fara PDF-uri reale:
fitz si pdfplumber sunt monkeypatch-uite cu obiecte false care expun exact
suprafata de API folosita de harta_coduri()/extrage_text()."""

import json

import pytest

import extragere_mo_bis
from extragere_mo_bis import extrage_text, harta_coduri, incarca_tabela


# ---------------------------------------------------------------------------
# harta_coduri: semantica /Differences, prin fitz fals (monkeypatch)
# ---------------------------------------------------------------------------


class _PaginaFalsa:
    def __init__(self, fonturi):
        self._fonturi = fonturi

    def get_fonts(self, full=True):
        return self._fonturi


class _DocumentFals:
    """Simuleaza suprafata fitz.Document folosita de harta_coduri: iterare pe
    pagini, xref_object(xref) si close()."""

    def __init__(self, pagini, obiecte_xref):
        self._pagini = pagini
        self._obiecte_xref = obiecte_xref
        self.inchis = False

    def __iter__(self):
        return iter(self._pagini)

    def xref_object(self, xref):
        return self._obiecte_xref[xref]

    def close(self):
        self.inchis = True


def test_harta_coduri_respecta_semantica_differences(monkeypatch):
    """Numar -> cod curent; fiecare nume ce urmeaza foloseste codul si il
    incrementeaza, indiferent daca e /gNNN sau alt nume; un GID absent din
    tabela ramane nemapat. Ar pica dacă parsarea nu ar respecta ordinea
    numar/nume din /Differences sau dacă gid-urile nemapate ar primi totuși
    un caracter."""
    obiect_font = (
        "<< /Type /Font /Subtype /Type1 /BaseFont /ABCDEF+TimesNewRomanPSMT "
        "/Encoding 11 0 R >>"
    )
    obiect_encoding = "<< /Type /Encoding /Differences [1 /g10 /space /g12 5 /g20] >>"
    document = _DocumentFals(
        pagini=[_PaginaFalsa([(10, "type1", "Type1", "ABCDEF+TimesNewRomanPSMT", "F1", "")])],
        obiecte_xref={10: obiect_font, 11: obiect_encoding},
    )
    monkeypatch.setattr(extragere_mo_bis.fitz, "open", lambda _cale: document)

    tabela = {"TimesNewRomanPSMT": {10: "ă", 12: "ț"}}  # 20 absent -> nemapat

    harta = harta_coduri("fals.pdf", tabela)

    assert document.inchis is True
    coduri = harta["ABCDEF+TimesNewRomanPSMT"]
    # 1 -> /g10 (mapat), cod devine 2
    assert coduri[1] == "ă"
    # 2 -> /space (nume non-gNNN, consuma codul 2 fara maparea), cod devine 3
    assert 2 not in coduri
    # 3 -> /g12 (mapat), cod devine 4
    assert coduri[3] == "ț"
    # numarul "5" reseteaza codul curent la 5, apoi /g20: GID 20 absent din
    # tabela -> nemapat, dar codul tot a fost consumat (nu apare in `coduri`)
    assert 5 not in coduri
    assert set(coduri) == {1, 3}


def test_harta_coduri_font_fara_differences_produce_harta_goala(monkeypatch):
    """Un font fara /Encoding cu /Differences (font standard, fara probleme de
    codare) nu trebuie sa ridice eroare — trebuie sa primeasca o harta goala."""
    obiect_font = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    document = _DocumentFals(
        pagini=[_PaginaFalsa([(20, "type1", "Type1", "Helvetica", "F2", "")])],
        obiecte_xref={20: obiect_font},
    )
    monkeypatch.setattr(extragere_mo_bis.fitz, "open", lambda _cale: document)

    harta = harta_coduri("fals.pdf", {})

    assert harta == {"Helvetica": {}}


# ---------------------------------------------------------------------------
# incarca_tabela: chei GID -> int, tabela reala
# ---------------------------------------------------------------------------


def test_incarca_tabela_converteste_cheile_gid_la_int(tmp_path):
    cale = tmp_path / "tabela_test.json"
    cale.write_text(
        json.dumps({"_descriere": "x", "fonturi": {"FontA": {"10": "ă", "20": "ț"}}}),
        encoding="utf-8",
    )

    tabela = incarca_tabela(cale)

    assert tabela == {"FontA": {10: "ă", 20: "ț"}}
    assert all(isinstance(gid, int) for gid in tabela["FontA"])


def test_incarca_tabela_reala_contine_timesnewromanpsmt_259_si_288():
    """Tabela reala din font_maps/mo_bis_glyph_map.json: TimesNewRomanPSMT are
    259 -> 'ă' si 288 -> 'ţ' (sedila, normalizata ulterior de
    diacritice.normalizeaza_diacritice). Ar pica dacă tabela reală ar fi
    regenerată greșit sau dacă `incarca_tabela` ar altera valorile citite."""
    tabela = incarca_tabela()

    assert tabela["TimesNewRomanPSMT"][259] == "ă"
    assert tabela["TimesNewRomanPSMT"][288] == "ţ"


# ---------------------------------------------------------------------------
# extrage_text: rezolvare (cid:N), raport, normalizare, antet lipit de pagina
# ---------------------------------------------------------------------------


class _PdfFals:
    def __init__(self, pagini):
        self.pages = pagini

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


class _PaginaPdfFalsa:
    def __init__(self, chars):
        self.chars = chars


def _patch_pdfplumber(monkeypatch, pagini):
    monkeypatch.setattr(extragere_mo_bis.pdfplumber, "open", lambda _cale: _PdfFals(pagini))
    # extract_text real face layout geometric complex; pentru teste sintetice,
    # inlocuim cu o concatenare simpla a caracterelor deja rezolvate/eliminate,
    # in ordinea data — comportamentul verificat aici e rezolvarea (cid:N) si
    # raportul, nu algoritmul de layout al pdfplumber.
    monkeypatch.setattr(
        extragere_mo_bis, "extract_text",
        lambda caractere, layout=False, x_tolerance=1.5: "".join(c["text"] for c in caractere),
    )
    monkeypatch.setattr(extragere_mo_bis, "harta_coduri", lambda _pdf, _tabela: {"FontA": {5: "ă"}})


def test_extrage_text_rezolva_cid_din_harta(monkeypatch):
    pagini = [_PaginaPdfFalsa([{"text": "(cid:5)", "fontname": "FontA"}, {"text": "b"}])]
    _patch_pdfplumber(monkeypatch, pagini)

    text, raport = extrage_text("fals.pdf", tabela={})

    assert text == "ăb"
    assert raport["nerezolvate"] == {}
    assert raport["pagini"] == 1


def test_extrage_text_cid_nerezolvat_e_eliminat_si_numarat(monkeypatch):
    pagini = [_PaginaPdfFalsa([
        {"text": "(cid:7)", "fontname": "FontB"},
        {"text": "(cid:7)", "fontname": "FontB"},
        {"text": "x"},
    ])]
    _patch_pdfplumber(monkeypatch, pagini)

    text, raport = extrage_text("fals.pdf", tabela={})

    assert text == "x"
    assert raport["nerezolvate"] == {"FontB:7": 2}


def test_extrage_text_aplica_normalizarea_diacriticelor(monkeypatch):
    """Sedila din caracterele deja rezolvate (sau din textul brut al PDF-ului)
    trebuie transformata in virgula pe intreg textul final. Ar pica dacă
    `extrage_text` nu ar mai apela `diacritice.normalizeaza_diacritice`."""
    pagini = [_PaginaPdfFalsa([{"text": "mecanicş si siguranţa"}])]
    _patch_pdfplumber(monkeypatch, pagini)

    text, _ = extrage_text("fals.pdf", tabela={})

    assert text == "mecanicș si siguranța"


def test_extrage_text_rand_cu_numar_lipit_de_antet_devine_doua_randuri(monkeypatch):
    """Corectura planner: '2 MONITORUL OFICIAL AL ROMÂNIEI, PARTEA I, Nr. 595
    bis/24.IX.2013' (numarul de pagina para lipit de antet, pe acelasi rand)
    trebuie separat in doua randuri, ca antetul sa fie recunoscut de chunker."""
    pagini = [_PaginaPdfFalsa([
        {"text": "2 MONITORUL OFICIAL AL ROMÂNIEI, PARTEA I, Nr. 595 bis/24.IX.2013"},
    ])]
    _patch_pdfplumber(monkeypatch, pagini)

    text, _ = extrage_text("fals.pdf", tabela={})

    assert text == "2\nMONITORUL OFICIAL AL ROMÂNIEI, PARTEA I, Nr. 595 bis/24.IX.2013"


def test_extrage_text_rand_cu_numar_fara_antet_ramane_neatins(monkeypatch):
    """Un rând care începe cu un număr dar nu e urmat de antetul MO (ex. un
    număr de tabel oarecare) nu trebuie despărțit — ar pica dacă regex-ul de
    corectură ar prinde orice rând numeric, nu doar antetul real."""
    pagini = [_PaginaPdfFalsa([{"text": "77 Un rand obisnuit de tabel, fara vreun antet."}])]
    _patch_pdfplumber(monkeypatch, pagini)

    text, _ = extrage_text("fals.pdf", tabela={})

    assert text == "77 Un rand obisnuit de tabel, fara vreun antet."
