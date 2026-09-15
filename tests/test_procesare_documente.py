"""Teste pentru procesare_documente.py — extragerea PDF si normalizarea diacriticelor.

Folosim un PDF minimal, generat in memorie cu fitz, ca sa nu depindem de
documente_noi (gitignored, nu e mereu prezent in worktree).
"""

import fitz
import pytest

import procesare_documente


def _scrie_pdf_gol(cale):
    """Un PDF valid, cu o singura pagina fara text - suficient pentru
    extrage_text (page.get_text() intoarce "" pe o pagina goala)."""
    document = fitz.open()
    document.new_page()
    document.save(str(cale))
    document.close()


def test_extrage_text_normalizeaza_diacriticele_sedila(tmp_path, monkeypatch):
    """Textul "stricat" (obtinut din get_text()/corecteaza_text_pagina) e
    normalizat la final: ţ/ş/Ţ/Ş devin ț/ș/Ț/Ș inainte de a ajunge in
    extracted.txt, deci in fragmente si in embeddings."""
    monkeypatch.setattr(procesare_documente, "incarca_tabela", lambda: {})
    monkeypatch.setattr(procesare_documente, "invata_proxy_glife", lambda document, tabela: {})
    monkeypatch.setattr(
        procesare_documente,
        "corecteaza_text_pagina",
        lambda pagina, tabela, proxy=None: "Rețeaua ştie despre acțiunea Ţării, cu şi fara sedila",
    )

    cale_pdf = tmp_path / "sintetic.pdf"
    _scrie_pdf_gol(cale_pdf)

    text, pagini = procesare_documente.extrage_text(cale_pdf)

    assert pagini == 1
    assert "ţ" not in text and "ş" not in text and "Ţ" not in text and "Ş" not in text
    assert text == "Rețeaua știe despre acțiunea Țării, cu și fara sedila\n"


def test_repara_np091_verificat_inlocuieste_numai_sursa_validata(tmp_path, monkeypatch):
    cale_pdf = tmp_path / "np091.pdf"
    cale_pdf.write_bytes(b"sursa-validata")
    monkeypatch.setattr(procesare_documente, "_NP091_SHA256", procesare_documente.hashlib.sha256(b"sursa-validata").hexdigest())

    assert procesare_documente._repara_np091_verificat("A?B" * 11, cale_pdf) == "A→B" * 11


def test_repara_np091_verificat_nu_modifica_alta_sursa(tmp_path):
    cale_pdf = tmp_path / "alta-sursa.pdf"
    cale_pdf.write_bytes(b"alta")

    assert procesare_documente._repara_np091_verificat("A?B", cale_pdf) == "A?B"


def test_repara_np091_verificat_esueaza_la_numar_neasteptat(tmp_path, monkeypatch):
    cale_pdf = tmp_path / "np091.pdf"
    cale_pdf.write_bytes(b"sursa-validata")
    monkeypatch.setattr(procesare_documente, "_NP091_SHA256", procesare_documente.hashlib.sha256(b"sursa-validata").hexdigest())

    with pytest.raises(ValueError, match="np091_symbol_count_invalid"):
        procesare_documente._repara_np091_verificat("A?B", cale_pdf)


def test_extrage_text_nu_modifica_simbolurile_matematice_si_literele_grecesti(tmp_path, monkeypatch):
    """Textul reconstruit din formule CambriaMath (radical, litere grecesti,
    punctul suprapus combinat) trece nemodificat prin normalizarea de
    diacritice - doar cele patru perechi sedila->virgula sunt vizate."""
    text_formula = "V̇ = 0,83/√N-1 × λ Σ ψ θ"
    monkeypatch.setattr(procesare_documente, "incarca_tabela", lambda: {})
    monkeypatch.setattr(procesare_documente, "invata_proxy_glife", lambda document, tabela: {})
    monkeypatch.setattr(
        procesare_documente, "corecteaza_text_pagina", lambda pagina, tabela, proxy=None: text_formula
    )

    cale_pdf = tmp_path / "formula.pdf"
    _scrie_pdf_gol(cale_pdf)

    text, _ = procesare_documente.extrage_text(cale_pdf)
    assert text == text_formula + "\n"
