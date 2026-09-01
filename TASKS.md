# TASKS — Omnia

## Acum

### Faza 0 — Stabilizare

- [x] Eliminare normative-demo din Supabase.
- [x] Structurare locală `documente_noi/` pentru NP 010-2022 și NP 057-02.
- [x] Adaptare `procesare_documente.py`, `populare_db.py`, `chunkingv2.py`.
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
- [x] Configurație strictă: 10 întrebări/browser, 5/minut/IP, 30/oră/IP, cookie 365 zile și bucket-uri IP 24 ore.
- [x] Repository PostgreSQL DB-API parametrizat, fără commit implicit: rezervare atomică quota, rate limit atomic minute+oră care contabilizează și tentativele blocate, plus cleanup expirări.
- [x] Migrarea `20260831230000_anonymous_access_controls.sql` (SHA-256 `a2840a5364f0`) a fost aplicată persistent la 01-09-2026 (România) prin tranzacție PostgreSQL directă; fresh connection PASS: 2 tabele, 10 constraints, RLS fără politici, zero granturi publice, index cleanup, zero rânduri inițiale și snapshot intact (2 documente, 694 chunk-uri, 2 approved).
- [x] Gate concurență real cu hash-uri sintetice: quota 9, două conexiuni `[false, true]`, final 10; rate 4, două conexiuni `[false, true]`, contoare 6, apoi a treia blocked le-a crescut la 7. Cleanup sintetic verificat; ambele tabele au final zero rânduri. `supabase_migrations.schema_migrations` nu a fost vizibilă conexiunii, deci nu se afirmă istoric de migrare înregistrat și nu s-a modificat manual.
- [x] Teste locale/mockuite pentru cookie, hash, quota, rate limit, cleanup, SQL, schema și audit; gate local trecut.
- [ ] Integrarea FastAPI, emiterea atributelor cookie HTTP și tranzacțiile runtime nu fac parte din Faza 4A.
- [x] SQL-ul pentru controalele anonime este aplicat persistent și verificat; integrarea aplicației rămâne neimplementată.

## Backlog ordonat

1. Faza 1: migrarea Supabase pentru metadata și chunk identity. **Finalizată.**
2. Faza 3A: retrieval core descris mai sus. **Finalizată în branch-ul `feat/retrieval-core`; fără API public.**
3. Faza 3B1: Generation Core și citări oficiale validate. **Finalizată; fără FastAPI.**
4. Faza 3B2: contract și integrare API pentru retrieval/generare. **Finalizată mock-first.**
5. Faza 4: cost control: fiecare browser are quota anonimă de 10 întrebări și rate limiting; cei 4 testeri inițiali folosesc același URL public, fără privilegii.
6. Faza 5: testare agresivă.
7. Faza 6: UI real.
8. Faza 7: review și deployment.
9. Faza 8: business/CV material.

## Observații

- `np057_02` nu are PDF original local; are doar `extracted.txt` și metadata notează acest lucru.
- Supabase are 694 chunk-uri aprobate pentru retrieval: NP010 = 408, NP057 = 286.
- `claude_herdr.md` este handoff istoric neversionat; `PLAN.md` și acest fișier sunt sursele active de coordonare.
