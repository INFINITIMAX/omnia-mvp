# R30 — Raport tester (transcris de planner din mesajul de predare; tester-ul nu a scris fișierul)

## Fișiere noi
- `tests/test_query_rewrite.py` — `AnthropicQueryRewriter` izolat (client fake): răspuns valid → rescrierea; gol / prea lung / `max_tokens` / pachet malformat (gol, bloc non-text, mai multe blocuri) → original; `AnthropicError` și excepție generică (`TypeError`) → original, fără propagare; cheie API lipsă → original, fără client; apelul nu trimite `temperature`; promptul conține întrebarea ca JSON neîncrezător, cu escaparea `<`/`>`/`&`; client lazy construit o singură dată.
- `tests/test_query_rewrite_retrieval.py` — `RetrievalService` + `rewriter` (fake-uri care disting rezultatele pe embedding): ruta exactă și codul necunoscut D25 nu apelează nici rewriter, nici embedder; semantic global combină cele două embedding-uri pe scor maxim și respectă `top_k`; rescriere identică după spații → un singur embedding; scope D12 folosește `find_semantic_in_documents` pentru ambele; fără rewriter → un singur embedding.

## Fișiere modificate
- `tests/test_api_integration.py` — secțiunea R30 (`configure_with_rewriter`, `QueryRewriterFake`): eșecul rescrierii (Anthropic 503 prin client fake, cu `AnthropicQueryRewriter` real) → 200 `answered`, un singur embedding, `/health/provideri` ok; rescrierea trece prin bugetul de apeluri plătite; generarea primește întrebarea originală, nu marcajul rescris.
- `tests/test_retrieval_eval.py` — `install_fakes`: `RetrievalServiceFake` acceptă `rewriter=None`, parametru `instances`; secțiunea „8. Rescriere (R30)”: `--rescriere` fără `--run` → exit 2; fără rescriere nu se construiește rewriter și sumarul e neschimbat; cu rescriere `rescriere_calls` în sumar și `_CountingRewriter` peste delegat; plafonul rescrierii la `MAX_GENERATION_CALLS`; numărătoarea reală a apelurilor.

## Neacoperit (motivat)
- Verificarea cu apel real (sintetic doar eroarea de provider).
- Investigarea testului instabil (cere rulare).
- D12 + D25 combinate pe ruta semantică (redundant cu `test_multi_document_retrieval.py`).

## Suspiciuni de bug
Niciuna. Notă de design: cu plafonul zilnic epuizat, blocarea apare la rescriere (primul apel plătit pe ruta semantică).

---

## Note planner (29-09-2026)
Două teste ale tester-ului erau greșite și au fost corectate de planner: (1) inserarea în `test_api_integration.py` mutase ultima aserțiune a testului scriptului de deploy în testul nou — mutată înapoi; (2) `test_rescrierea_trece_prin_bugetul…` aștepta apelul rescrierii cu plafonul epuizat; corect `rewriter.questions == []` (garda refuză înaintea apelului plătit). După corecturi: 1390 passed, 34 skipped (3 rulări).
