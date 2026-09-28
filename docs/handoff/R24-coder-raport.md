# R24 — Coder: raport

## Fișiere modificate

### `generation_core.py`
- `MAX_ANSWER_TOKENS = 1200` → `2000`.
- Constantă nouă `_NOT_FOUND_MESSAGE` (textul standard, identic cu `_NOT_FOUND` din `main.py`), refolosită la evidență goală și la `gasit=false`.
- `_decode_payload`: schema acceptată devine exact `{"raspuns", "pasaje", "gasit"}`; `gasit` trebuie să fie `bool` strict (`type(...) is not bool`, ca `0`/`1` să nu treacă).
- `_generate_validated` întoarce acum un tuplu de 4 elemente (adaugă `gasit: bool`). Cu `gasit=False`: verifică `pasaje == []` și că `raspuns` nu conține `[Cn]` (regex `_CITATION_ID`), altfel `InvalidGenerationPayloadError`; nu mai cere citare (`_validated_used_ids` nu se apelează pe această ramură).
- `generate()`: după primul apel, dacă `gasit` e `False`, întoarce direct `GenerationResult("not_found", _NOT_FOUND_MESSAGE, ())`, fără verificarea referințelor nesusținute și fără retry. Ramura `gasit=True` e neschimbată (D20/D22 intacte). Dacă retry-ul (declanșat de referințe nesusținute pe ramura `gasit=True`) revine tot cu `gasit=False`, tratez la fel — refuz `not_found`, nu eroare (comportament simetric, nu era explicit în task dar e consecința directă a contractului).
- Prompt: schema JSON din regula 6 include `"gasit":true`; regulă nouă (10) explică semantica `gasit=false`/`true`, regula 4 rămasă neschimbată pentru cazul parțial.

### `main.py`
- `AnthropicTextGenerator._TOOL.input_schema`: `"gasit"` adăugat la `required` și la `properties` (`type: boolean`).
- Ruta `/intreaba`: în ramura de generare reușită (fără `UngroundedReferenceError`), dacă `generated.status == "not_found"`, construiește `IntreabaResponse(status="not_found", raspuns=_NOT_FOUND, citari=[], intrebari_ramase=...)` — identic cu ramura `not_found` de la căutare. Altfel, comportamentul `answered` e neschimbat. Cota rămâne consumată normal (nu am atins tranzacția/commit-ul).

### `docs/DECISIONS.md`
- D26 adăugat deasupra D25, cu textul exact din handoff.

## Runda 2 (28-09-2026) — `gasit=false` nu mai poate produce 503

Motiv (planner): evaluarea R24 a arătat că regulile stricte de conținut din runda 1 (`pasaje==[]`, fără `[Cn]`) transformau un refuz `gasit=false` care le încălca într-un `InvalidGenerationPayloadError` → 503 — exact eroarea pe care refuzul trebuia s-o evite.

- `generation_core.py::_generate_validated`: verificarea `gasit` s-a mutat **înaintea** validării `raspuns`/`pasaje`. Cu `gasit=False`, întoarce direct `GeneratedText("", truncated=...), (), {}, False` — conținutul `raspuns`/`pasaje` nu mai e citit, nu mai e validat, nicio excepție posibilă din el. Rămân erori de validare doar: chei lipsă/în plus, `gasit` care nu e boolean, JSON invalid (neschimbate, tot în `_decode_payload`).
- `generate()` (neschimbat față de runda 1): pe `gasit=False` întoarce `GenerationResult("not_found", _NOT_FOUND_MESSAGE, ())`.
- Promptul păstrează neschimbată regula 10 (instrucțiunea către model rămâne `pasaje=[]`, fără `[Cn]`), dar serverul nu mai depinde de respectarea ei.
- `docs/DECISIONS.md`: D26 actualizat cu paragraful „Runda 2” (motiv, decizie, ce rămâne eroare de validare).
- Decizia din runda 1 (retry care revine tot cu `gasit=False` → `not_found`, nu eroare) a fost acceptată de planner, neschimbată.

## Ce nu am făcut
- Nu am scris/modificat teste (rol Tester).
- Nu am atins `retrieval_core.py`, `chunking_core.py`, `retrieval_eval.py`, `static/`, `supabase/`, `.env`, `documente_noi/`.
- `real_grounding_eval.py` doar referențiază `AnthropicTextGenerator._TOOL_NAME`/`._TOOL` (nu redefinește schema local) — rămâne importabil fără nicio modificare acolo.

## De verificat de Planner
- Testele existente pentru schema pachetului (`{"raspuns","pasaje"}` → acum `{"raspuns","pasaje","gasit"}`) și pentru limita veche 1200, plus orice test care aștepta `InvalidGenerationPayloadError` pe `gasit=false` cu conținut invalid, vor pica/trebui rescrise de Tester — de așteptat, nu e regresie.
- Confirmați că `NEG-04` (și cazuri similare) acum trec prin `not_found` fără 503 în evaluarea reală.
