# R17 — Tester

Worktree: `D:\Omnia-MVP-r17-fiabilitate`, branch `feat/r17-fiabilitate`, commit `775372b`. Citește `R17-coder.md` și `R17-coder-raport.md` (inclusiv Runda 2).

## Starea verificată de planner
- `python -m pytest -q`: 1098 passed, 28 skipped (documente reale absente din worktree).
- Conexiune reală read-only cu noile setări: OK (`connect_timeout`, `sslmode=require`). `statement_timeout` a fost scos (pooler-ul Supabase în mod transaction îl ignora).
- `scripts/deploy.ps1` parsează corect în PowerShell 5.1.
- Anthropic SDK 0.116.0 are tipul de eroare `billing_error` (`anthropic/types/shared/billing_error.py`).

## Sarcina — teste în `tests/test_api_integration.py` (sau fișier nou dedicat), cu clienți falsificați, fără rețea
1. **Timeout-uri:** adaptorul Anthropic construiește clientul cu `timeout=30, max_retries=1`; Voyage cu `timeout=15, max_retries=1`; `_open_db_connection` trimite `connect_timeout=10` și `sslmode="require"` și **nu** trimite `options` (monkeypatch pe `psycopg2.connect`, `Anthropic`, `voyageai.Client`).
2. **Clasificare `provider_failure`:** pentru fiecare categorie (credit_exhausted cu `billing_error`, rate_limited 429, auth 401/403, server_error 5xx, timeout, other) un caz Anthropic; câteva pentru Voyage și DB (pgcode 28P01 → auth, 57014 → timeout). Verifică linia de log exactă (`provider_failure provider=… category=… status=…`) și că **nu** conține mesajul excepției, întrebarea sau vreo cheie. Răspunsul public rămâne 503 generic identic.
3. **Logul D21** rămâne neschimbat pentru `GenerationValidationError` (există deja teste — nu le duplica; adaugă doar ce lipsește).
4. **`/health/provideri`:** 200 când nu sunt eșecuri; 503 cu `{"status":"degraded","provideri":[…]}` după 3 eșecuri consecutive ale unui provider în 15 minute; un succes resetează; eșecuri mai vechi de 15 minute nu degradează (timp injectat, fără `sleep`); nu face apeluri externe; `/health` rămâne `{"status":"ok"}` chiar când providerii sunt degradați.
5. **`scripts/deploy.ps1`:** doar un test static ieftin (conținutul refuză branch ≠ main, working tree murdar, HEAD ≠ origin/main și rulează pytest înainte de `railway up`) — fără a-l executa.

## Constrângeri
Scrii doar în `tests/`. Nu rula comenzi. Fără modificări de producție; bug suspectat → raportezi. Fiecare test trebuie să poată pica. Raport în `docs/handoff/R17-tester-raport.md`.
