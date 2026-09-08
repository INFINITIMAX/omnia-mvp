# NormativAI — vedere completă a proiectului

## Ce este acum funcțional

- Supabase/PostgreSQL conține 3345 chunk-uri cu embeddings Voyage, în 6 documente aprobate (verificare read-only 03-09-2026): `np010_2022` = 408, `np057_02` = 286, `i9_2022` = 650, `p118_1_2025` = 1401, `spitale_2022` = 578, `p118_2_2013_modificari` = 22.
- Tabelul `documente` păstrează codul și titlul oficial, anul și statusul.
- Toate cele 6 documente au status `approved`; aprobarea este înregistrată în migrări SQL reproductibile (`20260831220000` pentru lotul 1, `20260903120000` pentru lotul 2).
- `p118_2_2013_modificari` conține **numai** Ordinul 966/2018 cu modificări și completări, nu textul de bază al normativului P 118/2-2013. Normativul complet este planificat pentru un lot ulterior; până atunci, o întrebare despre P 118/2 poate primi răspuns doar din lista de modificări.
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
- Suita curentă are 209 teste complet locale/mockuite, inclusiv 31 teste statice pentru UI și setul formal de evaluare din §10 al `docs/HYBRID_SEARCH_SPEC.md`. Setul de evaluare e un **regression eval sintetic, determinist, local/mockuit pentru un set controlat** (nu o evaluare de calitate reală Voyage/Claude): un repository sintetic unic caută exact strict document+articol într-un corpus comun cu decoy-uri, iar la semantic rankuiește tot corpusul prin similaritate cosinus reală calculată determinist din text (fără `hash()` randomizat, fără hardcodare caz→dovadă); `SEMANTIC_CASES` are 12 parafraze sintetice controlate — 12 cazuri fac pragul ≥90% neechivalent cu o cerință de 100% (11/12 = 91,7%) —, fiecare cu alt vocabular/altă structură de frază decât propoziția-țintă din `CORPUS` — un test dedicat verifică literal, prin cel mai lung șir de cuvinte consecutive identice, că nicio întrebare nu o copiază; embedderul recunoaște parafrazele printr-un vocabular conceptual sintetic de sinonime/variante morfologice — un vocabular conceptual sintetic, definit manual, comun corpusului și întrebărilor —, nu o mapare caz→dovadă. Metricile verifică identitatea document+articol așteptată, iar un control negativ confirmă că o întrebare fără semnal relevant nu primește automat dovada (exact lookup 100%, refuz articole inventate 100%, semantic 100% din 12 cazuri, prag ≥90%, fără apeluri reale/plătite și fără validare pe trafic public). Testul HTTP anti-leak folosește un helper comun (`_assert_no_technical_identifiers`) aplicat pe statusurile retrieval sub 200 și, separat, în testele reprezentative pentru 422/403/429/503 — acoperire reală pe toate codurile publice, plus un warning extern de deprecere TestClient.

## Ce nu este încă funcțional în aplicația publică

- Gate-ul de deployment care obligă `ANONYMOUS_COOKIE_SECURE=true` în producție este încă out of scope. Ferestrele rate-limit expiră logic prin `expires_at` după 24 ore și nu mai sunt reutilizate, dar ștergerea fizică în maximum 24 ore nu este garantată fără un scheduler/job separat, rămas deferred până la aprobare înainte de deployment.
- Rate limiting-ul folosește exclusiv `request.client.host`; nu există suport trusted proxy (`X-Forwarded-For` nu este citit/folosit), CORS sau cleanup runtime.
- UI-ul nu are cont. `/health` este implementat. **`/documents` nu există și nu se va implementa** — a fost livrat la 05-09-2026 (commit `9bd65d5`) urmând backlogul din `PLAN.md`, apoi eliminat la 07-09-2026: catalogul complet al normativelor indexate arată exact ce acoperă și ce nu acoperă produsul, informație sensibilă competitiv. Din același motiv lista documentelor fusese scoasă din nav la 03-09-2026, înlocuită cu istoricul conversațiilor.
- UI MVP-ul curent este funcțional finalizat (conectat la `POST /intreaba` și la controalele anonime), dar redesign-ul vizual și testarea manuală în browser real rămân deferate.
- Nu există deployment public final.
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
- `populare_db.py` — ingestion controlat și validat.
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

Faza 4A/4B (controalele anonime) și `POST /intreaba` sunt finalizate și integrate; UI MVP este o sublivrare funcțională finalizată, dar Faza 6 în ansamblu rămâne parțială. `/health` este implementat. **`/documents` a fost eliminat definitiv la 07-09-2026** (decizie de produs: catalogul documentelor nu se expune public) — nu mai e o restanță și nu se reimplementează. Restanțele curente pentru Faza 4-7: cleanup fizic al ferestrelor IP în maximum 24 ore, suport trusted proxy, gate-ul `ANONYMOUS_COOKIE_SECURE=true` pentru producție, testare vizuală/redesign UI, review-ul independent final pre-deployment și deployment cu smoke tests.
