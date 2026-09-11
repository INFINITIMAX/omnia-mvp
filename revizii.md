# Revizii NormativAI — de la audit la producție verificată

Actualizat: **11-09-2026**, România (EET; pentru programări locale se folosește `Europe/Bucharest`, inclusiv ora de vară).

**Stare generală: BLOCAT pentru declararea „gata de producție”.** Aplicația este deja live, dar existența unui deploy nu dovedește pregătirea pentru utilizare largă sau comercializare.

Document cerut de Lucian pentru păstrarea integrală a constatărilor, deciziilor, statusurilor și pașilor de remediere. Crearea planului este autorizată; nu autorizează implicit toate implementările, costurile sau operațiunile de mai jos.

## 1. Cum folosim acest document

- `AGENTS.md` rămâne sursa regulilor și rolurilor.
- `docs/DECISIONS.md` rămâne registrul deciziilor de produs aprobate. Acest document le rezumă; nu le înlocuiește.
- `revizii.md` este registrul consolidat al auditului și traseul de remediere. Fiecare problemă are ID, pas și criteriu de închidere.
- `TASKS.md` păstrează predările operative și indică ID-ul curent din acest plan.
- `GATES.md` păstrează comenzile și dovezile lotului activ; `PLAN.md` se schimbă numai la schimbarea unei decizii aprobate.
- `docs/PROJECT_OVERVIEW.md` trebuie să reflecte implementarea și operarea reale, nu intențiile.
- La predare actualizăm statusul aici și sumarul din `TASKS.md`. Nu menținem două backloguri independente care se contrazic.
- Lucrăm strict după pași și dovezi, nu după impresia „pare gata”. Disciplina poate fi strictă; absența absolută a erorilor nu poate fi garantată.

### Statusuri permise

| Status | Sens exact |
|---|---|
| PROPUS | Recomandare neaprobată pentru implementare/comportament. |
| AȘTEAPTĂ DECIZIE | Lucian trebuie să aleagă înainte de implementare. |
| APROBAT / TODO | Scope aprobat, implementare neîncepută. |
| ÎN LUCRU | Un singur Coder deține modificarea curentă. |
| IMPLEMENTAT / NEVERIFICAT | Fișiere schimbate, fără toate dovezile de acceptare. |
| VERIFICAT LOCAL | Teste și review pentru exact modificarea predată; nu implică publicare. |
| INTEGRAT | Commit integrat în ramura țintă; nu implică deploy sau migrare. |
| PUBLICAT / VERIFICAT | SHA publicat și verificat prin gate-urile post-deploy aprobate. |
| BLOCAT | Există o dependență, o eroare sau o aprobare lipsă identificată explicit. |
| AMÂNAT EXPLICIT | Lucian a acceptat amânarea, cu motiv și condiție de reluare. Nu înseamnă rezolvat. |

Orice status VERIFICAT/PUBLICAT cere: SHA sau diff identificabil, comandă/procedură, rezultat, dată, responsabil și limitări. Un test omis nu este un test trecut. Un verdict de agent nu este aprobare de deploy.

## 2. Fotografia verificată și limitele auditului

### 2.1 Git, producție și lucrul local

| Element | Stare cunoscută |
|---|---|
| Repository | `INFINITIMAX/omnia-mvp`; brand public NormativAI. |
| `origin/main` verificat | `237e11db81251b8eb316ec02aa01e428089c66bc`, PR #8 integrat. |
| Fix status importer | `e49223f955907afa441461de6c1a6a2f94bdd6fa`, inclus în PR #8. |
| Worker automat | `6cfd69c2966eeca6b2710fa682109390065cae4f`, inclus în PR #8, neactivat. |
| Ultimul deploy identificat și verificat anterior | `47a61339037c941e97f136686832142b8e1ac8e6`, Railway, 08-09-2026. Nu presupunem că PR #8 este publicat. |
| Worktree activ pentru revizii | `D:/Omnia-MVP-stabilizare`, branch `fix/stabilizare-coduri-normative`, HEAD `237e11d`. |
| Pasul 0 înaintea acestui fișier | 6 documente modificate local, 121 adăugări/15 ștergeri; diff-check trecut, nimic staged; QA/review final neefectuate. |
| Pasul 1 | Runtime-ul și testele retrieval sunt nemodificate; regresia RED nu a fost încă scrisă/rulată în acest lot. |
| Blocaje și reluări | Limitele ChatGPT au întrerupt lotul 0 și ulterior R06. La 11-09-2026 R06 are QA/Reviewer OK după reluare; fără agenți activi. Review-ul separat al lotului 0 rămâne deschis. |
| Publicare în acest lot | Fără commit, push, merge, migrare, ingestion sau deploy. |

Nu sincronizăm sau curățăm alte worktree-uri prin presupunere. `D:/Omnia-MVP-context-safe` păstrează `.unlazy/` preexistent; acesta nu este produsul acestei etape. Artefactul gazdei `checks/baseline.txt` a fost mutat controlat la 10-09-2026 în `C:/Users/Lucian-PC/AppData/Local/Temp/normativai-stabilizare-237e11d/initial-host-baseline.txt`, fără suprascrierea destinației și fără atingerea altor fișiere. Nu face parte din codul produsului.

### 2.2 Dovezi efectiv obținute

- Audit read-only al snapshotului `237e11d`: **557 passed, 11 skipped, 1 warning extern Starlette/TestClient**.
- Baseline repetat în worktree-ul de stabilizare: **557 passed, 11 skipped, 1 warning**, în 12,99 secunde. Acesta este baseline, nu validarea viitorului fix.
- `pip-audit -r requirements.txt`: fără vulnerabilități cunoscute raportate la audit. Nu este pentest sau garanție de securitate.
- GitHub CI pentru SHA auditat: pytest și pip-audit verzi.
- Audit HTTP live: GET `/health`, `/`, `/termeni`, `/confidentialitate` au răspuns 200; CSP, HSTS, nosniff și protecție anti-iframe prezente. GET-urile nu identifică singure SHA-ul live.
- Probe sintetice locale pentru parsing, retrieval, generation, chunking și replay UI. Probe UI prin harness Node, nu sesiune completă într-un browser real.
- Documentația pasului 0: `git diff --check` trecut, exact cele șase fișiere de documentație permise schimbate, zero fișiere staged.

### 2.3 Ce NU a demonstrat auditul

- Nu a interogat Supabase; **10 documente approved** reprezintă confirmarea anterioară a lui Lucian. Numărul actual de chunk-uri și acoperirea exactă sunt necunoscute.
- Nu a inspectat corpusul complet real și nu a verificat manual fidelitatea fiecărui articol.
- Nu a măsurat acuratețea modelelor live sau frecvența erorilor de citare în trafic real.
- Nu a executat Voyage/Anthropic plătit, ingestion, migrare sau deploy.
- Nu a confirmat granturile reale, configurația TLS efectivă DB, bugetul public persistent, proxy spoofing-ul sau restaurarea.
- Cele 11 teste omise depind de corpus local absent; numărul mare de teste mock nu le înlocuiește.
- Auditul s-a concentrat pe main auditat și contextul relevant; nu este certificarea fiecărui branch istoric.

### 2.4 Dovezi locale pentru reluare

Aceste locații sunt temporare, nu infrastructură durabilă. Dacă lipsesc la reluare, verificările se refac; nu declarăm că un raport absent este dovadă disponibilă.

- Audit: `C:/Users/Lucian-PC/AppData/Local/Temp/normativai-audit-fe53601b54424a1a930e18719ae970f4/` — snapshot `source/` și `probes.py`.
- Stabilizare: `C:/Users/Lucian-PC/AppData/Local/Temp/normativai-stabilizare-237e11d/` — `baseline.log`, `powershell-preflight.log`, `documentation-check.log`, scriptul local de verificare `verify.py`.
- Workflow eșuat: `ff8a67dd-ee4c-4fa7-951b-ebd84c7a2822`; Coder: `4cced0c8-cee0-47b2-95eb-2e3b9e42c683`. Fișierele editate au rămas; raportul final al copilului nu a fost livrat.
- La acceptarea unui task consemnăm dovezile minimale fără secrete în documentația de predare; logurile voluminoase rămân în afara repository-ului.

## 3. Evaluare sinceră și ceea ce păstrăm

Evaluare calitativă de Planner, nu scor calculat statistic: **6/10 produs**, **8/10 portofoliu**, **6/10 MVP pentru testeri controlați**, **4/10 pregătire pentru comercializare** la audit.

Riscul central: **o afirmație incorectă care pare credibilă pentru că are o citare validă**. Alte riscuri centrale sunt documentul greșit și pierderea informației în ingestion.

Păstrăm:

- FastAPI, separarea retrieval/generation/access-control și PostgreSQL/pgvector; fără rescriere.
- Catalog și retrieval limitate la `approved`, SQL parametrizat, RLS și protecțiile document–sursă.
- Exact lookup pentru referințe recunoscute și lipsa fallback-ului semantic după articol exact inexistent.
- Scoped semantic retrieval fără fallback global atunci când documentul este rezolvat corect.
- Metadata de citare construită de backend, nu inventată ca obiect public de model.
- Refuzul calculelor ca direcție de produs; clasificatorul necesită măsurare/remediere țintită.
- Quota/rate limiting/buget public, tranzacții și rollback; limitele se explică onest.
- DOM/textContent, absența download-ului și accesului browserului la Supabase.
- Teste mock, CI și deploy trasabil la SHA.

**Valoare CV:** corectitudinea măsurată, trasabilitatea, controlul costurilor și gestionarea incidentelor valorează mai mult decât numărul de agenți sau framework-uri.

## 4. Decizii aprobate versus propuneri

### 4.1 Decizii deja aprobate — de păstrat

1. Brandul public este NormativAI; Omnia este numele intern.
2. Răspunsurile trebuie bazate pe context recuperat și document/articol oficial. Nu se expun nume tehnice de sursă, embeddings, corpus sau endpoint de download.
3. Catalogul complet nu este public; `/documents` a fost eliminat intenționat și nu se reintroduce din backlog istoric.
4. Retrieval folosește numai `approved`. Importul creează pending; aprobarea publică este o acțiune separată a lui Lucian.
5. Importerul nu aprobă/reactivează documente. Fixul integrat reconciliază statusul înainte de hash-skip, permite dezactivarea controlată și păstrează verificările identității.
6. **D11 aprobat, 11-09-2026:** căutare multi-document implicită, restricții numai la cerere explicită. Citările anterioare/simpla menționare nu impun singure scope. Într-un scope cerut explicit nu există extindere globală ascunsă. Aceasta înlocuiește vechea politică de scope automat, încă prezentă în runtime la aprobarea D11.
7. Produsul nu execută calcule/dimensionări. Poate indica metode, formule și valori normative susținute de surse.
8. Ingestion curent: **Lucian depune un PDF, anunță Planner, primește raport local, aprobă separat DB/Voyage, apoi separat approved**. Ruta sigură punctuală încă trebuie livrată.
9. Fără worker permanent, Task Scheduler sau pornire la logon. Codul workerului, scriptul și migrarea se păstrează inactive.
10. Registrul SHA și logon-ul sunt independente. Migrarea SHA nu este aplicată conform predării; nu o aplicăm implicit pentru import manual.
11. Testele implicite sunt locale/mockuite. DB, migrări, apeluri plătite, push, merge și deploy au aprobări explicite separate. Acest lot este și fără commit/staging.
12. Un singur Coder; Tester și Reviewer read-only. Nu se modifică aceleași zone simultan.
13. Direcția vizuală existentă se păstrează. Nu se pornește un nou redesign pentru a evita problemele de fond.
14. Inițial au fost porniți pașii **0 și 1**. Ulterior Lucian a cerut atacarea problemelor celor mai complicate: prioritatea curentă este **5A — diagnostic local R05/R06 și specificarea verificării afirmațiilor/citărilor**. Pașii 0/1 rămân deschiși, nu anulați. Alegerea strategiei, schimbările publice și costurile se aprobă separat; cererea de a finaliza planul nu elimină aceste gates.

### 4.2 Controale existente — nu le reinterpretăm

- Accesul anonim are 10 întrebări totale/browser; ștergerea cookie-ului sau alt browser poate reseta identitatea. Nu este o identitate personală robustă.
- Rate limit documentat: 5 cereri/minut și 30/oră per IP; ferestrele expiră logic, cleanup-ul fizic nu este garantat încă.
- `answered`, `not_found` și ambiguitățile consumă quota conform contractului existent; refuzul de calcul restituie quota, dar tentativa rămâne în rate limit.
- Tranzacția quota rămâne deschisă pe durata providerului pentru rollback, decizie acceptată pentru MVP cu trafic redus; se reevaluează înainte de scalare.
- Bugetul public numără cereri eligibile pentru cost, nu euro. O cerere poate include embedding și mai mult de o generare.
- Workerul inactiv are limita aleasă anterior de 5 PDF-uri noi/10.000 chunk-uri pe zi, stare locală și resetare `Europe/Bucharest`. Nu este buget distribuit și nu este plafon monetar; nu se transferă implicit în fluxul manual.
- Workerul are controale specifice (`sslmode=require`, conectare 10s, statement 30s, Voyage 30s/fără retry), duplicate verificate înainte de rezervare, tranzacție insert-only și blocare a bugetului local. Acestea nu configurează automat API-ul public sau importerul legacy. `require` criptează, fără a echivala cu verificarea completă a certificatului/hostname-ului.

### 4.3 Decizii încă deschise — cerute la pasul relevant

| ID | Întrebare | Recomandarea Plannerului, NU implementare aprobată |
|---|---|---|
| D01 | Ce facem cu un document explicit necunoscut? | Clarificare, nu ignorarea codului și căutare globală. Definim mesaj/status/quota înainte de cod. |
| D02 | Articol exact fără document, dar cu context? Mai multe documente posibile? | De clarificat prioritatea referinței explicite și continuările/întinderea restricției. Recomandarea veche de restrângere automată după citări nu mai este ținta implicită: D11 cere multi-document. |
| D03 | Ce înseamnă redeschiderea istoricului și ștergerea lui? | Înlocuirea contextului activ, nu acumulare; aliniem stocarea, conversația afișată și mesajul UI. |
| D04 | Persistența duplicatelor pentru import manual? | Evaluăm reutilizarea registrului SHA și ruta punctuală insert-only; migrarea cere aprobare distinctă. |
| D05 | Conținut nou pentru un document aprobat? | Recomand reaprobarea versiunii schimbate; modelul de versiuni/tranziții și impactul asupra accesului se aprobă separat. |
| D06 | Articole duplicate, fragmente scurte, PDF-uri ambigue? | Raport și oprire înainte de scriere când integritatea nu este demonstrată; fără alegerea tăcută a textului mai lung. Definim excepțiile cu Lucian. |
| D07 | Setul de evaluare, pragurile și costul acceptabil? | Propun inițial 30 de întrebări verificate manual, categorii obligatorii și zero erori critice observate. Pragurile numerice finale se aprobă înainte de rulare. |
| D08 | Pasajul citat și validarea afirmațiilor? | **Direcție și eșec aprobate la 10-09-2026:** modelul indică pasajul exact, backendul verifică existența în dovada citată; pasaj lipsă/invalid → 503, rollback quota verificat, fără retry suplimentar pentru această eroare și fără fallback la prefix. Schema/trunchierea sunt de precizat; nu este garanție a adevărului afirmațiilor. |
| D09 | SLA, timeout/retry, plafon financiar, retenție, restaurare? | Valori explicite potrivite MVP-ului, RPO/RTO și buget aprobate; nu copiem arbitrar setările workerului. |
| D10 | După producție? | De clarificat: ultima cerere a lui Lucian este neterminată. Nu presupunem monetizare, abonamente sau funcții noi. |

## 5. Registrul complet al constatărilor

Referințele de linii sunt orientative pentru SHA auditat `237e11d`; înainte de editare se caută simbolul în fișierul curent. „Demonstrat” înseamnă cod/probă locală, nu incident cuantificat în trafic real. Constatările rămân deschise, cu excepția **R06 verificat local la 11-09-2026**, fără deploy. Progresul parțial este menționat separat; o remediere locală nu închide gate-urile de producție.

| ID | Constatare și dovadă | Impact / închidere cerută | Pas |
|---|---|---|---|
| R01 | `retrieval_core.py:41,147`, `_ALIAS_SEPARATOR` exclude `/`; `P 118/1-2025` nerezolvat, forma compactă recunoscută. | Documentul explicit poate pierde scope-ul. Regresii pe coduri oficiale, delimitare și rutarea scoped, apoi fix minimal. **APROBAT/TODO.** | 1 |
| R02 | `retrieval_core.py:433`: „Dar articolul 1.1?” cu context document execută exact lookup cu `document_id=None`. | Identitatea referinței poate fi pierdută. D02 necesită scenarii explicite; D11 nu permite remedierea prin blocare automată la documentele citate. Sinteza multi-document este dorită, nu un defect în sine. | 2 |
| R03 | Codul necunoscut poate fi ignorat și întrebarea ajunge semantic global. | Comportament de produs de clarificat prin D01; nu îl reparăm tacit în regexul R01. | 2 |
| R04 | `static/index.html:911`: replay adaugă context peste conversația precedentă; refuzurile excluse inițial reintră prin replay. | Amestec de subiecte și inconsistență de context. D03, teste de secvență și browser. | 2 |
| R05 | `generation_core.py:359`: generator sintetic „999 metri [C1]” cu dovadă sintetică „2 metri” produce `answered`. | ID-ul citării nu verifică susținerea afirmației. Măsurare reală și remediere demonstrată; nu afirmăm frecvența live. | 5 |
| R06 | La audit, citatul public era prefixul fragmentului, maximum 600 caractere. | **VERIFICAT LOCAL, 11-09-2026:** pasaj declarat de model, verificat literal în dovada proprie; 2 → 0 pasaje omise în setul sintetic, QA/Reviewer OK. Fără deploy sau dovadă de relevanță semantică generală. | 5B închis local |
| R07 | `populare_db.py:122–158`: duplicatele de articol păstrează numai textul mai lung. | Contradicții pierdute înainte de retrieval; raportare și politică explicită, fără eliminare tăcută. | 3/4 |
| R08 | Exemplul sintetic `Art. 1`/`Art. 2` a produs zero chunk-uri; fragmente sub 15 caractere sunt eliminate. | Acoperire incompletă. Raport de omisiuni și testare pe structuri reale aprobate; nu presupunem parser universal. | 3/4 |
| R09 | `populare_db.py:255`: idempotency compară hash-uri de text sortate, ignorând articolul/ordinea. | Citări/metadate vechi după modificări. Identitate completă și regresii pe text identic/articol sau ordine schimbate. | 4 |
| R10 | Importerul general scanează directoare și înlocuiește chunk-urile documentului schimbat; nu este insert-only. | Risc de atingere a corpusului existent. Rută manuală strict punctuală; fără rulare oarbă pe folder. | 3 |
| R11 | Documentul schimbat este re-embedded integral, nu doar fragmentele schimbate. | Costul a fost descris anterior prea optimist. Raport corect de cost; reutilizarea per-fragment nu este funcție livrată. | 3/4 |
| R12 | Reimportul conținutului unui document `approved` poate păstra statusul. | Conținut nou eligibil fără reaprobarea lui. D05; nu schimbăm automat statusurile datelor reale. | 4 |
| R13 | Metadata workerului poate păstra doar prima linie din titlul multilinie; parser intenționat îngust. | Titlu incomplet/ambiguitate acceptată. Raport local și teste de metadata; verificare umană înainte de import. | 3 |
| R14 | Worker automat: 1.281 linii adăugate pentru o cerință ulterior retrasă; migrarea SHA neaplicată. | Suprafață de operare inutilă pentru fluxul actual. Păstrat inactiv, reutilizăm doar ce este necesar importului manual. | 0/3 |
| R15 | `main.py:100,130,220`: controale explicite TLS/conectare/query/provider timeout/retry incomplete; Voyage instalat avea timeout implicit `None`, Anthropic retry implicit 2. | Cereri blocate, resurse ținute, cost/retry greu de anticipat. Configurații explicite și probe de eșec, distinct de worker. | 6A |
| R16 | Bugetele numără cereri/PDF-uri/chunk-uri, nu bani; starea reală a `paid_call_budget` nu a fost verificată în audit. | Protecții utile, dar fără dovadă de plafon monetar sau activare DB reală. Inventar aprobat, fail-closed, măsurare cost și verificare concurență. | 5/6A |
| R17 | `scope_core.py`: probă în engleză ratează refuzul; „Stabileste articolul aplicabil pentru scoli” produce fals pozitiv. | Calcul permis lexical sau cerere legitimă blocată. Set de regresii bilingv/română cu diacritice, contract clar și măsurare. | 5 |
| R18 | `static/confidentialitate.html:37` spune că istoricul nu pleacă din dispozitiv; UI trimite întrebări/coduri serverului și posibil Voyage. | Informare tehnică incorectă. Documentarea traseului real și review juridic. | 6B |
| R19 | Afirmații prea absolute despre imposibilitatea corelării HMAC, loguri IP și expirare/ștergere. | Privacy promite mai mult decât mecanismele demonstrate. Inventar date/hosting/provideri, retenție și formulări corecte. | 6B |
| R20 | Prima migrare presupune `documente_chunks` existent; două migrări au prefixul `20260903120000`. | Reconstrucție de la zero și istoric ambiguu. Reconciliere fără redenumire/reaplicare oarbă în producție. | 6C |
| R21 | `backup_baza_de_date.py`: export JSON fără restaurare demonstrată, snapshot consistent explicit sau noua tabelă SHA; nu acoperă singur schema/indexuri/secvențe. | Backup-ul nu dovedește recuperarea. Restore izolat, comparații și runbook cu RPO/RTO. | 6C |
| R22 | Privilegii backend/TLS DB și spoofing proxy în infrastructura reală neverificate. | Configurația efectivă poate invalida protecțiile codului. Probe aprobate, fără trafic abuziv sau secrete în rapoarte. | 6A/6C |
| R23 | Cleanup fizic neschedulat; monitorizare minimală erori/latency/cost și rollback operațional insuficient demonstrate. | Retenție neîndeplinită, incidente greu de detectat și recuperat. Soluție minimă, aprobată separat de workerul PDF. | 6C/6D |
| R24 | UI fără timeout/abort explicit la `fetch`; ștergerea istoricului nu șterge și conversația afișată; context activ insuficient de evident. | Formular blocat sau comportament confuz. Contract D03/D09, recuperare UI și browser real desktop/mobil. | 2/6B |
| R25 | Multe teste mock/static/SQL-string; 11 omise; eval semantic sintetic și puține probe PDF reale. | CI verde nu măsoară calitatea corpusului/modelului. Set real verificat manual, integrare și browser pe fluxuri importante. | 3/5/6D |
| R26 | PyMuPDF dual AGPL/comercial conform metadata; drepturile corpusului/comercializării neclarificate. | Verificare de licență și juridică înainte de vânzare. Nu reprezintă constatarea unei încălcări. | 6B |
| R27 | Documentație contradictorie despre 6 vs 10 documente, hold P118/2, redesign, cod/deploy și worker. | Predări viitoare pot reintroduce decizii anulate. **IMPLEMENTAT/NEVERIFICAT:** șase documente editate, fără acceptare finală. | 0 |
| R28 | Repetare de review-uri, WSL nefuncțional și editări în worktree greșit în etape anterioare. Limita providerului a oprit lotul actual. | Un writer, căi absolute, preflight host, agenți refolosiți, dovezi păstrate și reluare controlată. Nu relansăm în buclă la limită de capacitate. | 0/toate |

Filtre de raportat explicit înainte de release: `approved`, coduri rezolvabile, prioritatea exact/semantic, prag/top-K/buget context, eliminări/colapsări la chunking, clasificatorul de calcul și selecția pasajului citat. Parametrii existenți nu se schimbă doar pentru a obține un scor mai bun în teste.

## 6. Plan de execuție, în ordinea stabilită

**Un singur task de implementare activ.** Prioritate schimbată la cererea lui Lucian: începem cu partea cea mai complicată, **5A — R05/R06, corectitudinea afirmațiilor și a citărilor**. Numerotarea de mai jos păstrează dependențele, nu impune începerea cu 0/1. Diagnosticul și specificația 5A se pot face local; evaluarea reală rămâne dependentă de corpus și buget. Nicio bifă finală fără dovezi și nicio dependență ocolită. Niciun import real înaintea preflight-ului necesar și a aprobărilor.

### Pasul 0 — sursa de adevăr și recuperarea lucrului

Status: **IMPLEMENTAT PARȚIAL / QA-REVIEW BLOCATE de capacitatea agentului**. Acest fișier se adaugă ca plan la cererea lui Lucian.

1. La reluare inspectăm branch, HEAD, diff, index, worktree-uri și agenții activi; nu presupunem că starea de astăzi a rămas identică.
2. Păstrăm cele șase modificări ale Coder-ului. Nu refacem documentația de la zero și nu ștergem istoricul.
3. Verificăm manual sincronizarea acestui plan cu `TASKS.md`, deciziile și overview-ul.
4. Arhivăm numai artefactele host identificate din `checks/`, fără atingerea lucrului altor agenți.
5. Tester verifică dovezile locale; Reviewer verifică exactitatea stării și limitele autorizării.
6. Închidem pasul numai cu review acceptat și predare completă. Publicarea în Git are gate separat.

Acceptare: nicio instrucțiune activă de pornire worker; import manual marcat nelivrat; cod/live/DB separate; statusuri oneste. Fișiere: cele șase documente existente, plus `revizii.md` cerut acum.

### Lot D11 / 2A — retrieval multi-document, fără filtre implicite (11-09-2026)

**IMPLEMENTAT / GREEN LOCAL, QA/Reviewer PENDINTE (11-09-2026).** D11–D14 sunt salvate numai în `retrieval_core.py`, testele retrieval/API aprobate; R06/evaluator/main/UI/DB/SDK rămân neatinse. RED: 42 failed/35 passed/0 errors, plus D14/istoric 5 failed. Host GREEN: **515 focused passed; 863 full passed, 11 skipped, 0 failures/errors**. Evaluatorul protejat rămâne 19 cazuri/10 constatări R05/zero pasaje omise/zero erori, exit 1 intenționat. Gate-uri: 7/8, numai QA/Reviewer și predarea locală lipsesc.

Runtime: slash recunoscut; documente menționate/citate anterior nu filtrează; comparațiile de documente distincte sunt globale; numai „doar/numai/exclusiv din [cod]” curent restrânge; cod absent → `ambiguous_reference` fără dependențe, cu quota/rate; „nu doar din [cod]” → global. Păstrăm istoricul valid în embedding inclusiv cu scope. Negațiile generale, expresiile alternative, scope-urile multiple, persistența, continuările ambigue și replay-ul UI rămân D02/D03, în afara lotului. Acoperă R01 și filtrarea/contextul semantic, nu declară R02–R04 complet rezolvate. Nicio operațiune externă/publicare.

| Scenariu | Ținta aprobată / limita |
|---|---|
| Întrebare generală, fără context | Căutare între toate documentele `approved`, cu top-K/prag/context neschimbate. |
| Întrebare generală/continuare, cu documente citate anterior | Istoricul ajută textul de embedding, fără filtru obligatoriu după acele citări. |
| Menționare simplă a unui document, fără cerere de exclusivitate | Nu introduce singură o restricție de document. |
| Comparare/întrebare generală despre două documente, fără articole exacte | Nu devine ambiguă doar din cauza numărului documentelor; permite dovezi multi-sursă. |
| Restricție clar cerută, de exemplu „doar din [cod oficial]” | Scope explicit respectat, fără ieșire globală ascunsă. Formele recunoscute și ambiguitățile se arată în diff/scenarii înainte de runtime. |
| Document + articol exact | Identitatea cerută și ruta exactă fără embedding rămân protejate; articolul A nu se substituie cu B. |
| Coduri cu slash/spații, părți și ani diferiți | Catalogul aprobat rezolvă identitatea corectă, fără confundarea părților/limitelor tokenurilor. |
| Cod necunoscut într-o restricție, referință de continuare ambiguă, persistența restricției | D13 decis: cod absent → `ambiguous_reference`, fără dependențe, quota/rate consumate. D02/D03 rămân deschise pentru continuări/persistență; nu le alegem tacit. |

Diff propus: `retrieval_core.py` (alias separator, distincția menționare/ambiguitate/cerere de scope, rutare semantică globală implicită); `tests/test_multi_document_retrieval.py` (RED nou); `tests/test_retrieval_core.py` și `tests/test_api_integration.py` (adaptări trasabile ale politicii vechi după RED). Fără rescriere de arhitectură, query fan-out, reranking, model nou, schimbări R06/evaluator/gold, UI, schema DB, statusuri publice ori plafoane. O căutare în toate documentele eligibile nu garantează câte un rezultat din fiecare și nu pretinde evaluare a corpusului/modelului real.

Ordine: baseline și snapshot → Coder propune diff-ul și scrie numai regresiile noi → host RED → Planner verifică acordul cu D11 și cere lui Lucian orice decizie lipsă → același Coder implementează strict contractul confirmat → host focused/full și verificarea conservării testelor → QA + Reviewer read-only → predare. Fără modificare runtime înainte de aprobarea de etapă a Plannerului; aceasta nu poate suplini o aprobare de produs lipsă a lui Lucian.

Dovezi temporare: `C:/Users/Lucian-PC/AppData/Local/Temp/normativai-stabilizare-237e11d/multi-document/`. Păstrăm separat diff-ul acestui lot față de snapshotul R06, nu confundăm tot diff-ul necomis cu noua schimbare. Limita providerului/shell-ul defect se raportează, fără a pretinde o eroare a aplicației. Checkpoint GitHub după GREEN este aprobat de regula de trasabilitate din `AGENTS.md`; merge/DB real/API plătit/deploy rămân neaprobate.

**Valoare CV:** politici de retrieval conforme cu intenția utilizatorului, cu graniță explicită între context conversațional și autorizarea unui filtru; regresii care verifică atât sinteza multi-sursă, cât și proveniența.

### Pasul 1 — recunoașterea codurilor cu slash

Status: **APROBAT / TODO**, execuție suspendată de capacitate. Acoperă R01, fără a implementa D01/D02.

1. Coder scrie teste noi `alias_slash_regression` în `tests/test_retrieval_core.py` pe aliasurile catalogului: P 118/1-2025, P 118/2-2013, forme compacte și spații în jurul slash-ului.
2. Host rulează selecția înainte de modificarea runtime. Tester confirmă că eșecul vine din document nerezolvat, nu import/dependențe/colectare.
3. Coder aplică diff-ul minimal prezentat: `_ALIAS_SEPARATOR` admite `/` pe lângă whitespace/cratimă; fără schimbări SQL/status/provideri.
4. Testează separarea documentelor/partelor și anilor conform aliasurilor disponibile, limite alfanumerice și ambiguitatea existentă. Nu promitem rezolvarea tuturor aliasurilor scurte preexistente.
5. Demonstrează exact lookup cu document corect și zero embedding. Conform D11, simpla recunoaștere a unui cod nu autorizează singură scope semantic; verificările scoped/no-fallback se aplică cererilor de restricție explicite, nu citărilor istorice.
6. Rulează focalizat, full suite, diff-check; QA și review independent; actualizează predarea.

Acceptare: RED real, GREEN real, lipsa regresiilor și niciun comportament nou pentru documente necunoscute. Cost/API/DB: zero în implementare și teste implicite.

### Pasul 2 — context conversațional și istoric coerent

Status: **AȘTEAPTĂ D01–D03 și brief separat**. Acoperă R02–R04 și partea de context din R24.

1. Planner prezintă un tabel de scenarii înainte/după: document explicit, articol fără document, context unic, context multiplu, cod necunoscut, istoric redeschis, istoric șters.
2. Lucian aprobă rezultatul vizibil, statusul și efectul quota pentru fiecare scenariu nou.
3. Coder scrie întâi regresiile, apoi modifică strict parser/retrieval/UI necesare; nicio schimbare globală de fallback fără decizie.
4. QA rulează conversații complete: document A → continuare → document B → continuare; articol exact; refuz → replay; conversație veche redeschisă peste alta.
5. Verificare browser real pentru istoricul/contextul afișat, pe desktop și mobil; nu doar prezența unui șir JS.

Acceptare: sinteză multi-document implicită conform D11, fără atribuirea greșită sau ignorarea unei restricții explicit cerute; exact lookup respectă contractul aprobat; UI și contextul trimis coincid; refuzul exclus nu reintră prin replay. Filtrarea automată după citări nu este o remediere acceptabilă.

### Pasul 3 — import manual sigur al unui PDF

Status: **AȘTEAPTĂ D04/D06 și brief de implementare**. Acoperă R07/R08/R10/R11/R13/R14/R25 pentru documente noi.

1. Inspectăm ruta disponibilă. Alegem între reutilizarea funcțiilor insert-only și un entrypoint punctual minim; nu instalăm watcher/scheduler.
2. Definim raportul local: SHA/fișier, cod/titlu/an detectate, stabilitate fișier, pagini procesate, articole/chunk-uri, fragmente omise, duplicate/conflicte, metadata ambiguă și motive de blocare.
3. Separăm validarea locală fără DB/Voyage de verificarea duplicatelor care poate necesita DB și de importul cu cost.
4. Validăm structuri sintetice și apoi PDF-ul real ales de Lucian. Fără texte normative/PDF-uri în Git sau rapoarte publice.
5. Pentru schema SHA: prezentăm diff SQL, efecte RLS/granturi, verificarea pe schemă izolată și rollback. Aplicare reală numai la aprobare separată.
6. Înainte de orice import real: identificare clară a țintei, duplicate, cost estimat și limită aprobată, verificări DB/TLS relevante, backup/recuperare potrivită operațiunii și tranzacție testată. Dacă acestea lipsesc, ne oprim la dry-run local.
7. La aprobarea DB/Voyage inserăm numai document nou și chunk-urile lui, atomic, `indexed_pending_validation`. Nu atingem documentele existente.
8. Validăm importul; Lucian aprobă separat eligibilitatea publică. Nu transformăm importul în aprobare.

Acceptare: un fișier explicit, dublurile fără apel Voyage, rollback fără rânduri parțiale, corpus existent neatins, raport suficient pentru decizia umană. Eșecurile providerului/costurile deja consumate sunt raportate, nu ascunse prin retry automat.

### Pasul 4 — integritatea corpusului și a reimportului

Status: **AȘTEAPTĂ D05/D06, acces la corpus și aprobări**. Acoperă R07–R09/R11/R12 și reconcilierea inventarului.

1. Cu aprobare, inventar read-only: documente/statusuri/chunk-uri, fișiere complete versus amendamente, coduri/titluri/ani și dubluri. Totalul de 10 nu dovedește conținutul fiecărui document.
2. Măsurăm acoperirea extracției și comparăm articolele cu originalele selectate; înregistrăm pagini/structuri pierdute fără publicarea textului.
3. Identitatea de import include textul, articolul și ordinea relevante; documentăm strategia/versionarea algoritmului dacă se schimbă chunking-ul.
4. Nu mai rezolvăm conflictele alegând tăcut textul mai lung. Politica aprobată decide raportare, blocare sau păstrare; teste pe contradicții și duplicate identice.
5. Stabilim explicit relația dintre modificarea conținutului și statusul approved. Nicio dezactivare, reaprobarea sau înlocuire în masă fără decizie.
6. Pentru remedieri reale: plan per document, diferențe vechi/noi, cost complet de re-embedding, backup, rollback și aprobare. Nu rulăm importerul pe toate directoarele.

Acceptare: articole/ordine schimbate nu sunt ignorate; conflictele sunt vizibile; metadatele citării corespund versiunii validate; inventarul actual este documentat cu data verificării, nu dedus din istoric.

### Pasul 5 — calitatea răspunsului și citării, măsurată

Status: **5A — VERIFICAT LOCAL, QA/REVIEW OK (10-09-2026)**. Subetapa evaluatorului este închisă local, fără integrare/deploy; R05/R06 nu sunt remediate. Lucian a aprobat varianta 1, evaluare înainte de mecanism nou de protecție. D07 este decis numai pentru setul local; pragurile evaluării reale, costul și soluția D08 rămân deschise. Evaluarea reală rămâne dependentă de corpus validat și buget. Acoperă R05/R06/R16/R17/R25.

Specificație 5A aprobată ca scope local: adăugăm `grounding_eval.py` (cazuri exclusiv fictive, candidate fixe și raport diagnostic) și `tests/test_grounding_eval.py` (teste ale evaluatorului). Fără modificări în `generation_core.py`, API, retrieval, quota sau SDK-uri. Etichetele așteptate și justificările se stabilesc din dovezile sintetice, nu se deduc din răspunsul serviciului. Raportul distinge afirmații nesusținute acceptate, răspunsuri corecte respinse și pasaje relevante lipsă din citatul public. Comanda diagnostic are exit nonzero dacă găsește astfel de probleme; testele infrastructurii pot trece fără să declare produsul sigur. Nu se introduce judecător semantic automat sau LLM suplimentar. Coder implementează; Tester verifică execuția/contabilizarea; Reviewer verifică etichetele, independența și absența schimbărilor publice. Fără pytest skip/xfail pentru a ascunde limitele.

Probele preliminare din 09-09-2026 au reconfirmat limitele validatorului, fără schimbări runtime. Ulterior au fost adăugate **19 cazuri sintetice** în `grounding_eval.py` și **34 de teste ale evaluatorului** în `tests/test_grounding_eval.py`. Serviciul public și testele preexistente sunt nemodificate; nu au existat DB/provideri reali.

Dovezi ale implementării, reconfirmate după clarificarea docstring-ului la 10-09-2026:
- Baseline host: **557 passed, 11 skipped, 1 warning**, exit 0.
- Teste evaluator: **34 passed**, exit 0; full suite: **591 passed, 11 skipped, 1 warning**, exit 0.
- Diagnostic: **19 cazuri, 19 apeluri fake, 17 rezultate `answered`, 2 refuzuri structurale**, zero erori de execuție.
- **10 candidați nepublicabili acceptați**, **0 candidați publicabili respinși**, **2 pasaje relevante omise**: **12 constatări în 11 cazuri**. Diagnosticul are **exit 1 intenționat**. `answered` aici nu înseamnă publicare reală prin HTTP/UI.
- QA și Reviewer: **OK pentru evaluator**, nu pentru rezolvarea R05/R06. Reviewer a verificat justificările fiecărui caz; nu a existat validare de expert uman de domeniu.
- Raport: `C:/Users/Lucian-PC/AppData/Local/Temp/normativai-stabilizare-237e11d/grounding-report.json`; loguri `grounding-focused.log`, `grounding-full.log`, `grounding-diagnostic.log`. Workflow: `49d43a49-3ff6-4f3c-8705-1d3e7a7973d7`.
- Coder a salvat clarificarea docstring-ului înainte de a atinge din nou limita providerului. Planner a verificat prin AST că logica este identică versiunii aprobate de Reviewer, iar testele sunt identice octet cu octet. Focused/full/diagnostic au fost rerulate pe fișierul final; rezultate neschimbate. Nu a fost necesară modificarea codului de către Planner.
- `pytest -q -rs`, exit 0: cele 11 omisiuni sunt explicate efectiv de absența corpusului local: 1 pentru I9, 8 pentru folderul `documente_noi`, 1 pentru I13 modificări și 1 pentru P118/2 modificări. Log: `grounding-final-skips.log`. O primă afișare a logului a eșuat din codarea consolei Windows; reluarea cu UTF-8 a trecut, fără schimbări în aplicație/teste.
- Hash final `grounding_eval.py`: `9e2aed89ec2d3fd6646c3df02df0dbdddc406af65e0f12b03c46eca55d3a80b6`; `tests/test_grounding_eval.py`: `cd4e4bb9f6dbd804c731f28548dc1fe14fd55d6d1ff255ddf751b5360764348c`.
- Gate-uri EVAL-01–EVAL-06 închise pentru acest scope. Niciun gate PROD nu este închis implicit. Fără commit/push, DB, apel plătit, migrare sau deploy.

**Limită de utilizare:** etichetele se aplică exact candidaților fixați. Un text rescris de un serviciu viitor trebuie reevaluat; acest instrument nu verifică semantic automat orice răspuns nou. Rezultatele nu sunt rata de eroare a modelului live. **R05/R06 și gate-ul de calitate pentru producție rămân deschise.**

1. Pregătim setul propus de 30 de întrebări, verificat manual de Lucian sau evaluator de domeniu. Minimum categorii: exact, parafrază, continuare, absent, ambiguitate, valori numerice, calcule și întrebări legitime despre metode/articole.
2. Înainte de prima rulare aprobăm rubricile, pragurile, numărul de repetări și bugetul. Nu alegem pragurile retrospectiv ca să treacă modelul.
3. Păstrăm separat evaluarea retrieval (document/articol/dovadă) de generation (fiecare afirmație susținută, valori/unități/condiții/excepții și citări).
4. Separăm teste de calibrare de exemplele rezervate pentru verificarea finală. Nu ajustăm numai pentru întrebările cunoscute.
5. Rulăm local mock pentru controlul codului; abia după aprobare evaluarea plătită și înregistrarea cost/latency. Păstrăm versiuni model/prompt/corpus/config fără secrete.
6. Reparăm erorile demonstrate: selecția pasajului citat, prompt/context sau alte mecanisme minimale. Un al doilea LLM nu devine automat arbitru al adevărului.
7. Remediem falsurile clasificatorului de calcul cu regresii pentru cereri legitime și interzise; stabilim acoperirea lingvistică publică, fără promisiune de regex universal.
8. Re-rulăm setul afectat și evaluarea finală; raportăm toate erorile, nu doar exemplele reușite.

Acceptare propusă, de aprobat: zero erori critice observate pe setul de acceptare (document greșit, număr/obligație nesusținută, calcul executat contra contractului, citare care nu susține afirmația). Pragurile pentru acuratețe/refuzuri false/latency/cost sunt încă nefixate. Un set de 30 oferă o bază inițială, nu garanție universală.

### Subetapa 5B — R06, contract propus pentru pasajul selectat

Status: **VERIFICAT LOCAL / QA ȘI REVIEWER OK (11-09-2026)**. Cele 7 gate-uri locale R06 sunt închise. Coderul a salvat modificările înainte de limita providerului; gazda a executat verificările, iar Planner a acceptat predarea după ambele verdicte independente. Fără commit/push/deploy.

Dovezi de reluare:
- RED pe codul inițial: **133 failed, 18 passed**, exit 1, prin aserțiuni, nu collection errors.
- Snapshot curent: **402 focused passed**, **761 full passed, 11 skipped, 1 warning**, exit 0. Testele anterioare sunt păstrate ca nume; adaptarea aserțiunilor/fixture-urilor rămâne verificarea independentă a QA/Reviewerului.
- Aceleași 19 cazuri, candidați și gold: **0 pasaje relevante omise**, **0 candidați publicabili respinși**, **0 erori de execuție**; **10 candidați nepublicabili acceptați** rămân R05. Diagnostic exit 1, nu evaluare a modelului live.
- Dovezi: `C:/Users/Lucian-PC/AppData/Local/Temp/normativai-stabilizare-237e11d/r06/`, inclusiv `*.receipt.json` pentru comenzi/cwd/exit, rapoarte before/after și snapshoturi. Hash generation core: `47bcd5cde02a71c6ec8c4cc6eb316a45a653b7cb766cad2ac10960e12419d959`; evaluator: `2916bce94a45114ea0c4cc4198c8b8b343b25eb2f079866ee56a4df0a222d9e9`.
- Reviewer: **OK**, run `9d410cff-1c68-40d4-b5a4-d2e906232794`. QA: **OK** după reluarea finală `be7c1e58-6062-4fb1-b60d-15361d95d0db`; nu a fost nevoie de schimbări suplimentare de cod. La 11-09-2026 Planner a reconfirmat toate cele opt hash-uri față de snapshoturile revizuite, inclusiv `main.py` identic cu versiunea inițială.
- QA a verificat cele patru adaptări ale aserțiunilor/decoratorilor; funcțiile vechi sunt păstrate: generation 23/23, API 83/83, evaluator 26/26. Probe semantice suplimentare: trei cazuri invalide → 503 cu rollback quota și buget/rate păstrate, un caz valid trunchiat → 200 cu avertisment. Fiecare are un embedding, un generator și o rezervare de buget, toate mockuite.
- Rapoarte finale: `C:/Users/Lucian-PC/.pi/agent/sessions/--D--Omnia-MVP-context-safe--/subagent-artifacts/outputs/9d410cff-1c68-40d4-b5a4-d2e906232794/r06/review-resumed.md` și `C:/Users/Lucian-PC/.pi/agent/sessions/--D--Omnia-MVP-context-safe--/subagent-artifacts/outputs/e2296533-9f0a-4446-a6c7-66e51761ac7e/r06/qa-resumed.md`.
- Explicația codului, pentru începător: [`docs/R06_CODE_WALKTHROUGH.md`](docs/R06_CODE_WALKTHROUGH.md). Fără operațiuni externe/publicare; fără agenți activi la predare.

Aprobări: modelul indică pasajul exact; backendul verifică existența în dovada cu ID-ul citat și construiește metadata oficială. Lipsă/invalid → HTTP 503, rollback quota verificat, fără retry provocat de această eroare. Costul deja consumat și rate limit-ul rămân; fără fallback la prefixul fragmentului. Nu se schimbă implicit retry-ul existent pentru referințe normative inventate, retry-urile SDK, quota, DB sau modelul. Nu se aprobă apeluri reale.

**Schemă internă a lotului aprobat:** modelul întoarce JSON cu `raspuns` (text) și `pasaje` (listă de perechi `id`, `citat`). De exemplu, exclusiv sintetic:

```json
{"raspuns":"Carcasa fictivă este turcoaz. [C1]","pasaje":[{"id":"C1","citat":"Carcasa fictivă este turcoaz."}]}
```

- Contractul public existent `status/raspuns/citari/intrebari_ramase` rămâne. JSON-ul intern nu ajunge ca text brut la client.
- Pentru fiecare ID folosit în răspuns trebuie un pasaj nevid, asociat exact acelei dovezi. Identificatori necunoscuți, dublați, tipuri greșite, mapare lipsă sau payload malformat sunt erori de validare.
- Păstrăm plafonul existent de 600 caractere/citat. Pasajul declarat trebuie să fie subșir literal al dovezii corespunzătoare; nu îl construim din bucăți și nu înlocuim cu prefix. Nu normalizăm sau reparăm citatul: spațiile/diacriticele trebuie să existe exact în dovadă. Schema acceptă numai cheile stabilite; cheile JSON duplicate și ID-urile canonice duplicate sunt respinse. ID-urile păstrează compatibilitatea case-insensitive a citărilor existente, fără coliziuni `C1`/`c1`. Pasajele trebuie să corespundă ID-urilor folosite în răspuns, fără date suplimentare publicate implicit.
- Backendul continuă să impună metadata și ID-urile; providerul nu controlează titlul/codul/articolul public.
- Validarea pasajelor are loc înaintea publicării și înainte de orice retry de generare provocat de alte validări. Un pasaj invalid nu trebuie să ajungă la un retry suplimentar pe altă rută.
- Verificarea dovedește proveniența textului, **nu relevanța semantică sau susținerea fiecărei afirmații**. R05 rămâne separat.
- Același apel de generare furnizează text și pasaje. Nu propunem al doilea model sau apel suplimentar; pasajele consumă totuși tokeni în plafonul existent de 1.200. Efectul asupra lungimii și costului real trebuie măsurat ulterior, cu aprobare; nu pretindem cost identic.

**Trunchiere aprobată de Lucian:** păstrăm `TRUNCATION_NOTICE` pentru un payload JSON complet valid cu semnal de trunchiere; JSON incomplet sau pasaj invalid → 503, fără reparare/ghicire/retry. Nu mărim plafonul de 1.200 tokeni și nu schimbăm schema publică.

**Plan de diff propus:** `generation_core.py` pentru prompt, parsare, validare și citatul public; `main.py` numai dacă integrarea contractului tipat o cere; teste unitare și API pentru noile date structurate și efecte quota; adaptare explicită a candidaților evaluatorului local, fără introducerea gold-ului în generator.

**Protecția testelor/evaluatorului:**
1. Adăugăm mai întâi regresii R06: pasaj relevant după poziția 600, pasaj prezent numai în altă dovadă, lipsă/duplicat/necunoscut/gol/prea lung, JSON invalid și trunchiere.
2. Păstrăm verificările existente de unknown citation, referințe normative inventate, cost/apeluri, quota, rollback și trunchiere conform deciziei aprobate. Adaptarea fixture-urilor la noul protocol nu este permisiune de a șterge/slăbi assertions.
3. Evaluatorul 5A nu trebuie să devină artificial verde fiindcă toate fixture-urile vechi cu text simplu sunt respinse ca format invalid. Candidații sunt adaptați explicit la noul protocol, cu pasaje alese în datele de intrare, nu copiate automat din `required_passages`/gold în generator.
4. Cazurile R05 cu afirmație greșită dar citat literal valid rămân vizibile: nu confundăm remedierea R06 cu validarea sensului afirmației.
5. QA verifică RED/GREEN, regresiile API și lipsa retry-ului pentru pasaj invalid; Reviewer verifică maparea dovezii, schema, limitele și adaptarea onestă a evaluatorului. Testele rămân mockuite.

Gate de finalizare: niciun pasaj public fabricat sau luat din dovada greșită; cazul relevant dincolo de prefix este afișat fidel; toate eșecurile aprobate opresc răspunsul și urmează contractul quota; raportul R05 rămâne onest. Nu declarăm garanție semantică și nu publicăm fără aprobările separate.

### Pasul 6 — robustețe, conformitate și operare

Status: **PROPUS**, împărțit în taskuri independente, un singur Coder pe rând.

#### 6A. API, cost, TLS și proxy — R15/R16/R22

- Inventariem impliciturile SDK instalate și configurațiile runtime, fără afișarea secretelor.
- Aprobăm timeout-uri, retry-uri și comportamentul UI/API la expirare; configurăm explicit DB connect/query și providerii. Verificăm criptarea și verificarea certificatului/hostname-ului potrivit mediului.
- Testăm provider timeout, DB indisponibil, retry epuizat, rollback și concurență; nu dublăm costuri sau blocăm indefinit aceeași sesiune.
- Verificăm cu aprobare tabela/configurația reală de buget public și mecanismul fail-closed la lipsă/epuizare; distingem contoarele de plafonul financiar.
- Testăm controlat forwarded headers/proxy în infrastructura reală și rate limit fără trafic abuziv; setările nu se presupun corecte doar pentru că există în cod.
- Definim buget financiar operațional, monitorizare și acțiune la epuizare; acestea cer aprobarea lui Lucian.

Acceptare: timpul de eșec este mărginit, eroarea este sigură, quota/cost urmează contractul, nu se expun excepții/secrete, iar protecțiile sunt confirmate pe configurația țintă.

#### 6B. UI, privacy, termeni și licențe — R18/R19/R24/R26

- Mapăm browser → backend → Voyage/Anthropic/hosting și datele efectiv transmise/păstrate.
- Corectăm afirmațiile despre istoric, HMAC, IP și retenție; nu schimbăm comportamentul de colectare doar ca să se potrivească textului fără aprobare.
- Clarificăm PyMuPDF AGPL/comercial, drepturile PDF-urilor/extraselor și condițiile de utilizare înainte de comercializare; cerem specialist juridic unde este necesar.
- Adăugăm recuperare UI pentru cereri lente/blocate și verificăm formularul, quota, 403/429/422/503, JSON invalid și rețea întreruptă.
- Verificăm tastatură/focus, lizibilitate și mobil pe fluxul actual; nu pornim redesign.

Acceptare: informarea descrie realitatea, licențele relevante sunt clarificate, UI revine într-o stare coerentă după eșec și nu expune date tehnice/sensibile. Review-ul tehnic nu este aviz juridic.

#### 6C. Migrări, privilegii, backup și retenție — R20–R23

- Reconciliem inventarul SQL versionat cu schema reală și istoricul disponibil; documentăm baseline-ul pentru `documente_chunks` și rezolvăm controlat versiunea duplicată.
- Alegem backup care include schema, date, indexuri, secvențe și tabelele relevante inclusiv SHA dacă este aplicată; asigurăm snapshot consistent.
- Restaurăm într-un mediu izolat, niciodată peste producție pentru a „testa”; verificăm numere, FK, identități/hash-uri, embeddings, statusuri, indexuri și căutări reprezentative.
- Verificăm rol backend least-privilege, RLS/granturi publice, TLS și lipsa accesului direct client.
- Aprobăm retenția și jobul minimal de cleanup. Jobul pentru date expirate este independent de workerul PDF interzis la logon; nu se activează implicit.
- Stabilim RPO (pierdere de date acceptabilă), RTO (durată de recuperare), responsabilul și frecvența testării restaurării.

Acceptare: reconstrucție/restaurare demonstrată, rollback documentat, privilegii verificate și retenție realizabilă. Fișierul de backup singur nu închide taskul.

#### 6D. Observabilitate, release și întreținere — R23/R25/R28

- Monitorizare minimală: disponibilitate, erori, latență, apeluri/cost și epuizarea limitelor; fără întrebări/documente/secrete în loguri implicit.
- Runbook de incident: diagnostic, oprirea costului/controlul accesului conform contractului, rollback la SHA cunoscut, verificare și comunicare.
- Stabilim responsabilul alertelor și intervalul de observație după release; fără infrastructură enterprise inutilă.
- Pregătim gate-ul final din secțiunea 8 și o procedură de actualizare a corpusului/modelului fără pierderea evaluării.

Acceptare: un incident simulat într-un mediu sigur poate fi detectat și gestionat; dovezile leagă release-ul de SHA/config/corpus, nu de „ultimul build”.

## 7. Contractul echipei și al fiecărui task

### Roluri

| Rol | Responsabilitate | Interdicții |
|---|---|---|
| Planner | Scope, decizii, aprobări, arbitrarea findings, validarea dovezilor, coordonare. | Nu deleagă decizii de produs; nu devine writer de implementare în paralel cu Coder. |
| Coder | Un singur obiectiv, implementare și teste de regresie în worktree desemnat. | Fără subagenți, fără alte worktree-uri, fără operațiuni externe neaprobate. |
| Tester/QA | Reproduce, verifică teste/ramuri și raportează lipsuri; read-only în proiect. | Nu repară codul și nu slăbește teste. |
| Reviewer | Review independent corectitudine/arhitectură/securitate/cost/scope. | Nu dublează QA și nu implementează decizii de produs. |

Maximum patru roluri live. Refolosim agenții/worktree-ul, dar verificăm că reluarea păstrează contextul corect. La limită de provider oprim, păstrăm fișierele și cerem decizia lui Lucian; nu schimbăm automat providerul și nu repetăm lansări care vor eșua.

PowerShell și Python au trecut preflight pe gazdă (Python 3.14.6 în baseline-ul local). CI folosea Python 3.13; această diferență trebuie luată în calcul. Agenții nativi folosiți aveau `bash`, cu WSL indisponibil: comenzile sunt executate de gazdă și logurile date Testerului. Nu prezentăm acest lucru ca execuție personală a agentului.

### Fișa obligatorie înainte de editare

1. ID Rxx și un singur rezultat urmărit.
2. Branch/HEAD/worktree și fișierele permise.
3. Comportament înainte/după, valori implicite, efect DB, filtre, cost/API și funcții neconectate.
4. Deciziile/aprobările de care depinde taskul.
5. Diff/plan de modificare înainte de schimbările importante.
6. Test RED pentru bug; verificări GREEN și criterii independente de acceptare.
7. Riscuri, rollback și condiția de oprire.

### Bucla de execuție

`intent → spec aprobată → plan/diff → RED → build → GREEN → QA → review → predare → gate separat de publicare`

- Folosim `ai-native-sdlc`; la etape majore revalidăm skill-urile relevante, nu la fiecare editare mică. Supabase cere skill-urile locale specifice; dacă lipsesc din worktree, nu pretindem că sunt disponibile acolo.
- Coder explică fiecare linie runtime nouă/modificată la nivel începător; testele și modificările de documentație sunt explicate proporțional. Marcăm valoarea CV fără a exagera garanțiile.
- Finding-ul Reviewerului se clasifică: introdus de task/preexistent, blocker/neblocker, remediere tehnică/decizie de produs. Ultima categorie revine la Lucian.
- Orice fix schimbă starea revizuită: se refac testele relevante și review-ul zonei afectate. Nu raportăm rezultate de pe un diff anterior ca validare a celui nou.
- Dacă o eroare revine, adăugăm regresie și regulă de lucru adecvată; nu doar încă un review identic.
- Cerința de checkpoint la maximum 25 minute nu anulează interdicția de push neaprobat. Cerem aprobarea din timp; dacă lipsește, predăm starea și oprim extinderea taskului, fără publicare automată.

### Comenzi locale de referință, nu autorizație de execuție externă

Rulate în worktree-ul exact și cu dependențele verificate; comenzile/scripturile se inspectează înainte de rulare.

```text
git status --short
git diff --check
git diff --name-only
git diff --cached --name-only
python -m pytest -q tests/test_retrieval_core.py -k alias_slash_regression
python -m pytest -q tests/test_retrieval_core.py tests/test_api_integration.py
python -m pytest -q
```

Selecția `alias_slash_regression` este pentru testele încă de creat: în starea actuală nu reprezintă un gate trecut. RED trebuie să eșueze prin assertion-ul bugului; „zero teste selectate”, eroare de import sau SDK indisponibil nu sunt dovadă RED.

## 8. Gate final: când putem spune „gata de producție”

Toate sunt **NEÎNCHISE** la redactare. Criteriile concrete și eventualele praguri propuse se aprobă înainte de release. Nu amânăm un blocker de siguranță sub eticheta „polish”.

| Gate | Dovadă obligatorie |
|---|---|
| PROD-01 — comportament | R01–R04 remediate conform deciziilor și D11: multi-document implicit, identitate corectă a citărilor, restricții numai când sunt cerute explicit și fără încălcarea lor ascunsă; fără blocare automată la documentele citate anterior. |
| PROD-02 — corpus | Inventar actual verificat, eligibilitate explicită și acoperire controlată pentru corpusul declarat; conflictele/omisiunile cunoscute rezolvate sau accesul/limitele decise explicit. |
| PROD-03 — ingestion | Import punctual testat, insert-only, duplicate fără cost și tranzacție atomică; aprobare publică separată; cale sigură de actualizare a conținutului aprobat. |
| PROD-04 — calitate | Evaluare reală pe configurația/corpusul candidate, cu rubrică/praguri aprobate și rezultate complete. Zero eroare critică deschisă cunoscută în scope-ul lansării. |
| PROD-05 — siguranță și cost | DB/provider timeout/retry, TLS/privilegii, proxy/rate-limit, quota/buget/fail-closed confirmate; plafon și alertare operațională aprobate. |
| PROD-06 — UI și confidențialitate | Browser desktop/mobil pe fluxuri normale și de eșec; istoricul descris corect; date/retention/provideri documentați; licențe și drepturi clarificate pentru utilizarea urmărită. |
| PROD-07 — recuperare | Backup consistent și restore izolat trecute, RPO/RTO aprobate, rollback/runbook și cleanup verificate. |
| PROD-08 — cod și review | CI pe SHA candidat, suite și skip-uri explicate, QA și Reviewer independenți, diff în scope, zero secret/corpus în fișiere publicate. |
| PROD-09 — aprobări | Lucian aprobă separat commit/push conform scope-ului, integrare, migrările necesare, costul smoke și deploy-ul exact. Nicio aprobare nu se deduce din celelalte. |
| PROD-10 — post-deploy | SHA/deployment identificate, health/HTTPS/securitate și smoke funcțional aprobate; verificare paid E2E cu cost autorizat și observație în intervalul stabilit. |
| PROD-11 — predare operațională | Owner al alertelor/incidentelor, procedură de suport/rollback, limitări publice oneste și registru de riscuri reziduale acceptat de Lucian. |

### Ordinea release-ului

1. Pregătim SHA candidat și raportul QA/review, inclusiv cele șase categorii obligatorii: comportamente noi, implicituri, DB, filtre ascunse, cost/API, funcții neconectate.
2. Verificăm dependențele operaționale și planul de rollback înainte de schimbarea producției.
3. Cerem aprobările separate; nu rulăm comenzi Railway/Supabase înaintea lor.
4. Publicăm exact candidatul aprobat, nu un worktree cu modificări suplimentare.
5. Executăm smoke-ul aprobat și verificăm efectele, costul și restaurarea quota unde contractul o cere. Un POST poate scrie contoare chiar fără provider; raportăm acest lucru.
6. Dacă un gate critic eșuează, oprim promovarea și urmăm rollback-ul aprobat. Nu declarăm „aproape gata” drept acceptare.
7. Actualizăm SHA live, dovada deploy, starea migrărilor și toate limitările în documentele de coordonare.

`/health` rămâne liveness simplu și fără provider plătit. Este corect să nu demonstreze singur funcționarea RAG; verificarea end-to-end este separată.

## 9. Ce NU construim acum și ce urmează după producție

Nu adăugăm implicit LangChain/LangGraph, agentic chunking, reranker, microservicii, Redis, orchestrare nouă, frontend nou sau funcții de cont/plată. Nu schimbăm modelul sau baza vectorială fără problemă măsurată. Nu activăm workerul ca să justificăm codul deja scris.

Overengineering-ul identificat se tratează prin reducerea scope-ului și reutilizare selectivă, nu prin ștergere neaprobată. Cazurile reale și operarea sigură au prioritate față de numărul de features.

**După producție: AȘTEAPTĂ CLARIFICAREA lui Lucian (D10).** Nu este încă stabilit dacă următoarea etapă este monetizarea, validarea pieței, extinderea corpusului sau dezvoltarea comercială. Nicio funcție din această etapă nu intră în stabilizare pe ascuns.

Întreținerea este necesară indiferent de direcția comercială: monitorizarea incidentelor/costului, actualizarea dependențelor, verificarea restaurării și re-evaluare la schimbarea corpusului/modelului/promptului. Frecvențele se stabilesc explicit, nu se inventează acum.

## 10. Jurnal și următoarea acțiune exactă

| Data | Eveniment | Rezultat |
|---|---|---|
| 09-09-2026 | Audit main `237e11d` și probe locale/live limitate | Constatările R01–R28; fără modificări DB/producție; verdict pregătire producție blocată. |
| 09-09-2026 | Lucian aprobă pornirea planului: 0, apoi 1 | Worktree separat creat; baseline 557/11/1; Coder modifică șase documente. |
| 09-09-2026 | Providerul oprește Coderul la limita de utilizare | Fișiere păstrate, QA/review neîncepute, runtime/teste nemodificate. Estimarea de reset din eroare nu este o verificare actuală de cotă. |
| 09-09-2026 | Lucian cere `revizii.md` | Planner redactează acest registru și adaugă legătura de predare în TASKS; fără relansare agenți sau implementare runtime. |

**Actualizare 09-09-2026:** Lucian cere începerea cu problemele cele mai complicate. Prioritate 5A/R05–R06: șase probe locale, inclusiv control pozitiv, reconfirmă limitele validatorului și ale citatului-prefix. Fără schimbări runtime sau API real.

**Actualizare aprobare:** Lucian a aprobat explicit varianta 1 — set local de evaluare, fără DB sau costuri API. Mecanismul viitor de protecție și evaluarea reală nu sunt aprobate implicit.

**Actualizare 10-09-2026:** 5A finalizat și verificat local: 19 cazuri, 34 teste noi, 591 passed/11 skipped, QA și Reviewer OK; clarificarea finală doar documentară reverificată prin AST și rerulări. Nicio remediere publică implementată.

**Actualizare 11-09-2026 — R06 închis local:** 402 teste focalizate și 761 complete trecute, 11 omise pentru corpus absent; QA și Reviewer OK; toate cele opt fișiere revizuite reconfirmate neschimbate. Pasajele omise sunt 0/5 cerințe, pe aceiași 19 candidați. Cele 10 afirmații nepublicabile acceptate rămân R05. Nu există validare de expert uman/model live sau deploy.

**Actualizare după discuție, 11-09-2026:** Lucian aprobă D11 (multi-document implicit, restricții numai la solicitare explicită) și cere reluarea. Următoarea acțiune este lotul D11/2A de mai sus, cu baseline/contract/RED înainte de runtime. Oprirea după R06 a fost respectată și este înlocuită pentru acest lot; nu autorizează celelalte restanțe sau publicarea.

**Punctul de oprire actual:** 5A și 5B/R06 verificate local, lucrul necomis/nepublicat. R05, review-ul separat al pasului 0, R01 și celelalte restanțe/gate-uri de producție rămân deschise. Implementarea R06 nu autorizează push, merge, DB, apeluri plătite sau deploy. Discuția a autorizat ulterior numai lotul D11/2A: baseline reconfirmat 761 passed/11 skipped, workflow `ad822a9f-d64d-4aab-9b08-733390e2882b` pentru contract/RED înainte de runtime și review. Workflow-ul a eșuat înainte de salvarea testelor, la limita Codex. Nicio verificare RED/GREEN pentru D11 nu există. Predarea verificată și acțiunile de reluare sunt în `HANDOFF.md`; D11 rămâne blocat, R06 verificat local, R05 deschis.
