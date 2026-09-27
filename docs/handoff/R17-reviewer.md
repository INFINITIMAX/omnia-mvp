# R17 — Reviewer

Worktree: `D:\Omnia-MVP-r17-fiabilitate`, branch `feat/r17-fiabilitate`; `main` în `D:\Omnia-MVP`. Citește `R17-coder.md`, `R17-coder-raport.md` (inclusiv Runda 2), `R17-tester.md`, `R17-tester-raport.md`, `docs/DECISIONS.md` (D20–D22), `DEPLOYMENT.md`.

Dovezi planner: `python -m pytest -q` → **1136 passed**, 28 skipped (documente reale absente). Conexiune reală read-only OK cu `connect_timeout=10` și `sslmode=require`; `statement_timeout` scos (ignorat de pooler-ul Supabase în mod transaction, portul 6543). `scripts/deploy.ps1` parsează.

## Ce verifici
1. **Securitate/date:** logul `provider_failure` nu poate conține mesajul excepției, întrebarea, chei sau payload; `/health/provideri` nu expune detalii exploatabile; nu face apeluri externe.
2. **Comportament:** răspunsurile publice ale `/intreaba` rămân identice (503 generic); logul D21 neschimbat; `/health` neschimbat; retry-ul (`max_retries=1`) nu dublează costul în mod periculos cu cota/bugetul existent (rezervarea bugetului înainte de apel — `main.py`, `generate` cu `self._guard.reserve()`); timeout-urile compatibile cu latența reală a generării (max 1200 tokeni).
3. **Tracker-ul de stare:** thread-safety, fereastra de 15 minute, resetarea la succes, pragul de 3; comportament corect cu un singur proces uvicorn.
4. **`scripts/deploy.ps1`:** poate fi ocolit? erorile `git`/`pytest` opresc realmente scriptul (PowerShell 5.1: `$LASTEXITCODE` după comenzi native)? nu scrie secrete.
5. **Cod inutil** în producție sau teste; teste care trec indiferent de cod.

Read-only, fără comenzi. Verdict APROBAT/RESPINS, finding-uri pe severitate cu fișier:linie, separat coder/tester, max 600 de cuvinte.
