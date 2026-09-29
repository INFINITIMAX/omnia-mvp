# R26-D — Coder: marcajul de proveniență în toate bucățile unui articol modificat

Worktree `D:\Omnia-MVP-r26`, branch `feat/r26-p118-consolidat` (commit `16d4c2d`). Context: `R26-spec.md`, `R26-B-coder.md`, `R26-C-coder.md`, `docs/DECISIONS.md` D27.

## Problema (verificată de planner pe textele consolidate reale)
Consolidarea pune marcajul `[Text modificat prin Ordinul nr. …]` pe rând propriu **după** textul modificat. Chunker-ul împarte apoi articolul în bucăți: pe alineate (`3.3.1.(1)`, `3.3.1.(2)`, …, `3.3.1.(4)`) și/sau la limita de 1000 de caractere. Marcajul ajunge doar în **ultima** bucată. Exemplu P 118/3: punctul 3.3.1 e înlocuit integral prin Ordinul 6.025/2018, dar citarea lui `3.3.1.(1)` nu arată modificarea — exact prevederea-cheie.

## Sarcina
1. `chunking_core.creeaza_chunkuri`: pas final (după limita de caractere). Grupează bucățile după **articolul de bază** (identificatorul fără sufixul de alineat: `3.3.1.(1)` → `3.3.1.`; bucățile de lungime cu același identificator aparțin aceluiași articol). Pentru fiecare articol în care cel puțin o bucată conține un marcaj `PATTERN_MARCAJ_PROVENIENTA`, **fiecare** bucată a articolului care nu conține deja un marcaj pentru același ordin primește, pe un rând final propriu, marcajul la nivel de articol:
   `[Articol cu text modificat prin Ordinul nr. 6.025/2018, publicat în Monitorul Oficial nr. 977 din 19.11.2018]`
   (`modificat` / `introdus` / `abrogat` după tipul marcajului original; mai multe ordine sau tipuri → câte un rând per marcaj distinct, în ordinea primei apariții). Textele fără marcaje rămân **identice** byte cu byte (celelalte 9 documente nu se schimbă). Bucata poate depăși limita de caractere cu lungimea marcajelor adăugate.
   `PATTERN_MARCAJ_PROVENIENTA` trebuie să recunoască și forma nouă (ca tăietura la 1000 să nu o rupă).
2. `generation_core._MODIFICATION_MARKER`: acceptă și forma `Articol cu text (modificat|introdus|abrogat) prin …`. `modificari` conține textul exact al marcajului (fără paranteze), deci utilizatorul vede fie „Text modificat prin …” (bucata cu textul nou), fie „Articol cu text modificat prin …” (celelalte bucăți). Regula 11 din prompt menționează ambele forme.
3. `docs/DECISIONS.md` D27: o frază despre marcajul la nivel de articol.

## Constrângeri
Nu atinge `consolidare_normative.py`, `extragere_mo_bis.py`, `diacritice.py`, `populare_db.py`, `main.py`, `static/`, `tests/`. Nu rula comenzi, nu scrie teste. Raport: `docs/handoff/R26-D-coder-raport.md`.
