# R17 — Raport Tester

## Fișier atins
Toate testele noi au fost adăugate la finalul `tests/test_api_integration.py` (după linia 2087, secțiunea `# --- R17: timeout-uri, clasificare provider_failure, /health/provideri, deploy.ps1 ---`), refolosind fixture-urile/helper-ele existente (`api`, `configure`, `ConnectionFake`, `R06TransactionConnection`, `RawGeneratorFake`, `NOW`, `_assert_no_technical_identifiers`). Am adăugat un singur import nou la începutul fișierului: `import httpx` (dependență reală a `anthropic`, necesară ca să construiesc `APIStatusError`/`APITimeoutError` autentice, nu simulări).

Nu am atins `main.py`, `scripts/deploy.ps1` sau `DEPLOYMENT.md`.

## Ce verifică fiecare test (grupat pe cerințele din brief)

### 1. Timeout-uri / retries la construcția lazy a clienților
- `test_voyage_client_lazy_este_construit_cu_timeout_si_max_retries_impliciti` — monkeypatch pe `voyageai.Client`; ar pica dacă `timeout`/`max_retries`/`api_key` ar lipsi sau ar avea altă valoare decât `15`/`1`.
- `test_anthropic_client_lazy_este_construit_cu_timeout_si_max_retries_impliciti` — monkeypatch pe **`main.Anthropic`** (nu pe `anthropic.Anthropic`!, vezi Notă tehnică mai jos); ar pica la aceleași condiții, valori `30`/`1`.
- `test_open_db_connection_trimite_connect_timeout_si_sslmode_fara_options` — monkeypatch pe `psycopg2.connect`; verifică exact cele 7 chei așteptate (`connect_timeout=10`, `sslmode="require"`) și că **`options`/`statement_timeout` nu mai apar deloc** — test de regresie explicit pentru fix-ul din Runda 2 (dacă cineva reintroduce `options=...`, testul pică).

### 2. Clasificare `provider_failure` (funcții pure)
- `test_clasificarea_anthropic_acopera_toate_categoriile` — 10 cazuri parametrizate: `timeout`, `credit_exhausted` (400+`type=billing_error`), `rate_limited`(429), `auth`(401,403), `server_error`(500,529), `other`(400 fără billing_error, 404, `APIConnectionError` non-timeout). Excepțiile sunt instanțe **reale** din SDK (`anthropic.APIStatusError`/`APITimeoutError`/`APIConnectionError`), construite cu `httpx.Request`/`httpx.Response` reale — nu simulări de tip `SimpleNamespace`.
- `test_clasificarea_voyage_acopera_toate_categoriile` — 7 cazuri, instanțe reale din `voyageai.error`.
- `test_clasificarea_db_acopera_pgcode_si_euristica_operationalerror` — 6 cazuri: `pgcode` 28P01/28000→auth, 57014→timeout, `OperationalError` cu „timeout” în mesaj→timeout, fără→server_error, `DataError`→other.
- Oricare din aceste cazuri ar pica dacă `_classify_*` ar întoarce altă categorie/status.

### 3. Linia de log exactă + fără date sensibile
- `test_adaptorul_anthropic_logheaza_provider_failure_fara_date_sensibile` și `test_adaptorul_voyage_logheaza_provider_failure_fara_date_sensibile` — apelează adaptoarele reale (`AnthropicTextGenerator`/`VoyageQueryEmbedder`) cu un client fals care ridică o eroare al cărei mesaj conține un marker (`PROMPT_NU_TREBUIE_LOGAT` / `DETALIU_TEHNIC_NU_TREBUIE_LOGAT`) și o întrebare-marker (`INTREBARE_SECRETA`); verifică linia de log **exactă** (`provider_failure provider=... category=... status=...`) și că niciunul din markeri nu apare în `caplog.text`. Ar pica dacă mesajul excepției ar ajunge în log sau dacă formatul liniei s-ar schimba.
- `test_intreaba_db_pgcode_specific_logheaza_categoria_corecta_fara_intrebare` (parametrizat 28P01/57014) — trece prin endpoint-ul `/intreaba` complet (nu doar funcția de clasificare), verifică log-ul, 503 generic, și că întrebarea/mesajul Postgres nu apar în log.
- `test_generation_validation_error_nu_declanseaza_provider_failure_sau_starea_providerilor` — verifică interacțiunea dintre logul D21 (existent) și noul cod: o eroare de validare a generării **nu** trebuie să producă și o linie `provider_failure`, nici să atingă `_PROVIDER_HEALTH`. Nu duplic testul D21 existent de la linia 1689 (`test_r06_validation_logheaza_...`) — adaug doar asertarea nouă cerută de brief.

### 4. `/health/provideri`
- `test_provider_health_tracker_prag_reset_si_fereastra_de_15_minute` — test unitar pe `_ProviderHealthTracker` cu `now` injectat (fără `sleep`): sub prag (2 eșecuri) → gol; la al 3-lea → degradat; succes → reset; verifică și granița exactă a ferestrei de 15 minute (`<=15min` degradat, `>15min` nu).
- `test_health_provideri_200_fara_esecuri`, `test_health_provideri_503_dupa_3_esecuri_consecutive_ale_unui_singur_provider` (cu `main._utc_now` monkeypatch-uit, fără `sleep`), `test_health_ramane_ok_chiar_cu_provideri_degradati` (verifică `/health` separat de `/health/provideri`).
- `test_health_provideri_nu_face_apeluri_externe` — monkeypatch pe `voyageai.Client`, `main.Anthropic`, `psycopg2.connect` cu funcții care ridică `AssertionError`; dacă endpoint-ul ar face vreun apel extern, testul ar pica cu eroare necontrolată.
- `test_un_succes_reseteaza_contorul_dupa_esecuri_repetate_prin_adaptoarele_reale` — test end-to-end: 3 eșecuri Anthropic reale (prin `AnthropicTextGenerator.generate`) → `/health/provideri` 503 cu categoria corectă → un succes real → `/health/provideri` revine la 200. Acoperă explicit interacțiunea adaptor→tracker→endpoint cerută de item 4 din brief.

### 5. `scripts/deploy.ps1` (static, fără execuție)
- `test_deploy_script_refuza_pe_conditii_nesigure_si_ruleaza_pytest_inaintea_lui_railway` — citește fișierul, verifică prezența verificărilor de branch/status/HEAD vs `origin/main`, absența parametrilor (`param()` gol) și **ordinea**: `python -m pytest` trebuie să apară înaintea lui `railway up` în text, plus oprirea la `$LASTEXITCODE -ne 0`.

## Fixture nouă
`fresh_provider_health` — monkeypatch pe `main._PROVIDER_HEALTH` cu un tracker proaspăt, folosit de toate testele care ating starea globală de sănătate. Fără el, testele de prag ar fi flaky/order-dependente, pentru că starea e un singleton la nivel de modul și testele existente (ex. cele cu `ConnectionFake(error=...)`) acum ating și ele `_PROVIDER_HEALTH` ca efect de bord al codului R17.

## Notă tehnică importantă (bug evitat, nu al coder-ului)
`main.py` face `from anthropic import Anthropic, ...`, deci `main.Anthropic` e un nume legat direct în namespace-ul `main` la import. Monkeypatch pe `anthropic.Anthropic` (modulul) **nu** ar fi afectat `main.py` fără un `importlib.reload(main)` (exact cum face testul existent `test_import_main_nu_creeaza_clienti_externi`). Am patch-uit direct `main.Anthropic`, evitând reload-ul complet al modulului (care ar fi resetat toate celelalte fixture-uri de test). Pentru Voyage și `psycopg2`, `main.py` importă modulul întreg (`import voyageai`, `import psycopg2`), deci patch pe modulul original funcționează corect fără reload.

## Ce NU am acoperit și de ce
- Nu am testat `DEPLOYMENT.md` (nu a fost cerut explicit de brief, e documentație, nu cod executabil).
- Nu am testat comportamentul real al `railway up`/`git fetch` din `deploy.ps1` — brief-ul cere explicit doar un test static, ieftin, fără execuție.
- Nu am reluat testele D21 existente pentru `GenerationValidationError` (brief: „nu le duplica”); am adăugat doar interacțiunea nouă cu `provider_failure`/health.
- Nu am testat cazul `psycopg2.OperationalError` fără `connect_timeout` atins în producție reală (fără rețea) — doar euristica pe substring „timeout”, exact ca-n riscul semnalat de coder.

## Corectură (confirmată de planner)
`pgcode` e read-only pe excepțiile `psycopg2` (extensie C): `error.pgcode = pgcode` picase la colectare cu `AttributeError: readonly attribute`. Am înlocuit `_db_error` să construiască o subclasă locală (`type(cls.__name__, (cls,), {"pgcode": property(...)})`) care suprascrie `pgcode`, păstrând `isinstance` din `psycopg2.OperationalError`/`psycopg2.Error` — exact ce verifică `_classify_db_failure` din producție. Am actualizat și `test_intreaba_db_pgcode_specific_logheaza_categoria_corecta_fara_intrebare` să folosească același helper, în loc de setare directă a atributului.

## Comanda pentru planner
```
python -m pytest -q tests/test_api_integration.py
```
sau, pentru toată suita:
```
python -m pytest -q
```
