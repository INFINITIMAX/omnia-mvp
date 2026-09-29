# R26-C — Tester: raport (D27 — proveniența modificărilor în citare)

Am scris exclusiv în `tests/`. Nu am rulat nimic (nu am acces la shell).

## 1. Actualizare la schema nouă (`modificari`)

### `tests/test_api_integration.py`
Patru locuri comparau `response.json()` cu un dicționar literal complet pentru fiecare
citare, fără cheia nouă `modificari` — motivul exact al celor 15 eșecuri raportate de
planner (1 + 2 parametrizări + 6 parametrizări + 6 parametrizări = 15):
- `test_exact_answered_are_citare_publica_si_zero_voyage` — adăugat `"modificari": []`.
- `test_r06_endpoint_afiseaza_pasajul_literal_dupa_600_si_schema_publica` (parametrizat
  `truncated=[False, True]`) — adăugat `"modificari": []`.
- `test_api_d12_scope_explicit_gasit_pastreaza_citatul_r06_si_schema` (parametrizat
  3×2) — adăugat `"modificari": []`.
- `test_api_p1_restrictia_cu_articol_cunoscut_pastreaza_ruta_exacta` (parametrizat
  3×2×2, dar numai ramurile `has_evidence=True` foloseau dicționarul complet) —
  adăugat `"modificari": []`.

Ce ar rupe aceste teste acum: orice regresie care schimbă schema publică a
`CitationResponse` (lipsă câmp, tip greșit, valoare implicită diferită de `[]`) sau
care oprește derivarea server-side a `modificari`.

### `tests/test_citation_passages.py`
Două `vars(citation) == {...}` comparau tot dicționarul intern al `PublicCitation`
fără cheia `modificari` — cele 2 eșecuri raportate:
- `test_citation_passages_selecteaza_literal_dincolo_de_600_fara_prefix` — adăugat
  `"modificari": ()`.
- `test_citation_passages_c2_foloseste_numai_dovada_corespunzatoare` — adăugat
  `"modificari": ()`.

Ce le-ar rupe: orice schimbare a formei interne a `PublicCitation` (câmp lipsă, tip
diferit de `tuple`).

### `tests/test_ui_static.py`
`test_raspuns_si_citari_randate_prin_textcontent` avea un guard generic: orice
`citation.<câmp>` din script trebuie să apară fie într-o atribuire `.textContent =`,
fie într-un `if (citation....`. Codul nou pentru `modificari` (`Array.isArray(...)`
și `.forEach(...)`) nu se potrivea nici uneia dintre cele două forme — motivul celui
de-al 18-lea eșec. Am relaxat *strict* pentru aceste două forme suplimentare (guard de
tip listă și iterarea propriu-zisă), păstrând interzicerea oricărei alte utilizări.
Am adăugat și un test separat, mai concret, care verifică literal cele trei linii
esențiale ale randării (`Array.isArray`, `.forEach`, `mod.textContent =`,
`mod.className = 'art-mod'`), ca protecție redundantă și mai lizibilă dacă cineva
schimbă din nou tiparul de linie generic.

Ce ar rupe testul actualizat: revenirea la o formă generică prea permisivă (ar
trece indiferent de cod) e evitată prin al doilea test, care verifică literal
liniile — dacă oricare din cele patru dispare sau se schimbă (ex. revenire la
`innerHTML`, eliminarea guard-ului `Array.isArray`, redenumirea clasei `art-mod`),
pică explicit.

## 2. Teste noi

### `tests/test_citation_modificari.py` (nou, la nivel `GenerationService`)
Testează exclusiv prin contractul public `GenerationService.generate` (nu funcția
privată `_modification_markers`):

- `test_marcaj_unic_in_dovada_citata_ajunge_in_modificari_fara_paranteze` — un marcaj
  simplu în dovada citată apare fără parantezele drepte. Ar pica dacă derivarea
  ratează marcajul sau păstrează parantezele.
- `test_marcaje_identice_repetate_devin_o_singura_intrare` — două marcaje identice →
  o singură intrare. Ar pica dacă deduplicarea (`dict.fromkeys`) e eliminată.
- `test_marcaje_diferite_pastreaza_ordinea_aparitiei_nu_alfabetica` — Abrogat înaintea
  lui Text introdus în text → ordinea trebuie să reflecte asta, nu alfabetic. Ar pica
  dacă ordinea se schimbă (ex. sortare alfabetică sau după tipul de variantă).
- `test_toate_cele_trei_variante_de_marcaj_sunt_recunoscute` — Text modificat + Text
  introdus + Abrogat, toate trei prezente și în ordine. Ar pica dacă oricare variantă
  e scoasă din alternanța regexului.
- `test_marcaj_doar_in_alta_dovada_necitata_nu_apare_la_citarea_curenta` — marcaj
  numai în dovada C2 (necitată); citarea C1 rămâne `()`. Ar pica dacă derivarea
  amestecă dovezile (ex. concatenează tot `evidence` în loc de dovada proprie).
- `test_text_asemanator_dar_invalid_este_ignorat` (parametrizat, 4 variante: „Legea”
  în loc de „Ordinul”, lipsă „publicat în”, fără paranteze deloc, paranteză de
  deschidere lipsă) — niciuna nu trebuie recunoscută. Ar pica dacă regexul devine
  prea permisiv.
- `test_marcaj_scris_de_model_in_raspuns_dar_absent_din_dovada_nu_apare` — modelul
  scrie marcajul direct în `raspuns`, dar dovada nu-l conține → `modificari == ()`.
  Ar pica dacă derivarea ar citi vreodată din răspunsul modelului în loc de
  `Evidence.content`.
- `test_marcaj_scris_de_model_in_pasaj_dar_absent_din_dovada_nu_apare` — la fel, dar
  marcajul e în `citat`-ul propus de model (pasaj neprovenit, înlocuit server-side cu
  extras literal). Ar pica pe același motiv.
- `test_promptul_contine_regula_11_despre_marcajele_de_provenienta` — verifică textul
  regulii 11 în promptul construit de `_build_prompt`. Ar pica dacă regula e ștearsă
  sau reformulată fără mențiunile „Text modificat/introdus prin Ordinul” / „Abrogat
  prin Ordinul”.

### `tests/test_api_integration.py` (adăugat la final, înainte de testul deploy script)
- `test_intreaba_expune_modificari_ca_lista_json_cu_marcaj_din_dovada` — dovada
  conține un marcaj real; `/intreaba` trebuie să întoarcă `citari[0]["modificari"]`
  ca `list` cu exact acel text. Ar pica dacă `main.py` nu mai expune câmpul, îl expune
  ca alt tip (ex. tuple serializat diferit) sau dacă derivarea server-side se rupe.
- `test_intreaba_fara_marcaj_in_dovada_expune_modificari_lista_goala` — regresie
  simplă cu `EXACT_ROW` obișnuit (fără marcaj) → `modificari == []`.

### `tests/test_ui_static.py` (adăugate lângă `_run_citation_cases`)
- `test_citare_cu_modificari_randeaza_cate_un_rand_per_marcaj_prin_textcontent` —
  rulează efectiv `setMessage` prin harness-ul Node/JS existent, cu două marcaje
  distincte în `citation.modificari`; verifică (prin DOM simulat, nu prin regex pe
  text sursă) că apar exact două noduri cu `className === 'art-mod'`, cu textul
  fiecărui marcaj, în ordinea din listă. Ar pica dacă randarea nu (mai) creează
  elementele, dacă schimbă ordinea, sau dacă textul nu ajunge exact prin
  `.textContent`.
- `test_citare_fara_modificari_nu_randeaza_niciun_rand_art_mod` — `modificari: []` →
  niciun nod `art-mod` în arbore. Ar pica dacă randarea ar crea rânduri goale sau
  dacă guard-ul `Array.isArray`/lungime devine incorect.

Ambele folosesc infrastructura Node deja existentă (`_CITATION_HARNESS`,
`_run_citation_cases`) — dacă `node` nu e disponibil în mediu, se sar (`pytest.skip`),
la fel ca testele Markdown/citare existente.

## Ce nu am acoperit și de ce
- Nu am scris test separat pentru „hash-urile CSP corespund” — spec-ul spune explicit
  să verific doar că testul existent (`test_hash_urile_csp_corespund_exact_continutului_static_curent`,
  linia ~1285 din `test_api_integration.py`) trece; el recalculează hash-urile din
  fișierele reale și le compară cu constantele din `main.py`, deci acoperă exact
  cerința fără să fie nevoie de un test nou. Rămâne responsabilitatea planner-ului să
  recalculeze `_CSP_SCRIPT_HASHES`/`_CSP_STYLE_HASHES` (menționat explicit în raportul
  coder-ului) — fără asta, acest test picat rămâne al 19-lea eșec, distinct de cele 18
  inițiale.
- Nu am testat interacțiunea dintre marcaj și `_unsupported_normative_references`
  (posibilitatea ca textul unui marcaj să fie confundat cu o referință normativă
  inventată de model, ex. „P 118/2” sau „Ordinul nr. 6.025/2018” interpretat ca cod
  normativ). Am verificat manual regexurile din `normative_codes.py` — niciunul din
  tiparele `STAS/SR/EN/NP/P/I/C/NE/GP/GT/Mc` nu se potrivește pe textul marcajelor din
  spec, deci nu era un caz relevant de testat separat; dacă planner-ul consideră că
  merită un test explicit de neregresie, îl pot adăuga.
- Nu am atins `extragere_mo_bis.py`, `diacritice.py`, `populare_db.py` sau testele
  corespunzătoare (consolidare) — sunt ale celuilalt tester, conform instrucțiunii.
- Nu am găsit suspiciuni de bug în codul coder-ului: derivarea regexului, dedup-ul,
  ordinea și izolarea per-dovadă par corecte față de spec.

## Comanda exactă pentru planner
```powershell
cd D:\Omnia-MVP-r26
python -m pytest -q
```
Dacă planner-ul vrea să ruleze doar fișierele atinse de mine:
```powershell
python -m pytest -q tests/test_api_integration.py tests/test_citation_passages.py tests/test_ui_static.py tests/test_citation_modificari.py
```
Notă: testele Markdown/citare/modificari din `test_ui_static.py` (care rulează cod JS
prin `node`) se sar automat (`pytest.skip`) dacă `node` nu e pe `PATH` — nu vor apărea
ca eșec, ci ca `skipped`.
