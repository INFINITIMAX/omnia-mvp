# NormativAI — vedere completă a proiectului

## Ce este acum funcțional

- Supabase/PostgreSQL conține 694 chunk-uri cu embeddings Voyage: 408 pentru `np010_2022` și 286 pentru `np057_02`.
- Tabelul `documente` păstrează codul și titlul oficial, anul și statusul.
- Ambele documente existente au status `approved`; aprobarea este înregistrată și într-o migrare SQL reproductibilă.
- Relația document–sursă este protejată prin FK compus.
- Chunk-urile au articol normalizat, hash de conținut și ordine stabilă.
- RLS este activ; `anon` și `authenticated` nu au granturi sau politici.
- Retrieval Core este implementat și testat: parser, exact lookup, semantic pgvector, deduplicare, ambiguitate și limite.
- Generation Core este implementat și testat: ID-uri temporare deterministe, prompt cu întrebarea și dovezi tratate ca date neîncrezătoare, citări validate fail-safe și obiecte publice derivate exclusiv din Evidence.
- `POST /intreaba` orchestrează catalogul aprobat, Retrieval Core și Generation Core; returnează statusuri controlate și citări oficiale, fără identificatori tehnici.
- Controalele anonime sunt integrate mock-first în FastAPI: `GET /` emite cookie-ul semnat `normativai_anon`, iar `POST /intreaba` îl emite ca fallback; cookie-ul este `HttpOnly`, `SameSite=Lax`, `Path=/` și expiră în 365 zile. Atributul `Secure` este citit strict din configurația server-side, pentru local/test HTTP.
- `POST /intreaba` aplică rate limiting înainte de providerii externi și quota înainte de retrieval/generare, pe o singură conexiune: tranzacția rate este confirmată separat, iar quota este confirmată doar pentru răspunsurile normale sau restituită prin rollback la erori tehnice. Răspunsurile normale includ `intrebari_ramase`; 429 expune `rate_limited`, mesaj generic și `Retry-After`, iar 403 expune `quota_exhausted`, mesajul de epuizare și `intrebari_ramase: 0`.
- Schema Supabase pentru contoarele anonime este aplicată persistent din 01-09-2026 (România): 2 tabele, 10 constraints, RLS fără politici, zero granturi pentru rolurile publice și index de cleanup. Validarea fresh connection și gate-ul de concurență cu hash-uri sintetice au trecut; cleanup-ul a lăsat ambele tabele fără rânduri.
- `static/index.html` este UI-ul MVP conectat exclusiv la `POST /intreaba`: text inițial „Limită: 10 întrebări/browser”, apoi `intrebari_ramase` din răspunsul normal, blocare permanentă la 403 și temporară la 429 (`Retry-After` numeric strict validat), mesaje dedicate pentru 422 și generice fără status/excepții pentru 503/rețea/JSON invalid; randare exclusiv prin `textContent`/DOM, fără `innerHTML` pentru date server/utilizator și fără citire de cookie din JS.
- Suita curentă are 204 teste complet locale/mockuite, inclusiv 31 teste statice pentru UI și setul formal de evaluare din §10 al `docs/HYBRID_SEARCH_SPEC.md` (exact lookup 100%, refuz articole inventate 100%, semantic ≥90%, măsurate din date printr-un repository controlat, fără apeluri reale/plătite și fără validare pe trafic public), plus un warning extern de deprecere TestClient.

## Ce nu este încă funcțional în aplicația publică

- Gate-ul de deployment care obligă `ANONYMOUS_COOKIE_SECURE=true` în producție este încă out of scope. Ferestrele rate-limit expiră logic prin `expires_at` după 24 ore și nu mai sunt reutilizate, dar ștergerea fizică în maximum 24 ore nu este garantată fără un scheduler/job separat, rămas deferred până la aprobare înainte de deployment.
- Rate limiting-ul folosește exclusiv `request.client.host`; nu există suport trusted proxy (`X-Forwarded-For` nu este citit/folosit), CORS sau cleanup runtime.
- UI-ul nu are cont, istoric sau endpointuri `/documents`/`/health`; ambele sunt cerute de `PLAN.md` și rămân restante, nu „decizii deschise" cu privire la dacă vor exista. `/health` este restant obligatoriu, necesar înainte de deployment. `/documents` este restant pentru completarea Faza 6; contractul lui public exact (rută, formă răspuns) și metadata expusă necesită explicație și aprobare explicită înainte de implementare.
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
- Limitele implicite implementate în cod sunt: top-K 5, prag 0.50, context 12.000 caractere și răspuns maximum 800 tokenuri.

## Următorul obiectiv

Faza 4A/4B (controalele anonime) și `POST /intreaba` sunt finalizate și integrate; UI MVP este o sublivrare funcțională finalizată, dar Faza 6 în ansamblu rămâne parțială. Faza 4 în ansamblu rămâne parțială: PLAN.md cere și `/health` și `/documents`, ambele încă absente și restante — nu sunt decizii deschise cu privire la dacă vor exista. `/health` este restant obligatoriu înainte de deployment. `/documents` este restant pentru completarea Faza 6; contractul lui public exact și metadata expusă necesită explicație și aprobare explicită înainte de implementare. Restanțele curente pentru Faza 4-7: implementarea `/health`/`/documents` (cu aprobarea prealabilă a contractului `/documents`), cleanup fizic al ferestrelor IP în maximum 24 ore, suport trusted proxy, gate-ul `ANONYMOUS_COOKIE_SECURE=true` pentru producție, testare vizuală/redesign UI, review-ul independent final pre-deployment și deployment cu smoke tests.
