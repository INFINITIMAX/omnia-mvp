# R19 — Tester: raport

## Fișiere modificate

### `tests/test_multi_document_retrieval.py`
- Import `SEMANTIC_TOP_K` din `retrieval_core`; `assert_global`, `assert_scoped_once` și
  `test_d12_scope_curent_pastreaza_ultimele_trei_intrebari_in_embedding` folosesc acum
  constanta în loc de `5`. Ar pica dacă `SEMANTIC_TOP_K` s-ar schimba din nou fără să se
  actualizeze apelul real către repository.
- `test_multi_document_alias_slash_nu_potriveste_interiorul_altui_token` — redusă la cele
  3 tokenuri pe care `gaseste_referinte_normative` NU le detectează deloc ca și cod
  (`XP 118/1-2025`, `XP11812025`, `P11812025X` — fără frontieră de cuvânt înaintea lui P,
  respectiv fără separator între grupurile numerice). Verifică `document_id is None` și
  `not requires_clarification`, ca înainte.
- Test nou `test_multi_document_alias_slash_cod_asemanator_dar_negasit_cere_clarificare`
  pentru celelalte 3 tokenuri (`P 118/1-2025X`, `P 118/1-20250`, `P 118/12-2025`) — au
  formă compusă validă de cod, deci sunt detectate, dar nu se suprapun complet cu aliasul
  aprobat (caracter alfanumeric imediat adiacent) → `requires_clarification` acum True
  (politica D25). Ar pica dacă parser-ul ar reveni la vechiul comportament (ignoră codul
  necunoscut) sau dacă granița aliasului s-ar relaxa greșit să accepte aceste tokenuri.

### `tests/test_api_integration.py`
- Import `SEMANTIC_TOP_K`; cele 6 assert-uri pe `_interogari_semantice(connection)` cu
  `5` hardcodat (liniile fostei versiuni ~1854, 1875, 1971, 1996, 2069, 2085) folosesc
  acum constanta. Ar pica la orice regresie a `top_k`-ului trimis efectiv la interogarea
  SQL prin API.

### `tests/test_retrieval_core.py`
- Import `SEMANTIC_TOP_K`; cele 4 assert-uri `repository.top_k == 5` (testele D11 de
  context) → `== SEMANTIC_TOP_K`.
- `test_semantic_refuza_chunkuri_conflictuale_neconsecutive` **eliminat** (verifica
  politica veche, opusă celei noi) și înlocuit cu:
  - `test_exact_refuza_chunkuri_conflictuale_neconsecutive_cu_gol_intre_pozitii` (nou):
    regresie explicită — ruta **exactă** tot refuză cu `ambiguous_article` la un gol
    între poziții (chunk_order 40, 42, fără 41). Ar pica dacă cineva ar elimina refuzul
    și pe ruta exactă, nu doar pe cea semantică.
  - `test_semantic_grupeaza_fragmentele_neconsecutive_ale_aceluiasi_articol_pe_pozitia_celui_mai_bun_scor`
    (nou): trei dovezi semantice, două din același articol cu chunk_order neconsecutiv
    (40 și 42) intercalate cu o dovadă dintr-alt articol; verifică `status == "found"`
    (nu mai refuză) și ordinea exactă a rezultatului (`hash-c, hash-a, hash-b` / chunk_order
    `40, 42, 10`) — grupul e plasat la poziția primei apariții (a celui mai bun scor), dar
    reordonat intern după `chunk_order`. Ar pica dacă gruparea ar păstra ordinea brută
    după scor, dacă nu ar reordona intern, sau dacă ruta semantică ar reveni la refuz.
  - Bloc nou D25 (5 teste): `test_d25_cod_de_normativ_necunoscut_cu_articol_cere_clarificare`,
    `test_d25_cod_de_normativ_aprobat_cu_articol_ramane_neschimbat`,
    `test_d25_intrebare_fara_niciun_cod_ramane_neschimbata`,
    `test_d25_cod_aprobat_si_cod_necunoscut_in_aceeasi_intrebare_cere_clarificare`,
    `test_d25_refuzul_nu_apeleaza_embedder_sau_repository` — acoperă exact cele 4 cazuri
    cerute plus verificarea „nicio apelare de embedder/repository la refuz”. Fiecare ar
    pica dacă `ArticleParser.parse` ar renunța la verificarea D25, ar refuza greșit un cod
    aprobat sau o întrebare fără cod, sau dacă refuzul ar mai ajunge să apeleze
    embedder/repository.

### `tests/test_generation_core.py`
- Import `_normative_references` (funcție privată, wrapper peste `normative_codes`).
- Test nou `test_normative_references_extrage_acelasi_text_ca_inainte_de_mutarea_in_modul`:
  verifică pe exemple reale din testele existente (`STAS 6648`, `SR EN ISO 52016-1`, text
  fără cod) că textul extras și reconstrucția `text[start:end].strip()` rămân identice cu
  ce producea vechea implementare bazată pe `match.group(0).strip()`. Ar pica dacă
  wrapper-ul ar strica pozițiile sau ar întoarce alt text.

### `tests/test_normative_codes.py` (nou)
Teste directe pentru `gaseste_referinte_normative`, independent de cei doi clienți:
- pozitive: `NP 127-2010`, `I 13-2015`, `P 118/2-2013`, `SR EN 12831`, `STAS 6648`;
- negative: `ANEXA I 5-2` (cuvânt de structură), `[C1]` (fără formă compusă), `p. 12-14`
  (fără majusculă), `art. 4.4` (fără prefix de cod);
- filtrul de incluziune (`SR EN 12831` → o singură potrivire, cea mai lungă);
- reconstrucția poziției pentru un cod cu bară (`STAS 6648/1-82`).
Fiecare ar pica dacă tiparele/filtrul de excludere s-ar relaxa sau restrânge greșit.

## Ce nu am acoperit și de ce
- Nu am scris teste noi pentru `RepositoryFake`/SQL-ul propriu-zis al `find_semantic` —
  neschimbat de R19, deja acoperit.
- Nu am adaptat `test_retrieval_eval.py`, `test_real_grounding_eval.py`, `test_eval_set.py`,
  `test_glyph_mapping.py` — verificate, nu conțin `top_k` hardcodat sau presupuneri despre
  `ambiguous_article` pe ruta semantică specifică R19; nu erau afectate.
- Nu am rulat `evaluare/set_aur.json` (nu am unelte de rulare; planner-ul a raportat deja
  27/30 pe commit-ul curent).

## Suspiciuni de bug (nu le-am reparat)
Niciuna nouă găsită în afara riscurilor deja semnalate de coder în raportul lui (fals-pozitive
D25 pe coduri disabled/scrise diferit față de catalog) — acelea sunt comportament intenționat
al politicii noi, nu bug, și nu le-am testat ca eșec.

## Comandă pentru planner
```powershell
cd D:\Omnia-MVP-r19-cautare
python -m pytest -q
```
Pentru rulare țintită doar pe fișierele atinse:
```powershell
python -m pytest -q tests/test_normative_codes.py tests/test_generation_core.py tests/test_retrieval_core.py tests/test_multi_document_retrieval.py tests/test_api_integration.py
```
