# R16 — Tester

Worktree: `D:\Omnia-MVP-r16-dedup`, branch `fix/r16-dedup-normalizat`. Citește `docs/handoff/R16-coder.md` (inclusiv 3b și Runda 2) și `R16-coder-raport.md`.

## Starea verificată de planner (textele reale, local)
Articole normalizate în chunk-uri neconsecutive: **0** în toate cele 9 documente (înainte 63). Acoperire: i5 0,979; i7 0,971; i9 0,969; np004 0,923; np010 0,999; np057 0,882; p118 0,993; spitale 0,982; np091 0,989. Număr de chunk-uri nou: i5_2022 768, i7_2011 2214, i9_2022 790, np004_03 85, np010_2022 356, np057_02 298, p118_1_2025 2862, spitale_2022 616.

## Sarcina
1. Actualizează `NUMAR_CHUNKURI_ASTEPTAT_PER_DOCUMENT` din `tests/test_populare_db.py` la valorile de mai sus.
2. Adaugă în `tests/test_populare_db.py`, cu același `skipif` pe `documente_noi`, un test parametrizat pe cele 8 documente cu `extracted.txt`: niciun `articol_normalizat` (prin funcția de normalizare a importerului) nu apare în poziții neconsecutive ale listei de chunk-uri.
3. În `tests/test_chunking_core.py`, teste sintetice (pozitiv + negativ unde are sens) pentru:
   - dedup pe forma normalizată: `6.1.1 Titlu…` și `6.1.1. Text real…` → un singur articol, varianta mai lungă; `duplicate_eliminate` crește;
   - titlu de capitol cu un nivel (`4. Elemente generale de calcul` urmat de introducere cu `(1)…` și apoi `4.1. …`): introducerea nu se lipește de articolul anterior; titlul e context pentru `4.1.`; o enumerare `1. text… 2. text…` fără copil `1.1.` nu e tratată ca titlu;
   - subpuncte care reîncep (`(1)(2)(1)(2)`) → articolul nu e împărțit pe subpuncte, rămâne cu articolul de bază (bucăți consecutive la limita de 1000); subpuncte strict crescătoare → split ca înainte;
   - cifră lipită după marcaj (`4.2.4.5 și 4.2.4.6` precedat de „de la punctele”) → nu e articol, articolul real `4.2.4.5.` își păstrează textul;
   - cuvintele noi de final de rând (`punctele`, `prevederile`…) → marcajul următor e trimitere.
4. În `tests/test_reimport_approved.py`: ieșirea JSON a `main()` e ASCII (nu poate eșua pe consola cp1252) pentru un rezultat care conține „Ț”.

## Constrângeri
Scrii doar în `tests/`. Nu rula comenzi. Nicio modificare de cod de producție; bug suspectat → raportezi. Fiecare test trebuie să poată pica. Raport în `docs/handoff/R16-tester-raport.md`.
