# Omnia — Plan MVP

## Obiectiv

Omnia devine o aplicație publică pentru normative tehnice românești: răspunsuri bazate exclusiv pe dovezi, cu citare oficială, căutare exactă de articol, costuri API controlate și teste automate.

## Stare executivă — 03-09-2026 (actualizat 03-09-2026, seara — deploy live)

### Avem, în starea versionată sigură (`main` la `5dffaf9`, sincron cu `origin/main`)

- ingestion reproductibil și 6 documente aprobate, cu 3345 chunk-uri în Supabase (lotul 1 = 694, lotul 2 = 2651; verificat read-only la 03-09-2026);
- schemă Supabase versionată, RLS activ și fără acces public direct;
- retrieval hibrid, generare cu citări validate și integrare `POST /intreaba`, verificat end-to-end pe producție (răspuns `answered` cu citări reale din I9-2022);
- quota anonimă de 10 întrebări/browser și rate limiting 5/minut, 30/oră/IP, cu suport `TRUSTED_PROXY_HOPS` fail-closed (citește toate antetele `X-Forwarded-For`, nu doar primul — remediat o breșă de spoofing găsită de Reviewer înainte de deploy);
- UI redesign „negru-auriu” aprobat, live în producție (paleta `#E8B931`/`#FFD75E` pe negru, fonturi self-hostate);
- `/health` (fără interogare DB, sigur pentru healthcheck Railway), rute juridice `/termeni` și `/confidentialitate` publice și corecte (contact GDPR real, regiune Supabase corectă: West EU/Ireland);
- `/docs`, `/redoc`, `/openapi.json` dezactivate în producție (evită expunerea publică a `POST /intreaba` și a costului asociat);
- 262 de teste locale trec pe `main`;
- **aplicația e live**: `https://normativai.ro` (domeniu propriu, cumpărat de Lucian de la Hosterion, DNS administrat prin Cloudflare; certificat Railway valid, verificat 05-09-2026), și în continuare la `https://normativai-production.up.railway.app`; deploy manual (Railway nu are auto-deploy din Git — serviciul nu are niciun repo legat la Source; publicarea se face exclusiv cu `railway up` din `D:\Omnia-MVP`);
- limite de cost setate: Anthropic $20, Voyage $10 (praguri furnizor, neverificate programatic de acest asistent).

### Există, dar nu este încă livrat

- prototipul UI „Technical Paper” (`feat/technical-paper-ui`) a fost șters definitiv (worktree + prototip) la 03-09-2026 după respingerea vizuală — nu mai există în lucru, doar în istoricul git dacă e nevoie de recuperare;
- `/documents` cu contract aprobat — nu a fost implementat încă;
- lotul 4 de documente (P118/2) — neatins intenționat, ca să nu coincidă cu testarea externă.

### Ordinea recomandată la reluare

1. Testare externă controlată (4 testeri) pe linkul live, cu monitorizare manuală a costurilor Anthropic/Voyage în primele ore.
2. `/documents` cu contract aprobat, dacă testarea externă merge bine.
3. Lotul 4 (P118/2) — doar după ce testarea externă s-a stabilizat.
4. README/demo/CV, odată ce produsul e stabil în producție.

## Faza 0 — Stabilizare

- Review și commit pentru ingestion-ul structurat deja implementat.
- Adăugare `requirements.txt`, `AGENTS.md`, `TASKS.md` și `tests/`.
- Verificare că Git nu conține secrete sau documente normative.

**Gata când:** proiectul este reproductibil, Git este curat și testele au o comandă unică de rulare.

## Faza 1 — Schema Supabase

- Tabel `documents` cu identificator tehnic, cod/titlu oficial, an și status.
- Legătură între chunk-uri și documente.
- Identificator unic pentru fiecare chunk; `articol` nu este singur unic.
- Migrare SQL versionată, verificare RLS/privilegii și indexuri.
- Index pgvector după stabilizarea formei de retrieval.

**Gata când:** schema poate fi recreată din Git, iar API-ul nu mai expune nume interne de fișiere.

## Faza 2 — Ingestion sigur

- Validare `metadata.json` pentru fiecare document.
- Import per document, fără golirea întregului tabel.
- Tranzacții, hash de conținut și raport de validare.
- `--dry-run` fără apeluri Voyage sau modificări Supabase.
- Agentic chunking este upgrade ulterior, nu blocaj MVP.

**Gata când:** importul repetat nu creează duplicate și nu afectează alte documente.

## Faza 3 — Hybrid search

- Extracție/normalizare număr articol din întrebare.
- Exact lookup înainte de semantic search.
- Semantic top-K pentru întrebări generale sau fallback.
- Deduplicare, context limitat și citări structurate.

**Gata când:** un articol real este găsit exact, unul inventat este refuzat, iar răspunsul conține citări oficiale.

## Faza 4 — API și cost control

- Separare retrieval de generare Anthropic.
- Fără apel Claude când lipsesc dovezile.
- Limite pentru întrebare, chunk-uri, context și output.
- Endpoint-uri `/health`, `/documents`, `/intreaba`.
- Erori/timeouts clare, logging fără secrete sau text normativ integral.
- Testele plătite sunt opt-in.
- Tier anonim: maximum 10 întrebări în total per browser, urmărite server-side printr-un identificator semnat; resetarea cookie-ului/alt browser rămâne o limitare acceptată a MVP-ului.
- Rate limit separat per IP pentru protecție contra automatizării.
- Nu există tier, coduri sau conturi separate pentru testeri în MVP; aplicația este publică pentru oricâți vizitatori, fiecare cu limita anonimă de 10 întrebări per browser. Cei 4 testeri inițiali folosesc același URL și același flux.

**Gata când:** testele standard nu consumă Anthropic sau Voyage, iar limita anonimă este impusă înainte de apelurile plătite.

## Faza 5 — Testare agresivă

- Unit tests: parser articole, chunking, metadata.
- API tests mockuite: exact match, semantic, document/ articol inexistent, duplicate, conflict, lipsă dovezi, context limitat, erori servicii și prompt injection.
- Set de evaluare cu rezultate așteptate.
- Smoke tests reale puține și deliberate.

**Gata când:** `python -m pytest -q` trece, iar apelurile plătite sunt dezactivate implicit.

## Faza 6 — UI real

- Lista documentelor și contorul vin din `/documents`.
- Coduri/titluri oficiale și citări clare.
- Eliminarea datelor demonstrative false.
- Loading, erori și refuz explicit.
- Brand public aprobat: **NormativAI**. `Omnia` rămâne numele intern al proiectului/repository-ului.
- Redesign-ul pornește cu două capturi/prototipuri comparabile, nu direct cu implementare completă.
- Acceptarea tehnică și acceptarea vizuală sunt gates separate; testele verzi nu pot înlocui aprobarea vizuală a lui Lucian.

**Gata când:** varianta vizuală este aprobată explicit pe desktop și mobil, comportamentele 200/403/429/422/503 sunt reverificate, iar `/documents` are contract public aprobat și implementat.

## Faza 7 — Review și deployment

- Review independent pentru cod, securitate și cost.
- Aplicația publică și viitorul hosting/domeniu folosesc brandul **NormativAI**; verificarea de trademark a fost realizată de Lucian.
- Hosting, secrete, pooling Supabase, health check și budget alerts.
- Configurare explicită trusted proxy înainte de a folosi IP-ul clientului în spatele Railway.
- `ANONYMOUS_COOKIE_SECURE=true` și secrete distincte de producție.
- Job aprobat pentru ștergerea fizică a bucket-urilor IP expirate.
- Smoke tests pe URL public, cu providerii reali numai opt-in și cu limită de cost.

**Gata când:** diff-ul de deployment este revizuit, `/health` funcționează, configurația de securitate este validată, URL-ul public trece smoke tests și Lucian aprobă explicit lansarea.

## Faza 8 — Business și CV

- README, diagramă arhitectură, demo/capturi, metrici de test și limitări.
- Documentație și reexplicare pas cu pas, la nivel de începător, a deciziilor și implementărilor aprobate de Lucian.
- Rezultate tehnice transformate în bullets CV.

## Criterii obligatorii

- Niciun răspuns fără dovadă/citare.
- Fără secrete sau documente normative în Git.
- Fără push, deploy sau migrare Supabase fără aprobarea lui Lucian.
- Orice cod este explicat pentru nivel începător și orice decizie cu valoare de CV este marcată explicit.
