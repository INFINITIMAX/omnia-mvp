# R23 — Tester

Worktree: `D:\Omnia-MVP-r23-gen`, branch `feat/r23-evaluare-completa`. Citește `R23-coder.md` (rundele 1–3) și `R23-coder-raport.md`. Cod: `retrieval_eval.py` (opțiunea `--generare`).

## Starea verificată de planner
- Fără `--generare`: comportament și raport neschimbate (`set_valid`); `--generare` fără `--run` → `generare_requires_run`, exit 2.
- Rulare reală `--run --generare`: 30 cazuri, 23 embedding-uri, 24 generări; rezultate finale: 21 `raspuns`, 3 `eroare_generare:ProviderUnavailableError` (trunchiere la `max_tokens`, vizibil pe site ca 503), 6 `refuz_cautare`. 21/21 răspunsuri cu citate literale; 20 citează articolul așteptat.
- `python -m pytest -q`: 1217 passed.

## Sarcina — teste în `tests/test_retrieval_eval.py`, fără rețea și fără DB real
1. Fără `--generare`, nicio construcție de generator (fake care pică dacă e apelat) și raport/sumar identic cu cel de dinainte.
2. `--generare` fără `--run` → exit 2 și niciun apel.
3. Clasificarea `rezultat_final`: `found` + generare `answered` → `raspuns`; refuz de căutare / `out_of_scope` → `refuz_cautare` fără generare; `UngroundedReferenceError` → `refuz_generare_unsupported`; `MissingCitationError`, pasaj invalid, `ProviderUnavailableError` **fără cauză** (răspuns invalid/trunchiat) → `eroare_generare:<Clasa>` și rularea continuă; `ProviderUnavailableError` **cu cauză** `AnthropicError` (rețea/credit) → rularea se oprește.
4. `vizibil_utilizator` corect pentru fiecare clasă (200 + `unsupported_answer`; 503 pentru erori; `None` altfel).
5. Metrici: `citeaza_asteptat` (articol exact și copil; document greșit → fals), `citate_literale` (citat care nu apare literal → fals), `declara_lipsa` (inclusiv „nu se regăsește” fără diacritice), plafonul de 30 de generări (inclusiv reîncercarea), sumarul `generare` (distribuție, erori pe clasă, contoare), stdout ASCII.
6. Raportul nu conține chei; citatele sunt tăiate la 300 de caractere.

## Constrângeri
Scrii doar în `tests/`. Nu rula comenzi. Fără modificări de producție; bug suspectat → raportezi. Fiecare test trebuie să poată pica. Raport în `docs/handoff/R23-tester-raport.md`.
