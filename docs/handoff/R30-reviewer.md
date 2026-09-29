# R30 — Reviewer

Worktree `D:\Omnia-MVP-r30`, branch `feat/r30-rescriere`, bază `main` `2d45039` (`D:\Omnia-MVP`). Citește `R30-coder.md`, `R30-coder-raport.md`, `R30-tester.md`, `R30-tester-raport.md`.

## Corecturi planner (verifică-le)
1. `query_rewrite.py`: fără `temperature` (SDK anthropic 1.3.0 → `TypeError`); `except Exception` → fail-open pe original.
2. `retrieval_eval.py`: fără `--rescriere`, `RetrievalService` construit ca înainte; `MAX_EMBEDDING_CALLS = 2 * MAX_CASES`.
3. `tests/test_api_integration.py`: tester-ul își inserase blocul **înaintea** ultimei aserțiuni din `test_deploy_script_refuza_pe_conditii_nesigure…` (`assert "$LASTEXITCODE -ne 0" in text` ajunsese în testul nou) — mutată înapoi; `test_rescrierea_trece_prin_bugetul…` aștepta greșit apelul rescrierii cu plafonul epuizat — corect e `rewriter.questions == []` (garda refuză înaintea apelului plătit).

## Starea verificată de planner
- `python -m pytest -q`: 1390 passed, 34 skipped (3 rulări consecutive). Un eșec izolat văzut o singură dată înainte de testele tester-ului nu s-a mai reprodus (5 + 3 rulări).
- Real: set colocvial 11/17 → **17/17**; set oficial 34/36 → 33/36 (toate pozitivele găsite; NEG-05 trece de căutare, generarea refuză corect — verificat).

## Ce verifici
1. Parserul/D12/D25/ruta exactă rămân exclusiv pe originalul întrebării? Generarea primește originalul? Poate rescrierea introduce coduri de normativ sau valori care schimbă rezultatul (promptul le interzice — e suficient, dat fiind că rescrierea e folosită doar la embedding)?
2. Securitate: întrebarea în prompt ca JSON neîncrezător; nimic sensibil logat; bugetul de apeluri plătite respectat.
3. Fail-open real în toate căile; `/health/provideri` neafectat.
4. Cod inutil? Protocolul `QueryRewriter` duplicat (retrieval_core + query_rewrite) — acceptabil?
5. Teste: pot pica, nu sunt redundante; setul `evaluare/set_colocvial.json` e coerent (articolele așteptate sunt cele din setul oficial).

Verdict APROBAT / RESPINS cu listă. Nu modifici nimic.
