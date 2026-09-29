# R27 — Tester: raport

## Fișiere create/modificate (doar `tests/`)

### `tests/test_r27_definitii_terminologie.py` (nou)
Teste sintetice pentru `chunking_core._este_referinta_rupta`, ramura nouă R27
(definiție cu literă mică + cratimă/en dash pe același rând → articol propriu).

1. `test_definitie_cu_cratima_cu_spatii_devine_articol_propriu` — reproduce
   P1183-03 (`1.7.` vs `2.56.`). Ar pica dacă definiția ar rămâne lipită de `1.7.`
   (regresia raportată de planner) sau dacă „2.56.” nu ar apărea ca articol propriu.
2. `test_definitie_cu_cratima_lipita_de_cuvant_devine_articol_propriu` — cratimă
   lipită („-conexiune”). Ar pica dacă regex-ul de cratimă ar cere spațiu obligatoriu
   înainte/după `-`.
3. `test_definitie_cu_paranteza_inaintea_cratimei_devine_articol_propriu` —
   „(PIF) -”. Ar pica dacă paranteza chiar înaintea cratimei ar rupe potrivirea
   ferestrei de căutare.
4. `test_definitie_cu_en_dash_devine_articol_propriu` — en dash „–” (33.5, Anexa
   33). Ar pica dacă implementarea ar recunoaște doar cratima ASCII `-`.
5. `test_definitie_cu_subnivel_devine_articol_propriu` — `2.19.18.1.`. Ar pica
   dacă adâncimea numerotării ar bloca ramura nouă.
6. `test_litera_mica_fara_cratima_pe_acelasi_rand_ramane_atasata` — literă mică
   fără nicio cratimă/en dash → trebuie să rămână trimitere/continuare. Ar pica
   dacă ramura nouă ar deveni prea permisivă (orice literă mică → articol).
7. `test_i7_cratima_doar_pe_randul_urmator_nu_devine_articol` — regresia I7
   (`4.1.4.2.2.2. sau` + `-` pe rândul fizic următor). Ar pica dacă fereastra de
   căutare a cratimei ar depăși rândul curent (exact corectura cerută explicit de
   planner în brief).
8. `test_majuscula_dupa_numar_ramane_articol_indiferent_de_cratima_apropiata` —
   regresie: majusculă după număr rămâne articol necondiționat, chiar cu o
   cratimă în text apropiat. Ar pica dacă ramura nouă ar fi introdusă înaintea
   verificării de majusculă existente (ordine de branch-uri greșită), schimbând
   comportamentul deja validat.

Toate cele 8 folosesc `creeaza_chunkuri` direct, text sintetic minimal (fără
`documente_noi/`), în stilul deja existent în `test_chunking_core.py`.

### `tests/test_reimport_approved.py` (adăugat, secțiune nouă înainte de „Identitate document”)
9. `test_p118_2_si_p118_3_sunt_aprobate_cu_pragurile_din_brief` — verifică direct
   `DOCUMENTE_APROBATE["p118_2_2013"/"p118_3_2015"]` și
   `PRAGURI_ACOPERIRE[...]` (0.98/0.94). Ar pica dacă documentele ar lipsi din
   listă sau dacă pragurile ar fi greșite/inversate.
10. `test_p118_3_dry_run_trece_cu_source_key_corect` — control pozitiv end-to-end:
    `dry_run("p118_3_2015", ...)` cu `source_key` corect trece poarta cu
    `prag_acoperire == 0.94`. Ar pica dacă documentul ar fi respins ca
    `unknown_document`/`source_key_mismatch` sau dacă pragul citit efectiv la
    runtime nu ar coincide cu cel din `PRAGURI_ACOPERIRE`.

### `tests/test_populare_db.py` (sincronizare, cerută explicit în task pct. 4)
Am adăugat `"p118_2_2013": 0.98` și `"p118_3_2015": 0.94` în
`PRAG_ACOPERIRE_MINIM_PER_DOCUMENT` (linia ~489), cu comentariu explicit al
motivului. **Nu** am atins `NUMAR_CHUNKURI_ASTEPTAT_PER_DOCUMENT` — acolo e nevoie
de numărul real de chunk-uri produs de codul curent pe cele două documente noi
(un test de regresie exact, nu un prag), pe care nu am cum să-l calculez fără
să rulez comenzi. Planner-ul trebuie să ruleze `pytest` o dată cu `documente_noi/`
prezent, să citească numărul real de chunk-uri pentru `p118_2_2013`/`p118_3_2015`
din output și să-l adauge acolo dacă vrea invarianta „nu se schimbă
fragmentarea” și pentru aceste două documente (eu nu am acces la valoarea
corectă, iar a inventa un număr ar face testul fals — fie mereu verde cu o
valoare greșit calculată manual, fie fals-roșu la prima rulare).

## Ce nu am acoperit și de ce
- Nu am testat pe `documente_noi/*/extracted.txt` reale (P 118/2, P 118/3
  complete) — task-ul cere teste sintetice, iar fișierele reale sunt oricum
  acoperite de `test_populare_db.py` (skipif dacă `documente_noi` lipsește) și de
  rularea planner-ului (1341 passed, raportată în brief).
- Nu am adăugat testul „secțiune TERMINOLOGIE/DEFINIȚII” din al doilea criteriu
  opțional al task-ului coder — coder-ul a ales explicit varianta simplă (doar
  cratimă/en dash în fereastră), fără acel criteriu secundar, deci nu există cod
  de acoperit pentru el.
- Nu am adăugat un test explicit pentru contractul importerului (`≤1000 caractere,
  articol valid`) pe chunk-urile noi din P 118/3 — task-ul zice că acel criteriu
  e „verificat de planner”, nu de tester, și necesită documentul real.

## Suspiciuni de bug
Niciuna găsită. Codul coder-ului respectă exact corectura planner-ului (cratima
căutată doar pe același rând, via `urmator.split("\n", 1)[0]`), verificat direct
în `chunking_core.py` liniile 504-511.

## Comanda exactă pentru planner
```powershell
cd D:\Omnia-MVP-r27
python -m pytest tests/test_r27_definitii_terminologie.py tests/test_reimport_approved.py tests/test_populare_db.py -q
```
sau, pentru rulare completă:
```powershell
cd D:\Omnia-MVP-r27
python -m pytest -q
```
