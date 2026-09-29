# R26 — Reviewer (partea 1: consolidare, citare, marcaje în chunker)

Worktree `D:\Omnia-MVP-r26`, branch `feat/r26-p118-consolidat`. Bază: `main` `d3bd129` (copie de referință: `D:\Omnia-MVP`). Diff: commit-urile `f7e209e`..`6e09fe5`. Partea 2 (extragere MO bis, R26-A) va avea review separat.

Citește: `R26-spec.md`, `docs/DECISIONS.md` (D27 + Runda 2), brief-urile și rapoartele `R26-B-*` (inclusiv rundele 2–3), `R26-C-*`, `R26-D-*`.

## Corecturi făcute direct de planner (verifică-le separat)
1. `consolidare_normative.aplica_operatii`: `\n` după textul nou dacă lipsește (altfel punctul următor se lipea de marcaj).
2. `_verifica_final`: compară după înlocuirile globale ale ordinului.
3. Gardă `PATTERN_INSTRUCTIUNE_ASCUNSA` în `segmenteaza_ordin` (numerotare cu goluri) + testul actualizat.
4. `chunking_core`: tăietura la limită nu cade în marcaj (se mută **înaintea** lui); `_respecta_limita_cu_marcaje` re-împarte bucățile care depășesc 1000 după propagare; `_aplica_limita_caractere(limita=…)`.
5. Hash-uri CSP recalculate (`main.py`).
6. Manifest P 118/3 (local, în afara Git): înlocuirile globale restrânse la „detectare, semnalizare și avertizare” + varianta cu majuscule.

## Starea verificată de planner
- `python -m pytest -q` → 1316 passed, 30 skipped.
- Celelalte 8 documente cu `extracted.txt` local: `creeaza_chunkuri` dă rezultat **identic** cu `main`.
- Texte consolidate reale: P 118/2 1865 chunk-uri, P 118/3 384; toate ≤1000 caractere; 0 marcaje rupte; 0 articole cu marcaj doar în unele bucăți; contractul importerului (`manual_ingestion_import._valideaza_chunkuri`) trece; niciun cuvânt pierdut față de versiunea anterioară a chunker-ului.

## Ce verifici
1. **Coder vs. brief-uri**: cod inutil? Tipuri de operații corecte? Fail-closed real (nu există cale prin care o țintă ambiguă sau un text nou absent din ordin să treacă)?
2. **D27 onestitate**: poate apărea un marcaj pe text care NU a fost modificat, în afară de marcajul la nivel de articol (care spune explicit „Articol cu text modificat”)? Poate lipsi marcajul de pe text modificat? Regex-urile din `generation_core` și `chunking_core` sunt coerente? Forma `[modificat prin …]` (fără „Articol cu text”) acceptată de regex e o relaxare nedorită?
3. **Regresii**: schimbările din `chunking_core` pot afecta documente fără marcaje? `CitationResponse`/UI/CSP.
4. **Teste** (`test_consolidare_normative.py`, `test_chunking_core.py` noi, `test_citation_modificari.py`, actualizările din `test_api_integration.py`, `test_citation_passages.py`, `test_ui_static.py`): redundante, trec oricum, aserțiuni slăbite? Lipsesc teste pentru corecturile planner 4 (limita cu marcaje propagate) și `abroga_subunitate`?

Verdict: APROBAT / RESPINS cu listă (fișier:linie, gravitate, motiv). Nu modifici nimic.
