# R26 — Raport reviewer, partea 2 (transcris integral de planner)

VERDICT FINAL PENTRU TOT R26 (A-D): APROBAT

## Ce am verificat

Am citit R26-reviewer-raport.md (partea 1, verdict RESPINS transcris + decizia planner), R26-A-coder.md/-raport.md, R26-tester-runda2.md/-raport.md, și codul efectiv: `extragere_mo_bis.py` (nou, întreg), `diacritice.py` (diff complet), `populare_db.py` (diff linie-cu-linie față de `D:\Omnia-MVP\populare_db.py`), `chunking_core.py` liniile 760-883 (`_aplica_limita_caractere`, `_propaga_marcaj_provenienta`, `_respecta_limita_cu_marcaje`), `generation_core.py` liniile 85-107 (`_MODIFICATION_MARKER`), `consolidare_normative.py` liniile 450-499 (inclusiv fix-ul `912d5f1` la `abroga_subunitate`), și testele noi: `tests/test_chunking_core.py` (liniile 532-640+), `tests/test_citation_modificari.py` (150-233), `tests/test_consolidare_normative.py` (383-423), `tests/test_extragere_mo_bis.py` (întreg, 219 linii), `tests/test_populare_db.py` (întreg, 985 linii, secțiunile noi 709-806).

## R26-A (cod nou) — corect, nimic în plus față de brief

- `extragere_mo_bis.py`: `incarca_tabela`, `harta_coduri`, `extrage_text`, CLI — toate exact ca în `R26-A-coder.md`. Am verificat manual semantica `/Differences` în `harta_coduri` (linia 77-88): număr → cod curent, fiecare nume (inclusiv non-`gNNN`) incrementează, GID absent rămâne nemapat — corect și confirmat de testele sintetice cu obiecte fitz false.
- Dependența de fonturile Windows e strict la generarea offline a `mo_bis_glyph_map.json` (deja generat, netouched) — la rulare, modulul citește doar JSON-ul + PyMuPDF/pdfplumber pentru structura PDF-ului, fără `fontTools`/`TTFont`. Confirmat prin lipsa oricărui import de acest gen în fișier.
- Corectura antet-pagină (`_PATTERN_PAGINA_LIPITA_DE_ANTET`, linia 36-38): regex-ul cere literal `MONITORUL OFICIAL AL ROMÂNIEI, PARTEA I, Nr. ` după număr — nu poate atinge un rând numeric legitim fără acel text (confirmat de `test_extrage_text_rand_cu_numar_fara_antet_ramane_neatins`).
- `diacritice.py`: doar adăugarea `ǎ`/`Ǎ` în `_SEDILA_LA_VIRGULA` + docstring actualizat corect; `_SUBSTITUIRI_PDF_LA_DIACRITICE`/`corecteaza_substituiri_pdf` neatinse.
- `populare_db.py`: am comparat linie cu linie cu `D:\Omnia-MVP\populare_db.py` (main). Singurele diferențe: import `acoperire_text_brut`, argumentul `--document` (linia 353-356), filtrarea în bucla `main()` (linia 361-362), print-ul de acoperire în `--dry-run` (linia 369-370). Exact conform brief-ului, fără cod suplimentar.

## Corectura `912d5f1` (`abroga_subunitate`) — corectă

`consolidare_normative.py:476`: `eticheta_text = f"{tinta['litera']})" if tinta.get("litera") else f"({tinta['alineat']})"` — scrie corect `b) Abrogat.` când e specificată o literă, respectiv `(2) Abrogat.` când e doar alineat. Testată direct de `test_abroga_subunitate_alineat` și `test_abroga_subunitate_litera`, care verifică exact eticheta corectă, dispariția textului vechi și prezența marcajului — ambele teste ar fi picat pe bug-ul vechi (`(2) Abrogat.` în loc de `b) Abrogat.`).

## Golurile din partea 1 — acoperite real (nu teste care trec oricum)

Am verificat fiecare test nou cerut de reviewer-ul din partea 1 — toate au aserțiuni specifice cu condiție de eșec clară, nu `assertTrue`/`toBeDefined` slăbite:

1. `_propaga_marcaj_provenienta` (4 teste, `test_chunking_core.py:546-640+`): scenariul multi-alineat din spec (3.3.1.(1)/(2)/(4)), regresie byte-identic fără marcaj, deduplicare + ordinea primei apariții pe două tipuri de marcaj, re-împărțire prin `_respecta_limita_cu_marcaje` cu verificare cuvânt-cu-cuvânt. Toate ar pica pe o regresie reală (verificat manual traiectoria codului pe fiecare caz).
2. `_modification_markers`/`PublicCitation.modificari` (`test_citation_modificari.py:206-233`): forma „Articol cu text …” testată izolat și împreună cu celelalte două variante, prin `GenerationService.generate` complet (nu doar regexul rupt din context). Testul regulii 11 (linia 200) e întărit exact cum a cerut reviewer-ul — `assert "Articol cu text" in prompt`, care ar fi picat pe testul vechi.
3. `abroga_subunitate` — cele două teste de mai sus, cu localizare corectă alineat/literă și marcaj.

## Ce nu e o problemă

- Deciziile testerului de a testa `_propaga_marcaj_provenienta`/`_respecta_limita_cu_marcaje` direct (nu prin `creeaza_chunkuri` capăt-la-capăt) sunt motivate corect: scenariul cere un chunk de bază ≥2000 caractere ca să declanșeze split-ul secundar, iar testarea directă a funcțiilor care conțin exact logica cerută e mai robustă, nu mai fragilă.
- Monkeypatch-urile din `test_extragere_mo_bis.py` expun exact suprafața de API folosită (`get_fonts`, `xref_object`, `close`, `pages`, `chars`) — nu testează implementarea internă a `fitz`/`pdfplumber`, ci contractul folosit de cod.
- Nu am găsit teste redundante sau teste care ar trece indiferent de schimbări în cod.
- Nu am găsit cod inutil în A, nici regresii introduse de fix-ul `912d5f1` sau de corectura antet-pagină a planner-ului.

## Recomandare

APROBAT integral pentru R26 (A-D). Nimic de retrimis la coder sau tester.

---

## Decizia planner-ului (29-09-2026)
Accept. R26 e gata de PR. Merge în main, deploy, importul în DB (Voyage) și statusul `approved` al celor două documente așteaptă aprobarea explicită a lui Lucian (vezi `D:\_scratch\omnia\R26-status.md`).
