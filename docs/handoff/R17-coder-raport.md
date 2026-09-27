# R17 — Raport Coder

## Fișiere atinse

- `main.py` — toate cele 3 puncte de cod (timeout-uri, diagnostic de provider, `/health/provideri`).
- `scripts/deploy.ps1` — nou.
- `DEPLOYMENT.md` — secțiune nouă „6.1 Deploy și rollback” + rând nou în tabelul de rute (§5).
- `docs/handoff/R17-coder-raport.md` — acest fișier.

Nu am atins `generation_core.py`, `retrieval_core.py`, `chunking_core.py`, `access_control.py`, `static/`, `supabase/`, `.env`, conform constrângerii.

## 1. Timeout-uri (main.py)

Constante numite lângă `_LOGGER` (linia ~61): `_ANTHROPIC_TIMEOUT_SECONDS=30`, `_ANTHROPIC_MAX_RETRIES=1`, `_VOYAGE_TIMEOUT_SECONDS=15`, `_VOYAGE_MAX_RETRIES=1`, `_DB_CONNECT_TIMEOUT_SECONDS=10`, `_DB_STATEMENT_TIMEOUT_MS=15000`.

- `Anthropic(api_key=..., timeout=_ANTHROPIC_TIMEOUT_SECONDS, max_retries=_ANTHROPIC_MAX_RETRIES)` — verificat în sursa SDK (`anthropic` acceptă exact acești parametri de kwarg).
- `voyageai.Client(api_key=..., timeout=_VOYAGE_TIMEOUT_SECONDS, max_retries=_VOYAGE_MAX_RETRIES)` — verificat în `voyageai/client.py` (`__init__(self, api_key, max_retries=0, timeout=None, base_url=None)`).
- `psycopg2.connect(..., connect_timeout=10, sslmode="require", options="-c statement_timeout=15000")`.

Nu am schimbat altceva în comportamentul clienților (același model, aceleași tool_choice, același `embed`).

## 2. Clasificarea erorilor — pachete efectiv instalate

Nu am găsit un venv în worktree-ul R17; am citit sursa reală a pachetelor instalate la `D:\PYthon\Lib\site-packages` (`anthropic==0.116.0`, `voyageai==0.5.0`, versiuni identice cu `requirements.txt`).

**Anthropic** (`anthropic/_exceptions.py`): `AnthropicError` → `APIConnectionError` → `APITimeoutError` (fără `status_code`); `APIStatusError` (are `status_code` + `type: ErrorType|None`, populat din `body["error"]["type"]`) cu subclase fixe pe cod (`BadRequestError=400`, `AuthenticationError=401`, `PermissionDeniedError=403`, `RateLimitError=429`, `InternalServerError`, etc.). Am descoperit `ErrorType` include explicit `"billing_error"` (`anthropic/types/shared/error_type.py`, `billing_error.py`) — acesta e semnalul distinct pentru epuizarea creditului (400 + `type=="billing_error"`), nu doar un `invalid_request_error` generic.

Clasificare (`_classify_anthropic_failure`):
- `APITimeoutError` → `timeout`, status `-`.
- `APIStatusError` cu `type=="billing_error"` → `credit_exhausted` (status=cod, de regulă 400).
- altfel `status==429` → `rate_limited`; `status in (401,403)` → `auth`; `status>=500` → `server_error`; rest → `other`.
- orice alt `AnthropicError` (ex. `APIConnectionError` non-timeout) → `other`, status `-`.

**Voyage** (`voyageai/error.py` + `api_resources/api_requestor.py`): `VoyageError` are `http_status` (poate fi `None`). Subclase relevante generate de requestor: `Timeout`, `APIConnectionError`, `AuthenticationError` (401), `RateLimitError` (429), `ServerError` (500), `ServiceUnavailableError` (502/503/504), `InvalidRequestError` (400, generic — Voyage nu are un tip distinct pentru credit epuizat, deci `credit_exhausted` nu se declanșează niciodată pentru Voyage; e o limitare a SDK-ului, nu una introdusă de mine).

Clasificare (`_classify_voyage_failure`): `Timeout`→`timeout`; `AuthenticationError`→`auth`; `RateLimitError`→`rate_limited`; `ServerError`/`ServiceUnavailableError`→`server_error`; rest→`other`.

**DB** (`psycopg2.Error`, `pgcode` standard DB-API): am folosit `pgcode` când există (`28000`/`28P01`→`auth`, `57014` query_canceled/statement_timeout→`timeout`); altfel, pentru `OperationalError` (conexiune eșuată, ex. `connect_timeout` depășit fără pgcode) verific dacă mesajul conține „timeout” doar pentru clasificare internă (nu se loghează mesajul) → `timeout`, altfel `server_error`; orice alt `psycopg2.Error` → `other`.

## 3. Logging și stare provideri

- `_log_provider_failure` loghează exact `provider_failure provider=<p> category=<c> status=<cod|->` la nivel `WARNING`, apelat din `except AnthropicError`/`except VoyageError` (în adaptoare) și din `except (... psycopg2.Error)` din `/intreaba` (doar când `isinstance(error, psycopg2.Error)`). Nu am atins logul D21 (`generation_validation_failed`).
- `_ProviderHealthTracker` (lock `threading.Lock`, dict cu 3 chei fixe `anthropic|voyage|db`) — `record_failure` incrementează contorul și salvează categoria + `now`; `record_success` resetează contorul la 0 și salvează `now`. Success e apelat: în `VoyageQueryEmbedder.embed_query` și `AnthropicTextGenerator.generate` după un apel reușit (înainte de validarea payload-ului — o validare eșuată nu e „eșec de provider” per task); pentru DB, după primul `commit()` reușit din `/intreaba` (tranzacția rate-limit), folosind `now`-ul deja injectat al cererii.
- `GET /health/provideri`: `200 {"status":"ok"}` dacă `degraded_providers()` e goală; altfel `503 {"status":"degraded","provideri":[{"provider":...,"category":...}]}`. `degraded_providers` cere `consecutive_failures>=3` ȘI `now-last_event_at<=15min`. Nu face niciun apel extern — citește doar starea din memorie. `/health` neschimbat.

## 4. Deploy (scripts/deploy.ps1)

PowerShell 5.1 compatibil (`Set-StrictMode -Version Latest`, fără sintaxă PS7). Refuză dacă branch curent ≠ `main`, dacă `git status --porcelain` nu e gol (acoperă și necommise, și netracked), sau dacă `HEAD` ≠ `origin/main` după `git fetch origin main`. Apoi `python -m pytest -q` (oprire la `$LASTEXITCODE -ne 0`), apoi `railway up --detach`, apoi afișează SHA-ul (`$LocalSha`, deja verificat egal cu `origin/main`). Fără parametri, fără secrete.

## 5. DEPLOYMENT.md

Secțiune nouă „6.1 Deploy și rollback” (deploy prin script, rollback din Railway UI, monitorizare pe cele 2 endpoint-uri, tabel cu categoriile `provider_failure`) + rând nou pentru `/health/provideri` în tabelul de rute publice (§5). Nu am modificat CSP — `/health/provideri` e JSON, fără pagină statică nouă.

## Riscuri / ce ar trebui verificat

- **Clasificarea `credit_exhausted` la Anthropic depinde de `type=="billing_error"` în corpul răspunsului** — nu am putut testa live (fără acces la API real); dacă Anthropic schimbă formatul de eroare pentru credit epuizat, clasificarea ar cădea silențios în `other`/`rate_limited`/etc. în funcție de status code. Testerul ar trebui să verifice cu un `APIStatusError` mock (`status_code=400`, `type="billing_error"`).
- **Clasificarea DB prin `pgcode`/mesaj**: nu există un semnal universal pentru „connect_timeout depășit” fără pgcode; heuristic pe substring „timeout” în mesaj (folosit doar intern, nu logat) — testerul ar trebui să verifice cu `OperationalError` mock cu și fără „timeout” în mesaj.
- **`record_success("db")` se declanșează o singură dată per cerere**, după commit-ul tranzacției de rate-limit — un eșec DB ulterior în aceeași cerere tot ajunge la `record_failure`, deci contorul poate crește chiar dacă un commit anterior a reușit; comportament intenționat (ultimul eveniment contează), dar merită verificat cu un test de „succes urmat de eșec în aceeași cerere”.
- Nu am rulat `python -m pytest`, `railway`, sau orice altă comandă — Planner-ul trebuie să ruleze suita existentă (riscă breaking la teste care instanțiază `Anthropic`/`voyageai.Client` fără mock pe `timeout`/`max_retries` sau care verifică semnătura exactă a `psycopg2.connect`).
- Nu am scris teste noi (rol Tester).

## Runda 2 (27-09-2026)

Verificare reală a planner-ului: pytest 1098 passed; `deploy.ps1` parsează; conexiune DB
read-only OK cu `connect_timeout`/`sslmode=require`, dar `SHOW statement_timeout` întoarce
`2min`, nu 15s — `DB_PORT=6543` e pooler-ul Supabase (Supavisor) în mod transaction, care
ignoră `options` trimis la conectare. Un `SET statement_timeout` de sesiune ar fi periculos
(conexiunea de backend e partajată între clienți în acest mod).

Am scos din `main.py` `options="-c statement_timeout=..."` din `_open_db_connection` și
constanta `_DB_STATEMENT_TIMEOUT_MS` (config ineficientă = cod mort); am păstrat
`connect_timeout` și `sslmode="require"`. În `DEPLOYMENT.md`, la secțiunea „6.1 Deploy și
rollback”, am corectat rândul `timeout` din tabelul de categorii (DB: doar timeout de
conectare, nu de interogare) și am adăugat un paragraf nou care explică limitarea
pooler-ului, valoarea implicită de 2 minute a rolului Supabase, și că o limită mai strictă
necesită o migrare aprobată separat la nivel de rol Postgres.

## Runda 3 (27-09-2026)

Reviewer APROBAT cu finding MEDIUM: `$ErrorActionPreference='Stop'` nu oprește scriptul la
eșecul comenzilor native (`git`), doar la erori PowerShell; fără verificare `$LASTEXITCODE`
după `git rev-parse --abbrev-ref HEAD`, `git status --porcelain`, `git fetch origin main`,
`git rev-parse HEAD`, `git rev-parse origin/main`, un `git fetch` picat pe rețea putea lăsa
verificarea „HEAD == origin/main” să treacă pe ref-uri vechi din cache-ul local.

Am adăugat, în `scripts/deploy.ps1`, câte un `if ($LASTEXITCODE -ne 0) { throw "…" }` cu
mesaj distinct după fiecare din cele 5 comenzi `git` native, exact ca la `pytest`/`railway`.
Nu am schimbat altceva în script.
