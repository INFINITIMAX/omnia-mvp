# R24 — Tester

Worktree: `D:\Omnia-MVP-r24`, branch `feat/r24-limita-refuz` (commit coder `917509d`). Citește `R24-coder.md` (inclusiv „Runda 2”) și `R24-coder-raport.md`. Cod: `generation_core.py`, `main.py`, `docs/DECISIONS.md` (D26).

## Starea verificată de planner
`python -m pytest -q`: **253 failed**, 964 passed, 30 skipped. Distribuție: `test_citation_passages.py` 154, `test_api_integration.py` 58, `test_generation_core.py` 40, `test_grounding_eval.py` 1. Cauze așteptate: (a) pachetele JSON false din teste nu au cheia obligatorie `gasit` (acum cheile acceptate sunt exact `raspuns`, `pasaje`, `gasit`); (b) teste care verifică limita veche 1200 (ex. `test_service_refuza_limita_de_raspuns_invalida`, regex `1..1200`); (c) teste de prompt care verifică textul regulilor. Helper comun probabil: `tests/generation_fixture_helpers.py`.

## Sarcina
1. **Actualizează testele existente** la contractul D26: adaugă `"gasit": true` în pachetele false unde testul verifică un răspuns normal; limita 1200 → 2000; textul promptului doar unde regula s-a schimbat real. **Nu slăbi** nicio aserțiune care verifică D20/D22 (pasaj literal, ≥1 citare, reîncercare pentru referințe nesusținute) — acestea trebuie să treacă neschimbate cu `gasit=true`. Dacă un test pică din alt motiv decât (a)–(c), nu-l „repara”: raportează-l ca bug suspectat.
2. **Teste noi** (în fișierele existente potrivite):
   - `gasit` lipsă / cheie în plus / `gasit` ne-boolean (ex. `"false"`, `0`, `null`) → eroare de validare (fail-closed);
   - `gasit=false` → `GenerationResult` cu status `not_found`, mesajul standard, `citari=()` — **inclusiv** când `pasaje` e nevid sau `raspuns` conține `[C1]` (Runda 2: conținutul e ignorat), și fără reîncercare (un singur apel la generator);
   - reîncercarea pentru referință nesusținută care revine cu `gasit=false` → `not_found`;
   - `gasit=true` fără citări → rămâne eroare ca înainte;
   - `MAX_ANSWER_TOKENS == 2000` și e transmis către generator;
   - schema `AnthropicTextGenerator._TOOL` cere `gasit` (boolean, în `required`);
   - `/intreaba`: generare `not_found` → HTTP 200, `status="not_found"`, `raspuns` = mesajul `_NOT_FOUND`, `citari=[]`, cota consumată (a existat un apel).
3. `real_grounding_eval.py` / `test_real_grounding_eval.py`: doar să rămână importabile și coerente cu noua schemă.

## Constrângeri
Scrii doar în `tests/`. Nu rula comenzi. Nu modifica codul de producție; bug suspectat → raportezi. Fiecare test nou trebuie să poată pica (spune pentru fiecare ce schimbare de cod l-ar face să pice). Raport în `docs/handoff/R24-tester-raport.md`: fișiere modificate, câte teste actualizate vs. noi, orice aserțiune pe care ai considerat-o și ai decis să n-o schimbi.
