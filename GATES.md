# Gate-uri — refuz calcule/proiectare

## MIP — preflight manual pentru un PDF (11-09-2026)

**OWNS:** `manual_ingestion_preflight.py`, `tests/test_manual_ingestion_preflight.py`, `docs/MANUAL_INGESTION_PREFLIGHT_SPEC.md`, `TASKS.md`, `GATES.md`, `PLAN.md`, `docs/DECISIONS.md`, documentația de rulare nouă.

- [x] **MIP-RED:** host, 11-09-2026: `python -m pytest -q tests/test_manual_ingestion_preflight.py` → 12 errors, exit 1, toate `ModuleNotFoundError: manual_ingestion_preflight`; runtime-ul lipsește intenționat. Testele mockuite descriu refuzul căii din afara `_inbox`, extensiei ne-PDF, PDF instabil, extracției/chunking-ului invalid, metadata lipsă/ambiguă și raport existent, plus absența dependențelor externe. Dovezi: `manual-ingestion/mip-red.{log,xml,receipt.json}`.
- [x] **MIP-LOCAL:** după finding QA, 13 teste focalizate trecute: PDF fixture valid produce numai raport JSON local cu hash, număr de pagini/caractere/chunk-uri, candidați metadata și status; raportul nu conține text/chunk-uri/embedding/secrete și nu se suprascrie. Pipeline-ul implicit parser/chunker/validator/candidați este testat; articolul neacceptat este refuzat. Dovezi `manual-ingestion/mip-qa-fix-focused.*`.
- [x] **MIP-BOUNDARY:** test static și inspecție host: `manual_ingestion_preflight.py` nu importă/apelează `psycopg2`, `voyageai`, `load_dotenv`, workerul automat sau `populare_db.py`; testul injectează dependențe externe interzise și ruta validă rămâne locală.
- [x] **MIP-REGRESSION:** host după fix QA: `python -m pytest -q tests/test_manual_ingestion_preflight.py` → 13 passed; `python -m pytest -q` → 975 passed, 11 skipped, 1 warning extern TestClient, exit 0. Testele metadata acoperă cod/titlu/an lipsă și ambiguu; nu sunt slăbite teste existente.
- [x] **MIP-CHECKPOINT:** diff inspectat, `git diff --check` curat, documentația explică pașii pentru începător, iar GREEN verificat este checkpointat pe branchul de lucru. SHA-ul remote este consemnat în predare.
- [ ] **MIP-REVIEW:** QA a găsit incompatibilitatea articolului și testul implicit lipsă; fixul este GREEN, deci re-QA read-only, apoi Reviewer separat. Aprobarea locală nu este aprobare DB + Voyage sau publicare.


## Lot D11 / 2A — multi-document implicit (11-09-2026)

**BLOCAT, 1/8 gate-uri îndeplinite:** Coderul a atins limita de utilizare înainte să salveze testele RED. Nu există schimbări de runtime D11, RED/GREEN sau review. Predarea [`HANDOFF.md`](HANDOFF.md) include pașii de reluare. Rerularea proaspătă a suitei vechi (761 passed/11 skipped) confirmă integritatea stării păstrate, nu îndeplinirea gate-urilor D11 rămase.

Scope/decizie: `revizii.md` lot D11/2A și `docs/DECISIONS.md`. CWD pentru comenzi: `D:/Omnia-MVP-stabilizare`. Evidențe și script host în directorul temporar `C:/Users/Lucian-PC/AppData/Local/Temp/normativai-stabilizare-237e11d/multi-document/`. Nu sunt gate-uri de producție. Execuția este staged: contract + RED, apoi confirmarea Plannerului înainte de runtime; nicio alegere D01/D02 nu se deleagă Coderului.

- [x] **MD-BASELINE:** snapshot înainte de cod/teste și suită implicită verde; fișierele R06 protejate și zero staged. Host: 761 passed, 11 skipped, 0 failed/errors, exit 0; dovezi `multi-document/baseline.receipt.json`, `baseline.xml`, `baseline.log` și `baseline-code.json`.
  CHECK: python -m pytest -q
  EXPECT: exit 0; rezultate/skip-uri și hash-uri salvate de host, fără DB/providers reali.
- [x] **MD-CONTRACT:** contractul D11–D13 este explicit și autorizat înainte de runtime: global implicit; citări/menționări nu filtrează; comparațiile de documente distincte nu sunt ambigue; slash recunoscut; numai „doar/numai/exclusiv din [cod]” curent restrânge; cod necunoscut → `ambiguous_reference`, fără dependențe, consumă quota/rate. Dovezi: `docs/DECISIONS.md` D11–D13, `revizii.md` lot D11/2A, `multi-document/runtime-authorized.txt`. D14 adaugă numai guard-ul exact „nu doar din [cod]” → global implicit; D02/D03 (alte negații, multiple scope, persistență, continuări de articol și replay UI) sunt excluse explicit, nu decise implicit.
- [x] **MD-RED:** regresiile noi eșuează pe runtime-ul inițial din motive comportamentale, nu import/colectare. Host, 11-09-2026: testele D11–D13 au **42 failures, 35 passed, 0 errors/skipped, exit 1**; dovezi `multi-document/red.log`, `red.xml`, `red.receipt.json`. Eșecurile sunt contractul neimplementat (scope automat vechi, comparații ambigue, slash și restricții explicite), nu colectare/import. Supliment D14/D12-history: host `-k "d14 or scope_curent"` → **5 failures, 77 deselected, exit 1**; receipt/log `multi-document/d14-red.*`. Prima invocare din cwd greșit (exit 4, fără teste) este păstrată separat ca receipt de infrastructură; rerularea corectă este singura dovadă RED. Testele noi sunt `tests/test_multi_document_retrieval.py`; runtime-ul rămâne needitat.
  CHECK: python -m pytest -q tests/test_multi_document_retrieval.py
  EXPECT: exit 1 înainte de runtime; scriptul host validează și salvează eșecurile/receipt-ul.
- [x] **MD-GLOBAL:** întrebări generale/comparații și context anterior fără filtre obligatorii după documentele menționate/citate; dovezi multi-sursă păstrate când sunt relevante și în limite. Host GREEN: 515 teste focalizate trecute; verifică global/scoped, dovezi și embedding. Nu promite relevanța semantică live/R05.
  CHECK: python -m pytest -q tests/test_multi_document_retrieval.py
  EXPECT: exit 0 după implementare; aserțiuni pe apelul global/scoped, dovezi și embedding.
- [x] **MD-IDENTITY:** coduri slash/spații/ani/părți corecte, aliasuri realmente ambigue tratate distinct de două documente menționate; exact lookup și scope explicit fără substituție/fallback ascuns, conform scenariilor aprobate. P1 exact-article remediat: articolul cunoscut nemarcat/marker după cod complet păstrează `find_exact` fără embedding; `NP 010 2099` rămâne `ambiguous_reference`. Host: 105 focused passed, 962 full passed/11 skipped.
  CHECK: python -m pytest -q tests/test_retrieval_core.py tests/test_multi_document_retrieval.py
  EXPECT: exit 0; controale pozitive și negative, fără relaxarea contractelor neaprobate.
- [x] **MD-API:** schimbarea ajunge la API, metadata/citările R06 rămân corecte, quota/rate/buget și numărul de apeluri nu se schimbă implicit. P1 exact-article API regression verifică nemarcat/marker, exact hit/miss, fără semantic/embedding și contractul quota/rate/citare. Host focused: 105 passed.
  CHECK: python -m pytest -q tests/test_api_integration.py tests/test_citation_passages.py
  EXPECT: exit 0; numai mock-uri; zero adaptări de test care maschează defecte.
- [x] **MD-REGRESSIONS:** full suite verde, fără noi skip/xfail și cu maparea explicită a testelor politicii vechi adaptate la D11; fișierele din afara scope-ului neschimbate. P1 exact-article GREEN: **962 passed, 11 skipped, 0 failures/errors**, exit 0; un warning extern Starlette/httpx. R06/5A rămân protejate. Re-review P1 încă necesar.
  CHECK: python -m pytest -q
  EXPECT: exit 0; comparație de snapshot și diff pentru acest lot, testele și gold-urile R06/5A protejate.
- [x] **MD-REVIEW:** QA P1 **OK** și re-review P1 **OK** pe `0f9540b`, fără findings. Dovezi host inspectate: 105 focused/962 full passed, 11 skip-uri; repro exact/no embedding și 2099 fail-closed. D11–D14 este acceptat **local**. D01/D02/R02–R04 rămase se raportează separat. Fără merge/DB/API plătit/deploy.

**Închidere MD locală, 11-09-2026:** 8/8 gate-uri locale. Checkpointuri: implementare `bf9e16b`, P1 numeric `ee14516`, P1 exact-article `0f9540b`; QA P1 `c55719f`, review P1 final OK. Nu este gate de producție: R05, D02/D03, corpus/model/DB real, ingestie, operațiuni și deploy rămân deschise.

## Lot 5B — R06, verificat local și închis la 11-09-2026

Contract aprobat în `revizii.md` §5B și `docs/DECISIONS.md`. Un singur writer; fără modificare DB, API real, staging/commit/push/deploy.

- [x] **R06-RED:** teste noi în `tests/test_citation_passages.py`, înainte de runtime; `python -m pytest -q tests/test_citation_passages.py` eșuează prin aserțiuni ale problemei, nu prin importul unui simbol încă inexistent.
- [x] **R06-PASSAGES:** JSON strict, ID folosit ↔ pasaj unic nevid de maximum 600 caractere ↔ subșir literal al dovezii corecte; fără prefix fallback, quote repair, chei duplicate sau leak de metadata.
- [x] **R06-FAILURE:** pasaj lipsă/invalid sau JSON incomplet → 503, rollback quota verificat, fără retry provocat de această eroare; costul consumat/rate limit rămân; erorile rollback rămân fail-closed.
- [x] **R06-TRUNCATION:** pachet complet/valid cu semnal de trunchiere → răspuns cu avertisment; incomplet → 503. Plafonul de generare și schema publică neschimbate.
- [x] **R06-REGRESSIONS:** focused + full suite locale trec; testele anterioare și aserțiunile lor sunt păstrate, cu adaptare explicită de fixture/protocol, fără skip/xfail sau mascarea cazurilor negative. Retry-ul existent pentru referințe normative inventate rămâne verificat separat.
- [x] **R06-EVALUATOR:** cele 19 cazuri inițiale păstrează identitatea și gold-ul. Intrarea nouă include pasaje explicite, independente de câmpurile gold; falsurile semantice cu citat autentic rămân vizibile. Zero pasaj relevant omis și zero candidat valid respins din cauza protocolului pe setul adaptat; nu raportăm R05 rezolvat.
- [x] **R06-REVIEW:** QA și Reviewer independenți pe snapshotul final; diff limitat la fișierele aprobate, zero staged, predare completă și explicația codului. Nicio integrare/publicare implicită.

**Închidere 11-09-2026:** RED 133 failed/18 passed (exit 1 înainte de runtime); GREEN 402 focused passed, 761 full passed/11 skipped/1 warning (exit 0). Diagnostic pe aceleași 19 gold-uri: 0 pasaje omise/0 candidați valizi respinși/0 erori, dar 10 publicări neconforme R05 (exit 1). Patru probe mockuite suplimentare pe ruta semantică au trecut. QA și Reviewer OK; comparația AST a celor patru adaptări de teste a fost acceptată de QA. Planner a reconfirmat la închidere hash-urile celor opt fișiere față de snapshoturile revizuite; `main.py` este neschimbat. `r06/*.receipt.json`, `qa-preservation-comparison.json` și `qa-semantic-probes.json` păstrează dovezile în directorul temporar indicat în `revizii.md`. Explicația codului este în `docs/R06_CODE_WALKTHROUGH.md`. Sunt închise 7/7 gate-uri R06 locale, nu gate-urile de producție. Fără staged/commit/push/deploy. Oprire după predare la cererea lui Lucian.

## Lot verificat 5A — evaluator local afirmații/citări (09-09-2026)

Scope aprobat: numai `grounding_eval.py`, `tests/test_grounding_eval.py` și predarea documentară. Cazuri exclusiv sintetice; fără validator public nou, DB/provideri, commit/push/migrare/deploy. Gate-urile 0–1 de mai jos rămân deschise, nu sunt înlocuite ca obligații.

- [x] **EVAL-01 — etichete independente:** fiecare caz are identitate unică, dovezi fictive, candidat fix, așteptare și justificare; Reviewer validează separat textul, nu preia drept adevăr verdictul runtime.
- [x] **EVAL-02 — infrastructură:** `python -m pytest -q tests/test_grounding_eval.py` trece, inclusiv controale evaluator negativ/pozitiv; fără skip/xfail și fără enshrinement al unui bug de produs ca rezultat permanent obligatoriu.
- [x] **EVAL-03 — diagnostic onest:** `python grounding_eval.py --output <cale-temporară-aprobată>` produce raport reproductibil și exit nonzero când găsește candidat nesusținut acceptat, candidat susținut respins ori pasaj cerut lipsă. Raportul măsoară numai candidați ficși sintetici, nu rata de eroare a modelului live.
- [x] **EVAL-04 — regresii:** `python -m pytest -q` trece; skip-urile istorice sunt raportate distinct, nu ascund erori noi.
- [x] **EVAL-05 — limite:** diff-check trecut; hash-urile fișierelor runtime publice neschimbate; numai fișierele autorizate și documentația deja prezentă sunt modificate; nimic staged.
- [x] **EVAL-06 — QA/review:** rapoarte read-only independente pe același snapshot final; problemele de produs R05/R06 rămân deschise indiferent de trecerea testelor evaluatorului.


**Dovezi de închidere EVAL, 10-09-2026:** worktree `D:/Omnia-MVP-stabilizare`, baza `237e11d`; 34 focused passed (exit 0), 591 full passed/11 skipped/1 warning (exit 0), diagnostic 19 cazuri/12 constatări în 11 cazuri (exit 1 intenționat, zero erori de execuție). QA și Reviewer OK pe snapshotul inițial. Clarificarea finală numai în docstring are AST executabil neschimbat și teste identice; host a rerulat toate verificările. SHA256 final evaluator `9e2aed89ec2d3fd6646c3df02df0dbdddc406af65e0f12b03c46eca55d3a80b6`, teste `cd4e4bb9f6dbd804c731f28548dc1fe14fd55d6d1ff255ddf751b5360764348c`. Loguri în directorul temporar `normativai-stabilizare-237e11d` indicat în `revizii.md`: `grounding-focused.log`, `grounding-full.log`, `grounding-diagnostic.log`, `grounding-final-docstring-check.log`, `grounding-final-skips.log`; rapoarte QA/review în workflow `49d43a49-3ff6-4f3c-8705-1d3e7a7973d7`. `git diff --check` trecut, whitespace/UTF-8 pentru fișierele noi verificate separat, nimic staged. R05/R06 și toate gates PROD rămân deschise.

## Lot 0–1 — stabilizare coduri normative (09-09-2026)

Secțiune nouă; gate-urile pentru refuzul calculelor de mai jos rămân istoric și nu se înlocuiesc. Pentru acest lot, singurul worktree autorizat este `D:/Omnia-MVP-stabilizare`, branch `fix/stabilizare-coduri-normative`, bază `origin/main` la `237e11d`. Comenzile istorice către alt worktree nu se folosesc.

- [ ] **Documentație coerentă, verificare manuală:** cele șase fișiere ale pasului 0 disting codul integrat de deploy-ul verificat anterior, confirmarea istorică a catalogului de auditul DB, workerul inactiv de importul manual încă nelivrat și migrările documentate aplicate de cele neaplicate/neverificate.
- [ ] **Regresie înainte de runtime:** host-ul rulează `python -m pytest -q tests/test_retrieval_core.py -k alias_slash_regression` după adăugarea testelor, dar înainte de schimbarea `_ALIAS_SEPARATOR`; eșecul așteptat trebuie documentat ca eroare de recunoaștere slash, nu de mediu sau colectare. După fix, aceeași selecție trebuie să treacă.
- [ ] **Teste focalizate retrieval + API:** host-ul rulează `python -m pytest -q tests/test_retrieval_core.py tests/test_api_integration.py`; fără schimbări de coduri necunoscute/context/status/DB/provideri și fără slăbirea testelor.
- [ ] **Full suite mock:** host-ul rulează `python -m pytest -q`; fără opt-in la teste externe/plătite.
- [ ] **Diff și index:** host-ul verifică `git diff --check`, `git diff --name-only`, `git status --short` și `git diff --cached --name-only`; numai fișierele autorizate, nimic staged.
- [ ] **Review independent:** Reviewer și Tester/QA read-only dau verdict separat pe diff-ul final și dovezile host; orice finding de produs cere aprobare, nu remediere implicită.
- [ ] **Zero operațiuni externe:** fără DB, rețea/provider API, ingestion, migrări, scheduler, stage/commit/push/merge/deploy; fără acces la secrete.

Baseline disponibil, **nu gate final**: logul host `C:/Users/Lucian-PC/AppData/Local/Temp/normativai-stabilizare-237e11d/baseline.log` raportează `557 passed, 11 skipped, 1 warning` (TestClient). Nicio bifă de mai sus nu este închisă prin acest baseline. Coder-ul nu a executat personal comenzile.

## Gate-uri istorice — refuz calcule/proiectare

## Rezultate observabile

1. `POST /intreaba` detectează local, determinist și conservator cererile de execuție a unui calcul, estimări sau dimensionări și răspunde HTTP 200 cu statusul, mesajul și citările aprobate.
2. Pentru acest refuz, rate limit-ul rămâne contabilizat, quota este restituită verificat fail-closed, iar catalogul, retrieval-ul, Voyage și Anthropic nu sunt apelate.
3. Întrebările despre metodă, formule, praguri, valori prescrise, debit minim și localizarea explicației într-un articol nu sunt clasificate drept execuție de calcul; excepțiile nu pot ocoli un imperativ explicit.
4. Matricea include cererile mixte (metodă + imperativ), puterea în kW, capacitatea frigorifică și capacitatea de răcire instalată, toate refuzate local.
5. UI-ul afișează răspunsul normal, îl păstrează în istoricul vizibil și nu îl trimite în `context_conversatie` ulterior.
6. Promptul interzice categoric executarea calculelor, estimărilor și dimensionărilor; CSP-ul permite scriptul inline actualizat.

## Comenzi pentru Planner (PowerShell; nu sunt executate de Coder)

```powershell
Set-Location D:\Omnia-MVP-no-calculations
python -m pytest -q
python -m pytest -q tests\test_api_integration.py tests\test_generation_core.py tests\test_ui_static.py
python -c "from pathlib import Path; import base64, hashlib, re; text=Path('static/index.html').read_text(encoding='utf-8'); script=re.search(r'<script>(.*)</script>', text, re.S).group(1).encode(); print(base64.b64encode(hashlib.sha256(script).digest()).decode())"
git diff --check
git status --short
git diff --cached --name-only
```
