# R27 — Tester

Worktree `D:\Omnia-MVP-r27`, commit `793aa45`. Citește `R27-coder.md`, `R27-coder-raport.md`.

## Starea verificată de planner
- Corectură planner după coder: cratima definiției se caută **doar pe același rând** (altfel I7 „4.1.4.2.2.2. sau” + „-” pe rândul următor devenea articol și schimba chunk-urile I7).
- Real: P 118/3 → definițiile 2.1–2.64 (+ 2.19.x) articole proprii, `2.56` = „semnal de confirmare alarmă…”, 1.7 nu mai conține definiții; i5, i7, i9, np004, np010, np057, p118_1, spitale → chunk-uri identice cu `main`.
- P 118/2: se schimbă (33.5 din Anexa 33 e recunoscut, dar Anexa 33 „Terminologie” se ciocnește numeric cu capitolul 33 — problemă preexistentă, va fi R28). P 118/2 **nu** se reimportă în R27.
- `python -m pytest -q` → 1341 passed.

## Sarcina (sintetic, fără fișierele reale)
1. Definiție cu literă mică + cratimă/en dash pe același rând (cu spații, lipită „-conexiune”, după paranteze „(PIF) -”, en dash „– ”, sub-nivel `2.19.18.1.`) → articol propriu.
2. Literă mică **fără** cratimă pe același rând → rămâne trimitere/continuare (inclusiv cazul I7: cratimă doar pe rândul următor).
3. Majusculă → comportament neschimbat (regresie).
4. `reimport_approved.DOCUMENTE_APROBATE`/`PRAGURI_ACOPERIRE` conțin cele două documente noi cu sursele și pragurile din brief; dacă `tests/test_populare_db.py` are o listă paralelă de praguri pe documente reale, sincronizeaz-o (0.98 / 0.94) și spune de ce.

Scrii doar în `tests/`. Nu rula comenzi. Raport: `docs/handoff/R27-tester-raport.md`.
