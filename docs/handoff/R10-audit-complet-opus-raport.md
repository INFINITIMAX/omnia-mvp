# R10 — audit complet independent (Opus 5.5), 25-09-2026

Audit read-only, refăcut cu Opus 5.5 la cererea lui Lucian. Rapoartele anterioare R07 (operations, security) și R09 (ingestie), scrise de Sonnet, au fost tratate ca ipoteze și reverificate. Trei audituri paralele (nucleu RAG, ingestie, securitate/operațiuni/dependențe) plus verificări directe ale planner-ului.

## Dovezi rulate

- `python -m pytest -q` pe cod identic cu `main` `132f7f4` → **1021 passed, 1 warning** (deprecare externă httpx/starlette).
- Worktree R08 (`fix/r08-split-article-retrieval`, `8023d1a`) → **1013 passed, 11 skipped** (skip-urile = `documente_noi/` local, gitignored). Merge-base = `132f7f4`, fără conflicte.
- Teste ingestie: 113 passed.
- CI pe `main`: ultimele 3 rulări `success` (15-09-2026).
- Live, doar GET: `/health` 200, `/docs` și `/openapi.json` 404, headere de securitate prezente, cookie `Secure; HttpOnly; SameSite=lax`, `index.html` live identic cu `main` după normalizarea CRLF.
- Planner a verificat direct finding-ul F1 în `main.py:157-168`, `generation_core.py:313-317`, commit-urile `1091bb8` și `6888902`, `docs/DECISIONS.md` (nicio decizie care aprobă schimbarea).

## Verdict global

**Cod solid și fail-closed; NU e gata de extins până nu se rezolvă F1 (decizie) și F2 (R08).** Nicio vulnerabilitate critică exploatabilă găsită. Rapoartele anterioare au fost corecte în direcție, dar au omis cel mai important finding (F1) și au exagerat impactul R08 în producție.

## Finding-uri, ordonate după severitate

### F1 — MEDIU-MARE: contractul de citare s-a schimbat fără decizie scrisă
- `main.py:157-168`: schema toolului Anthropic cere doar `raspuns` (commit `1091bb8`, 15-09-2026, fără body).
- `generation_core.py:313-317`: fără `pasaje`, citatul public devine primele ~600 caractere ale chunk-ului (`_literal_evidence_excerpt`), nu pasajul care susține afirmația (commit `6888902`).
- Contrazice textul aprobat: D22 (`docs/DECISIONS.md:9`, „schema pentru `raspuns` și `pasaje`"), D20 (`:14`) și R06 (`:70`, „Nu folosim prefixul de 600 caractere ca fallback").
- Promptul (`generation_core.py:425-434`) încă cere `pasaje` → contradicție internă.
- Pilotul R05 (`0941ea3`) a fost rulat după schimbare, deci a măsurat noul comportament.
- **Necesită decizie Lucian:** fie aprobă scris noul contract (D23), fie se revine la `pasaje` verificat.

### F2 — MEDIU: refuz fals pentru articole lungi (R08) — confirmat, cu impact corectat
- `manual_ingestion_preflight.py:358-369` taie la 1000 caractere cu același `articol`; `retrieval_core.py:542-546` refuză orice `(document, articol)` cu mai multe `content_hash` → `ambiguous_article`.
- **Corecție față de R09:** afectează în principal documentele importate pe calea manuală după `1ed2770` (15-09) — deci blochează mai ales **aprobarea** lor (NP091, NP 015-2022). Documentele legacy `approved` sunt afectate doar la coliziuni de normalizare. Impact live de confirmat cu un `GROUP BY document_id, articol_normalizat HAVING count(DISTINCT content_hash) > 1` pe `approved`.
- Fix-ul R08 e corect (refuză gap-uri/duplicate, nu amestecă documente), merge fără conflicte. **Dar e parțial:** pe ruta semantică (`SEMANTIC_TOP_K=5`) pot veni chunk-urile 40 și 42 fără 41 → tot refuz fals; evidence-ul ajunge la model în ordinea scorului, nu a `chunk_order`.
- Minor în R08: `retrieval_core.py:411-423` ghicește indexul scorului după lungimea rândului (compatibilitate cu mock-uri) — fixture-urile ar trebui actualizate în loc.
- Lipsește un test care leagă ieșirea chunkerului de retrieval — de aceea a scăpat.

### F3 — MEDIU: reimport legacy peste document `approved` fără gate uman
- `populare_db.py:222-249`, `:342`: dacă statusul rămâne `approved`, face DELETE și INSERT de chunk-uri și actualizează `cod_oficial`/`titlu_oficial` pe un document servit live. Gate-ul `approved` protejează doar trecerea de status, nu conținutul.

### F4 — MEDIU: IP falsificabil neverificat în producție
- Codul `main.py:600-618` e corect (citește `X-Forwarded-For` din dreapta), dar depinde de `TRUSTED_PROXY_HOPS=1` și de edge-ul Railway. Testul manual din `DEPLOYMENT.md:113-127` nu apare executat; `revizii.md:176` (R22) încă deschis.

### F5 — MEDIU: epuizarea plafonului zilnic = indisponibilitate pentru toți
- Cota de 10/vizitator e pe cookie (resetabilă). Rămân 5/min + 30/oră per IP și plafon global `DAILY_PAID_CALL_LIMIT=200` (`access_control.py:21`). Cu ~7 IP-uri plafonul se consumă și toți primesc 503. Costul e plafonat, disponibilitatea nu.

### F6 — MEDIU: fără timeout la provideri și DB în runtime
- `main.py:134`, `main.py:177`: clienții Anthropic/Voyage fără `timeout`, cu retry implicit (scripturile de eval/ingestie setează `timeout=30, max_retries=0`). DB `main.py:260-266` fără `connect_timeout`, `statement_timeout`, `sslmode=require`.

### F7 — MEDIU: nicio protecție în cod contra SR/SR EN
- `manual_ingestion_preflight.py:29`, `auto_ingestion_worker.py:54`: `_PATTERN_COD` acceptă explicit `STAS`, `SR`, `SR EN`, `SR EN ISO`. Regula „doar Monitorul Oficial" depinde doar de operator.

### F8 — MEDIU: deduplicare care pierde conținut în tăcere
- `populare_db.py:137`, `manual_ingestion_preflight.py:338`: „cea mai lungă variantă câștigă" — dacă numerotarea reîncepe în anexe, o variantă dispare fără log. Testul `test_populare_db.py:395` acoperă doar cazul fericit.

### Minore
- F9 — Două chunkere divergente (legacy vs. manual): granularitate diferită între documentele `approved`.
- F10 — `populare_db.py:255-267` compară doar hash-urile textului; schimbarea etichetei `articol` sau a ordinii e ignorată.
- F11 — `main` neprotejat pe GitHub (404 „Branch not protected"); nimic nu obligă CI verde înainte de merge/deploy.
- F12 — Deploy prin `railway up` din copia de lucru Windows (pagina live servită cu CRLF) → modificări necommise pot ajunge în producție; comanda de deploy și rollback-ul nu sunt în `DEPLOYMENT.md`.
- F13 — Acțiuni GitHub nefixate pe SHA; nicio fixare a versiunii Python pentru Railway (CI 3.13, numpy 2.5 cere ≥3.12).
- F14 — `manual_ingestion_import.py:61` definește `ImportError`, care umbrește builtin-ul.
- F15 — Chunk-urile nu au număr de pagină; citarea nu poate indica pagina.
- F16 — Legacy: embeddings plătite pentru toate documentele într-o tranzacție; eșecul documentului N pierde embeddings 1..N-1.
- F17 — Protecția anti-calcul (`scope_core.py`) e o listă de cuvinte-cheie, ocolibilă prin reformulare (există apărare în prompt).

## Confirmat fără probleme
- `answered` cere cel puțin o citare `[Cn]` validă; ID necunoscut = eroare (`generation_core.py:450-457`).
- JSON invalid/duplicat/schemă străină respins; `max_tokens` → 503; retry unic pentru referințe nesusținute, apoi `unsupported_answer`.
- Erori provider/DB → 503 generic cu rollback al cotei; log D21 doar clasă+cod (`main.py:797-803`).
- SQL parametrizat; filtrul `approved` nu poate fi ocolit; niciun cod nu promovează la `approved`.
- Căile manuale de ingestie atomice (embeddings înainte de DELETE/INSERT, SHA reverificat).
- Rate limiting atomic (`pg_advisory_xact_lock`, `access_control.py:191`), fail-closed.
- Fără XSS: tot textul modelului/citărilor randat prin `createElement`/`textContent` (`static/index.html:945-1195`); hash CSP corect.
- Worker-ul automat inactiv (niciun task programat pe host).
- D16/D18 în `main` (`4cce49a`, `fa82e31`, merge-uri `4bc4973`, `762fe34`).

## Corecții față de rapoartele anterioare
- **R09:** a exagerat impactul R08 („orice normă cu articole lungi în producție"); a atribuit greșit cauza split-ului secundar din `populare_db` (cauza reală: limita de 1000, `1ed2770`); a omis F3, F7, F9, F10.
- **R07:** a omis F4, F5, F6, F12. Două puncte trecute ca „necesită verificare externă" au fost verificate live (cookie securizat, paritate `index.html`).
- **HANDOFF.md (25-09):** afirma că D20/D22 sunt live conform contractului — fals după F1; D18 era marcat nereconfirmat — e confirmat în `main`.

## PR-uri Dependabot
- #1 pydantic, #2 pymupdf, #4 python-dotenv: CI verde, patch-uri sigure.
- #3 numpy 2.5.2: CI picat din cauza runner-ului Python <3.12 de pe 06-09, nu din bump; rebase + CI.
- #5 anthropic 0.116 → 1.3.0: **nu acum**. Codul folosește API de bază (`messages.create` cu `tools`/`tool_choice`), dar testele folosesc fake-uri și nu ar prinde schimbări de formă; changelog 1.0 neverificat. Pași: rebase, CI, un smoke real aprobat.

## Necesită verificare live (nu se poate static)
1. SHA-ul rulat acum pe Railway (F1 e sau nu în producție; ultimul deploy consemnat `e895605`).
2. Documente `approved` cu articole împărțite (query-ul de la F2).
3. Falsificarea `X-Forwarded-For` pe edge-ul Railway (testul din `DEPLOYMENT.md:113-127`).
4. Privilegiile `DB_USER` și RLS în Supabase.

## Ordinea recomandată
1. **Decizie Lucian pe F1** (aprobă D23 sau revenire la `pasaje`).
2. Merge R08 după aprobare, apoi task pentru ruta semantică (ordonare după `chunk_order`, gap-uri top-k) și testul chunker→retrieval.
3. Timeout-uri provideri/DB (F6) — mic, izolat.
4. Verificările live 1-4.
5. F3, F7, F8 ca task-uri separate de ingestie.
6. Dependabot #1, #2, #4, apoi #3; #5 separat, cu smoke.

## Planner — decizie pe baza raportului
Raport consolidat de planner din cele trei audituri + verificare directă a F1. Nicio modificare de cod făcută. Aștept decizia lui Lucian pe F1 și aprobarea ordinii de mai sus.
