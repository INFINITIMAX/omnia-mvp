# D11–D14 — explicația modificărilor

Status: **GREEN local, QA/Reviewer încă necesari** (11-09-2026). Nu este deploy sau validare pe corpus/model real.

## Ce se schimbă

- Căutarea semantică este globală implicit între documentele `approved`.
- Documentele citate în istoric sau doar menționate în întrebare nu mai filtrează automat căutarea.
- Doar expresiile exacte `doar din [cod]`, `numai din [cod]`, `exclusiv din [cod]` restrâng întrebarea curentă.
- `nu doar din [cod]` păstrează căutarea globală. Alte negații/formulări nu sunt suportate implicit.

## `retrieval_core.py`

1. `_ALIAS_SEPARATOR` include `/`. Astfel `P 118/1-2025` și formele cu spații/slash se compară ca același cod, fără a permite potriviri în interiorul altui token.
2. `_DOCUMENT_RESTRICTION` enumeră literal cele patru expresii aprobate. Nu folosește `IGNORECASE` sau normalizare de spații; nu ghicește sinonime.
3. `parse()` păstrează poziția fiecărui alias găsit, nu numai lista documentelor. Două coduri în zone diferite ale întrebării sunt o comparație permisă; două aliasuri suprapuse pentru documente diferite rămân ambiguitate.
4. Pentru articol explicit sau articol cunoscut, mai multe documente rămân `ambiguous_reference`. Nu alegem documentul arbitrar și nu facem embedding.
5. `restricted_document_ids()` separă lipsa unei directive (`None`) de o directivă care nu rezolvă exact un document (mulțime goală sau cu mai multe identități).
6. Metoda caută un cod imediat după directivă. Nu folosește un cod găsit mai târziu în propoziție ca să ascundă un cod absent.
7. Verificarea numerică de după alias reutilizează exact separatorii oficiali (whitespace, slash, cratimă). Ea împiedică un alias scurt să accepte greșit un an sau o parte necunoscută, de exemplu `NP 010-2099` sau `NP 010 2099`; codul complet cunoscut rămâne valid.
8. `nu doar din` întoarce `None`: este guard-ul D14, deci ruta rămâne globală. Nu este un parser general de negații.
9. `retrieve()` verifică întâi o directivă nerezolvată. Ea întoarce `ambiguous_reference` înainte de embedding sau citirea dovezilor.
10. Ruta exactă document+articol rămâne înainte de semantic și nu apelează embedderul.
11. Embedding-ul primește întrebările validate din ultimele trei tururi plus întrebarea curentă, inclusiv când există scope explicit. Istoricul oferă subiect, nu autorizare de filtru.
12. O singură ramură alege query global sau scoped. În scope valid nu există fallback global după un miss; fără scope nu există query scoped ascuns.
13. `_preferred_document_ids()` a fost eliminată: codurile citate anterior nu mai devin filtre SQL implicite.

## Teste

- `test_multi_document_retrieval.py` verifică RED/contractul global, comparațiile, aliasurile slash, scope-ul explicit, codul absent, D14 și istoricul în embedding.
- Testele vechi de retrieval/API care cereau scope automat au fost redenumite și adaptate, păstrând fixtures și controalele de cost. Acum verifică query global cu context, nu elimină scenariile.
- Testele API verifică D13: HTTP 200 `ambiguous_reference`, fără embedding/generare/buget/dovezi, cu quota/rate consumate; verifică D12 fără fallback, citările R06 și ordinea multi-document.
- Fiecare fake înregistrează query-uri, embedding-uri și tranzacții. Nu există DB sau provider real în aceste teste.

## Dovezi locale

- RED complet: 42 failures / 35 passed / 0 errors.
- RED D14/istoric: 5 failures, 77 deselected.
- GREEN inițial: 515 passed focalizat și 863 passed/11 skipped complet.
- După P1: 81 passed focalizat și 932 passed/11 skipped complet; un warning extern Starlette/httpx.
- Evaluator R05 după D11: 19 cazuri, 10 constatări, zero pasaje omise, exit 1 intenționat.

## Limite

Nu sunt rezolvate R05, negațiile generale, formulările alternative, restricțiile multiple, persistența scope-ului, continuările de articol ambigue sau replay-ul UI. Nu s-au schimbat schema DB, eligibilitatea `approved`, quota/rate ca limite, SDK-uri, numărul de apeluri per rută, plafoanele de retrieval/context/generare ori producția.

**Valoare CV:** separarea intenției explicite de contextul conversațional, cu regresii pentru provenance, fallback și cost; fără afirmația falsă că rutarea corectă garantează răspunsuri normative corecte.
