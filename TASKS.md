# TASKS — Omnia

## Predare — Deploy live 03-09-2026

- [x] Merge API (trusted proxy fail-closed, `/health`, rute statice) + UI negru-auriu în `main`, 262 teste treceau pe combinație.
- [x] Reviewer a găsit spoofing pe `X-Forwarded-For` (primul header lua valoarea clientului, nu a proxy-ului) — remediat de Coder API, verificat de Reviewer.
- [x] Remedieri finale înainte de testeri externi: `/docs`+`/redoc`+`/openapi.json` dezactivate, link juridic corectat, contact GDPR real (`ilielucian97@gmail.com`), regiune Supabase corectă (West EU/Ireland) — commit `b062db6`, merge `5dffaf9`.
- [x] Push pe `origin/main`; deploy manual pe Railway cu `railway up` (serviciul nu are Git Source legat, deci `git push` singur nu publică nimic).
- [x] Verificare end-to-end pe producție: `/health` 200, `/docs` 404, `POST /intreaba` răspunde cu citări reale (I9-2022, art. 15.22/15.44).
- [x] Worktree-uri vechi șterse (toate merge-uite în `main`); prototipul „Technical Paper" respins a fost eliminat definitiv.

## Predare — randare Markdown sigură (03-09-2026, seara)

- [x] Bug găsit prin verificarea live: răspunsul venea cu Markdown brut (`##`, `**`, tabele) afișat literal într-un singur `<p>`, fără `white-space: pre-wrap` și cu `text-align: justify` — tot răspunsul se prăbușea într-un paragraf ilizibil.
- [x] Renderer Markdown propriu în `static/index.html`, construit exclusiv cu `createElement`/`createTextNode`/`textContent`: titluri (`##`→h3, `###`→h4), paragrafe, bold inline, liste cu buline și numerotate, tabele cu scroll orizontal propriu pe mobil.
- [x] **Zero `innerHTML`/`insertAdjacentHTML`/`outerHTML`/`document.write`**, păstrate intenționat absente: textul randat vine din LLM și din documente normative, deci randarea prin HTML ar fi fost un vector de XSS prin prompt injection. Un test static anti-regresie interzice explicit reintroducerea lor.
- [x] Markdown malformat (tabel cu coloane inegale, bold neînchis, titlu fără text) cade elegant pe text simplu, fără excepție și fără pierdere de conținut.
- [x] 280 de teste trec (262 + 18 noi). Gate vizual dat de Lucian pe capturi desktop 1280px și mobil 390×844.
- [x] Mergeuit (`c2f2bd5`), push pe `origin/main`, deploy manual pe Railway, verificat live în producție.

**Rămâne deschis, ordonat după impact:**
1. Antete de securitate — lipsesc toate (CSP, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, HSTS, `Permissions-Policy`). Risc: clickjacking prin iframe, MIME sniffing.
2. Kill switch global de cost — limitele Anthropic $20 / Voyage $10 sunt doar alerte, nu opresc nimic automat.
3. `GET /documents` cu contract aprobat — blochează contorul de documente din nav.
4. Scheduler pentru ștergerea fizică a bucket-urilor IP expirate în max 24h (acum expiră doar logic).
5. Chips-urile de sugestie: două întreabă lucruri neacoperite de cele 6 documente aprobate, deci produc refuzuri garantate. Decizie de conținut.
6. Metrul vizual de quotă (bara 7/10 din mockup) — acum e doar text.
7. Lotul 4: P118/2-2013 complet (acum doar 22 chunk-uri din amendamentul 2018).
8. Testare reală de calitate Voyage/Claude pe date reale; smoke tests plătite opt-in.
9. Faza 8: README, diagramă arhitectură, demo/capturi, metrici și limitări, bullets CV.

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
- [x] Gate producție pentru `ANONYMOUS_COOKIE_SECURE=true` — setat în Railway la 03-09-2026 și confirmat live (`Set-Cookie` are `Secure`, `HttpOnly`, `SameSite=lax`). Suportul de trusted proxy a fost implementat ulterior; CORS rămâne out of scope.
- [ ] Cerința țintă de ștergere fizică a bucket-urilor IP în maximum 24 de ore este deferred: ferestrele expiră logic și nu mai sunt reutilizate, însă nu există scheduler/job; acesta necesită aprobare separată înainte de deployment.

## Predare — UI MVP conectat la controalele anonime

- [x] `static/index.html` cheamă exclusiv `POST /intreaba`; textul inițial este exact „Limită: 10 întrebări/browser”, apoi este înlocuit cu `intrebari_ramase` din fiecare răspuns normal (fără `localStorage` sau ghicit local).
- [x] HTTP 403 afișează `detail` din server, fixează afișajul la 0 întrebări și blochează permanent formularul; HTTP 429 afișează `detail` plus timpul aproximativ, validează strict `Retry-After` ca întreg pozitiv (fără interpretare de dată calendaristică) și blochează temporar exact pe durata respectivă.
- [x] HTTP 422 are mesaj dedicat, fără a expune corpul brut al erorii de validare; 503, erorile de rețea și JSON invalid au un singur mesaj generic comun, fără cod de status sau text de excepție.
- [x] Trimiterea prin click, Enter și chips-urile de sugestie trec toate prin același guard (`sendQuestion`); input, buton și chips se dezactivează în timpul cererii și pe durata blocărilor.
- [x] Răspunsul și citările (`cod_document`, `titlu_document`, `articol`, `citat`) sunt randate exclusiv prin `textContent`/DOM, fără `innerHTML` pentru date server/utilizator; JS nu citește `document.cookie`.
- [x] Eliminate: badge-ul cu „247 documente indexate” și popover-ul cu `demoIndexed`, lista de conversații demonstrative din sidebar, „Contul meu” (înlocuit cu „Vizitator anonim”) și butonul inert „+ Conversație nouă”; badge-ul rămas este neutru („Documente aprobate”, fără interacțiune).
- [x] CSS moarte pentru elementele eliminate a fost curățată; fără redesign, restul aspectului este păstrat.
- [x] Teste statice noi în `tests/test_ui_static.py` (31 teste) validează contractul de mai sus și rulează `node --check` pe JS-ul extras din pagină; suita completă `python -m pytest -q` → 209 passed.

## Predare sesiune — Audit și prototip UI (03-09-2026)

- [x] Auditul browser read-only a demonstrat că UI-ul MVP versionat este funcțional pe desktop, dar layout-ul cu sidebar fix este rupt pe mobil.
- [x] A fost construit izolat prototipul „Technical Paper” în `feat/technical-paper-ui`; testele locale și verificările browser mockuite au trecut tehnic.
- [x] Lucian a respins direcția executată deoarece rezultatul pare insuficient stilizat și nu atinge calitatea vizuală dorită.
- [x] Prototipul nu a fost comis, îmbinat, împins sau publicat; nu reprezintă UI-ul aprobat al produsului.
- [x] ~~La reluare: două propuneri vizuale desktop+mobil~~ — **anulat la 03-09-2026**: Lucian a dat direcția explicit, vezi „Interfață" în `docs/DECISIONS.md`.
- [x] Implementare a direcției aprobate (negru-auriu) într-un worktree curat, Reviewer read-only pe branch-ul API, Tester read-only pe pornirea sub uvicorn, gate vizual final dat de Lucian; livrat în producție la 03-09-2026.
- [x] Lucrul extern necomis a fost inventariat, separat pe commit-uri și integrat (branch `chore/reconciliere-railway`, mergeuit în `main`); auditul din 03-09-2026 a confirmat zero secrete și zero documente normative în Git.

## Predare sesiune — Reconciliere Railway și lot 2 (03-09-2026)

- [x] Inventariat diff-ul extern necomis din worktree-ul principal: 4 subiecte independente amestecate (docs roadmap, `Procfile`, pagini juridice, lot 2 de documente).
- [x] Verificat că niciun fișier necomis nu conține secrete; `Procfile` are doar comanda uvicorn.
- [x] Verificare READ-ONLY Supabase aprobată de Lucian și executată (`SET TRANSACTION READ ONLY`, doar `SELECT`): **6 documente, toate `approved`, 3345 chunk-uri** — nu 2 documente / 694 cum afirma documentația.
- [x] Constatare: importul lotului 2 și migrarea `20260903120000` au fost **deja aplicate pe Supabase înainte de această sesiune**; costul Voyage pentru 2651 chunk-uri noi este deja consumat. Commit-urile versionează retroactiv o stare deja live.
- [x] `supabase_migrations.schema_migrations` nu este vizibilă conexiunii; nu se afirmă istoric de migrare înregistrat și nu s-a modificat manual.
- [x] Split în 4 commit-uri pe ramura `chore/reconciliere-railway` (`a55eeed`, `95ccd72`, `0e1f84b`, `a28bf1e`); `main` rămâne intact la `c6e14ba`. Zero push, zero deploy, zero SQL aplicat în această sesiune.
- [x] Suita locală după split: `python -m pytest -q` → **211 passed** (209 + 2 teste noi pentru saritul reimportului neschimbat).
- [x] Documentația la timpul prezent sincronizată cu starea reală (`PLAN.md`, `TASKS.md`, `docs/PROJECT_OVERVIEW.md`, `docs/DECISIONS.md`). Înregistrările istorice din `supabase/*.md` au fost lăsate neatinse — sunt corecte la momentul lor.

### Constatări deschise, pentru decizia lui Lucian

- [x] **Paginile juridice sunt accesibile pe server** prin `GET /termeni` și `GET /confidentialitate` (branch `feat/health-si-static`). Rămâne restant **doar** linkul din footer-ul `static/index.html`, care este în sarcina Coder-ului de UI.
- [x] **Afirmațiile din paginile juridice au fost verificate și corectate la 03-09-2026:** aplicația chiar rulează pe Railway; regiunea Supabase confirmată de Lucian ca West EU (Ireland) și păstrată ca atare; cookie-ul `Secure` confirmat live; adresa de contact placeholder înlocuită cu `ilielucian97@gmail.com`. Fonturile sunt self-hostate, deci nu există scurgere de IP-uri către Google ca procesator nedeclarat.
- [ ] **P 118/2-2013 complet** este planificat de Lucian pentru **lotul 4**, azi. Până la import, o întrebare despre P 118/2 primește răspuns doar din amendamentul 2018 (22 chunk-uri), fără textul de bază modificat.
- [x] `/health` este implementat (branch `feat/health-si-static`): public, fără DB și fără provideri. `/documents` rămâne neimplementat, cu contractul public încă neaprobat.

## Predare — Faza 7 pregătire deployment Railway (API)

- [x] Suport trusted proxy fail-closed: `TRUSTED_PROXY_HOPS` (întreg nenegativ, implicit `0`).
      La `0` se folosește exclusiv `request.client.host`, exact comportamentul anterior; la `N > 0`
      se ia al N-lea element **de la dreapta** din `X-Forwarded-For`, iar antetul absent, prea scurt
      sau cu element invalid cade înapoi pe `request.client.host`. Valoare invalidă = `503` generic,
      consecvent cu `ANONYMOUS_COOKIE_SECURE`.
- [x] `GET /health` public, fără DB, fără Voyage/Anthropic, fără configurație anonimă și fără cookie.
- [x] `GET /termeni` și `GET /confidentialitate` servesc paginile juridice prin `FileResponse`, din
      căi fixe; `static/` nu este montat integral.
- [x] `GET /assets/*` montat read-only strict pe `static/assets/` (creat cu `.gitkeep`), pentru
      fonturi self-hostate și favicon.
- [x] `DEPLOYMENT.md` documentează variabilele de producție, fără nicio valoare reală, plus
      `TRUSTED_PROXY_HOPS=1`, `ANONYMOUS_COOKIE_SECURE=true` și healthcheck pe `/health`.
- [x] Remedieri după `REQUEST_CHANGES` de la Reviewer:
      **F1 blocant** — `X-Forwarded-For` este citit cu `getlist` și unit cu `", "`, nu cu `get`,
      care returna doar prima apariție; antetele duplicate nu mai permit falsificarea IP-ului și
      ocolirea rate limiting-ului. Cele 4 teste noi de neregresie pică demonstrat pe codul dinainte.
      **F2** — `DEPLOYMENT.md` avertizează explicit că supraevaluarea lui `N` este o breșă, nu o
      imprecizie, cu regula „în dubiu scade `N`" și un smoke test post-deploy obligatoriu.
      **F3** — paginile juridice cu fișier lipsă dau `503` generic, ca `/`, fără `RuntimeError` cu
      cale absolută în loguri. **F4** — `StaticFiles(check_dir=False)`. **F5** — artefactul de test
      din `static/assets/` este ignorat de Git și curățat în `finally`.
- [x] Validare locală: `python -m pytest -q` → **258 passed** (de la 211), `git diff --check` fără erori.
- [x] `TRUSTED_PROXY_HOPS=1` și `ANONYMOUS_COOKIE_SECURE=true` au fost setate de Lucian direct în Railway la 03-09-2026 (niciodată de agent);
      Lucian le configurează manual în panoul Railway.
- [ ] Zero push, zero deploy, zero SQL, zero apeluri API plătite în acest task.

## Următorul task UI — brief pentru Coder

**Titlu:** Redesign `static/index.html` pe direcția negru-auriu aprobată la 04-09-2026.

**Referință obligatorie:** `docs/UI_DESIGN_TOKENS.md`. Conține paleta, tipografia, scara de
spațiere, razele și lista de pattern-uri interzise. Nu inventa valori care nu sunt acolo.

**Scope:**
- carcasă întunecată cu nav lateral stânga, composer rotunjit, gradiente difuze de fundal;
- răspunsul cules ca document tipărit: Crimson Pro justificat cu `hyphens: auto`, secțiuni
  numerotate, citări `[1]`/`[2]` în superscript, listă de surse la final;
- articolele citate randate ca într-un standard tipărit: linii de păr sus și jos peste toată
  măsura, referința agățată în marginea stângă, text în roman;
- fonturi **self-hostate** sub `static/assets/fonts/`, cu rută read-only `GET /assets/*`
  (`StaticFiles` limitat strict la `static/assets/`), ca în prototipul anterior; fără CDN
  Google, ca să nu apară un procesator terț neînregistrat în politica de confidențialitate.

**Constrângeri:**
- contractul `POST /intreaba` și controalele anonime rămân neschimbate;
- lista de pattern-uri interzise din `docs/UI_DESIGN_TOKENS.md` se respectă integral;
- fără date demonstrative false; contoarele de documente se afișează **numai** dacă
  `GET /documents` există, altfel se omit (vezi constatarea deschisă mai jos);
- randare exclusiv prin `textContent`/DOM pentru date de la server; fără `innerHTML`;
  JS nu citește `document.cookie`;
- cele 31 de teste statice din `tests/test_ui_static.py` rămân verzi sau se actualizează
  motivat, fără a fi slăbite;
- worktree separat; fără merge, push sau deploy.

**Criterii de acceptare:**
- comportamentele 200/403/429/422/503 reverificate în browser real;
- desktop și mobil verificate; layout-ul cu sidebar fix era rupt pe mobil;
- contrastul fiecărei perechi text/fundal peste 4.5:1;
- `python -m pytest -q` verde;
- gate vizual final explicit al lui Lucian, separat de acceptarea tehnică.

**Foaia răspunsului:** decis la 04-09-2026, varianta **închisă** (`--ink-850`). Fără comutator.

## Predare — redesign UI negru-auriu (branch `feat/ui-negru-auriu`)

- [x] `static/index.html` rescris pe direcția aprobată: carcasă întunecată cu nav lateral,
      composer rotunjit, gradiente difuze, răspunsul cules ca document tipărit (Crimson Pro,
      justificat, `hyphens: auto`), sursele citate cu linii de păr peste toată măsura și
      referința agățată în marginea stângă. Fără bară colorată, fără card, fără italice.
- [x] Logica JS este neschimbată funcțional: același `POST /intreaba`, aceleași ramuri
      403/429/422/503/rețea, același guard `sendQuestion`, aceeași validare `Retry-After`.
      Au fost atinse doar `setMessage` (structura DOM a citărilor) și `addMessage` (clase).
- [x] Fonturi self-hostate în `static/assets/fonts/` (Archivo, Crimson Pro, IBM Plex Mono,
      woff2, subseturi latin + latin-ext, `LICENSE.txt` OFL versionat). Zero CDN terț.
      Depinde de ruta `GET /assets/*`, implementată separat de celălalt Coder.
- [x] Linkuri către `/termeni` și `/confidentialitate` în footer-ul nav-ului, vizibile și pe mobil.
- [x] Mobil reparat: sub 900px nav-ul colapsează într-o bară orizontală, coloana articolelor
      se stivuiește, composer-ul devine `sticky` jos. Verificat în Chrome real la 390, 768 și
      1440px: `scrollWidth == clientWidth`, deci fără scroll orizontal.
- [x] Cele cinci statusuri reverificate în Chrome real cu răspunsuri interceptate, la 1440 și
      390px: 200 (citări randate, contor 7), 403 (contor 0, blocare permanentă), 429
      (`Retry-After: 42`, blocare temporară), 422 (mesaj dedicat, fără corpul brut al erorii),
      503 (mesaj generic). Fără scurgeri de cod de status sau de text de excepție.
- [x] Contrast recalculat cu formula WCAG pe fundalul efectiv (gradient + halou auriu compuse),
      nu pe `--ink-900` pur. Toate perechile text/fundal ≥ 5,4:1. A fost nevoie de o corecție
      măsurată a lui `--paper-quiet`, documentată în `docs/UI_DESIGN_TOKENS.md`.
- [x] Validare locală: `python -m pytest -q` → **215 passed** (211 anterioare + 4 noi),
      `node --check` pe JS-ul extras trece, `git diff --check` fără erori.
- [x] **Gate vizual final al lui Lucian** — dat la 03-09-2026 pentru designul negru-auriu și, separat, pentru randarea Markdown.
- [ ] Contorul de documente din nav rămâne neimplementat: `GET /documents` nu există, deci
      cifrele din mockup ar fi date inventate. În nav apar doar codurile documentelor.
- [ ] Metrul de quotă din mockup (bara 7/10) nu este implementat: ar cere logică nouă de stare,
      iar acest task este strict de prezentare. Contorul textual rămâne singura sursă.
- [ ] Chips-urile de sugestie au rămas cele din MVP. Două dintre ele („stările limită”,
      „debitul minim pentru grupuri sanitare”) nu sunt acoperite de cele 6 documente aprobate
      și vor produce refuzuri. Înlocuirea lor este o decizie de conținut pentru Lucian.

## Backlog ordonat

1. Faza 1: migrarea Supabase pentru metadata și chunk identity. **Finalizată.**
2. Faza 3A: retrieval core descris mai sus. **Finalizată în branch-ul `feat/retrieval-core`; fără API public.**
3. Faza 3B1: Generation Core și citări oficiale validate. **Finalizată; fără FastAPI.**
4. Faza 3B2: contract și integrare API pentru retrieval/generare. **Finalizată mock-first.**
5. Faza 4: cost control: quota anonimă (10 întrebări/browser) și rate limiting (5/minut, 30/oră per IP). **Faza 4A + 4B (controalele anonime) și `POST /intreaba` sunt finalizate și integrate** în FastAPI și în UI MVP. **Faza 4 în ansamblu rămâne parțială**: PLAN.md cere și endpoint-urile `/health` și `/documents`, ambele încă absente și restante — nu sunt „decizii deschise" cu privire la dacă vor exista. `/health` este restant obligatoriu, necesar înainte de deployment (Faza 7). `/documents` este restant pentru completarea Faza 6; contractul lui public exact (rută, formă răspuns) și metadata expusă necesită explicație și aprobare explicită înainte de implementare. Rămân deschise și: gate producție `ANONYMOUS_COOKIE_SECURE=true`, suport trusted proxy (în prezent se folosește exclusiv `request.client.host`, fără `X-Forwarded-For`) și ștergerea fizică a ferestrelor IP expirate în maximum 24 ore (fără scheduler/job dedicat).
6. Faza 5: testare agresivă. **Suita locală mockuită este finalizată (209 teste, inclusiv 31 teste statice UI și setul formal de evaluare din §10 al `docs/HYBRID_SEARCH_SPEC.md`, implementat local/mockuit în `tests/eval_set_data.py` și `tests/test_eval_set.py`).** Setul de evaluare este un **regression eval sintetic, determinist, local/mockuit pentru un set controlat** — nu o evaluare de calitate reală Voyage/Claude. Rulează prin `RetrievalService` real cu un repository sintetic unic care **nu primește `EvalCase`/tip/expected**: caută exact strict după `document_id`+`articol_normalizat` într-un corpus comun (`CORPUS`, cu identitate document/articol și decoy-uri pe teme fără legătură), iar la semantic clasifică tot corpusul prin similaritate cosinus reală, calculată determinist (bag-of-words, fără `hash()` randomizat) între vectorul întrebării și vectorii conținutului, cu scor și `top_k` — fără hardcodare caz→dovadă. `SEMANTIC_CASES` are 12 cazuri — 12 cazuri fac pragul de acceptare ≥90% neechivalent cu o cerință de 100% (11/12 = 91,7%) —, fiecare o parafrază sintetică controlată a articolului-țintă (alt vocabular, altă structură de frază) — nu formularea propoziției din `CORPUS`; un test dedicat (`test_intrebarile_semantice_sunt_parafraze_sintetice_controlate_nu_copii_ale_corpusului`) verifică literal, prin cel mai lung șir de cuvinte consecutive identice, că nicio întrebare nu reproduce fragmentul-țintă. Embedderul sintetic recunoaște parafrazele printr-un vocabular conceptual sintetic de sinonime/variante morfologice (`_SYNONYM_GROUPS` în `test_eval_set.py`) — un vocabular conceptual sintetic, definit manual, comun corpusului și întrebărilor, nu o mapare caz→dovada așteptată. Metricile verifică identitatea document+articol așteptată (nu doar statusul `found`), iar un caz de control negativ (`NEGATIVE_SEMANTIC_CASES`, fără nicio suprapunere de vocabular cu corpusul) confirmă că o întrebare semantică fără semnal relevant primește scor 0.0 și e refuzată, nu potrivită automat. Rezultatul măsurat din date: exact lookup 100%, refuz articole inventate 100%, semantic 100% (12/12, prag de acceptare ≥90%) — tot local, fără apeluri reale/plătite și fără validare pe trafic public. Testul HTTP anti-leak (`test_raspunsul_public_nu_contine_niciodata_identificatori_tehnici`) acoperă statusurile retrieval sub 200; verificarea e factorizată în helper-ul comun `_assert_no_technical_identifiers`, aplicat și direct în testele reprezentative pentru 422, 403, 429 și 503 (fără duplicarea setup-ului, fără slăbirea aserțiunilor de body exact) — acoperire reală pe toate codurile publice, nu doar afirmată. Rămân restante: testarea vizuală/manuală în browser real, evaluarea reală de calitate Voyage/Claude (pe date reale) și smoke test-urile plătite.
7. Faza 6: UI real. **Sublivrare funcțională finalizată:** UI MVP conectat exclusiv la `POST /intreaba` și la controalele anonime. **Faza 6 în ansamblu rămâne parțială/nefinalizată:** lipsește `GET /documents` (lista documentelor și contorul cerute de PLAN.md pentru această fază — vezi Faza 4 pentru statutul contractului), redesign-ul vizual și testarea manuală în browser real rămân deferate.
8. Faza 7: review și deployment. Există un review punctual, explicit documentat, pentru migrarea metadata (remedierile Reviewer și review-ul final `APPROVE`, vezi predarea de mai sus, liniile 22 și 25) — nu se afirmă că alte componente/faze au fost revizuite similar. **Rămân pendinte:** review-ul independent final pre-deployment, deployment-ul public și smoke tests pe URL public.
9. Faza 8: business/CV material. **Neînceput.**

## Observații

- `np057_02` nu are PDF original local; are doar `extracted.txt` și metadata notează acest lucru.
- Supabase are 3345 chunk-uri aprobate pentru retrieval, în 6 documente (verificare read-only 03-09-2026): NP010 = 408, NP057 = 286, I9-2022 = 650, P118/1-2025 = 1401, NP015-2022 = 578, P118/2-2013 modificări = 22.
- `PLAN.md` și acest fișier sunt sursele active de coordonare.
- Commit `319cf5f`: 17 scripturi legacy neutilizate (ex. `chunkingv2.py`, `omnia_qa.py`, `verificare_db.py`) au fost eliminate din proiectul activ. `_archive/` este în `.gitignore` și nu face parte din repo sau din starea versionată; versiunile eliminate rămân recuperabile din istoricul Git (`git show 319cf5f^:<cale>`).
