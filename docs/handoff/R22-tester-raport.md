# R22 — Raport Tester

## Fișiere modificate

### tests/test_diacritice.py
Adăugate teste pentru `corecteaza_substituiri_pdf`:
- `test_corecteaza_substituiri_pdf_pe_cuvinte_reale_din_i7` (parametrizat, 5 cazuri): fiecare din cele 5 substituiri (Ġ→ț, ú→ș, ğ→Ț, U+070A→ț, U+0708→ș) pe cuvinte reale din I7. Ar pica dacă oricare mapare ar lipsi sau ar fi greșită în `_SUBSTITUIRI_PDF_LA_DIACRITICE`.
- `test_corecteaza_substituiri_pdf_x98_ramane_neschimbat`: `\x98` neatins. Ar pica dacă cineva ar adăuga greșit o mapare pentru el.
- `test_corecteaza_substituiri_pdf_text_fara_caractere_corupte_ramane_identic`: text curat rămâne identic. Ar pica dacă funcția ar altera alte caractere.
- `test_corecteaza_substituiri_pdf_nu_atinge_sedila_sau_diacritice_corecte`: sedilă (ţ/ş/Ţ/Ş) și diacritice deja corecte rămân neatinse de această funcție (rămân treaba lui `normalizeaza_diacritice`). Ar pica dacă cele două funcții ar ajunge să se suprapună.
- `test_corecteaza_substituiri_pdf_refuza_valori_non_text`: `None` → `ValueError`. Ar pica dacă validarea de tip ar fi eliminată.

### tests/test_chunking_core.py
- `test_creeaza_chunkuri_corecteaza_substituirile_pdf_din_text`: text sintetic cu toate cele 4 caractere corupte relevante (Ġ, ú, U+070A, U+0708) → chunk-urile rezultate nu le mai conțin, iar cuvintele corectate apar întregi. Ar pica dacă `creeaza_chunkuri` nu ar mai apela `corecteaza_substituiri_pdf` la început.
- `test_acoperire_text_brut_pe_text_corupt_ramane_simetrica`: același text brut corupt trecut prin `creeaza_chunkuri` + `acoperire_text_brut` dă exact 1.0. Ar pica dacă `acoperire_text_brut` nu ar corecta și ea textul brut înainte de comparație (regresia de simetrie care ar produce fals pierderi la poarta D24).

### tests/test_procesare_documente.py
- `test_extrage_text_corecteaza_substituirile_pdf_i7_impreuna_cu_sedila`: text cu ambele tipuri de corupere (substituiri I7 + sedilă) trecut prin `extrage_text` (PDF sintetic, `corecteaza_text_pagina` mock-uit ca în testele existente) → rezultatul final nu conține niciunul din caracterele corupte și cuvintele sunt corect normalizate. Ar pica dacă `corecteaza_substituiri_pdf` nu ar mai fi aplicată în `extrage_text`.

**Limitare asumată**: nu am putut scrie un test care distinge strict *ordinea* `corecteaza_substituiri_pdf` → `normalizeaza_diacritice` de ordinea inversă, pentru că mulțimile de caractere vizate de cele două funcții sunt disjuncte (Ġ/ú/ğ/U+070A/U+0708 vs. ţ/ş/Ţ/Ş) — orice ordine produce exact același rezultat final. Testul de mai sus verifică doar că *ambele* corecturi sunt efectiv aplicate pe același text, nu ordinea relativă (care e neobservabilă din output).

### tests/test_populare_db.py
- `NUMAR_CHUNKURI_ASTEPTAT_PER_DOCUMENT["i7_2011"]` actualizat la **2215** (era 2214).
- `test_i7_niciun_chunk_nu_contine_substituirile_pdf_necorectate` (nou, `skipif` pe `documente_noi`): pe `documente_noi/i7_2011/extracted.txt` real, niciun chunk rezultat din `creeaza_chunkuri` nu conține Ġ/ú/ğ/U+070A/U+0708. Ar pica dacă corectura nu s-ar aplica efectiv (sau incomplet) pe documentul real.

## Suspiciuni de bug
Niciuna găsită în codul livrat de coder pentru R22 — mapările din `diacritice.py` și integrarea în `procesare_documente.py`/`chunking_core.py` par consistente cu cifrele verificate de planner.

## Comandă pentru planner
```powershell
cd D:\Omnia-MVP-r22-i7
pytest tests/test_diacritice.py tests/test_procesare_documente.py tests/test_chunking_core.py tests/test_populare_db.py -v
```
