# R17 — Coder: fiabilitate în producție

Worktree: `D:\Omnia-MVP-r17-fiabilitate`, branch `feat/r17-fiabilitate` (din `main` `39d7340`). Aprobat de Lucian 27-09-2026: prioritatea e ca aplicația să nu cadă în producție și să știm imediat când are o problemă.

## Context și dovezi
- 25-09-2026: creditul Anthropic s-a epuizat; `/intreaba` a răspuns 503 tuturor, iar în loguri **nu a apărut nimic**: `main.py:193` transformă orice `AnthropicError` în `ProviderUnavailableError`, iar `main.py:808-817` loghează doar `GenerationValidationError` (D21). La fel pentru Voyage (`main.py:136`) și `psycopg2.Error`.
- Audit R10, F6: clienții runtime nu au timeout și folosesc retry-urile implicite (`main.py:188` `Anthropic(api_key=…)`, `main.py:133` `voyageai.Client(api_key=…)`); scripturile de ingestie folosesc deja `timeout=30, max_retries=0`. DB-ul (`main.py:271-279`) nu are `connect_timeout`, `statement_timeout` sau `sslmode`.
- `/health` (`main.py:464`) e healthcheck-ul platformei Railway și trebuie să rămână ieftin (nu atinge DB/provideri). Aplicația rulează un singur proces (`Procfile`: `uvicorn main:app` fără workers).
- Audit R10, F12: deploy-ul se face cu `railway up` din copia de lucru (pot urca modificări necommise); rollback-ul nu e documentat.

## Sarcina
1. **Timeout-uri:** Anthropic `timeout=30`, `max_retries=1`; Voyage `timeout=15`, `max_retries=1`; `psycopg2.connect(..., connect_timeout=10, sslmode="require", options="-c statement_timeout=15000")`. Valorile ca constante numite la începutul modulului. Nu schimba altceva în comportamentul clienților.
2. **Diagnostic de provider, fără date sensibile:** când un apel Anthropic/Voyage eșuează sau DB-ul ridică `psycopg2.Error` în `/intreaba`, loghează o singură linie de nivel `WARNING`: `provider_failure provider=<anthropic|voyage|db> category=<credit_exhausted|rate_limited|timeout|server_error|auth|other> status=<cod HTTP sau ->`. Clasificarea din tipul excepției și codul HTTP (ex. Anthropic 400 cu tipul de eroare pentru credit, 429, 401/403, 5xx, timeout). **Nu** loga mesajul excepției, întrebarea, promptul, chei sau payload. Răspunsul public rămâne exact cel de acum (503 generic).
3. **Starea providerilor pentru monitorizare:** o stare în memorie, thread-safe, care ține pentru fiecare provider (`anthropic`, `voyage`, `db`) numărul de eșecuri consecutive, ultima categorie și momentul ultimului eșec/succes. Un succes resetează contorul providerului respectiv. Endpoint nou `GET /health/provideri`: **nu** face apeluri externe; întoarce 200 `{"status":"ok"}` dacă niciun provider nu are ≥3 eșecuri consecutive în ultimele 15 minute, altfel 503 `{"status":"degraded","provideri":[{"provider":…,"category":…}]}`. Fără detalii suplimentare, fără timestamp-uri exacte. `/health` rămâne neschimbat.
4. **Deploy sigur:** script nou `scripts/deploy.ps1` (PowerShell 5.1) care refuză să ruleze dacă branch-ul curent nu e `main`, dacă există modificări necommise sau fișiere netracked, sau dacă `HEAD` diferă de `origin/main` după `git fetch`; apoi rulează `python -m pytest -q` și se oprește la eșec; apoi `railway up --detach` și afișează SHA-ul publicat. Fără secrete, fără parametri care ocolesc verificările.
5. **`DEPLOYMENT.md`:** secțiune scurtă „Deploy și rollback”: deploy doar prin `scripts/deploy.ps1`; rollback din Railway (Deployments → deployment-ul anterior → Redeploy); monitorizare externă pe `/health` și `/health/provideri`; ce înseamnă fiecare categorie din `provider_failure`. Documentează și CSP/allowlist dacă e nevoie pentru ruta nouă (nu ar trebui).

## Constrângeri dure
- Nu rula comenzi. Nu scrie teste noi (Tester-ul).
- Atinge doar `main.py`, `scripts/deploy.ps1`, `DEPLOYMENT.md` și raportul. Nu atinge `generation_core.py`, `retrieval_core.py`, `chunking_core.py`, `access_control.py`, `static/`, `supabase/`, `.env`.
- Contractele D20/D21/D22 rămân neschimbate (inclusiv logul D21 exact).
- Fără comentarii inutile.

## Predare
`docs/handoff/R17-coder-raport.md`: fișiere, cum ai clasificat erorile (cu tipurile de excepție SDK folosite), riscuri.
