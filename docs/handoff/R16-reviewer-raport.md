# R16 — raport Reviewer (transcris integral de planner, 27-09-2026)

APROBAT — coder și tester.

## Ce am verificat
- `chunking_core.py`: dedup pe `_normalizeaza_pentru_dedup` (linia 118, 284-288), regula "titlu de capitol cu un nivel" (`PATTERN_TITLU_CAPITOL_SIMPLU` linia 42, `_este_titlu_capitol_simplu_valid` 388-405, `_propaga_titluri_capitol_simplu` 476-495), regula 3b subpuncte strict-crescătoare (`_aplica_split_secundar` 559-566), fix-ul cifrei lipite + cuvinte noi de trimitere ruptă (`_este_referinta_rupta` 350-385, `_CUVINTE_TRIMITERE_RUPTA` 329-332).
- `reimport_approved.py` linia 532: `main()` folosește acum `ensure_ascii=True`; linia 135 (altă funcție, scriere pe disc) a rămas `ensure_ascii=False`, cum cerea task-ul ("nu schimba altceva").
- Am citit rapoartele coder+tester și textul din `documente_noi/i5_2022/extracted.txt` (rândurile citate) pentru a verifica exemplul capitolului "4. Elemente generale de calcul".
- Diff-ul rămâne strict în `chunking_core.py`, `reimport_approved.py`, `tests/*`, `docs/handoff/*` — nimic atins din `retrieval_core.py`, `main.py`, `generation_core.py`, `supabase/`, `.env`, `documente_noi/`.

## Coder — fără finding-uri
- Task 1 (dedup normalizat): cheia e normalizată doar pentru comparare; `articol` stocat rămâne forma brută a variantei câștigătoare — corect, nu schimbă contractul DB.
- Task 2 (titlu de capitol cu un nivel): validarea cere explicit copil direct la marcajul imediat următor (`_este_titlu_capitol_simplu_valid`), deci enumerările simple ("1. text… 2. text…" fără "1.1.") nu sunt afectate — am confirmat logic că respinge corect acest caz.
- Task 3b (subpuncte care reîncep): implementat exact ca "strict crescător" (nu +1 obligatoriu), documentat corect în comentarii.
- Runda 2 (regresie NP 010): fix-ul cifrei lipite e restrâns la `pas == 0` (fără spațiu real) — nu afectează cazul cu spațiu real, cum cerea task-ul. Coder-ul a găsit proactiv un al doilea caz similar (rândul 2817, `4.2.2, (30)`) nemenționat în dovezi, l-a verificat și documentat — semn bun, nu cod în plus nejustificat.
- Nu am găsit cod nenecesar: fiecare funcție/pattern nou corespunde direct unui punct din task. Câmpul nou `titlu_capitol` e justificat (evită dublă procesare în `_contopeste_titluri`).
- Riscurile semnalate onest de coder însuși (regex generic `PATTERN_TITLU_CAPITOL_SIMPLU` neverificat pe NP004/I9/NP091) sunt acoperite de dovezile planner-ului (acoperire neschimbată/mai bună pe toate cele 9) și de testul de neconsecutivitate al tester-ului.

## Tester — fără finding-uri
- Testele sunt discriminante, nu trec necondiționat: fiecare are un scenariu negativ sau izolează exact regula nouă (ex. `3.2.(B)`/`3.2.(b)` chiar depinde de normalizare, spre deosebire de exemplul `6.1.1`/`6.1.1.` din task, unde tester-ul a semnalat onest în raport că nu izolează fix-ul singur — și a compensat cu testul de caz corect).
- Control negative prezente unde contează: `3.2.(b)` vs `3.2.(c)` (nu se confundă), enumerare simplă fără copil (nu devine titlu), subpuncte strict-crescătoare neconsecutive (1,2,4,7) se despart normal, cifră lipită fără cuvânt de trimitere (izolează regula generică separat de lista de cuvinte).
- Niciun test cu aserțiuni slabe tip `assertIsNotNone`; toate verifică valori/conținut concret.
- Nu am găsit redundanțe reale — fiecare test acoperă o combinație distinctă.
- Test `test_main_tipareste_json_ascii...`: verifică explicit `.encode("ascii")` (reproduce eroarea reală cp1252) + conținut JSON corect — solid.
- Scope respectat: doar `tests/`.

Concluzie: aprob ambele livrări fără rezerve. Pytest 1126 passed conform dovezilor planner-ului rămâne referința pentru integrare.

---

## Decizia planner-ului
- R16 acceptat local; PR către `main` pentru aprobarea lui Lucian.
- După merge: reimport prin `reimport_approved.py --commit` pentru toate cele 9 documente (fiecare trece poarta D24 în dry-run local), apoi deploy nu e necesar (fără schimbări în rutele runtime), verificare read-only a zero articole neconsecutive în DB și un smoke real `/intreaba` cu aprobare.
