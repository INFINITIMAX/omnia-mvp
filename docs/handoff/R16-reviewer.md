# R16 — Reviewer

Worktree: `D:\Omnia-MVP-r16-dedup`, branch `fix/r16-dedup-normalizat`; `main` în `D:\Omnia-MVP`. Citește `R16-coder.md` (inclusiv 3b și Runda 2), `R16-coder-raport.md`, `R16-tester.md`, `R16-tester-raport.md`, `docs/DECISIONS.md` (D18, D24).

Dovezi planner: `python -m pytest -q` cu `documente_noi` local → **1126 passed**. Pe textele reale: articole normalizate în chunk-uri neconsecutive 63 → **0** în toate cele 9 documente; acoperire neschimbată sau mai bună (i5 0,979; i7 0,971; i9 0,969; np004 0,923; np010 0,999; np057 0,882; p118 0,993; spitale 0,982; np091 0,989). Regresia intermediară NP 010 (0,980, prin dedup normalizat + marcaj fals „4.2.4.5 și…”) a fost reparată în runda 2.

## Ce verifici
1. **Coder:** dedup pe cheie normalizată — poate înlocui un articol real cu o variantă falsă mai lungă în alte cazuri decât cel reparat? Regula „capitol cu un nivel” — fals-pozitive (enumerări, numere de listă)? Regula 3b (fără split la subpuncte reluate) — pierde granularitate utilă sau conținut? Cifra lipită și cuvintele noi de trimitere — prea largi? `ensure_ascii` în `reimport_approved.py`. Cod inutil sau în plus.
2. **Tester:** teste care trec indiferent de cod (tester-ul a semnalat singur că exemplul `6.1.1`/`6.1.1.` nu e discriminant și a adăugat `3.2.(B)`/`3.2.(b)`), redundanțe, fragilitate.
3. **Contracte:** D18 intact; nimic în afara `chunking_core.py`, `reimport_approved.py`, `tests/`, `docs/handoff/`.

Read-only, fără comenzi. Verdict APROBAT/RESPINS, finding-uri pe severitate cu fișier:linie, separat coder/tester, max 600 de cuvinte.
