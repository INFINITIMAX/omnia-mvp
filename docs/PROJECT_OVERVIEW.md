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
- Suita curentă are 106 teste complet locale/mockuite (cu un warning extern de deprecere TestClient).

## Ce nu este încă funcțional în aplicația publică

- Quota anonimă de 10 întrebări per browser și rate limiting-ul nu sunt implementate; maximum 4 testeri vor folosi fluxul anonim.
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

Faza 4: controale de cost aprobate separat: maximum 4 testeri folosesc fluxul anonim, cu quota de 10 întrebări per browser și rate limiting.
