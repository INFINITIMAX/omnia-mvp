# R27 — Reviewer

Worktree `D:\Omnia-MVP-r27`, branch `fix/r27-definitii`, bază `main` `916f40f` (`D:\Omnia-MVP`). Citește `R27-coder.md`, `R27-coder-raport.md`, `R27-tester.md`, `R27-tester-raport.md`.

## Starea verificată de planner
- `python -m pytest -q` (cu documentele reale) → 1383 passed.
- Corectură planner: cratima definiției se caută doar pe același rând (I7 „4.1.4.2.2.2. sau” + „-” pe rândul următor).
- Real: P 118/3 2.1–2.64 articole proprii; i5, i7, i9, np004, np010, np057, p118_1, spitale identice cu `main`. P 118/2 se schimbă din cauza coliziunii Anexa 33 / capitolul 33 (preexistentă → R28); **P 118/2 nu se reimportă** în R27, doar P 118/3.

## Ce verifici
1. Cod inutil față de brief? Regula poate transforma în articol ceva ce nu e definiție (trimiteri „conform 2.5. din …”, enumerări, text cu cratimă obișnuită pe același rând după o trimitere cu literă mică)? Dă exemple concrete de risc, dacă există.
2. Teste: acoperă cazurile din brief, pot pica, nu sunt redundante?
3. `reimport_approved`: sursele și pragurile noi coerente cu metadata (`source_key` `P118_2_2013_consolidat.txt` / `P118_3_2015_consolidat.txt`)?

Verdict: APROBAT / RESPINS cu listă. Nu modifici nimic.
