# NormativAI — registrul deciziilor aprobate

Acest fișier separă deciziile explicite ale lui Lucian de propunerile agenților. O propunere nu devine comportament de produs până când Lucian nu o aprobă.

## Decizii active

### D17 — commit incert la importer, aprobat Lucian (11-09-2026)

Dacă `connection.commit()` ridică o eroare, Lucian aprobă statusul local terminal `commit_unknown`. Importerul nu declară rollback garantat și nu reîncearcă automat sau manual același `--commit`. Operatorul păstrează PDF/report/metadata neschimbate și face obligatoriu o reconciliere DB **read-only**, după SHA/document/cod, înainte de orice decizie ulterioară. Un rezultat existent oprește reluarea; un rezultat absent necesită o nouă aprobare explicită de la Lucian pentru o nouă comandă `--commit`. Această decizie nu aprobă o conexiune DB reală, Voyage, `approved`, deploy sau migrare.

### D16 — importer persistent manual, aprobat Lucian (11-09-2026)

Lucian aprobă contractul din `docs/MANUAL_INGESTION_IMPORT_SPEC.md`: metadata locală explicită, dry-run fără DB/Voyage implicit și `--commit` explicit pentru un document nou, insert-only, cu status exclusiv `indexed_pending_validation`. Importerul verifică reportul/SHA/metadata, refuză identități existente înainte de Voyage, păstrează lock DB în tranzacție pentru a evita costuri duplicate și nu face retry automat. La eșec, DB face rollback; un apel Voyage deja acceptat poate rămâne facturabil fără persistență. Nu se aprobă update/delete/reimport, migrare nouă/aplicare, worker/scheduler, `approved`, DB/Voyage real, deploy sau publicare prin această decizie.

### D15 — preflight manual pentru un PDF, aprobat Lucian (11-09-2026)

Lucian aprobă implementarea locală a preflight-ului din `docs/MANUAL_INGESTION_PREFLIGHT_SPEC.md`: un PDF indicat explicit din `documente_noi/_inbox` produce un raport local fără text normativ, după extracție, verificarea stabilității SHA-256, validarea chunking-ului și identificarea strictă a candidaților unici de metadata. Preflight-ul nu importă, nu citește/scrie Supabase, nu apelează Voyage/Anthropic, nu modifică statusuri și nu activează workerul/schedulerul. Un rezultat local nu aprobă DB + Voyage sau publicarea; acestea rămân aprobări separate ale lui Lucian.


### D14 — negația exactă „nu doar din”, aprobată Lucian (11-09-2026)

Lucian alege opțiunea 1: expresia exactă **„nu doar din [cod]”** nu creează scope; ea păstrează căutarea multi-document globală implicită. Este un guard împotriva false scope-ului produs de subșirul „doar din”, nu un parser general de negații. Nu extindem automat regula la „nu numai”, „nu exclusiv”, alte poziții, case/spacing, negații multiple ori alte expresii; acestea rămân în afara lotului. Nu se schimbă schema, quota, DB sau providerii.

### D13 — cod explicit necunoscut, aprobat Lucian (11-09-2026)

Pentru „doar/numai/exclusiv din [cod necunoscut sau neaprobat]”, Lucian aprobă răspuns HTTP 200 cu statusul existent `ambiguous_reference` și mesajul de clarificare existent. Nu se face embedding, retrieval global, generare sau apel plătit. Cererea **consumă o întrebare din quota**, la fel ca celelalte cereri valide dar ambigue; tentativa rămâne în rate limit. Nu se adaugă un nou status public, nu se modifică schema, DB sau limitele.

### D12 — formele restricției explicite, aprobat Lucian (11-09-2026)

Lucian aprobă ca o restricție de document să fie recunoscută numai în întrebarea curentă prin formele finite: **„doar din [cod]”**, **„numai din [cod]”** și **„exclusiv din [cod]”**. Codul se rezolvă prin catalogul oficial de aliasuri aprobat; o simplă menționare a codului nu este restricție. Restricția nu persistă automat în următorul tur.

- Pentru un cod recunoscut/aprobat, căutarea semantică rămâne numai în documentul solicitat, fără fallback global ascuns.
- Pentru cod necunoscut/neaprobat, Lucian aprobă clarificare fără căutare globală ascunsă. **Mesajul/statusul public și efectul quota rămân D01 deschis**; nu le alegem tacit la implementare.
- Negații, formulări diferite, mai multe restricții și continuări după o restricție nu sunt suportate implicit; ele rămân de clarificat, nu devin scope dintr-un regex vag.
- Această regulă adaugă comportament public de retrieval, dar nu autorizează DB, apeluri plătite, commit/push, migrare sau deploy.

### D11 — multi-document implicit; reluare aprobată (11-09-2026)

Lucian confirmă explicit: **căutare multi-document implicită, cu restricții de document numai când utilizatorul le solicită explicit**. Scopul este răspunsul relevant și complet din documentația aprobată, nu evitarea răspunsurilor multi-sursă. La „please go on and proceed” autorizează reluarea lucrului local pentru această direcție după oprirea R06.

- Toate documentele `approved` sunt eligibile implicit pentru căutare; nu promitem citarea fiecărui document sau încărcarea întregului corpus într-un prompt.
- Întrebările anterioare ajută interpretarea continuării; codurile citate anterior nu creează singure un filtru obligatoriu. Simpla menționare a unuia sau mai multor documente nu înseamnă automat exclusivitate ori ambiguitate.
- O restricție cerută explicit rămâne respectată, fără extindere globală ascunsă. O citare/articol din documentul A nu se atribuie documentului B.
- D11 înlocuiește politica anterioară care restrângea implicit căutarea semantică după documentele numite/citate în context. **Codul existent încă implementează politica veche la momentul deciziei.**
- Detaliile încă neaprobate D01/D02 (document necunoscut, continuare de articol/ambiguitate, întinderea unei restricții în conversație) se semnalează înainte de modificarea acelor ramuri. D03/replay-ul UI rămâne separat.
- R06, eligibilitatea `approved`, quota, rate limit, schema publică, plafoanele de retrieval/context/generare și numărul de apeluri provider nu se schimbă implicit. Nici commit/staging/push, DB real, apel plătit, migrare sau deploy nu sunt autorizate prin reluare.


### 5B/R06 — pasaj indicat de model și verificat de backend (10-09-2026)

Lucian aprobă direcția 1: modelul indică pasajul exact, backendul verifică existența sa în dovada asociată citării, iar metadata oficială rămâne construită de backend. Aceasta nu garantează suportul semantic al tuturor afirmațiilor și nu închide R05. Lucian a ales apoi **varianta 1 pentru pasaj lipsă/invalid**: nu publicăm răspunsul, întoarcem HTTP 503 pe ruta existentă și restituim quota prin rollback verificat; fără reîncercare provocată de această eroare. Costul apelului deja efectuat și rate limit-ul rămân. Nu folosim prefixul de 600 caractere ca fallback. Retry-ul existent pentru referințe normative inventate și politica SDK nu sunt schimbate implicit. Lucian a confirmat și trunchierea: pachet JSON complet și valid cu semnal de trunchiere → răspuns cu avertismentul existent; pachet incomplet → 503, fără reparare/ghicire/retry. Planul intern este `raspuns` plus `pasaje[{id,citat}]`, cu validare strictă și citat literal de maximum 600 caractere din dovada asociată. Contractul public și plafonul de generare existent rămân; nu este autorizat un apel real/plătit. Implementarea locală și testele R06 pot începe conform specificației 5B din `revizii.md`.

### 5A — evaluare locală înainte de protecții noi, aprobat Lucian (09-09-2026)

Lucian aprobă varianta 1: set sintetic local de evaluare a afirmațiilor și citărilor, fără DB sau API plătit. Se adaugă evaluatorul și testele lui, nu un nou comportament în GenerationService/API. Etichetele au justificări din dovezile fictive; raportul trebuie să distingă limitele produsului de corectitudinea evaluatorului. Pragurile/calitatea modelului live, soluția viitoare de protecție și costurile rămân decizii separate. Această aprobare actualizează punctele de mai jos care încă descriu strategia locală ca nealeasă.

### Ordinea reviziilor — actualizare Lucian, 09-09-2026

- După planul consolidat `revizii.md`, Lucian a cerut începerea cu problemele cele mai complicate. Planner-ul prioritizează 5A/R05–R06: corectitudinea afirmațiilor și a citărilor, începând cu diagnostic local și specificație.
- Această actualizare înlocuiește ordinea inițială 0 apoi 1, nu anulează restanțele și nu autorizează implicit o schimbare de răspuns public, DB, API plătit sau publicare. D07/D08 rămân de decis.
- Lotul 0–1 descris mai jos este starea autorizării inițiale, nu un motiv de a ignora noua prioritate. Alegerea soluției de verificare cere aprobarea lui Lucian.

### Stabilizare și ingestion manual — decizie Lucian, 09-09-2026

- Lucian a renunțat la activarea workerului. Fluxul curent este: pune **un PDF** în `documente_noi/_inbox`, anunță Planner-ul, primește raport **local** de extracție/validare, apoi aprobă separat accesul DB + costul Voyage. Publicarea documentului prin `approved` este o aprobare separată, nu efectul implicit al importului.
- Importul manual sigur punctual **nu este încă livrat**. Alegerea fluxului nu declară `populare_db.py` insert-only și nu autorizează folosirea lui ca substitut sigur.
- Workerul integrat rămâne în cod, **inactiv**; scriptul și migrarea se păstrează. Task Scheduler este neinstalat și `20260909000000_document_ingestion_sources.sql` este neaplicată conform predării. Runbook-ul automat este referință istorică, nu recomandare de activare.
- Registrul SHA al PDF-urilor și pornirea la logon sunt decizii independente; niciuna nu este aprobată implicit pentru fluxul manual.
- Este autorizat numai lotul 0–1: mai întâi sursa de adevăr/documentația, apoi suport `/` în `_ALIAS_SEPARATOR`, pe lângă whitespace/cratimă, cu teste în `tests/test_retrieval_core.py`. Nu se modifică tratarea codurilor necunoscute, contextul, statusurile, DB sau providerii. Backlogul 2–6 din `TASKS.md` rămâne TODO și necesită aprobare separată înainte de execuție.
- Cele 10 documente `approved` sunt confirmarea istorică a lui Lucian; nu reprezintă audit DB nou și numărul curent de chunk-uri este necunoscut. Starea migrărilor se documentează numai la nivelul dovezilor istorice disponibile.
- **Valoare CV:** aprobări separate pentru validare locală, cost/persistență și publicare, cu trasabilitate fără automatizări activate implicit.

### Identitate și acces

- Brand public: **NormativAI**; Omnia rămâne numele intern al repository-ului.
- FastAPI este singurul client al Supabase.
- Browserul nu primește acces Supabase, fișiere normative, embeddings, chunk-uri brute sau endpoint de download.
- Ingestion-ul este controlat exclusiv de Lucian.

### Documente

- Documentele au statusurile `indexed_pending_validation`, `approved` și `disabled`.
- Retrieval-ul folosește numai documente cu status `approved`.
- Lucian a aprobat explicit documentele `np010_2022` și `np057_02`; statusurile au fost actualizate în Supabase, iar cele 694 chunk-uri au fost reconfirmate.
- Decizia este reproductibilă prin migrarea `20260831220000_approve_initial_documents.sql`, care verifică identitatea și nu aprobă alte documente.
- Lotul 2 (03-09-2026): Lucian a aprobat `i9_2022`, `p118_1_2025`, `p118_2_2013_modificari` și `spitale_2022`. Importul și aprobarea au fost executate direct pe Supabase înainte de versionare; migrarea `20260903120000_approve_second_batch_documents.sql` le înregistrează retroactiv, fail-fast pe identitate sau status incompatibil.
- **Istoric 03-09-2026, nu inventar curent:** normativul complet P 118/2-2013 fusese pus deliberat pe hold pentru un lot ulterior. Nu deducem acoperirea actuală din această înregistrare sau doar din totalul de 10 documente confirmat de Lucian.
- Orice document nou intră implicit în `indexed_pending_validation` și necesită aprobare explicită înainte să poată genera răspunsuri.

### Interfață (decizie Lucian, aprobată 04-09-2026)

- Cerința de „două propuneri vizuale comparate" a fost anulată la 03-09-2026; Lucian a dat direcția explicit.
- Paleta violet derivată din `ai.acquisition.com`, explorată pe 03-09-2026, este **abandonată**. Nu se mai folosește.
- **Direcție aprobată pe mockup vizual la 04-09-2026:** negru cu auriu, două straturi vizuale distincte.
  - Carcasa aplicației: interfață modernă întunecată, nav lateral stânga, chat box rotunjit, gradiente difuze.
  - Răspunsul: cules ca document tipărit, serif justificat, secțiuni numerotate, citări `[1]`/`[2]`, listă de surse.
- Motivul respingerii prototipului „Technical Paper" este acum documentat: a transformat **toată** aplicația în hârtie, în light mode, fără nav lateral și fără gradiente, adică inversul cerinței.
- Valorile exacte, tipografia și scara de spațiere sunt în `docs/UI_DESIGN_TOKENS.md`, sursa unică pentru implementare.
- Lucian a impus o listă explicită de pattern-uri interzise (glassmorphism, carduri cu bordură colorată la stânga, italice serif ca accent, em dash peste tot, Inter peste tot, contrast scăzut și altele). Lista completă este în `docs/UI_DESIGN_TOKENS.md` și **se aplică integral, nu selectiv**.
- Foaia răspunsului: decis la 04-09-2026, varianta **închisă** (`--ink-850`). Varianta „hârtie” a fost prototipată și respinsă; nu se implementează comutator.

### Retrieval și răspunsuri

- Referința explicită la articol folosește exact lookup înainte de semantic search.
- Un articol explicit inexistent returnează `not_found`; nu există fallback semantic ascuns.
- Duplicatele identice se deduplică după `content_hash`; texte diferite pentru aceeași pereche document/articol produc `ambiguous_article`.
- Căutarea semantică păstrează top-K, pragul și limita de context. **Ținta aprobată D11 (11-09-2026): multi-document implicit, restricție numai la solicitarea explicită a utilizatorului.** Politica veche, încă prezentă în cod la aprobarea D11, restrânge automat după documentul numit sau codurile citate anterior și nu are fallback global. Acea restrângere implicită este înlocuită ca decizie, nu deja remediată în implementare.
- Citările publice vor conține numai metadata oficială și citat limitat; niciodată `source_key`.
- Cererile de execuție a calculelor, estimărilor sau dimensionărilor de proiect sunt refuzate server-side, determinist și înainte de catalog, retrieval, Voyage sau Anthropic. Contractul este HTTP 200, `status: out_of_scope`, citări goale și mesajul: „NormativAI nu efectuează calcule sau dimensionări de proiect. Pot indica prevederile și datele cerute de normative.” Tentativa rămâne în rate limit, nu consumă quota de 10 și rollback-ul rezervării temporare este fail-closed. Întrebările despre metodă, formule, praguri, valori prescrise sau debit minim rămân eligibile; UI-ul păstrează refuzul vizibil în istoric, fără a-l trimite ca context ulterior.
- UI-ul MVP folosește exclusiv `POST /intreaba`: afișează inițial exact „Limită: 10 întrebări/browser”, apoi numai `intrebari_ramase` primit de la API, fără `localStorage` sau estimare locală. HTTP 403 afișează `detail` din server și blochează permanent formularul; HTTP 429 afișează `detail` și timpul aproximativ, validează strict `Retry-After` ca întreg pozitiv și blochează temporar exact acea durată; 422 are mesaj dedicat, iar 503 și erorile de rețea/JSON invalid au un singur mesaj generic, fără status sau excepții expuse.

### Cost și utilizare

- Testele implicite mockuiesc Supabase, Voyage și Anthropic; apelurile reale sunt opt-in.
- Utilizator anonim: maximum 10 întrebări totale per browser, cu cookie semnat și contor server-side.
- Nu există tier de tester, coduri sau conturi în MVP. Aplicația este publică și poate avea oricâți vizitatori; fiecare browser primește maximum 10 întrebări.
- Cei 4 testeri inițiali primesc direct același URL public și folosesc exact fluxul anonim, fără privilegii. Numărul lor nu este o limită tehnică sau de produs.
- Consecințe acceptate: identitatea anonimă nu poate fi revocată individual, ștergerea cookie-ului/alt browser poate reseta limita, iar utilizatorii de pe același IP împart rate limit-ul.
- Consumă quota: `answered`, `not_found`, `ambiguous_article` și `ambiguous_reference`.
- Nu consumă quota: input invalid, HTTP 503, eroare DB/Voyage/Claude sau cerere blocată de rate limit.
- Quota se rezervă atomic înainte de serviciile plătite și se restituie la eroare tehnică, pentru a controla cererile simultane.
- Decizie aprobată la 01-09-2026 (România): pentru MVP cu trafic redus, tranzacția quota rămâne deschisă pe durata apelului provider pentru a garanta rollback la eroare tehnică. Numai cererile simultane din același browser pot aștepta durata primei cereri; lock-ul rate limit per IP este scurt. Decizia se reevaluează înainte de scalare.
- Rate limiting per IP: maximum 5 cereri/minut și 30 cereri/oră, verificat înainte de Voyage/Claude.
- Cookie-ul anonim expiră după 1 an; quota de 10 rămâne asociată lui pe această durată.
- IP-ul nu este stocat brut; identificatorul pentru rate limiting este derivat prin HMAC-SHA-256 server-side, cu o cheie separată de cheia cookie-ului.
- `expires_at` face ca ferestrele IP să expire logic după 24 de ore și acestea nu mai sunt reutilizate. Ștergerea fizică în maximum 24 de ore nu este garantată încă: necesită un job separat, aprobat înainte de deployment; cerința țintă rămâne deferred.

## Regula de schimbare

Înainte de implementarea unei schimbări care afectează comportamentul public, datele eligibile, accesul, costul sau fallback-ul, Planner-ul trebuie să explice:

1. ce vede utilizatorul înainte și după;
2. ce date sau servicii sunt afectate;
3. riscurile și alternativele;
4. dacă există cost sau modificare persistentă;
5. ce rămâne neimplementat.

Schimbarea se implementează numai după aprobarea explicită a lui Lucian.
