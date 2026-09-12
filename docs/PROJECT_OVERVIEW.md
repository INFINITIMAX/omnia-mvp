# NormativAI — vedere completă a proiectului

## Predare D11 — aprobat, implementare blocată (11-09-2026)

Rezumat complet și pași următori: [`HANDOFF.md`](../HANDOFF.md). Coderul a eșuat la limita de utilizare înainte să salveze fișierul de teste D11; implementarea/QA/Reviewer nu au fost lansate. Rerularea de predare confirmă 761 passed/11 skipped, diagnostic 19 cazuri/10 afirmații nepublicabile acceptate/zero pasaje omise și toate fișierele Python identice cu snapshotul pre-D11. Fără agenți activi, DB/API real sau deploy. Checkpoint-ul GitHub `8ca650ec21d01142c1936712097b86ec81733188` este împins pe `origin/fix/stabilizare-coduri-normative`; păstrează R06/5A locale și testele RED D11–D13, nu reprezintă merge sau producție. D11–D14 sunt acceptate local: după P1, 105 teste focalizate și 962 complete trec/11 skip-uri corpus absent; QA P1 și Reviewer P1 OK. R05 rămâne deschis: diagnosticul are încă 10 afirmații nepublicabile acceptate. Nicio producție/DB/API plătit nu este schimbată. Actualizare: D12 aprobă „doar/numai/exclusiv din [cod]” numai pentru întrebarea curentă; codul necunoscut cere clarificare fără global fallback, însă statusul/quota rămân decizie D01. La verificarea GitHub din 11-09-2026, `origin/main` este același `237e11d` ca baza locală; nu există remote de integrat și nu s-a făcut pull/rebase/merge/push.

Lucian a clarificat obiectivul: răspunsuri complete și relevante din mai multe documente aprobate, cu restricții numai la cerere explicită. A aprobat apoi reluarea lucrului. Contextul trebuie să ajute înțelegerea întrebării, nu să blocheze automat căutarea la documentele citate anterior. Codul actual încă are filtrul implicit și tratează două documente menționate ca ambiguitate; modificarea este blocată înainte de salvarea/rularea testelor RED, nu implementată. D11 înlocuiește vechea politică în plan; nu modifică eligibilitatea, quota, R06, DB sau plafoanele. Detalii în `revizii.md`, `TASKS.md` și `docs/D11_CODE_WALKTHROUGH.md`. Oprirea de mai jos este istoric, depășită numai pentru acest task local. Fără autorizare de publicare/DB/API plătit.

## R06 verificat local; execuție oprită pentru discuție (11-09-2026)

QA și Reviewer au aprobat R06; Planner a reconfirmat hash-urile celor opt fișiere revizuite, fără modificări ulterioare de cod. 402 teste focalizate, 761 complete trecute, 11 omise pentru corpus absent; patru probe semantice mockuite suplimentare trecute. Pasajele omise din evaluator: 2 → 0 pe aceiași 19 candidați. R05 rămâne deschis cu 10 afirmații nepublicabile acceptate; nu s-a testat modelul live. Detaliile sunt în `revizii.md`, iar explicația implementării în `docs/R06_CODE_WALKTHROUGH.md`.

Lucrul este încă necomis/nepublicat, fără DB, API plătit sau deploy. La cererea lui Lucian ne oprim după această predare, fără task nou. Statusurile de review în curs de mai jos sunt istoric, depășite de această actualizare.

## R06 — implementare locală în review (10-09-2026)

Generation core folosește acum local JSON strict cu pasaje declarate, verificate literal în dovada corespunzătoare; schimbarea nu este publicată. Host: 402 focused passed, 761 full passed/11 skipped/1 warning. Pe aceiași 19 candidați sintetici, pasajele omise scad de la 2 la 0; cele 10 afirmații nepublicabile acceptate rămân problema R05, fără măsurare a modelului live. QA și Reviewer verifică independent snapshotul înainte de acceptarea locală finală. Coderul a salvat lucrul înainte să fie oprit de limita providerului. Schema publică/DB/SDK sunt neschimbate; fără commit/push/deploy. Statusurile „pregătire RED/neimplementat” din istoricul de mai jos sunt depășite de această actualizare.

## Stare actualizată — 5A verificat local (10-09-2026)

Evaluatorul local este livrat în worktree: `grounding_eval.py`, 19 cazuri fictive și 34 teste noi. Host: 591 passed, 11 skipped din cauza corpusului absent, un warning extern. QA/Reviewer OK; ultima clarificare doar în docstring a fost verificată prin AST și rerulări. Diagnosticul are exit 1 și 12 constatări în 11 cazuri; **R05/R06 rămân deschise**. Nu este test al modelului live, nu este validator conectat la API și nu schimbă produsul public. Lucrul este încă necomis/nepublicat. Ulterior Lucian a aprobat direcția D08/R06: pasaj indicat de model și verificat în dovada citată de backend. Politica pasajului lipsă/invalid a fost ulterior aprobată: 503, rollback quota verificat, fără retry nou sau fallback. Trunchierea a fost confirmată: JSON complet/valid păstrează avertismentul, JSON incomplet produce 503 fără reparare/retry. Lotul local R06 intră în pregătire RED; nu este încă implementat/publicat. Actualizarea de față înlocuiește numai statusul 5A „în pregătire” din istoricul de mai jos.

## Prioritate actuală — revizii (09-09-2026)

**Aprobare ulterioară:** Lucian a ales evaluarea locală întâi (5A): cazuri sintetice și raport diagnostic, fără nou validator public, DB sau costuri API. Implementarea acestui set este în pregătire; deciziile despre protecția viitoare și evaluarea live rămân deschise. Mențiunea de strategie încă nealeasă din paragraful istoric de mai jos este depășită numai pentru această subetapă locală.

Lucian a cerut începerea cu problemele cele mai complicate: 5A/R05–R06 din `revizii.md`, corectitudinea afirmațiilor și citărilor. Probe locale noi au reconfirmat acceptarea unor afirmații sintetice greșite cu ID valid și omiterea pasajului relevant de citatul-prefix. Nu este remediere și nu este măsurare a modelului live. Strategia D07/D08 așteaptă decizie; nu s-a modificat runtime-ul și nu s-au apelat DB/provideri reali. Pasul 0 rămâne nerevizuit final, pasul 1 neînceput; ordinea inițială 0–1 menționată în istoricul de mai jos este depășită de această prioritate.

## Stare de referință — 09-09-2026

- **Cod integrat:** `origin/main` la `237e11db81251b8eb316ec02aa01e428089c66bc`, cu fixul de status `e49223f` și workerul `6cfd69c`, ambele prin PR8. Cod integrat nu înseamnă deploy sau activare.
- **Ultimul deploy verificat anterior:** `47a6133` (08-09-2026). Nu există verificare live nouă în acest lot.
- **Workflow aprobat:** Lucian pune **un PDF** în `documente_noi/_inbox`, anunță Planner-ul și primește raport **local** de extracție/validare; DB + Voyage cer aprobare separată, iar publicarea (`approved`) încă una. Importul manual sigur punctual **nu este încă livrat**; `populare_db.py` nu este insert-only.
- **Worker păstrat, inactiv:** Lucian a renunțat la activare; Task Scheduler este neinstalat, migrarea `20260909000000_document_ingestion_sources.sql` este neaplicată conform predării. Nu se elimină codul/scriptul/migrarea. Registrul SHA și pornirea la logon sunt decizii independente, neaprobate implicit pentru fluxul manual.
- **Validare locală de referință:** logul host `C:/Users/Lucian-PC/AppData/Local/Temp/normativai-stabilizare-237e11d/baseline.log` arată `557 passed, 11 skipped, 1 warning` (TestClient). Este baseline, nu gate final, test rulat personal de Coder sau evaluare reală de calitate.

### Migrări — dovezi istorice, fără audit DB nou

- `20260831165749_document_metadata.sql`: aplicarea persistentă și verificarea sunt documentate în `TASKS.md`.
- `20260831220000_approve_initial_documents.sql`: aprobarea inițială și statusurile sunt documentate; migrarea reproduce decizia, fără a afirma aici un istoric de execuție SQL reverificat.
- `20260831230000_anonymous_access_controls.sql`: aplicarea persistentă este documentată la 01-09-2026, inclusiv gate-urile de atunci.
- `20260903120000_approve_second_batch_documents.sql`: importul/aprobarea lotului 2 și aplicarea sunt documentate istoric la 03-09-2026, înainte de versionare.
- `20260909000000_document_ingestion_sources.sql`: **neaplicată conform predării**.
- Pentru celelalte migrări nu se afirmă aplicare neverificată. Prezența unui fișier SQL sau a unui merge nu dovedește execuția în Supabase. Registrul `supabase_migrations.schema_migrations` nu era vizibil conexiunilor istorice; acest lot nu face audit DB.

## Ce este funcțional în cod / documentat istoric

- Lucian a confirmat istoric 10 documente cu status `approved`; nu este verificare DB nouă. Numărul curent de chunk-uri este necunoscut.
- Tabelul `documente` păstrează codul și titlul oficial, anul și statusul.
- Documentele eligibile pentru retrieval au status `approved`. Aprobările loturilor inițiale sunt înregistrate în migrări SQL reproductibile (`20260831220000` pentru lotul 1, `20260903120000` pentru lotul 2).
- **Inventar istoric 03-09-2026:** `p118_2_2013_modificari` conținea numai Ordinul 966/2018, iar textul de bază P 118/2-2013 era pe hold. Acoperirea actuală nu se deduce din acel inventar sau din totalul confirmat de 10 documente.
- Relația document–sursă este protejată prin FK compus.
- Chunk-urile au articol normalizat, hash de conținut și ordine stabilă.
- RLS este activ; `anon` și `authenticated` nu au granturi sau politici.
- Retrieval Core este implementat și testat: parser, exact lookup, semantic pgvector, deduplicare, ambiguitate și limite. Contextul conversațional cu coduri aprobate și documentul numit explicit restrâng semantic retrieval-ul; un scoped miss devine `not_found`, fără fallback global.
- Generation Core este implementat și testat: ID-uri temporare deterministe, prompt cu întrebarea și dovezi tratate ca date neîncrezătoare, citări validate fail-safe și obiecte publice derivate exclusiv din Evidence.
- `POST /intreaba` orchestrează catalogul aprobat, Retrieval Core și Generation Core; returnează statusuri controlate și citări oficiale, fără identificatori tehnici.
- Controalele anonime sunt integrate mock-first în FastAPI: `GET /` emite cookie-ul semnat `normativai_anon`, iar `POST /intreaba` îl emite ca fallback; cookie-ul este `HttpOnly`, `SameSite=Lax`, `Path=/` și expiră în 365 zile. Atributul `Secure` este citit strict din configurația server-side, pentru local/test HTTP.
- `POST /intreaba` aplică rate limiting înainte de providerii externi și quota înainte de retrieval/generare, pe o singură conexiune: tranzacția rate este confirmată separat, iar quota este confirmată doar pentru răspunsurile normale sau restituită prin rollback la erori tehnice. Răspunsurile normale includ `intrebari_ramase`; 429 expune `rate_limited`, mesaj generic și `Retry-After`, iar 403 expune `quota_exhausted`, mesajul de epuizare și `intrebari_ramase: 0`.
- Schema Supabase pentru contoarele anonime este aplicată persistent din 01-09-2026 (România): 2 tabele, 10 constraints, RLS fără politici, zero granturi pentru rolurile publice și index de cleanup. Validarea fresh connection și gate-ul de concurență cu hash-uri sintetice au trecut; cleanup-ul a lăsat ambele tabele fără rânduri.
- `static/index.html` este UI-ul MVP conectat exclusiv la `POST /intreaba`: text inițial „Limită: 10 întrebări/browser”, apoi `intrebari_ramase` din răspunsul normal, blocare permanentă la 403 și temporară la 429 (`Retry-After` numeric strict validat), mesaje dedicate pentru 422 și generice fără status/excepții pentru 503/rețea/JSON invalid; randare exclusiv prin `textContent`/DOM, fără `innerHTML` pentru date server/utilizator și fără citire de cookie din JS.
- **Rezultat istoric anterior PR8:** 533 teste complet locale/mockuite, inclusiv 31 teste statice pentru UI și setul formal de evaluare din §10 al `docs/HYBRID_SEARCH_SPEC.md`. Setul de evaluare e un **regression eval sintetic, determinist, local/mockuit pentru un set controlat** (nu o evaluare de calitate reală Voyage/Claude): un repository sintetic unic caută exact strict document+articol într-un corpus comun cu decoy-uri, iar la semantic rankuiește tot corpusul prin similaritate cosinus reală calculată determinist din text (fără `hash()` randomizat, fără hardcodare caz→dovadă); `SEMANTIC_CASES` are 12 parafraze sintetice controlate — 12 cazuri fac pragul ≥90% neechivalent cu o cerință de 100% (11/12 = 91,7%) —, fiecare cu alt vocabular/altă structură de frază decât propoziția-țintă din `CORPUS` — un test dedicat verifică literal, prin cel mai lung șir de cuvinte consecutive identice, că nicio întrebare nu o copiază; embedderul recunoaște parafrazele printr-un vocabular conceptual sintetic de sinonime/variante morfologice — un vocabular conceptual sintetic, definit manual, comun corpusului și întrebărilor —, nu o mapare caz→dovadă. Metricile verifică identitatea document+articol așteptată, iar un control negativ confirmă că o întrebare fără semnal relevant nu primește automat dovada (exact lookup 100%, refuz articole inventate 100%, semantic 100% din 12 cazuri, prag ≥90%, fără apeluri reale/plătite și fără validare pe trafic public). Testul HTTP anti-leak folosește un helper comun (`_assert_no_technical_identifiers`) aplicat pe statusurile retrieval sub 200 și, separat, în testele reprezentative pentru 422/403/429/503 — acoperire reală pe toate codurile publice, plus un warning extern de deprecere TestClient.

## Ce nu este încă funcțional în aplicația publică

- `ANONYMOUS_COOKIE_SECURE=true`, `TRUSTED_PROXY_HOPS=1` și healthcheck-ul Railway `/health` sunt configurate în production. Ferestrele rate-limit expiră logic prin `expires_at` după 24 ore și nu mai sunt reutilizate, dar ștergerea fizică în maximum 24 ore nu este garantată fără un scheduler/job separat, rămas deferred până la aprobare.
- Rate limiting-ul folosește `TRUSTED_PROXY_HOPS=1` în production pentru proxy-ul Railway; CORS și cleanup runtime rămân neimplementate.
- UI-ul nu are cont. `/health` este implementat. **`/documents` nu există și nu se va implementa** — a fost livrat la 05-09-2026 (commit `9bd65d5`) urmând backlogul din `PLAN.md`, apoi eliminat la 07-09-2026: catalogul complet al normativelor indexate arată exact ce acoperă și ce nu acoperă produsul, informație sensibilă competitiv. Din același motiv lista documentelor fusese scoasă din nav la 03-09-2026, înlocuită cu istoricul conversațiilor.
- **Corecție de stare:** redesign-ul negru-auriu și verificările vizuale/browser sunt documentate ca livrate în predările din `TASKS.md`; afirmația veche că sunt deferate este depășită. Nu s-a făcut o verificare browser nouă în acest lot.
- Ultimul deploy verificat anterior este merge commitul `47a6133` din `main`, publicat manual pe Railway la 08-09-2026. Healthcheck-ul `/health` și smoke-ul HTTPS fără provider au trecut atunci; serviciul era fără Git Source/autodeploy legat. Nu se afirmă o verificare live nouă.
- Nu s-a rulat un smoke test plătit pentru noul Retrieval Core.

## Fluxul țintă

1. FastAPI validează întrebarea.
2. Parserul detectează documentul/articolul.
3. Referința explicită folosește exact lookup, fără Voyage.
4. Întrebarea semantică primește un singur embedding Voyage.
5. Retrieval Core filtrează, deduplică și limitează dovezile.
6. Claude primește numai dovezile aprobate și ID-uri temporare de citare.
7. Backend-ul validează citările și construiește răspunsul public.
8. Browserul primește răspunsul și metadata oficială, nu date tehnice.

## Fișiere principale

- `main.py` — FastAPI: `GET /` și `POST /intreaba`, integrează Retrieval Core, Generation Core și controalele anonime.
- `retrieval_core.py` — parser, repository PostgreSQL și serviciul de retrieval.
- `populare_db.py` — ingestion existent, nu insert-only și nu livrarea importului manual sigur punctual.
- `auto_ingestion_worker.py` — worker automat integrat, păstrat **inactiv**; runbook istoric în `docs/AUTO_INGESTION_WORKER.md`.
- `supabase/migrations/` — schema reproductibilă și metadata.
- `docs/HYBRID_SEARCH_SPEC.md` — contractul detaliat hybrid search/API/teste.
- `docs/DECISIONS.md` — deciziile explicite aprobate.
- `PLAN.md` — etapele proiectului.
- `TASKS.md` — progres și handoff între agenți.
- `AGENTS.md` — reguli obligatorii pentru agenți.

## Date și securitate

- `documente_noi/`, `.env`, PDF-urile și textele extrase nu intră în Git.
- Nu se tipăresc sau expun secrete și conținut normativ brut.
- Browserul nu se conectează direct la Supabase.
- Query-urile retrieval folosesc parametri DB-API.
- Numai documentele `approved` sunt eligibile pentru retrieval.

## Costuri

- Testele standard nu apelează servicii plătite.
- Voyage va fi apelat numai pentru întrebări semantice acceptate; adaptorul este lazy și injectabil.
- Claude va fi apelat numai dacă există dovezi suficiente; adaptorul este lazy și injectabil.
- Limitele implicite implementate în cod sunt: top-K 5, prag 0.50, context 12.000 caractere și răspuns maximum 1200 tokenuri.

## Următorul obiectiv

Lotul aprobat **0 — documentație**, apoi **1 — aliasuri slash**, cu gates încă deschise în `GATES.md`. Pasul 1 adaugă `/` în `_ALIAS_SEPARATOR`, alături de whitespace/cratimă, și regresii în `tests/test_retrieval_core.py`; fără schimbări de coduri necunoscute/context/status/DB/provideri. Pașii 2 context, 3 import manual, 4 integritate articole, 5 evaluare reală, 6 operare rămân TODO și neautorizați în acest lot (`TASKS.md`). `/documents` rămâne eliminat definitiv; nici workerul, nici cleanup-ul programat nu se activează implicit.
