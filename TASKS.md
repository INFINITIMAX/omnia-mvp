# TASKS — Omnia

## Acum

### Faza 0 — Stabilizare

- [x] Eliminare normative-demo din Supabase.
- [x] Structurare locală `documente_noi/` pentru NP 010-2022 și NP 057-02.
- [x] Adaptare `procesare_documente.py`, `populare_db.py`, `chunkingv2.py` (istoric — `chunkingv2.py` a fost eliminat ulterior ca script legacy în `319cf5f`; logica activă de chunking este în `populare_db.py`).
- [x] Dry-run: 694 chunk-uri validate fără cost API.
- [x] Import real: 694 chunk-uri în Supabase.
- [x] Review și commit pentru schimbările de ingestion (`e9b4932`).
- [x] Adăugare `requirements.txt`, structură `tests/` mockuită și documentație locală minimă.
- [x] Verificare Git: fără secrete; documentul-demo eliminat; fișierele locale sunt ignorate.

## Predare — draft migrare Supabase metadata documente

- [x] Draft creat în `supabase/migrations/20260831165749_document_metadata.sql`.
- [x] Rollback și validare locală documentate în `supabase/DOCUMENT_METADATA_MIGRATION.md`.
- [x] Test contractual local și teste pentru metadata viitoare adăugate în `tests/`.
- [x] `populare_db.py` actualizat strict pentru a popula metadata noilor coloane la importurile viitoare.
- [x] Remedieri Reviewer: FK compus document–sursă, importer fail-fast, contract ASCII, preflight RLS și rollback separat pentru granturi.
- [x] Validări locale după remediere: `python -m pytest -q` → 18 passed; `git diff --check` fără erori.
- [x] Gate SQL tranzacțional executat pe Supabase cu `ROLLBACK`; 694 rânduri și schema originală reconfirmate după rollback.
- [x] Review final `APPROVE` pentru corecția `U+00A0` și dovada gate-ului.
- [x] Migrare aplicată persistent și verificată: 2 documente, 694 chunk-uri, RLS activ, zero granturi publice.

**Titlu:** Draft migrare Supabase pentru metadata documentelor.

**Scope:** creează doar migrarea SQL versionată și testele/documentația ei. Schema aprobată:
- tabel `documente`: identificator tehnic, `source_key`, cod/titlu oficial, an, status și timestamp;
- coloană `document_id` în `documente_chunks`, cu foreign key către `documente`;
- backfill pentru `NP010_extras.txt` și `NP0572002_extras.txt`;
- indexuri B-tree pentru exact lookup pe document/articol;
- RLS activ fără politici publice.

**Constrângeri:** nu aplica SQL în Supabase, nu modifica `.env`, documente locale, API-ul sau UI-ul; nu apela API-uri plătite; nu face commit/push/deploy; oprește-te cu SQL-ul, planul de rollback, comenzile de validare și riscurile.

**Criterii de acceptare:**
- migrarea este sigură pentru datele existente;
- nu expune acces public la documente/chunk-uri;
- poate fi revizuită și aplicată ulterior fără ambiguități;
- testele locale existente rămân verzi.

## Următorul task după aprobarea schemei

**Titlu:** Retrieval core pentru hybrid search, fără API public.

**Scope:**
- parser pur pentru document/articol și normalizare conform `docs/HYBRID_SEARCH_SPEC.md`;
- exact lookup pe `document_id + articol_normalizat`;
- semantic top-K limitat și compatibil cu indexul pgvector;
- deduplicare după `content_hash` și detectare `ambiguous_article`;
- zero Anthropic și zero schimbări UI/quota în acest task;
- teste complet mockuite pentru ramurile exact, semantic, not-found și ambiguitate.

**Gate:** începe numai după verdictul final al Reviewer-ului și validarea/aplicarea controlată a schemei Supabase.

## Predare — Faza 3A Retrieval Core

- [x] Parser pur pentru document/articol, normalizare compatibilă cu DB și aliasuri injectate din metadata.
- [x] Repository PostgreSQL cu lookup exact parametrizat și semantic pgvector parametrizat.
- [x] Service cu ramuri exact/semantic exclusive, deduplicare, ambiguitate și limită de context.
- [x] Teste sintetice mockuite pentru parser, SQL, exact, semantic, deduplicare, ambiguitate și erori.

## Predare — Faza 3B1 Generation Core și citări validate

- [x] `generation_core.py` pur, cu generator injectabil și fără integrare FastAPI.
- [x] ID-uri temporare deterministe `C1`, `C2` pentru Evidence deja recuperate.
- [x] Prompt JSON sigur: metadata oficială și text tratate ca date neîncrezătoare, fără identificatori tehnici.
- [x] Validare fail-safe tipată pentru răspuns gol, lipsă citare sau ID de citare necunoscut.
- [x] Citări publice construite exclusiv din Evidence folosită, deduplicate în ordinea primei apariții și limitate la 600 caractere.
- [x] Teste sintetice/mockuite pentru toate ramurile de generare, citări și prompt injection.
- [x] Gate local, audit de scurgeri și commit local executate.

## Predare — Faza 3B2 integrare FastAPI mock-first

- [x] `POST /intreaba` orchestrează catalogul aprobat, Retrieval Core și Generation Core, cu statusuri publice controlate și citări oficiale.
- [x] Adaptoarele lazy/injectabile Voyage (`voyage-3.5`) și Anthropic (`claude-sonnet-4-6`, maximum 800 tokenuri) nu creează clienți externi la import.
- [x] Catalogul read-only interoghează explicit `public.documente` și `public.documente_chunks`, numai pentru statusul aprobat, fără `source_key` sau text brut.
- [x] Testele FastAPI și unit sunt complet mockuite; validarea locală: `python -m pytest -q` → 106 passed (1 warning extern de deprecere TestClient), `git diff --check` fără erori.

## Transparență și aprobare documente

- [x] Lucian a aprobat explicit `np010_2022` și `np057_02` pentru retrieval.
- [x] Statusurile Supabase sunt `approved`; cele 694 chunk-uri au fost reconfirmate.
- [x] Aprobarea este reproductibilă prin migrarea fail-safe `20260831220000_approve_initial_documents.sql`.
- [x] Deciziile active sunt centralizate în `docs/DECISIONS.md`.
- [x] Starea funcțională și limitele proiectului sunt descrise în `docs/PROJECT_OVERVIEW.md`.

## Predare — Faza 4A nucleu anonim quota/rate-limit (neintegrat)

- [x] `access_control.py` pur: cookie anonim semnat HMAC, verificare fail-closed, `visitor_hash` derivat și hash IP HMAC cu cheie separată.
- [x] Configurație strictă: 10 întrebări/browser, 5/minut/IP, 30/oră/IP, cookie 365 zile și ferestre IP cu `expires_at` la 24 ore, nereutilizate după expirare.
- [x] Repository PostgreSQL DB-API parametrizat, fără commit implicit: rezervare atomică quota, rate limit atomic minute+oră care contabilizează și tentativele blocate, plus cleanup expirări.
- [x] Migrarea `20260831230000_anonymous_access_controls.sql` (SHA-256 `a2840a5364f0`) a fost aplicată persistent la 01-09-2026 (România) prin tranzacție PostgreSQL directă; fresh connection PASS: 2 tabele, 10 constraints, RLS fără politici, zero granturi publice, index cleanup, zero rânduri inițiale și snapshot intact (2 documente, 694 chunk-uri, 2 approved).
- [x] Gate concurență real cu hash-uri sintetice: quota 9, două conexiuni `[false, true]`, final 10; rate 4, două conexiuni `[false, true]`, contoare 6, apoi a treia blocked le-a crescut la 7. Cleanup sintetic verificat; ambele tabele au final zero rânduri. `supabase_migrations.schema_migrations` nu a fost vizibilă conexiunii, deci nu se afirmă istoric de migrare înregistrat și nu s-a modificat manual.
- [x] Teste locale/mockuite pentru cookie, hash, quota, rate limit, cleanup, SQL, schema și audit; gate local trecut.
- [x] Integrarea FastAPI, emiterea atributelor cookie HTTP și tranzacțiile runtime nu au făcut parte din scope-ul Faza 4A; au fost livrate ulterior în Faza 4B de mai jos.
- [x] SQL-ul pentru controalele anonime este aplicat persistent și verificat. La momentul acestei predări (doar Faza 4A), integrarea în aplicație nu era încă făcută — vezi Faza 4B pentru integrarea FastAPI finalizată.

## Predare — Faza 4B integrare FastAPI controale anonime

- [x] `GET /` emite `normativai_anon` semnat, iar `POST /intreaba` îl emite ca fallback pentru cookie absent sau invalid; atributele sunt 365 zile, `HttpOnly`, `SameSite=Lax`, `Path=/` și `Secure` configurabil strict.
- [x] Configurația este lazy și injectabilă: `ANONYMOUS_COOKIE_SIGNING_KEY`, `ANONYMOUS_IP_HASH_KEY` și `ANONYMOUS_COOKIE_SECURE`; booleanul acceptă numai `true`/`false` case-insensitive după trim, iar orice valoare lipsă/invalidă produce HTTP 503 generic.
- [x] Folosește numai `request.client.host` pentru hash IP și o singură conexiune: rate-limit commit separat, apoi quota commit pentru răspuns normal sau rollback pentru refuz/eroare tehnică.
- [x] Contracte publice: 429 `rate_limited`, `Retry-After` și mesajul generic aprobat; 403 `quota_exhausted`, mesajul clar aprobat și `intrebari_ramase: 0`; răspunsurile normale includ `intrebari_ramase`; excepțiile neașteptate fac rollback și sunt repropagate.
- [x] Teste locale/mockuite acoperă cookie absent/falsificat/expirat, `Secure=true`, config, ordine tranzacții, rate/quota, rollback, IP direct și erori; invarianta fail-closed post-increment cere contoare `int` strict pozitive și `allowed` echivalent limitelor, fără quota/retrieval/provider la invalidare; cheia publică este numai `intrebari_ramase` (0..9, respectiv 0 la epuizare).
- [ ] Gate producție pentru `ANONYMOUS_COOKIE_SECURE=true`, proxy/UI/CORS rămân explicit out of scope.
- [ ] Cerința țintă de ștergere fizică a bucket-urilor IP în maximum 24 de ore este deferred: ferestrele expiră logic și nu mai sunt reutilizate, însă nu există scheduler/job; acesta necesită aprobare separată înainte de deployment.

## Predare — UI MVP conectat la controalele anonime

- [x] `static/index.html` cheamă exclusiv `POST /intreaba`; textul inițial este exact „Limită: 10 întrebări/browser”, apoi este înlocuit cu `intrebari_ramase` din fiecare răspuns normal (fără `localStorage` sau ghicit local).
- [x] HTTP 403 afișează `detail` din server, fixează afișajul la 0 întrebări și blochează permanent formularul; HTTP 429 afișează `detail` plus timpul aproximativ, validează strict `Retry-After` ca întreg pozitiv (fără interpretare de dată calendaristică) și blochează temporar exact pe durata respectivă.
- [x] HTTP 422 are mesaj dedicat, fără a expune corpul brut al erorii de validare; 503, erorile de rețea și JSON invalid au un singur mesaj generic comun, fără cod de status sau text de excepție.
- [x] Trimiterea prin click, Enter și chips-urile de sugestie trec toate prin același guard (`sendQuestion`); input, buton și chips se dezactivează în timpul cererii și pe durata blocărilor.
- [x] Răspunsul și citările (`cod_document`, `titlu_document`, `articol`, `citat`) sunt randate exclusiv prin `textContent`/DOM, fără `innerHTML` pentru date server/utilizator; JS nu citește `document.cookie`.
- [x] Eliminate: badge-ul cu „247 documente indexate” și popover-ul cu `demoIndexed`, lista de conversații demonstrative din sidebar, „Contul meu” (înlocuit cu „Vizitator anonim”) și butonul inert „+ Conversație nouă”; badge-ul rămas este neutru („Documente aprobate”, fără interacțiune).
- [x] CSS moarte pentru elementele eliminate a fost curățată; fără redesign, restul aspectului este păstrat.
- [x] Teste statice noi în `tests/test_ui_static.py` (31 teste) validează contractul de mai sus și rulează `node --check` pe JS-ul extras din pagină; suita completă `python -m pytest -q` → 204 passed.

## Backlog ordonat

1. Faza 1: migrarea Supabase pentru metadata și chunk identity. **Finalizată.**
2. Faza 3A: retrieval core descris mai sus. **Finalizată în branch-ul `feat/retrieval-core`; fără API public.**
3. Faza 3B1: Generation Core și citări oficiale validate. **Finalizată; fără FastAPI.**
4. Faza 3B2: contract și integrare API pentru retrieval/generare. **Finalizată mock-first.**
5. Faza 4: cost control: quota anonimă (10 întrebări/browser) și rate limiting (5/minut, 30/oră per IP). **Faza 4A + 4B (controalele anonime) și `POST /intreaba` sunt finalizate și integrate** în FastAPI și în UI MVP. **Faza 4 în ansamblu rămâne parțială**: PLAN.md cere și endpoint-urile `/health` și `/documents`, ambele încă absente și restante — nu sunt „decizii deschise" cu privire la dacă vor exista. `/health` este restant obligatoriu, necesar înainte de deployment (Faza 7). `/documents` este restant pentru completarea Faza 6; contractul lui public exact (rută, formă răspuns) și metadata expusă necesită explicație și aprobare explicită înainte de implementare. Rămân deschise și: gate producție `ANONYMOUS_COOKIE_SECURE=true`, suport trusted proxy (în prezent se folosește exclusiv `request.client.host`, fără `X-Forwarded-For`) și ștergerea fizică a ferestrelor IP expirate în maximum 24 ore (fără scheduler/job dedicat).
6. Faza 5: testare agresivă. **Suita locală mockuită este finalizată (207 teste, inclusiv 31 teste statice UI și setul formal de evaluare din §10 al `docs/HYBRID_SEARCH_SPEC.md`, implementat local/mockuit în `tests/eval_set_data.py` și `tests/test_eval_set.py`).** Setul de evaluare este un **regression eval sintetic, determinist, local/mockuit pentru un set controlat** — nu o evaluare de calitate reală Voyage/Claude. Rulează prin `RetrievalService` real cu un repository sintetic unic care **nu primește `EvalCase`/tip/expected**: caută exact strict după `document_id`+`articol_normalizat` într-un corpus comun (`CORPUS`, cu identitate document/articol și decoy-uri pe teme fără legătură), iar la semantic clasifică tot corpusul prin similaritate cosinus reală, calculată determinist (bag-of-words, fără `hash()` randomizat) între vectorul întrebării și vectorii conținutului, cu scor și `top_k` — fără hardcodare caz→dovadă. Metricile verifică identitatea document+articol așteptată (nu doar statusul `found`), iar un caz de control negativ (`NEGATIVE_SEMANTIC_CASES`, fără nicio suprapunere de vocabular cu corpusul) confirmă că o întrebare semantică fără semnal relevant primește scor 0.0 și e refuzată, nu potrivită automat. Rezultatul măsurat din date: exact lookup 100%, refuz articole inventate 100%, semantic ≥90% — tot local, fără apeluri reale/plătite și fără validare pe trafic public. Tot acest commit a mai închis două goluri: testul explicit pentru un candidat semantic care depășește limita de context (nu doar cazul care nimerește exact pragul) și verificarea la nivelul răspunsului HTTP real că `source_key`, `document_id` intern sau nume `_extras.txt` nu se scurg niciodată către client. Rămân restante: testarea vizuală/manuală în browser real, evaluarea reală de calitate Voyage/Claude (pe date reale) și smoke test-urile plătite.
7. Faza 6: UI real. **Sublivrare funcțională finalizată:** UI MVP conectat exclusiv la `POST /intreaba` și la controalele anonime. **Faza 6 în ansamblu rămâne parțială/nefinalizată:** lipsește `GET /documents` (lista documentelor și contorul cerute de PLAN.md pentru această fază — vezi Faza 4 pentru statutul contractului), redesign-ul vizual și testarea manuală în browser real rămân deferate.
8. Faza 7: review și deployment. Există un review punctual, explicit documentat, pentru migrarea metadata (remedierile Reviewer și review-ul final `APPROVE`, vezi predarea de mai sus, liniile 22 și 25) — nu se afirmă că alte componente/faze au fost revizuite similar. **Rămân pendinte:** review-ul independent final pre-deployment, deployment-ul public și smoke tests pe URL public.
9. Faza 8: business/CV material. **Neînceput.**

## Observații

- `np057_02` nu are PDF original local; are doar `extracted.txt` și metadata notează acest lucru.
- Supabase are 694 chunk-uri aprobate pentru retrieval: NP010 = 408, NP057 = 286.
- `PLAN.md` și acest fișier sunt sursele active de coordonare.
- Commit `319cf5f`: 17 scripturi legacy neutilizate (ex. `chunkingv2.py`, `omnia_qa.py`, `verificare_db.py`) au fost eliminate din proiectul activ. `_archive/` este în `.gitignore` și nu face parte din repo sau din starea versionată; versiunile eliminate rămân recuperabile din istoricul Git (`git show 319cf5f^:<cale>`).
