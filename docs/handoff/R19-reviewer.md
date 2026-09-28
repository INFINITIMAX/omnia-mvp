# R19 — Reviewer

Worktree: `D:\Omnia-MVP-r19-cautare`, branch `feat/r19-corectitudine-cautare`; `main` în `D:\Omnia-MVP`. Citește `R19-coder.md` (inclusiv Runda 2), `R19-coder-raport.md`, `R19-tester.md`, `R19-tester-raport.md`, `docs/DECISIONS.md` (D25 nou, D11–D14, D20–D22), `AGENTS.md`.

Dovezi planner: `python -m pytest -q` → **1189 passed**. Evaluare reală pe `evaluare/set_aur.json`: 25/30 → **27/30** (exact 4/4, semantic 18/20, negativ 5/6); recall@1 0,75; recall@5 0,875. Erori rămase explicate: P118-05 (anexe P 118/1 numerotate greșit), NP015-03 (sub prag, decizie D25), NEG-04 (depinde de refuzul la generare).

## Ce verifici
1. **Refuzul pentru cod necunoscut:** fals-pozitive realiste pe întrebări obișnuite (numere de tabel, „Anexa I 5”, unități, ani, „[C1]”)? cod aprobat scris în altă formă decât aliasul (ex. „P118-1/2025”, „NP10-2022”) → refuz greșit? interacțiunea cu D11–D14 (restricții „doar din”).
2. **Mutarea în `normative_codes.py`:** comportament identic în `generation_core.py` (detecția referințelor inventate, D-urile de generare)? fără import circular.
3. **Ruta semantică:** eliminarea `ambiguous_article` sigură dat fiind invariantul R16? gruparea după `chunk_order` corectă, fără pierderi sau duplicate, compatibilă cu `_limit_context`? ruta exactă neschimbată.
4. **`SEMANTIC_TOP_K = 10`:** impact pe `MAX_CONTEXT_CHARS` și pe costul generării (tokeni de intrare).
5. **Tester:** testele actualizate păstrează intenția originală; testele noi pot pica; niciun test adaptat fără motiv.

Read-only, fără comenzi. Verdict APROBAT/RESPINS, finding-uri pe severitate cu fișier:linie, separat coder/tester, max 600 de cuvinte.
