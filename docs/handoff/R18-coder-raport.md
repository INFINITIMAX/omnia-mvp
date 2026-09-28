# R18 — Coder: raport

## Fișiere

- **`retrieval_eval.py`** (nou) — runner-ul cerut.
- **`.gitignore`** — adăugat `evaluare/rapoarte/` (rapoartele locale, fără text normativ).
- Nu am atins `real_grounding_eval.py`, `main.py`, `retrieval_core.py`, `generation_core.py`, `chunking_core.py`, `scope_core.py`, `supabase/`, `.env`, `documente_noi/`.
- Nu am creat `evaluare/set_aur.json` — rămâne al planner-ului.

## Flux `retrieval_eval.py`

1. `load_gold_set(path)`: citește și validează strict setul (chei exacte la nivel de fișier `{"versiune","cazuri"}` cu `versiune == 1`, și per caz `{"id","tip","intrebare","asteptat"}`; `tip` ∈ `{exact, semantic, negativ}`; `id` unic; `asteptat` gol doar pentru `negativ`, nevid altfel, fiecare intrare `{"document_id","articol"}`; `articol` normalizat cu `ArticleParser.normalize_article` — respinge formate invalide). Maximum 30 de cazuri, minimum 1 (am considerat un set gol invalid; nu era explicit în task, semnalez pentru verificare). Orice abatere → `RealEvaluationError("invalid_set")`, fără nicio conexiune DB/Voyage deschisă.
2. Fără `--run`: doar validează, tipărește `set_valid` pe stderr, exit 0. Cu set invalid: exit 2, indiferent de `--run`.
3. Cu `--run`: `run_evaluation` deschide o singură conexiune (`_open_db_connection` din `main.py`, `set_session(readonly=True, autocommit=False)`), construiește catalogul aprobat → parser, `PostgresRetrievalRepository`, `RetrievalService` cu valorile implicite (nu suprascriu `semantic_top_k`/`semantic_min_score`/`max_context_chars`). Pentru fiecare caz aplică întâi `is_engineering_calculation_request` (poarta D-anti-calcul identică cu ruta publică din `main.py`) → `out_of_scope` fără embedding; altfel `retrieval.retrieve(intrebare)`. Fără generare Anthropic.
4. Embedder: `_CountingEmbedder` local (prag propriu `MAX_EMBEDDING_CALLS = 30`, distinct de cel din R05 care e 8) în jurul `_build_runtime_embedder()` reutilizat prin import din `real_grounding_eval.py` (Voyage `timeout=30, max_retries=0`). La al 31-lea apel ridică `RealEvaluationError("cost_limit")`.
5. Metrici per caz: `gasit`/`rang` calculate din prima dovadă a cărei `(document_id, articol_normalizat)` potrivește un articol așteptat (potrivire exactă sau copil `articol.` / `articol(`); pentru `negativ`, `corect` = statusul e în `{not_found, ambiguous_reference, out_of_scope}`. Raportul per caz conține exact `id, tip, status, gasit, rang, dovezi` (`dovezi` = `document_id`+`articol_normalizat`, fără text); `corect` e folosit intern doar pentru sumar, nu apare per caz (task-ul enumeră explicit doar acele 6 chei).
6. O eroare de caz care nu e `RealEvaluationError` deja marcat (DB, embedding invalid etc.) e învelită ca `RealEvaluationError("case_failed:<id>:execution_error")` și oprește toată rularea (fail-fast), fără să expună mesajul original. O nepotrivire simplă (status greșit, articol negăsit) NU oprește rularea — e doar înregistrată.
7. Sumar: `total`, `corecte`, `acuratete_totala`, `pe_tip` (total/corecte/acuratete per `exact|semantic|negativ`), `pe_document` (agregat pe `document_id` din `asteptat`, deci un caz cu articole așteptate din mai multe documente contribuie la fiecare — decizie mea, nespecificată explicit), `recall_at_1`, `recall_at_5` (calculate doar peste cazurile non-negative), `embedding_calls`. Scris atomic prin `_write_report_atomically` reutilizat din `real_grounding_eval.py` (eșuează dacă fișierul deja există). Directorul `report_path.parent` e creat cu `mkdir(parents=True, exist_ok=True)` înainte de scriere.
8. Stdout: doar `sumar`, `json.dumps(..., ensure_ascii=True, sort_keys=True)`.

## Coduri de ieșire / eroare

- `2` — set invalid (`invalid_set`, mesaj pe stderr).
- `3` — eroare de rulare (`missing_environment`, `invalid_embedding`, `cost_limit`, `case_failed:<id>:execution_error`, `report_exists`, `report_error`, `report_dir_error`) — toate din/analog cu `RealEvaluationError` (reutilizată prin import din `real_grounding_eval.py`, aceleași coduri unde se suprapun).
- `0` — succes (rulare completă sau doar validare fără `--run`).

## Reutilizat prin import (fără modificare)

Din `real_grounding_eval.py`: `RealEvaluationError`, `_build_runtime_embedder` (adaptor Voyage `timeout=30, max_retries=0`), `_write_report_atomically`. Din `main.py`: `_open_db_connection`. Din `retrieval_core.py`: `ArticleParser`, `Evidence`, `PostgresApprovedCatalogRepository`, `PostgresRetrievalRepository`, `RetrievalService`. Din `scope_core.py`: `is_engineering_calculation_request`.

## Ce nu am făcut

- Nu am scris teste (Tester-ul).
- Nu am creat `evaluare/set_aur.json`.
- Nu am rulat nimic.

## Ce ar trebui verificat de planner

- Rulare fără `--run` pe un `set_aur.json` valid și pe unul invalid (chei lipsă, `id` duplicat, `asteptat` gol pe non-negativ, `asteptat` nevid pe negativ, >30 cazuri, `articol` cu format invalid).
- Rulare cu `--run` (cost real Voyage) pe un set mic, verificând: raportul apare în `evaluare/rapoarte/` (gitignored), stdout e ASCII, plafonul de 30 embeddings chiar blochează al 31-lea apel dacă testat separat.
- Verifică dacă pragul minim de 1 caz (setul nu poate fi gol) e acceptabil sau trebuie relaxat.
- Verifică dacă agregarea `pe_document` pe cazuri cu `asteptat` multi-document (dacă vor exista în set) dă cifre utile sau ar trebui restrânsă la primul document așteptat.

## Runda 2

Tester a găsit că `_REFUSAL_STATUSES` excludea `ambiguous_article`. Planner a decis: pentru cazurile negative, orice refuz (`not_found`, `ambiguous_reference`, `ambiguous_article`, `out_of_scope`) e corect. Am adăugat `ambiguous_article` în `_REFUSAL_STATUSES` din `retrieval_eval.py`; nimic altceva schimbat.
