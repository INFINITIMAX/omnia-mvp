# TASKS — Omnia

## Predare verificată — 11-09-2026

La cererea lui Lucian, situația completă și pașii executabili sunt în [`HANDOFF.md`](HANDOFF.md). Verificare proaspătă de host: **761 passed, 11 skipped**; diagnostic 19 cazuri, 10 afirmații nepublicabile acceptate, zero pasaje omise/erori. Toate fișierele Python sunt identice cu snapshotul pre-D11; zero staged și zero agenți activi. Predarea este finalizată, **implementarea D11 nu este finalizată**. Nu s-a relansat Coderul și nu s-a schimbat providerul pentru această predare. Dovezi în directorul temporar `normativai-stabilizare-237e11d/handoff-11-09-2026/`.

## Sarcină curentă BLOCATĂ — D11, multi-document implicit (11-09-2026)

Lucian a aprobat căutarea multi-document implicită, cu restricții numai la solicitare explicită, apoi a cerut „please go on and proceed”. Această reluare înlocuiește oprirea după R06, **numai pentru lucrul local descris aici**, nu pentru publicare sau celelalte restanțe.

- Obiectiv: recunoașterea corectă a codurilor și retrieval multi-document fără blocare automată după sursele citate anterior. Nu evităm sinteza multi-sursă; evităm atribuirea greșită și încălcarea unei restricții explicite.
- Baseline: **761 passed, 11 skipped**, exit 0; snapshot Python complet și zero staged. Coderul reutilizat a salvat exclusiv `tests/test_multi_document_retrieval.py` (18 funcții/77 cazuri parametrizate declarate); host RED: **42 failed, 35 passed, 0 errors/skipped**, exit 1 comportamental. Confirmă filtrarea automată după coduri/context, ambiguitatea artificială la două documente, lipsa separatorului `/` și D12/D13 neimplementate; nu există editări runtime. Doar `MD-BASELINE` și `MD-RED` sunt închise (2/8). Implementarea, QA și Reviewer nu sunt lansate.
- **D12/D13/D14 aprobate:** numai „doar din [cod]”, „numai din [cod]”, „exclusiv din [cod]”, în întrebarea curentă; cod recunoscut/aprobat → scope fără fallback global; cod necunoscut/neaprobat → HTTP 200 `ambiguous_reference`, mesaj existent, zero embedding/generare/global fallback/apel plătit, dar consumă quota și rate limit existente. Exact „nu doar din [cod]” este guard: global implicit, nu scope. Nu persistă implicit. „Nu numai”, „nu exclusiv”, formulările alternative, mai multe restricții, continuarea de articol ambiguă și replay-ul UI rămân D02/D03. Coderul nu poate alege aceste ramuri tacit.
- Fișiere de implementare propuse: `retrieval_core.py`, testele de retrieval și adaptările strict necesare ale testelor API. `main.py`, R06/generation, evaluatorul/gold-urile, UI, DB, SDK, quota și plafoanele sunt protejate.
- Un Coder în worktree-ul existent `D:/Omnia-MVP-stabilizare`; QA și Reviewer read-only după implementare. Gazda rulează testele prin PowerShell/Python, deoarece bash-ul nativ al agenților nu are WSL funcțional.
- Criterii și restanțe: `revizii.md` lot D11/2A și `GATES.md`. Nu declarăm R02–R04 rezolvate prin simpla eliminare a unui filtru.
- **Checkpoint GitHub:** `0fc92e22ea659620ce220e452bd542435f348b1a`, branch `origin/fix/stabilizare-coduri-normative`; include checkpointul RED `8ca650e` și evidența lui. Este încă lot RED, nu candidat de merge.
- Planner a autorizat runtime-ul strict prin `multi-document/runtime-authorized.txt`: D11–D14 sunt contract complet pentru acest lot, cu D02/D03 și alte negații excluse explicit. Coderul a blocat corect înainte de editări când D14 lipsea; după aprobarea D14 a salvat numai 5 cazuri RED suplimentare (2 D14, 3 scope+istoric), apoi a atins limita Codex înainte de runtime. Host: 5 failed/77 deselected, exit 1 comportamental; runtime este încă neatins. Nu relansăm automat; checkpoint GitHub urmează pentru testele/dovezile salvate. Gate-uri înainte de runtime: **3/8** (baseline, RED, contract). Coderul a salvat runtime-ul în `retrieval_core.py` și migrările trasabile D11 în testele retrieval/API. Host GREEN istoric: **515 focused passed; 863 full passed, 11 skipped, 0 failures/errors**. Diagnosticul R05 este păstrat: 19 cazuri, 10 constatări, exit 1 intenționat, zero pasaje omise/erori.
- **P1 D13 remediat local:** `NP 010 2099` nu mai consumă aliasul scurt; repro host confirmă `ambiguous_reference`, zero embedding/query. Regresii pentru whitespace/slash/cratimă și API D13: **81 focused passed**. Full după P1: **932 passed, 11 skipped, 1 warning**, exit 0. Dovezi `multi-document/p1-*.{log,xml,receipt.json}` și `d13-whitespace-suffix-fixed-repro.json`.
- Taskul P1 este terminat și urmează checkpoint GitHub. QA precedent a fost întrerupt de limita providerului; acceptarea D11 rămâne fără verdict QA și fără merge/deploy, DB real sau API plătit. Respectăm regula: nu pornim alt task înainte de checkpoint și decizia explicită de continuare.

## Predare finală R06 — verificat local, apoi STOP (11-09-2026)

- **R06 / 5B VERIFICAT LOCAL:** Reviewer OK și QA OK; cele opt fișiere revizuite au fost reconfirmate neschimbate prin hash. `main.py` este identic cu snapshotul inițial.
- Dovezi: RED 133 failed/18 passed înainte de runtime; GREEN 402 focused passed, 761 full passed/11 skipped/1 warning. Patru probe semantice suplimentare mockuite au trecut. Comenzile au fost executate de host, nu de agenții read-only.
- Pe cele 19 cazuri inițiale păstrate: 2 → 0 pasaje omise, zero refuzuri false/erori de execuție. Cele 10 afirmații nepublicabile acceptate rămân **R05 deschis**; diagnosticul are exit 1. Nu este evaluare de model live sau validare de expert uman.
- QA a confirmat păstrarea tuturor funcțiilor vechi de test și a celor patru adaptări de aserțiuni/decoratori. Niciun scenariu eliminat/slăbit și nicio omisiune nouă pentru a masca erori.
- Explicația codului: [`docs/R06_CODE_WALKTHROUGH.md`](docs/R06_CODE_WALKTHROUGH.md). Dovezi, hash-uri și rapoarte: `revizii.md` §5B și `GATES.md`.
- Comportament local: pasaj declarat verificat literal în dovada proprie; payload/pasaj invalid → 503 și rollback quota verificat, fără retry provocat de pasaj; JSON complet valid trunchiat păstrează avertismentul. Schema publică/DB/SDK și plafoanele sunt neschimbate; costul/compatibilitatea modelului real nu au fost măsurate.
- **Fără commit/staging/push, migrare, API plătit sau deploy.** Nicio schimbare în producție. Gate-urile PROD, R05 și celelalte taskuri rămân deschise conform planului.
- **STOP cerut de Lucian:** nu pornim următorul task. Nu există agenți activi la predare; continuarea necesită discuția cu Lucian.

## Reluare R06 — implementare salvată, GREEN local (10-09-2026)

- Coderul a salvat implementarea și migrarea fixture-urilor/evaluatorului înainte de limita providerului; nu refacem munca de la zero.
- RED istoric confirmat: 133 failed, 18 passed, exit 1 înainte de runtime. După reluare, host a rulat focused: **402 passed**; full: **761 passed, 11 skipped, 1 warning**, exit 0. Skip-urile sunt corpusul local absent.
- Evaluator: aceleași 19 cazuri, candidați și gold; **zero pasaje relevante omise**, zero candidați publicabili respinși, zero erori de execuție. Rămân **10 candidați nepublicabili acceptați** (R05), diagnostic exit 1 intenționat.
- Snapshot final în `C:/Users/Lucian-PC/AppData/Local/Temp/normativai-stabilizare-237e11d/r06/`; hash generation core `47bcd5cde02a71c6ec8c4cc6eb316a45a653b7cb766cad2ac10960e12419d959`.
- Status: **IMPLEMENTAT / QA-REVIEW ÎN CURS**, nu închis încă. Refolosim Testerul și Reviewerul 5A prin workflow `be4c8237-902a-464f-a6e2-086d1f191093`; Coderul nu se repornește fără finding concret.
- `main.py` executabil, schema publică, DB și SDK-urile sunt neschimbate. Fără commit/staging/push, apel plătit sau deploy.

## Următorul task — 5B/R06, direcție aprobată (10-09-2026)

- Lucian aprobă: modelul indică pasajul exact; backendul verifică existența în dovada citată; metadata rămâne controlată de backend.
- **Politică aprobată ulterior:** pasaj lipsă/invalid → 503 cu rollback quota verificat, fără retry provocat de această eroare, fără fallback la prefix. Costul deja consumat și rate limit-ul rămân; R05 nu este rezolvat prin verificarea existenței pasajului.
- **Trunchiere aprobată:** pachet JSON complet/valid cu semnal de trunchiere păstrează avertismentul; pachet incomplet → 503 fără reparare/retry.
- Status: **APROBAT / pregătire RED**, conform specificației 5B din `revizii.md`. Scope: generation core, adaptările strict necesare ale fixture-urilor/API/evaluatorului și regresii noi; fără DB/provideri reali sau publicare. Dacă agentul este încă la limită, workflow-ul se oprește fără încercări repetate.
- 5A rămâne verificat local, iar capacitatea Coderului nu este presupusă restabilită. Nicio relansare sau schimbare runtime în această actualizare.

## Predare finală — 5A, evaluator local verificat (10-09-2026)

- **VERIFICAT LOCAL:** `grounding_eval.py` (19 cazuri exclusiv sintetice) și `tests/test_grounding_eval.py` (34 teste noi). API-ul, GenerationService și testele existente sunt nemodificate.
- Host: 34 focused passed; full 591 passed, 11 skipped, 1 warning; diagnostic exit 1 intenționat: 10 candidați nepublicabili acceptați și 2 pasaje omise, 12 constatări în 11/19 cazuri. Nu este rata de eroare a modelului live.
- QA și Reviewer: OK pentru evaluator. Clarificarea finală salvată de Coder schimbă numai docstring-ul; Planner a confirmat AST executabil și teste identice cu snapshotul revizuit, apoi a rerulat verificările. Providerul a blocat din nou Coderul după salvare; nu s-au repetat lansările.
- `pytest -q -rs` confirmă că cele 11 skip-uri sunt cauzate de corpusul absent. Problemele temporare de afișare UTF-8 ale gazdei nu au necesitat schimbări în teste/aplicație.
- Dovezi și hash-uri finale în `revizii.md`, pasul 5; logurile locale în `C:/Users/Lucian-PC/AppData/Local/Temp/normativai-stabilizare-237e11d/`. Explicația pe linii este în raportul Coderului din workflow `49d43a49-3ff6-4f3c-8705-1d3e7a7973d7`, artefact `grounding/coder.md`.
- Etichetele au fost redactate/revizuite de agenți, nu validate de expert uman; se aplică exact candidaților fixați. Un răspuns rescris ulterior cere reevaluarea etichetelor.
- **R05/R06 rămân deschise; pasul 5 complet și gate-urile PROD nu sunt închise.** Urmează decizia D08, recomandat R06/pasaj relevant verificabil, înainte de orice schimbare publică.
- Fără commit/staging/push, DB, API plătit, ingestion, migrare sau deploy. Pasul 0 rămâne nerevizuit ca lot separat, iar R01 neînceput. Nu există agenți activi la această predare.
- **Valoare CV:** evaluare reproductibilă și verificată independent, cu distincția explicită între instrument corect și produs încă vulnerabil.

## Prioritate curentă — 5A, corectitudinea afirmațiilor/citărilor (09-09-2026)

- Lucian a cerut să începem cu problemele cele mai complicate. Lotul 0–1 de mai jos rămâne deschis, dar nu mai este primul în ordinea de execuție.
- Obiectiv actual: R05/R06 din `revizii.md`, diagnostic local și alegerea strategiei; fără implementare publică sau cost aprobat implicit.
- Planner a rulat șase probe sintetice: control pozitiv acceptat; patru afirmații greșite acceptate cu ID valid; pasaj relevant după 600 de caractere absent din citatul public. Raport: `C:/Users/Lucian-PC/AppData/Local/Temp/normativai-stabilizare-237e11d/r05-r06-probes.json`.
- Aceste probe demonstrează limitele validatorului, nu calitatea modelului live. Zero DB/provideri reali; runtime și teste proiect nemodificate. Nu avem încă un fix de bifat.
- **Aprobare nouă:** Lucian a ales varianta 1 — set local de evaluare înainte de mecanisme noi; fără DB/API plătit. Implementarea este limitată la `grounding_eval.py`, `tests/test_grounding_eval.py` și predare documentară, fără runtime public modificat.
- Următoarea acțiune: Coder implementează evaluatorul, host rulează testele/diagnosticul, Tester și Reviewer verifică separat. Un diagnostic care găsește erori trebuie să rămână vizibil ca nonzero; pytest al evaluatorului nu declară produsul sigur. Dacă providerul refuză din nou agentul, ne oprim, fără relansări repetate.

## Predare — plan consolidat de revizii (09-09-2026)

- La cererea lui Lucian, Planner-ul a redactat [`revizii.md`](revizii.md): constatările R01–R28, decizii aprobate versus propuneri, statusuri, pași 0–6 și gate-uri de producție PROD-01–PROD-11.
- Documentul consolidează auditul; nu înlocuiește `AGENTS.md` sau registrul `docs/DECISIONS.md` și nu autorizează implicit implementări, DB, costuri ori publicare.
- Workflow-ul lotului 0–1 s-a oprit la limita providerului după editarea celor șase documente. Baseline: 557 passed, 11 skipped, 1 warning; runtime-ul și testele retrieval sunt nemodificate, QA/review final neîncepute.
- Următoarea acțiune: la restabilirea capacității verificăm starea, închidem review-ul pasului 0 și reluăm testele RED pentru R01. Etapa de după producție rămâne de clarificat cu Lucian.
- Această predare modifică numai documentație; fără relansare de agenți, commit/push, DB, ingestion sau deploy.

## Lot aprobat 0–1 — stabilizare coduri normative (09-09-2026)

**Stare de referință:** `origin/main` la `237e11db81251b8eb316ec02aa01e428089c66bc` include fixul de status `e49223f` și workerul `6cfd69c`, integrate prin PR8. Lucrul acestui lot este limitat la `D:/Omnia-MVP-stabilizare`, branch `fix/stabilizare-coduri-normative`. Ultimul deploy **verificat anterior** este `47a6133` (08-09-2026); nu există verificare live nouă în acest lot.

**Intent:** sincronizarea sursei de adevăr, apoi remedierea strictă a aliasurilor cu slash, fără extinderea comportamentului de produs.

**Spec aprobat:** pasul 0 schimbă numai documentația; pasul 1 permite `/` în `_ALIAS_SEPARATOR`, alături de whitespace/cratimă, și extinde `tests/test_retrieval_core.py`. Codurile necunoscute, contextul, statusurile, DB și providerii rămân neschimbate.

**Plan minimal și stare:**
- [ ] **0 — Documentație:** sincronizare propusă în această predare în `TASKS.md`, `PLAN.md`, `GATES.md`, `docs/DECISIONS.md`, `docs/PROJECT_OVERVIEW.md`, `docs/AUTO_INGESTION_WORKER.md`; acceptarea manuală independentă rămâne deschisă.
- [ ] **1 — Slash:** mai întâi demonstrarea regresiei `pytest -k alias_slash_regression` pe runtime nemodificat, apoi modificarea separatorului și validările din `GATES.md`. Nu este implementat în predarea pasului 0.

**Workflow curent aprobat:** Lucian pune **un PDF** în `documente_noi/_inbox`, anunță Planner-ul, primește raport **local** de extracție/validare și aprobă separat DB + Voyage. Publicarea prin status `approved` necesită altă aprobare explicită. Importul manual sigur punctual **nu este încă livrat**; `populare_db.py` nu este un importer insert-only.

**Worker inactiv:** Lucian a renunțat la activare. Codul, scriptul de înregistrare și migrarea se păstrează; Task Scheduler este neinstalat și `20260909000000_document_ingestion_sources.sql` este **neaplicată**, conform predării, nu unui audit nou. Registrul SHA și pornirea la logon sunt decizii independente; fluxul manual nu le aprobă implicit.

**Dovezi disponibile:** logul host `C:/Users/Lucian-PC/AppData/Local/Temp/normativai-stabilizare-237e11d/baseline.log` raportează `557 passed, 11 skipped, 1 warning` (TestClient). Este baseline anterior schimbărilor, nu validare a lotului și nu execuție personală a Coder-ului. Gates rămân deschise până la dovezi. Zero operațiuni externe autorizate: fără DB, rețea/API, ingestion, migrări, scheduler, stage/commit/push/merge/deploy.

**Backlog ordonat — TODO, pașii 2–6 neautorizați în acest lot:**
- [ ] **2 — Context:** clarificare și stabilizare; orice schimbare de comportament cere aprobare explicită.
- [ ] **3 — Import manual sigur punctual:** livrare separată; aprobarea workflow-ului nu aprobă implicit implementarea, registrul SHA sau logon-ul.
- [ ] **4 — Integritate articole:** verificări și propuneri, fără reparări automate de date.
- [ ] **5 — Evaluare reală:** protocol și cost aprobate separat; testele mock nu dovedesc calitatea reală.
- [ ] **6 — Operare:** decizii și execuție aprobate separat, fără activare implicită de worker/scheduler.

**Notă de lectură a istoricului:** predările și backlogurile de mai jos sunt păstrate ca istoric. Afirmațiile vechi despre 6 documente/3345 chunk-uri, lotul P118/2 încă neimportat, lipsa antetelor/trusted proxy/deploy/redesign sau `/documents` de implementat nu sunt stare curentă. Cele **10 documente `approved`** sunt confirmarea istorică a lui Lucian, nu o verificare DB nouă; numărul curent de chunk-uri este necunoscut. Pentru migrări, vezi distincția documentat aplicat/neaplicat/neverificat din `docs/PROJECT_OVERVIEW.md`.

**Valoare CV:** trasabilitate între decizie, cod versionat, deploy verificat și gates cu dovezi, fără a confunda teste mock cu validare de producție.

## Predare — Deploy production din `main` (08-09-2026)

- [x] **Sursă publicată:** merge commit `47a6133` din `main`, prin deploy manual Railway; serviciul nu are Git Source/autodeploy legat.
- [x] **Gate infrastructură:** healthcheck Railway configurat la `/health`; redeploy-ul de configurare și deploy-ul SHA-ului `47a6133` au ajuns `SUCCESS`.
- [x] **Smoke HTTPS fără cost:** `/health`, rădăcina și antetele CSP/HSTS/nosniff/frame deny au trecut; contractul `out_of_scope` a răspuns HTTP 200, fără citări, cu quota restaurată. Nu s-au apelat Voyage sau Anthropic.
- [x] **Efect DB controlat:** smoke-ul `out_of_scope` a incrementat rate limit-ul și a făcut rollback pentru rezervarea quota; fără migrare, ingestion sau apel API plătit.
- [x] **Valoare CV:** deploy trasabil la SHA, healthcheck configurat și smoke post-deploy documentat, fără publicarea surselor ori a secretelor.

## Predare — context conversațional fără fallback semantic global (07-09-2026)

- [x] **Decizie aprobată implementată:** un document numit explicit fără articol exact sau codurile de context rezolvate la documente aprobate restrâng semantic retrieval-ul; un rezultat gol/sub prag devine `not_found`, fără căutare globală.
- [x] **Compatibilitate și cost:** fără document explicit/cod rezolvabil rămâne exact o căutare globală; fiecare rută semantică păstrează exact un embedding, iar `not_found` nu apelează Anthropic.
- [x] **Regresii mockuite:** scenariul sprinklere P 118/2 → obstacol nu poate ajunge în I7 nici la scoped gol/sub prag; API-ul verifică lista `document_ids`, absența SQL-ului global și zero generator la scoped miss. Validarea contextului rămâne 422 înainte de dependențe.
- [x] **Validare Coder:** țintit retrieval+API+UI `320 passed, 1 warning`; complet `533 passed, 11 skipped, 1 warning` (warning extern `TestClient`); `git diff --check` curat. Fără DB, API plătit, deploy, commit sau push.
- [x] **Valoare CV:** regresii unit+API dovedesc izolare de context, controlul costului și prevenirea răspunsurilor cross-document neancorate.


## Predare — blocarea calculelor și dimensionărilor de proiect (07-09-2026)

- [x] **Decizie de produs:** NormativAI nu este calculator; explică numai metodele, formulele și datele normative existente în dovezi.
- [x] **Contract public:** HTTP 200, `status: out_of_scope`, mesaj exact „NormativAI nu efectuează calcule sau dimensionări de proiect. Pot indica prevederile și datele cerute de normative.” și `citari=[]`.
- [x] **Gate server-side local:** rulează înainte de catalog, retrieval, Voyage și Anthropic; tentativa rămâne contabilizată în rate limit, quota anonimă de 10 este restaurată, iar rollback-ul neverificat produce 503 fail-closed.
- [x] **Classifier determinist:** diferențiază execuția cerută (imperativ, solicitare nominală bounded, necesar de putere/capacitate) de întrebări metodologice, documentare sau despre valori prescrise. Este o barieră lexicală conservatoare, nu analiză semantică exhaustivă.
- [x] **Apărare în profunzime:** promptul interzice executarea calculelor/estimărilor/dimensionărilor; UI-ul păstrează refuzul vizibil în istoric, dar îl exclude din contextul următoarei căutări.
- [x] **Validare finală Planner:** target 171 passed; full 522 passed, 11 skipped, 1 warning extern TestClient; hash-ul CSP verificat, `git diff --check` curat și zero U+FFFD verificat anterior.
- [x] **Review final:** Tester OK; Reviewer OK, fără findings la commit `e622793`.
- [x] Branch `fix/blocheaza-calcule-proiectare` este împins cu commiturile `37bcd60`, `7172cd6`, `907da33`, `328c300`, `e622793`; fără merge, deploy, DB sau apeluri API plătite.
- [ ] **Residual:** testul UI este static, nu browser E2E; regexurile nu pot garanta toate parafrazele posibile, iar apărarea prompt rămâne strat secundar.

## Predare — eliminarea `GET /documents` (07-09-2026)

- [x] **Endpointul `GET /documents` a fost eliminat complet** din `main.py`, împreună cu
      modelele de răspuns (`DocumentPublic`, `DocumenteResponse`), interogarea SQL și funcția
      ajutătoare — fără cod mort rămas.
- [x] **Motivul e de produs, nu tehnic.** Catalogul complet al normativelor indexate (cod,
      titlu, an, număr) arată exact ce acoperă și ce nu acoperă produsul — informație sensibilă
      competitiv. Aceeași decizie a lui Lucian scosese deja lista documentelor din nav-ul UI la
      03-09-2026, înlocuind-o cu istoricul conversațiilor.
- [x] **De ce a fost implementat totuși:** endpointul (commit `9bd65d5`, 05-09-2026) urma
      backlog-ul din `PLAN.md`, cerut din fazele 4 și 6, care preceda decizia de produs. Backlogul
      contrazicea decizia ulterioară; contradicția a fost prinsă de Planner la 07-09-2026.
- [x] Test anti-regresie adăugat: `test_ruta_documents_nu_exista_si_nu_poate_fi_reintrodusa_tacut`
      verifică 404 pe `/documents` și `/documente` **și** că nicio rută înregistrată nu conține
      „document" în cale — o reintroducere sub altă cale sau altă metodă nu poate trece tăcut.
      Verificat că testul chiar pică dacă ruta e readăugată.
- [x] Documentație actualizată cu motivul explicit, ca să nu fie reimplementat din backlog:
      `PLAN.md` (secțiune „Anulat definitiv" + fazele 4 și 6), `DEPLOYMENT.md` (tabelul de rute),
      `docs/PROJECT_OVERVIEW.md`, `docs/HYBRID_SEARCH_SPEC.md`.
- [x] Confirmat în cod că UI-ul nu apela endpointul nicăieri (`static/*.html` — zero referințe).

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
3. ~~`GET /documents` cu contract aprobat — blochează contorul de documente din nav.~~ **ANULAT (07-09-2026):** catalogul documentelor nu se expune public (decizie de produs — vezi predarea din capul fișierului). Nici endpointul, nici contorul din nav nu se implementează.
4. Scheduler pentru ștergerea fizică a bucket-urilor IP expirate în max 24h (acum expiră doar logic).
5. Chips-urile de sugestie trebuie reevaluate față de catalogul curent de 10 documente aprobate; acoperirea lor nu se mai deduce din inventarul istoric de 6 documente. Decizie de conținut.
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
- [x] Adaptoarele lazy/injectabile Voyage (`voyage-3.5`) și Anthropic (`claude-sonnet-4-6`, maximum 800 tokenuri la acel moment; plafonul e 1200 din 07-09-2026) nu creează clienți externi la import.
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
- [x] Contorul de documente din nav **nu se va implementa**: `GET /documents` a fost eliminat
      definitiv la 07-09-2026, fiindcă lista publică a normativelor e informație sensibilă
      competitiv. Nu e o restanță, e o decizie de produs închisă.
- [ ] Metrul de quotă din mockup (bara 7/10) nu este implementat: ar cere logică nouă de stare,
      iar acest task este strict de prezentare. Contorul textual rămâne singura sursă.
- [ ] Chips-urile de sugestie au rămas cele din MVP. Două dintre ele („stările limită”,
      „debitul minim pentru grupuri sanitare”) necesită reevaluare față de catalogul curent de 10 documente aprobate
      și vor produce refuzuri. Înlocuirea lor este o decizie de conținut pentru Lucian.

## Backlog ordonat — istoric, depășit de lotul 0–1 și backlogul 2–6 de mai sus

1. Faza 1: migrarea Supabase pentru metadata și chunk identity. **Finalizată.**
2. Faza 3A: retrieval core descris mai sus. **Finalizată în branch-ul `feat/retrieval-core`; fără API public.**
3. Faza 3B1: Generation Core și citări oficiale validate. **Finalizată; fără FastAPI.**
4. Faza 3B2: contract și integrare API pentru retrieval/generare. **Finalizată mock-first.**
5. Faza 4: cost control: quota anonimă (10 întrebări/browser) și rate limiting (5/minut, 30/oră per IP). **Faza 4A + 4B (controalele anonime) și `POST /intreaba` sunt finalizate și integrate** în FastAPI și în UI MVP. `/health` este implementat. **`/documents` a fost eliminat definitiv la 07-09-2026** — catalogul documentelor nu se expune public (decizie de produs, vezi predarea din capul fișierului); nu mai e restanță și nu se reimplementează. Rămân deschise și: gate producție `ANONYMOUS_COOKIE_SECURE=true`, suport trusted proxy (în prezent se folosește exclusiv `request.client.host`, fără `X-Forwarded-For`) și ștergerea fizică a ferestrelor IP expirate în maximum 24 ore (fără scheduler/job dedicat).
6. Faza 5: testare agresivă. **Suita locală mockuită este finalizată (209 teste, inclusiv 31 teste statice UI și setul formal de evaluare din §10 al `docs/HYBRID_SEARCH_SPEC.md`, implementat local/mockuit în `tests/eval_set_data.py` și `tests/test_eval_set.py`).** Setul de evaluare este un **regression eval sintetic, determinist, local/mockuit pentru un set controlat** — nu o evaluare de calitate reală Voyage/Claude. Rulează prin `RetrievalService` real cu un repository sintetic unic care **nu primește `EvalCase`/tip/expected**: caută exact strict după `document_id`+`articol_normalizat` într-un corpus comun (`CORPUS`, cu identitate document/articol și decoy-uri pe teme fără legătură), iar la semantic clasifică tot corpusul prin similaritate cosinus reală, calculată determinist (bag-of-words, fără `hash()` randomizat) între vectorul întrebării și vectorii conținutului, cu scor și `top_k` — fără hardcodare caz→dovadă. `SEMANTIC_CASES` are 12 cazuri — 12 cazuri fac pragul de acceptare ≥90% neechivalent cu o cerință de 100% (11/12 = 91,7%) —, fiecare o parafrază sintetică controlată a articolului-țintă (alt vocabular, altă structură de frază) — nu formularea propoziției din `CORPUS`; un test dedicat (`test_intrebarile_semantice_sunt_parafraze_sintetice_controlate_nu_copii_ale_corpusului`) verifică literal, prin cel mai lung șir de cuvinte consecutive identice, că nicio întrebare nu reproduce fragmentul-țintă. Embedderul sintetic recunoaște parafrazele printr-un vocabular conceptual sintetic de sinonime/variante morfologice (`_SYNONYM_GROUPS` în `test_eval_set.py`) — un vocabular conceptual sintetic, definit manual, comun corpusului și întrebărilor, nu o mapare caz→dovada așteptată. Metricile verifică identitatea document+articol așteptată (nu doar statusul `found`), iar un caz de control negativ (`NEGATIVE_SEMANTIC_CASES`, fără nicio suprapunere de vocabular cu corpusul) confirmă că o întrebare semantică fără semnal relevant primește scor 0.0 și e refuzată, nu potrivită automat. Rezultatul măsurat din date: exact lookup 100%, refuz articole inventate 100%, semantic 100% (12/12, prag de acceptare ≥90%) — tot local, fără apeluri reale/plătite și fără validare pe trafic public. Testul HTTP anti-leak (`test_raspunsul_public_nu_contine_niciodata_identificatori_tehnici`) acoperă statusurile retrieval sub 200; verificarea e factorizată în helper-ul comun `_assert_no_technical_identifiers`, aplicat și direct în testele reprezentative pentru 422, 403, 429 și 503 (fără duplicarea setup-ului, fără slăbirea aserțiunilor de body exact) — acoperire reală pe toate codurile publice, nu doar afirmată. Rămân restante: testarea vizuală/manuală în browser real, evaluarea reală de calitate Voyage/Claude (pe date reale) și smoke test-urile plătite.
7. Faza 6: UI real. **Sublivrare funcțională finalizată:** UI MVP conectat exclusiv la `POST /intreaba` și la controalele anonime. **Faza 6 în ansamblu rămâne parțială/nefinalizată:** lipsește `GET /documents` (lista documentelor și contorul cerute de PLAN.md pentru această fază — vezi Faza 4 pentru statutul contractului), redesign-ul vizual și testarea manuală în browser real rămân deferate.
8. Faza 7: review și deployment. Există un review punctual, explicit documentat, pentru migrarea metadata (remedierile Reviewer și review-ul final `APPROVE`, vezi predarea de mai sus, liniile 22 și 25) — nu se afirmă că alte componente/faze au fost revizuite similar. **Rămân pendinte:** review-ul independent final pre-deployment, deployment-ul public și smoke tests pe URL public.
9. Faza 8: business/CV material. **Neînceput.**

## Observații

- `np057_02` nu are PDF original local; are doar `extracted.txt` și metadata notează acest lucru.
- Lucian a confirmat istoric 10 documente `approved`; nu este o verificare DB nouă. Numărul curent de chunk-uri este necunoscut. Inventarul detaliat din 03-09-2026 rămâne istoric la predarea sa.
- `PLAN.md` și acest fișier sunt sursele active de coordonare.
- Commit `319cf5f`: 17 scripturi legacy neutilizate (ex. `chunkingv2.py`, `omnia_qa.py`, `verificare_db.py`) au fost eliminate din proiectul activ. `_archive/` este în `.gitignore` și nu face parte din repo sau din starea versionată; versiunile eliminate rămân recuperabile din istoricul Git (`git show 319cf5f^:<cale>`).
