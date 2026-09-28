# R19 — Tester

Worktree: `D:\Omnia-MVP-r19-cautare`, branch `feat/r19-corectitudine-cautare`, commit `86b2205`. Citește `R19-coder.md` (inclusiv Runda 2) și `R19-coder-raport.md`.

## Starea verificată de planner
- Evaluare reală pe `evaluare/set_aur.json`: 25/30 → **27/30** (P118-02 găsit; P118-04, NP091-01 corecte; NEG-01 refuzat ca `ambiguous_reference`).
- `python -m pytest -q`: 105 eșecuri, **toate schimbări intenționate de comportament**:
  - testele care verifică `top_k == 5` (acum `SEMANTIC_TOP_K = 10`) în `tests/test_multi_document_retrieval.py`, `tests/test_api_integration.py`, `tests/test_retrieval_core.py`;
  - `test_multi_document_alias_slash_nu_potriveste_interiorul_altui_token` (3 parametri): verifica explicit că un cod necunoscut *nu* cere clarificare — politica nouă e opusă;
  - posibil un test care verifica refuzul `ambiguous_article` pe ruta **semantică** (politica nouă: doar pe ruta exactă).

## Sarcina
1. **Actualizează testele de mai sus** la noul comportament. Unde un test compară `top_k`, folosește constanta `retrieval_core.SEMANTIC_TOP_K`, nu cifra. Pentru testul de aliasuri, păstrează verificarea granițelor aliasului (`document_id is None`) și cere acum `requires_clarification` adevărat pentru token-urile care arată a cod normativ. Dacă vreun alt test pică dintr-un motiv care **nu** e unul dintre cele trei, **nu-l adapta**: raportează-l ca posibil bug.
2. **Teste noi:**
   - `normative_codes.gaseste_referinte_normative`: pozitive (`NP 127-2010`, `I 13-2015`, `P 118/2-2013`, `SR EN 12831`, `STAS 6648`), negative („ANEXA I 5-2”, „[C1]”, „p. 12-14”, numere de articol ca „art. 4.4”);
   - `generation_core` produce aceleași referințe ca înainte (echivalența wrapper-ului; folosește exemple din testele existente);
   - parser: cod necunoscut cu articol → `requires_clarification`; cod aprobat cu articol → neschimbat; întrebare fără cod → neschimbat; cod aprobat și cod necunoscut în aceeași întrebare → `requires_clarification`; nicio apelare de embedder/repository când se refuză;
   - ruta semantică: fragmente neconsecutive ale aceluiași articol → `found`, grupate și ordonate după `chunk_order` la poziția celui mai bun scor; ruta exactă cu fragmente neconsecutive → tot `ambiguous_article`.

## Constrângeri
Scrii doar în `tests/`. Nu rula comenzi. Fără modificări de producție. Fiecare test trebuie să poată pica. Raport în `docs/handoff/R19-tester-raport.md` (lista testelor actualizate și motivul fiecăruia).
