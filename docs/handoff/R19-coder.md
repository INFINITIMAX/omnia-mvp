# R19 — Coder: corectitudinea căutării, pe baza evaluării R18

Worktree: `D:\Omnia-MVP-r19-cautare`, branch `feat/r19-corectitudine-cautare` (din `main` `d5a95c0`). Aprobat de Lucian 28-09-2026.

## Dovezi
Evaluare pe `evaluare/set_aur.json` (setul curent, 30 cazuri, inclusiv 3 negative noi din afara corpusului), cod `main` neschimbat: **25/30**; exact 4/4, semantic 17/20, negativ 4/6.

1. **NEG-01 „Ce prevede art. 5.12 din I 13-2015?”** → a răspuns din `i7_2011:5.12`. I 13-2015 e `disabled` (D23), codul nu e în catalogul aprobat; `ArticleParser.parse` (`retrieval_core.py:156+`) ignoră codul necunoscut, rămâne „art. 5.12” fără document → rută exactă pe toate documentele. Răspuns greșit dat cu încredere.
2. **P118-02** (pereți antifoc → `2.3.2.1.2`): articolul corect e pe **locul 9** (scor 0,712; locul 5 = 0,715). `SEMANTIC_TOP_K = 5` (`retrieval_core.py:13`); `MAX_CONTEXT_CHARS = 12000`, chunk-uri ≤1000 caractere → 10 dovezi încap.
3. **Pragul `SEMANTIC_MIN_SCORE = 0.50` rămâne neschimbat** (decizie planner, pe date): scorurile top-1 ale întrebărilor corecte (0,494–0,760) și ale celor fără răspuns (0,439–0,549) se suprapun; niciun prag nu le separă. Nu atinge pragul.

## Sarcina
1. **Coduri de normativ necunoscute → refuz.** Mută `_NORMATIVE_REFERENCE_PATTERNS` și ajutoarele lor (`_CODE_TAIL`, cuvintele de structură de excludere și funcția care le aplică) din `generation_core.py` (liniile ~86–140) într-un modul nou `normative_codes.py`, cu o funcție publică de tip `gaseste_referinte_normative(text) -> list[tuple[int, int]]` (poziții), folosită de `generation_core.py` cu comportament **identic** (testele existente trebuie să treacă neschimbate) și de `retrieval_core.py`. În `ArticleParser.parse`: dacă întrebarea conține o referință normativă care **nu se suprapune** cu niciun alias aprobat găsit, întoarce `ParsedReference(None, None, False, requires_clarification=True)` (→ `ambiguous_reference`), înainte de orice rută și fără embedding. Nu schimba restul logicii de aliasuri/restricții (D11–D14).
2. **`SEMANTIC_TOP_K = 10`.**
3. Nu atinge: `main.py`, `chunking_core.py`, `static/`, `supabase/`, `.env`, `documente_noi/`, `evaluare/`, pragul semantic.

## Constrângeri dure
Nu rula comenzi. Nu scrie teste noi (Tester-ul). Fără comentarii inutile. Raport: `docs/handoff/R19-coder-raport.md` (fișiere, cum ai evitat importul circular, riscuri: fals-pozitive ale tiparelor pe întrebări obișnuite).
