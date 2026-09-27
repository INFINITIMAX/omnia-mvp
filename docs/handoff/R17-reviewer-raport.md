# R17 — raport Reviewer (transcris integral de planner, 27-09-2026)

## Verdict: APROBAT (cu un finding MEDIUM de urmărit)

Am citit R17-coder.md, R17-coder-raport.md (Runda 1+2), R17-tester.md, R17-tester-raport.md, DECISIONS.md (D20-D22, D23/D24), DEPLOYMENT.md §5/§6.1, și codul efectiv: `main.py` (liniile 55-170, 225-420, 460-490, 595-613, 820-970), `scripts/deploy.ps1`, testele noi din `tests/test_api_integration.py` (liniile 2090-2438).

### Coder — verificat punct cu punct din brief
- **Timeout-uri** (`main.py:61-65`, 254, 316, 413): valori corecte, constante numite, comportament neschimbat altfel (același model, tool_choice, embed). Verificat de planner cu conexiune reală → `connect_timeout`/`sslmode=require` funcționează.
- **`statement_timeout` scos în Runda 2**: decizie corectă și documentată — pooler-ul Supabase (Supavisor, port 6543) ignoră `options`; a păstra o constantă/config care nu face nimic ar fi fost exact „cod inutil”. Bine prins și corectat de coder însuși.
- **Clasificare provider_failure** (`main.py:74-118`): mapare curată pe tipuri reale de excepție SDK (`APIStatusError.type=="billing_error"`, `pgcode` Postgres etc.), fără mesaj/payload logat — confirmat, `_log_provider_failure` (linia 120-124) loghează strict `provider=... category=... status=...`.
- **Tracker de stare** (`main.py:134-167`): thread-safe (`threading.Lock`), fereastră 15 min, prag 3, reset la succes — logica e corectă și minimală.
- **`/health/provideri`** (606-612): nu face niciun apel extern (doar citește tracker-ul în memorie); `/health` neatins (600-603).
- **Bugetul/retry**: `BudgetGatedTextGenerator`/`BudgetGatedEmbedder` (374-395) apelează `guard.reserve()` o singură dată (flag `_reserved`) înainte de apelul SDK; `max_retries=1` e retry la nivel de transport SDK, în interiorul acelei rezervări unice — nu dublează costul. Am verificat și că D22 („nu se adaugă retry”) se referă la retry aplicativ la răspuns invalid al tool-ului, un strat diferit de retry-ul de transport aprobat explicit acum de Lucian — nu e o încălcare de contract.
- Constrângerea de fișiere atinse respectată (`main.py`, `scripts/deploy.ps1`, `DEPLOYMENT.md`, raport).

### Finding MEDIUM — `scripts/deploy.ps1`
`$ErrorActionPreference='Stop'` nu oprește scriptul la eșecul comenzilor native (`git`); doar `pytest`/`railway up` sunt verificate explicit cu `$LASTEXITCODE` (liniile 27-35). Comenzile `git status --porcelain` (15), `git fetch origin main` (20), `git rev-parse HEAD`/`origin/main` (21-22) nu au verificare de `$LASTEXITCODE`. Cel mai relevant scenariu: dacă `git fetch` eșuează (rețea/VPN), scriptul continuă cu ref-uri `origin/main` potențial vechi din cache local — verificarea „HEAD diferă de origin/main” poate trece fals-pozitiv (pare sincronizat, deși fetch-ul real nu a rulat), oferind încredere falsă exact pe garanția de siguranță cerută explicit de task. Recomandare pentru coder: adaugă `if ($LASTEXITCODE -ne 0) { throw ... }` după fiecare comandă `git` nativă, la fel ca la pytest/railway. Nu blochează acceptarea — nu e cod inutil, nu poate fi ocolit prin parametri, doar insuficient de strict pe eșecuri native de rețea.

### Tester
Fiecare test verificat are o condiție de eșec concretă (kwargs greșite → pică; categorie greșită → pică; mesaj/întrebare scurse în log → pică; prag/fereastră greșite → pică). Notabil:
- `test_open_db_connection_trimite_connect_timeout_si_sslmode_fara_options` — test de regresie explicit pentru fix-ul Rundei 2 (`options` să nu mai apară).
- `fresh_provider_health` — izolare corectă a stării globale de singleton, evită teste flaky.
- Workaround-ul pentru `pgcode` read-only (subclasă locală cu property) e legitim și documentat, păstrează `isinstance`.
- Nu am găsit teste redundante sau teste care ar trece indiferent de cod; testul static pentru `deploy.ps1` verifică conținut relevant (ordinea pytest/railway, `$LASTEXITCODE`, absența parametrilor), consistent cu findingul de mai sus (nu a fost cerut să verifice `$LASTEXITCODE` pe comenzile git — nu e o omisiune a testerului, ci un gol în implementare).
- D21 corect neduplicat; interacțiunea nouă (`generation_validation_failed` nu declanșează `provider_failure`) e testată separat.

### Concluzie
Munca e solidă, fără cod inutil, cu dovezi reale (1136 passed, conexiune DB reală testată). Singurul gol e robustețea `deploy.ps1` la eșecuri native de `git` — recomand ca planner-ul să-l trimită coder-ului pentru o corecție mică (adăugare `$LASTEXITCODE` checks), fără a relua tot ciclul de tester/reviewer dacă schimbarea rămâne strict în `scripts/deploy.ps1`.

---

## Decizia planner-ului
Finding-ul MEDIUM trimis coder-ului (verificare `$LASTEXITCODE` după fiecare comandă `git`). Planner-ul verifică static corectura și rulează suita; fără reluarea ciclului tester/reviewer dacă schimbarea rămâne strict în `scripts/deploy.ps1`.
