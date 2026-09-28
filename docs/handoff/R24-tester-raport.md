# R24 — Tester: raport

## Fișiere modificate (toate în `tests/`)

### `tests/generation_fixture_helpers.py`
- `simulated_provider_payload`: adăugat `"gasit": True` în pachetul construit. Folosit de `GeneratorFake` din `test_generation_core.py` și `test_api_integration.py` — repară automat majoritatea cazurilor "answered" fără să ating fiecare test individual.
- Ar pica dacă: cineva scoate `"gasit": True` de aici din nou (orice test care folosește `GeneratorFake` prin acest helper ar reveni la eroarea de schemă D26).

### `tests/test_generation_core.py`
Actualizate:
- `test_service_refuza_limita_de_raspuns_invalida`: `1201` → `2001`, mesaj `"1..1200"` → `"1..2000"`.
- `test_c1_valid_construieste_...`: `generator.max_tokens == 1200` → `2000`.
- `test_id_inventat_este_eroare_tipata_fail_safe`, `test_lipsa_citarii_este_eroare_tipata_fail_safe`, `test_citatul_public_este_limitat_la_600_caractere`: adăugat `"gasit": True` în payload-urile RAW (altfel eroarea capturată nu mai era cea intenționată — `UnknownCitationError`/`MissingCitationError`/citat 600 — ci mismatch de schemă).

Noi (secțiunea „D26 (Runda 2)” + un test separat pentru limită):
- `test_max_answer_tokens_implicit_este_2000` — pică dacă `MAX_ANSWER_TOKENS` revine la 1200 sau altă valoare.
- `test_gasit_lipsa_este_eroare_de_validare_fail_closed` — pică dacă `_decode_payload` acceptă din nou schema veche `{raspuns, pasaje}` fără `gasit`.
- `test_gasit_neboolean_este_eroare_de_validare_fail_closed` (parametrizat `"false"`, `0`, `1`, `None`, `"true"`, `1.0`) — pică dacă verificarea `type(...) is not bool` e slăbită la un check `isinstance`/truthy (ar lăsa `0`/`1`/`1.0` să treacă).
- `test_gasit_cheie_in_plus_este_eroare_de_validare` — pică dacă setul de chei acceptat devine permisiv la chei suplimentare.
- `test_gasit_false_devine_not_found_fara_citari_chiar_daca_pasaje_sau_raspuns_incalca_regulile` — pică dacă serverul mai citește `raspuns`/`pasaje` pe ramura `gasit=false` (regresie la comportamentul din Runda 1, care redeschide 503 pe refuzuri oneste).
- `test_gasit_true_fara_citare_ramane_eroare_ca_inainte` — pică dacă `gasit=true` fără citare nu mai declanșează `MissingCitationError`.
- `test_reincercarea_care_revine_cu_gasit_false_este_refuz_not_found_nu_eroare` (+ clasa locală `RawSequenceFake`) — prima încercare are referință neancorată (`gasit=true`, declanșează retry), a doua revine cu `gasit=false`; pică dacă retry-ul nu se oprește la refuz sau dacă a doua rundă e tratată ca `UngroundedReferenceError` în loc de `not_found`. Verifică și `generator.calls == 2` (fără buclă).

Import nou: `MAX_ANSWER_TOKENS`, `InvalidGenerationPayloadError` din `generation_core`.

### `tests/test_citation_passages.py`
- `encode_payload(answer, passages, gasit=True)`: parametru nou cu default `True`; toate apelurile existente (majoritatea testelor din fișier) primesc automat schema D26 corectă.
- `assert_rejected_once`: `token_limits == [1200]` → `[2000]`.
- Toate asserturile explicite `token_limits == [1200]` / `[1200, 1200]` din fișier → `2000` / `[2000, 2000]` (6 locuri).
- Blocul `raw_template` (parametrize pentru JSON nestrict): fiecare template a primit `"gasit":true` acolo unde testează altceva (extra-chei, chei duplicate, virgulă finală, markdown fence, proză, listă/obiect top-level, `raspuns` cu tip greșit) — altfel toate ar fi picat pentru motivul greșit (schemă incompletă, nu comportamentul specific testat). Am adăugat explicit trei cazuri noi de id: `gasit-absent`, `gasit-duplicat`, `gasit-string`/`gasit-numar`/`gasit-null` (verifică fiecare tip de eroare posibilă pe câmpul `gasit` însuși, în contextul json nestrict).
- Cele două teste cu JSON brut hardcodat (`test_citation_passages_constante_non_json_sunt_respinse`, `test_citation_passages_chei_duplicate_cu_escape_json_sunt_respinse`) — adăugat `"gasit":true`.
- Test nou: `test_citation_passages_gasit_false_ignora_pasaje_malformate_si_ramane_not_found` — `pasaje` cu id necunoscut (`C9`), dar `gasit=False`; pică dacă serverul mai validează `pasaje` pe ramura de refuz (ar arunca `InvalidGenerationPayloadError` în loc de `not_found`).
- Nu am atins testele `pasaje-lipsa` (`'{"raspuns":"Răspuns [C1]."}'`, în `test_api_integration.py`) și json-incomplet — sunt deja invalide indiferent de `gasit`; adăugarea lui nu ar schimba comportamentul testat (503 generic).

### `tests/test_api_integration.py`
- `_r06_payload`: parametru nou `gasit=True` (default), propagat în payload.
- `test_erorile_dependentei_sunt_503_generic_si_conexiunea_se_inchide` (parametrul `RawGeneratorFake` cu `"raspuns fără citare"`): adăugat `"gasit": True` — altfel eroarea era de schemă, nu `MissingCitationError`.
- Cele 3 asserturi `generator.max_tokens == 1200` (test R06 endpoint, test R06 rollback, test D11 comparație multi-document) → `2000`.
- `test_r06_validation_logheaza_numai_clasa_si_codul_sigur_fara_payload_sau_evidence`: adăugat `"gasit": True` — testul verifică explicit `code=passage_value` în log, care altfel ar fi ascuns de eroarea de schemă lipsă.
- `test_api_d11_comparatia_multi_document_...`: adăugat `"gasit": True` la payload-ul RAW cu două citări.
- `test_generation_validation_error_nu_declanseaza_provider_failure_sau_starea_providerilor`: adăugat `"gasit": True` la payload-ul cu citat de 601 caractere.

Teste noi:
- `test_schema_toolului_anthropic_cere_gasit_boolean_obligatoriu` — verifică `main.AnthropicTextGenerator._TOOL["input_schema"]["required"]` conține `"gasit"` și `properties["gasit"]["type"] == "boolean"`. Pică dacă schema tool-ului Anthropic nu mai forțează câmpul.
- `test_gasit_false_devine_not_found_200_cu_cota_consumata_nu_503` — `/intreaba` cu un `RawGeneratorFake` care întoarce `gasit: False` (plus `raspuns`/`pasaje` care ar fi altfel invalide): verifică status HTTP 200, body exact `{"status": "not_found", "raspuns": main._NOT_FOUND, "citari": [], "intrebari_ramase": 9}`, un singur apel generator, cotă comisă (`connection.commits >= 1`). Pică dacă `/intreaba` nu mai mapează `GenerationResult("not_found", ...)` la statusul public `not_found`, sau dacă mai apare un al doilea apel plătit.

## Ce nu am schimbat / nu am acoperit
- `grounding_eval.py` (producție, NU în `tests/`): **bug suspectat**. `evaluate_case()` construiește pachetul JSON pentru `FixedGenerator` fără cheia `"gasit"`:
  ```python
  generator = FixedGenerator(json.dumps({
      "raspuns": case.candidate,
      "pasaje": [asdict(passage) for passage in case.model_passages],
  }, ensure_ascii=False))
  ```
  Testele care rulează prin `GenerationService` real (fără `service_factory` custom) — `test_grounding_eval_default_runner_uses_real_service_without_gold` și mai ales `test_grounding_eval_r06_real_service_has_no_missing_passages_false_refusals_or_execution_errors` — lovesc acum `InvalidGenerationPayloadError` (schemă incompletă) pentru orice caz, nu comportamentul intenționat (verificarea ancorării). Corespunde exact celui 1 eșec raportat de planner în `test_grounding_eval.py`. Nu am atins nici fișierul de producție, nici testul — testul deja detectează corect problema (`publishable_rejected == 0` pică). Recomand planner-ului să retrimită la coder: adăugare `"gasit": True` în `evaluate_case()` din `grounding_eval.py`.
- `real_grounding_eval.py` / `test_real_grounding_eval.py`: verificate, rămân coerente fără nicio modificare — `_RuntimeGenerator` doar transportă `tool_input`-ul primit de la Anthropic (nu validează `gasit` local), iar `GenerationServiceFake` din teste ocolește complet `_decode_payload`. Cele câteva `max_tokens=1200` rămase în acest fișier sunt valori proprii fixe ale fake-urilor de test (nu verifică limita de producție `MAX_ANSWER_TOKENS`), deci nu le-am schimbat.
- Nu am slăbit nicio aserțiune D20/D22 (pasaj literal, ≥1 citare, reîncercare pentru referințe nesusținute) — toate rămân neschimbate pe ramura `gasit=true`, doar cu cheia nouă adăugată în payload-uri.
- Nu am acoperit explicit "gasit lipsă în interiorul unui obiect nested" (nu e cazul — `gasit` e doar la nivel top-level) și nici interacțiunea cu trunchierea (`truncated=True` + `gasit=false`) — planner poate decide dacă merită un test separat; comportamentul actual (ignoră complet conținutul) face ca trunchierea să fie irelevantă pe această ramură, deci am considerat-o acoperită indirect de `test_gasit_false_devine_not_found_fara_citari_...`.

## Comanda pentru planner
```powershell
python -m pytest -q
```
Aștept: eșecurile din `test_citation_passages.py`, `test_api_integration.py`, `test_generation_core.py` dispar; rămâne 1 eșec în `test_grounding_eval.py` (bug de producție în `grounding_eval.py`, descris mai sus, netratat de mine conform regulii „nu repar codul de producție”).
