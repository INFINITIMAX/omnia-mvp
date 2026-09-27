# R14 — Reviewer: chunker unificat (cod + teste)

Worktree: `D:\Omnia-MVP-r14-chunker`, branch `feat/r14-chunker-unificat`. Diff de revizuit: `git diff origin/main...HEAD` (poți citi fișierele direct; nu rulezi comenzi).

Context: `docs/handoff/R14-coder.md` (sarcina + rundele 1–7 cu dovezile planner-ului), `R14-coder-raport.md`, `R14-tester.md`, `R14-tester-raport.md`, `docs/DECISIONS.md` (în special D18, D20, D23), `AGENTS.md`.

Dovezi planner: `python -m pytest -q` cu `documente_noi` disponibil local → **1071 passed**. Acoperire față de textul brut (vechi → nou): P 118/1 96,3% → 99,4% (plus 811/811 articole „Art.” proprii, față de 33), I7 79,8% → 95,9%, NP 057 83,8% → 88,5%, I5 93,5% → 97,9%; restul ≥ ca înainte, cu excepția colofonului/preambulului eliminate intenționat.

## Ce verifici
1. **Coder:** cod inutil sau în plus față de sarcină; reguli care pot pierde conținut în tăcere; fals-pozitive ale regulilor noi pe alte formate de normative; complexitate nejustificată în `chunking_core.py` (~500 linii); comportament schimbat în `populare_db.py`, `manual_ingestion_preflight.py` în afara chunking-ului; corectitudinea și siguranța SQL în `retrieval_core.find_exact` (parametrizare, filtrul `approved`, preferința exactă vs. copii, `LIKE` cu identificatori `[a-z0-9().-]`); `_is_known_article` (prefix cu punct).
2. **Tester:** teste redundante; teste care ar trece indiferent de cod; teste fragile (praguri de lungime); dacă testele de acoperire și 811/811 apără realmente regresiile găsite.
3. **Contracte:** D18 (virgula delimitatoare) respectat; nimic nu atinge generarea, pasajele D20 sau statusurile documentelor.

## Constrângeri
Read-only. Nu edita, nu rula comenzi. Întoarce verdictul (APROBAT / RESPINS cu motive), finding-urile ordonate după severitate cu fișier:linie și dovadă, separat pentru coder și tester. Planner-ul transcrie verdictul integral în `docs/handoff/R14-reviewer-raport.md`.
