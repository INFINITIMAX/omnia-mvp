# R18 — raport Reviewer (transcris integral de planner, 28-09-2026)

Verdict: APROBAT

## Ce am verificat
- `retrieval_eval.py` integral (301 linii) vs. compunerea din `main.py` ~899-908: catalog aprobat → parser, `PostgresRetrievalRepository`, `RetrievalService` cu valori implicite — identic. `retrieval.retrieve(case.intrebare)` fără context e corect (evaluarea rulează întrebări izolate, fără istoric conversațional; `context` are default `()` în `retrieval_core.retrieve`, deci comportamentul e echivalent cu producția pentru cazul fără conversație).
- Poarta anti-calcul: `is_engineering_calculation_request(case.intrebare)` aplicată înainte de căutare, identic cu `main.py:885`, cu rezultat `out_of_scope` fără embedding — corect.
- `_is_match`: potrivire exactă sau copil (`.` / `(`) — verificat manual în sursă (`p118_1_2025`, art. 2.3.2.1.2) că normalizarea și logica de copil corespund textului real.
- Siguranță/cost: `_CountingEmbedder` cu plafon propriu 30 (distinct de R05, prag 8), fără generare Anthropic, conexiune `readonly` cu `set_session`, `evaluare/rapoarte/` în `.gitignore` (confirmat, linia 28), rapoarte fără text normativ (`dovezi` conține doar `document_id`+`articol_normalizat`, testat explicit).
- Fail-fast: eroare reală de caz → `RealEvaluationError("case_failed:<id>:execution_error")` oprește tot, cu rollback/close garantate în `finally`; o nepotrivire simplă nu oprește rularea — corect, conform task.
- Cod: fără funcționalitate în plus față de task; reutilizarea prin import (`RealEvaluationError`, `_build_runtime_embedder`, `_write_report_atomically`, `_open_db_connection`, componentele din `retrieval_core.py`/`scope_core.py`) e rezonabilă, fără duplicare inutilă.
- Runda 2 (adăugarea `ambiguous_article` în `_REFUSAL_STATUSES`) e minimală și corect reflectată în raport și în teste.

## Setul de aur (`evaluare/set_aur.json`)
30 de cazuri, întrebările sunt formulate parafrazat (nu copiază textul articolului) pentru cazurile semantice — verificat spot-check pe P118-02 (rezistență la foc pereți antifoc → art. 2.3.2.1.2, confirmat în `extracted.txt`). Cazurile exacte citează articolul explicit (așteptat, sunt teste de „exact match”, nu semantic). Negativele acoperă: articol inexistent în document real (NEG-01), cerere de calcul (NEG-02), articol inexistent în document existent (NEG-03) — bună acoperire a tipurilor de refuz.

## Teste (`tests/test_retrieval_eval.py`)
Toate cele 24+ teste verificate individual pot pica la o schimbare reală de comportament (nu am găsit teste "mereu-verzi"): validarea setului acoperă fiecare regulă cu propriul test negativ, matching-ul testează exact/copil/prefix-fals-pozitiv/document-greșit, sumarul verifică aritmetică exactă cu date controlate (nu doar `toBeDefined`-echivalent), testul ASCII forțează diacritice reale în cheile sumarului ca să nu fie trivial, testul de eroare de provider verifică fail-fast + rollback + raport neexistent pe disc. Nu am găsit teste redundante — fiecare acoperă o ramură distinctă de cod.

## Concluzie
Nicio problemă de severitate blocantă. Cod și teste corespund task-ului, fără cod inutil, fără teste inutile.

---

## Decizia planner-ului
- Notă de acuratețe: NEG-01 întreabă despre un document scos din căutare (I 13-2015 e `disabled`, D23), nu despre un articol inexistent — cazul măsoară exact eroarea gravă găsită: sistemul a răspuns din I7 art. 5.12.
- Măsurare de bază R18 (28-09-2026): 26/30 (86,7%); exact 6/6; semantic 18/21; negativ 2/3; recall@1 0,778; recall@5 0,889. Diagnostic pe erori: P118-02 articolul corect pe locul 9 (scor 0,712 vs 0,715 la locul 5); NP015-03 articolul corect pe locul 2, dar toate scorurile sub pragul 0,50 (0,474); P118-05 locul 83 (problemă de căutare semantică); NEG-01 cod de normativ necunoscut ignorat.
- R18 acceptat; PR către `main` pentru aprobarea lui Lucian. Corecturile intră în R19, remăsurate cu același set.
