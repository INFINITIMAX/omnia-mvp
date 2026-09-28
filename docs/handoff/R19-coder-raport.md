# R19 — Coder: raport

## Fișiere

- **`normative_codes.py` (nou)**: mutat integral `_CODE_TAIL`, `_NORMATIVE_REFERENCE_PATTERNS`,
  `_CUVINTE_DE_STRUCTURA`, `_ULTIMUL_CUVANT`, `_precedat_de_cuvant_de_structura` din
  `generation_core.py`. Funcție publică `gaseste_referinte_normative(text) -> list[tuple[int, int]]`:
  aceeași logică de detecție + filtrare de incluziune (păstrează doar potrivirea cea mai lungă),
  dar întoarce doar poziții (start, end), nu și textul. Nu importă nimic din `generation_core.py`
  sau `retrieval_core.py` — evită circularitatea prin construcție (modul de nivel cel mai de jos,
  fără dependințe interne).
- **`generation_core.py`**: import `gaseste_referinte_normative`; blocul de tipare șters;
  `_normative_references(answer)` e acum un wrapper subțire: ia pozițiile din
  `gaseste_referinte_normative(answer)` și reconstruiește `answer[start:end].strip()` pentru
  fiecare — text identic cu ce producea înainte `match.group(0).strip()`, deci
  `_unsupported_normative_references` și tot restul comportă-se neschimbat.
- **`retrieval_core.py`**:
  - import `gaseste_referinte_normative`.
  - `SEMANTIC_TOP_K = 5` → `10`.
  - `ArticleParser.parse`: după calculul `matches` (potrivirile de aliasuri aprobate), verific
    dacă vreo referință normativă găsită de `gaseste_referinte_normative(question)` nu se
    suprapune cu niciun `(alias_start, alias_end)` din `matches`; dacă da, întorc
    `ParsedReference(None, None, False, requires_clarification=True)` înainte de orice altă
    logică (deci și înainte de verificarea de ambiguitate a aliasurilor suprapuse și de orice
    rută/embedding). Restul funcției (D11–D14, aliasuri, restricții) neschimbat.

## Decizii neincluse explicit în task

- Am ales să reconstruiesc textul referinței cu `answer[start:end]` în loc să extind
  semnătura publică cu textul — task-ul cerea explicit `list[tuple[int, int]]`, nu tuple cu
  text. Comportamentul rămas identic, verificat manual pe logica veche (pozițiile de
  start/end din `re.finditer` nu se schimbă la `.strip()`, doar valoarea string produsă).
- Comentariul din `generation_core.py` de deasupra secțiunii de detecție a rămas ca ancoră
  de context, dar am scurtat conținutul mutat, cu trimitere explicită către
  `normative_codes.py`.

## Ce nu am făcut

- Nu am scris teste (rol Tester).
- Nu am atins `main.py`, `chunking_core.py`, `static/`, `supabase/`, `.env`, `documente_noi/`,
  `evaluare/`, `SEMANTIC_MIN_SCORE`.

## Runda 2 (28-09-2026)

- **`retrieval_core.py` — `RetrievalService.retrieve`**: ruta semantică nu mai apelează
  `_has_ambiguous_article`; ruta exactă îl păstrează neschimbat.
- **`RetrievalService._grouped_by_article` (nou, static)**: pe ruta semantică, după
  `_deduplicate`, grupează dovezile cu același `(document_id, articol_normalizat)`,
  ordonează fiecare grup intern după `chunk_order` și păstrează grupul la poziția primei
  apariții a articolului în listă — poziție care e deja cea a celui mai bun scor al
  grupului, fiindcă `find_semantic`/`find_semantic_in_documents` întorc rezultatele deja
  sortate descrescător după scor. Aplicată înainte de `_limit_context`, care rămâne
  neschimbat.
- Nu am atins `_has_ambiguous_article`, `_deduplicate`, `_limit_context`, ruta exactă, sau
  vreun alt fișier din constrângerile inițiale.
- Nu am atins testele (Tester-ul actualizează cele 104 eșecuri așteptate + noile cazuri de
  regrupare semantică, semnalate de planner).

## Riscuri / de verificat

- **Fals-pozitive noi în `ArticleParser.parse`**: orice întrebare care menționează un cod ce
  se potrivește cu unul din tiparele din `normative_codes.py` (STAS, SR, EN, NP, P, I, C, NE,
  GP/GT, Mc — toate cer formă compusă număr-separator-număr) dar care **nu** e alias al unui
  document aprobat va fi acum refuzată direct (`ambiguous_reference`), fără să ajungă la
  ruta semantică. Asta include: coduri scrise diferit față de aliasurile din catalog (ex. un
  utilizator scrie „C 107-2010” dintr-o eroare de an, dacă în catalog e doar „C 107-2005”),
  sau întrebări care citează legitim un standard disabled/necunoscut alături de o întrebare
  altfel răspunsabilă din corpus. Recomand rulare pe `evaluare/set_aur.json` complet
  (nu doar NEG-01) ca să prindă eventuale căderi la P118-02, P118-alte cazuri sau altele cu
  cod P/I/C în formulare.
- Merită rulat testul existent de generare (`generation_core`) neschimbat, ca să confirme
  că extragerea wrapper produce byte-identic ce producea codul vechi (ar trebui, dar e
  singurul punct unde comportamentul „identic” depinde de o presupunere despre `.strip()`).
- `SEMANTIC_TOP_K = 10` dublează dovezile candidate trimise mai departe prin
  `MAX_CONTEXT_CHARS`/`_limit_context`; nu am verificat empiric impactul asupra costului de
  generare (mai multe chunk-uri în prompt), doar cerința explicită a task-ului.
- **Runda 2**: eliminarea `ambiguous_article` pe ruta semantică se bazează integral pe
  premisa R16 (fiecare articol e bloc continuu în DB) — dacă acea garanție se rupe vreodată
  (bug de ingestie, editare manuală), ruta semantică nu mai are nicio plasă de siguranță
  pentru fragmente conflictuale, doar gruparea/ordonarea. Recomand rulare pe
  `evaluare/set_aur.json` complet pentru P118-04, NP091-01 și restul cazurilor semantic.
