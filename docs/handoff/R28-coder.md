# R28 — Coder: titlurile „ANEXA NR. N” deschid regiuni de anexă (P 118/2)

Worktree `D:\Omnia-MVP-r28`, branch `fix/r28-anexe-nr` (din `main` `ce4ebee`). Aprobat de Lucian 29-09-2026.

## Dovezi (planner)
- R21 a introdus regiunile de anexă: `PATTERN_TITLU_ANEXA` (`chunking_core.py:46`) recunoaște `ANEXA 3`, `ANEXA 3.1.`, iar articolele din regiune devin `ANEXA N.<articol>` (`chunking_core.py:613-627`), ca să nu se ciocnească cu corpul.
- P 118/2 (MO 595 bis) scrie titlurile altfel: `ANEXA NR. 1`, `ANEXA NR.2`, `ANEXA Nr. 3`, `ANEXA NR.14bis` … `ANEXA NR.33` (rândurile ~11241–13754 din `documente_noi/p118_2_2013/extracted.txt`). Tiparul nu le prinde → nu există regiuni de anexă → Anexa 33 „TERMINOLOGIE” (`33.1. Instalație alternativă…` … `33.19`) se ciocnește cu capitolul 33 din corp (`33.5. Orificiile de refulare a aburului…`); chunker-ul elimină „duplicatele” (`duplicate_eliminate` 22) și se pierd definiții (ex. 33.1–33.4, 33.6, 33.7 din anexă). Finalul documentului apare și ca bucăți `1.0.`.
- Printre documentele `approved`, doar P 118/2 are titluri `ANEXA NR`. Rândurile din corp care încep cu `anexa nr. 8, la…` (literă mică) sunt trimiteri, nu titluri.

## Sarcina
1. `PATTERN_TITLU_ANEXA`: acceptă opțional `NR.`/`Nr.` (cu sau fără spațiu după punct) între `ANEXA` și număr, și sufixul `bis` (`14bis`). Numai `ANEXA` cu majuscule, ca acum. Identificatorul capturat rămâne numărul (`33`, `14bis`), deci articolele devin `ANEXA 33.33.5.` etc.
2. Nimic altceva — logica de regiune din R21 rămâne neschimbată. Dacă observi că un alt pas (cuprins, `prim_art_start`, trimiteri rupte) blochează titlurile noi, raportează cu dovezi în loc să rescrii logica.

## Criterii de acceptare (planner)
- P 118/2: articolele din anexe au prefixul `ANEXA N.`; definițiile Anexei 33 (33.1 … 33.19) apar ca `ANEXA 33.33.x.`; **niciun cuvânt pierdut** față de chunker-ul din `main` (comparație pe cuvinte, fără marcaje); `duplicate_eliminate` scade; capitolul 33 din corp rămâne `33.x.`.
- Celelalte 9 documente cu `extracted.txt` (inclusiv P 118/3): chunk-uri identice cu `main`.
- Contractul importerului (≤1000, articol valid: `ANEXA 33.33.5.` normalizat trebuie să treacă `[a-z0-9().-]+` — verifică cum normalizează importerul prefixul „ANEXA ” la P 118/1, unde există deja).

## Constrângeri
Nu atinge alte fișiere decât `chunking_core.py`. Nu rula comenzi, nu scrie teste. Raport: `docs/handoff/R28-coder-raport.md`.
