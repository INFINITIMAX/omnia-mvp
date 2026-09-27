# R07 — audit operațional release — raport

Data: 25-09-2026. Read-only: nicio comandă rulată, niciun fișier modificat, niciun apel Railway/Supabase/Voyage/Anthropic.

## Verdict: **PASS condiționat**

Fundația operațională e solidă pentru scara actuală (MVP, 4 testeri controlați, fără cont/plată): healthcheck corect, CI cu teste+audit CVE pe fiecare push/PR, headere de securitate complete și documentate, controale de cost/rate-limit explicate în detaliu tehnic în `DEPLOYMENT.md`. **Nu e "BLOCKED"** — nimic din ce am găsit oprește operarea curentă. E "condiționat" pentru că lipsesc trei lucruri standard înainte de o expunere publică completă, toate deja semnalate explicit de proiect însuși în `DEPLOYMENT.md §7` ca restanțe cunoscute — nu sunt findinguri noi, ci o confirmare independentă a lor.

## Finding-uri

### Critic — niciunul găsit în ce e read-only-verificabil.

### Mediu

1. **Nu există procedură de rollback documentată pentru deploy.** Căutare explicită în toate `.md`-urile proiectului (`TASKS.md`, `PLAN.md`, `GATES.md`, `revizii.md`, `docs/*.md`) — singurele potriviri pentru "rollback" sunt despre rollback de tranzacție DB la quota (`main.py`, cf. `docs/PROJECT_OVERVIEW.md:87`), nu despre revenirea la un deploy anterior pe Railway. Railway păstrează istoric de deployment-uri și permite revenire prin dashboard, dar acest lucru **nu e documentat în repo** — dacă un deploy nou stochează probleme, procedura de revenire trăiește doar în capul cuiva, nu în `DEPLOYMENT.md`. *Dovadă:* grep pe `rollback|backup|restore` peste `*.md`, fără nicio potrivire relevantă pentru deploy.
2. **Nu există procedură de backup/restore documentată pentru Supabase/PostgreSQL.** Aceeași căutare, același rezultat — zero mențiune a unei strategii de backup pentru baza de date de producție (Supabase are backup automat pe planurile plătite, dar retenția/frecvența/procedura de restore nu sunt confirmate nicăieri în repo). *Necesită verificare externă*: planul Supabase curent și politica lui de backup.
3. **Fără observabilitate dincolo de logging stdlib.** `main.py:7,51` — un singur `logging.getLogger(__name__)`, fără integrare Sentry/Datadog/Prometheus sau alt sistem de alerting. Railway are propriul vizualizator de log-uri (nu am acces să confirm ce reține/cât), dar nu există alertare proactivă pe erori 503/5xx — cineva trebuie să se uite manual. Pentru scara actuală (4 testeri) e acceptabil; pentru expunere publică e un gap real.
4. **Paritate main/Railway neconfirmată.** Deploy e manual (`railway up`, fără Git Source conectat — confirmat prin absența oricărui workflow de deploy în `.github/workflows/` — singurul fișier e `tests.yml`, doar teste+audit). Ultima verificare live documentată în `TASKS.md` e din 13-09-2026, SHA `4bc4973`; `main` a avansat de atunci prin mai multe merge-uri (D20/D21/D22, R05). **Necesită verificare externă**: SHA-ul rulat efectiv acum pe Railway — nu poate fi confirmat din fișiere locale.

### Minor

5. **Cleanup periodic (`cleanup_rate_limit_buckets.py`) nu e programat pe Railway** — confirmat explicit chiar în `DEPLOYMENT.md:212-223` ca restanță cunoscută, cu pași expliciți de configurare Cron Schedule, netrecuți. Rulează doar manual până atunci. Impact redus (retenție 24h).
6. **5 PR-uri Dependabot deschise, stale de 19+ zile** (deja notat în `HANDOFF.md`), inclusiv un major bump `anthropic` 0.116.0 → 1.3.0 cu risc de breaking changes — nu blochează operarea curentă dar e datorie tehnică de securitate acumulată.

## Ce NU poate fi verificat fără acces live (necesită verificare externă explicită)

- SHA-ul exact rulat curent pe Railway vs. `main` la `132f7f4`.
- Planul Supabase și politica lui reală de backup/retenție.
- Ce reține/cât Railway din log-uri, și dacă există vreo alertare nativă a platformei activată manual din dashboard (nevizibilă din repo).
- Dacă variabilele de mediu din `DEPLOYMENT.md §3` sunt efectiv setate corect în Railway (`TRUSTED_PROXY_HOPS=1`, `ANONYMOUS_COOKIE_SECURE=true`, cheile distincte) — documentul spune ce *trebuie* setat, nu confirmă ce *este* setat.
- Statusul real al celor 5 PR-uri Dependabot (severitate CVE-urilor pe care le rezolvă).

## Puncte forte confirmate (pozitiv, nu doar gap-uri)

- `/health` (main.py:453-456) e exact cum descrie documentația: nu atinge DB/provideri, răspuns ieftin și rapid — corect proiectat pentru healthcheck de platformă.
- CI (`​.github/workflows/tests.yml`) rulează pytest **și** `pip-audit` pe fiecare push/PR către `main` — scanare CVE automată există și e activă, nu doar planificată.
- `DEPLOYMENT.md` e neobișnuit de detaliat și corect pentru un proiect de această mărime: explică nu doar *ce* variabile sunt necesare, ci *de ce* (inclusiv un exemplu concret de exploatare pentru `TRUSTED_PROXY_HOPS` greșit configurat) — calitate de documentație rar întâlnită la stadiul de MVP.
- Politica de cost (`DAILY_PAID_CALL_LIMIT`) e gândită corect: fail-closed, răspuns nedistins de o eroare tehnică obișnuită, ca să nu semnaleze public mecanismul.
