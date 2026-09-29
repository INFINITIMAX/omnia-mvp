# R30 — Tester

Worktree `D:\Omnia-MVP-r30`, branch `feat/r30-rescriere` (commit `9a96051`). Citește `R30-coder.md`, `R30-coder-raport.md`.

## Corecturi planner după coder (verifică-le)
1. `query_rewrite.AnthropicQueryRewriter`: fără `temperature` (SDK anthropic 1.3.0 îl respinge cu `TypeError`); **orice** excepție (nu doar `AnthropicError`) → întrebarea originală (fail-open). Înainte, `TypeError` scăpa și ar fi dat 503.
2. `retrieval_eval`: fără `--rescriere`, `RetrievalService` e construit exact ca înainte (fără argumentul `rewriter`); `MAX_EMBEDDING_CALLS = 2 * MAX_CASES`.
3. Set nou `evaluare/set_colocvial.json` (17 cazuri).

## Starea verificată de planner (real)
- Colocvial: fără rescriere 11/17, cu rescriere **17/17**. Oficial: 34/36 → 33/36 (toate pozitivele găsite; NEG-05 trece de căutare, dar generarea refuză corect — verificat cu un apel real).
- `python -m pytest -q`: o dată 1 failed (nereprodus în 3 rulări ulterioare: 1362 passed) — **investighează** ce test poate fi instabil (timp, stare globală, cache `/health/db`, ordinea testelor) și raportează cauza.

## Sarcina — teste sintetice (fără rețea/DB/Anthropic real)
1. `AnthropicQueryRewriter`: răspuns text valid → rescrierea; răspuns gol / prea lung / `max_tokens` / bloc non-text / mai multe blocuri → original; excepție `AnthropicError` și excepție generică (ex. `TypeError`) → original; cheie API lipsă → original, fără client construit; apelul **nu** trimite `temperature`; promptul conține întrebarea ca JSON neîncrezător.
2. `RetrievalService` cu `rewriter`: ruta exactă, restricțiile D12, codurile necunoscute D25 folosesc doar originalul (rescrierea nici nu e apelată pe ruta exactă); pe ruta semantică două embedding-uri + combinare după `chunk_id` cu scor maxim, top_k respectat; rescriere identică (după spații) → un singur embedding; fără `rewriter` → comportament identic cu înainte.
3. `main.py` `/intreaba`: rescrierea trece prin bugetul de apeluri plătite (`reserve`); eșecul rescrierii nu schimbă răspunsul public și nu marchează `/health/provideri` degradat; generarea primește întrebarea **originală**.
4. `retrieval_eval --rescriere` cere `--run`; contorul `rescriere_calls` în sumar.

Scrii doar în `tests/`. Nu rula comenzi. Raport: `docs/handoff/R30-tester-raport.md`.
