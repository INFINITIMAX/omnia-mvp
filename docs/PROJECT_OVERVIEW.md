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
- Suita curentă are 165 teste complet locale/mockuite (cu un warning extern de deprecere TestClient).

## Ce nu este încă funcțional în aplicația publică

- Gate-ul de deployment care obligă `ANONYMOUS_COOKIE_SECURE=true` în producție este încă out of scope. Nu există logică nouă de proxy, cleanup runtime, UI sau CORS în această fază. Ferestrele rate-limit expiră logic prin `expires_at` după 24 ore și nu mai sunt reutilizate, dar ștergerea fizică în maximum 24 ore nu este garantată fără un scheduler/job separat, rămas deferred până la aprobare înainte de deployment.
- UI-ul este încă prototip.
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

- `main.py` — API-ul existent; urmează să fie refactorizat.
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
- Limitele actuale propuse sunt: top-K 5, prag 0.50, context 12.000 caractere și răspuns maximum 800 tokenuri.

## Următorul obiectiv

Faza 4: controale de cost aprobate separat: fiecare browser are quota anonimă de 10 întrebări și rate limiting; cei 4 testeri inițiali folosesc același URL public, fără privilegii.
