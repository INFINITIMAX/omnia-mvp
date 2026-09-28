# R18 — Tester — raport

Fișier nou: `tests/test_retrieval_eval.py` (nu am atins cod de producție).

## Ce acoperă fiecare grup de teste

**1. Validarea setului (`load_gold_set`)**
- `test_set_minim_valid_este_acceptat`, `test_set_negativ_valid_este_acceptat` — cazul normal; pică dacă parsarea/normalizarea articolului se strică.
- `test_chei_lipsa_sau_in_plus_resping_setul` (parametrizat: cheie lipsă, cheie în plus) — pică dacă validarea `set(value) != {...}` e slăbită.
- `test_id_duplicat_respinge_setul` — pică dacă verificarea `seen_ids` e eliminată.
- `test_tip_necunoscut_respinge_setul` — pică dacă `tip not in _TYPES` e eliminat.
- `test_peste_30_de_cazuri_respinge_setul` / `test_exact_30_de_cazuri_este_acceptat` — pică dacă plafonul `MAX_CASES` se schimbă sau bornarea e greșită (off-by-one).
- `test_asteptat_gol_la_non_negativ_respinge_setul` / `test_asteptat_nevid_la_negativ_respinge_setul` — pică dacă regula per-tip pentru `asteptat` e inversată sau eliminată.
- `test_articol_invalid_respinge_setul` — pică dacă `ArticleParser.normalize_article` nu mai e apelat la validare.
- `test_setul_real_set_aur_trece_validarea` — citește `evaluare/set_aur.json` real; pică dacă setul de aur devine invalid sau dacă validarea se rupe.
- `test_fara_run_nu_construieste_nicio_conexiune_sau_embedder` — monkeypatch pe `_open_db_connection`/`_build_runtime_embedder` cu funcții care ridică `AssertionError` dacă sunt apelate; pică dacă `main()` fără `--run` ajunge totuși să construiască providerii.

**2. Potrivirea (`_score`/`_is_match`)**
- articol exact → rang corect; copil cu `.` sau cu `.(n)` → găsit; prefix fără separator (`4.4.1` vs `4.4.11`) → nu găsit; alt document cu același articol → nu găsit. Fiecare pică dacă logica `startswith(expected + ".")`/`"("` sau verificarea `document_id` se schimbă.

**3. Negative (`_is_correct`)**
- `not_found`/`ambiguous_reference`/`ambiguous_article`/`out_of_scope` → corect pentru tip `negativ`; `found` → greșit. Pică dacă `_REFUSAL_STATUSES` sau `_is_correct` se modifică.
- **Actualizat după decizia planner-ului**: `ambiguous_article` e refuz valid; coder-ul l-a adăugat în `_REFUSAL_STATUSES`. Am redenumit `test_negativ_cu_ambiguous_article_nu_este_tratat_ca_refuz` → `test_negativ_cu_ambiguous_article_este_tratat_ca_refuz_corect`, care acum cere `corect=True`, și am adăugat `ambiguous_article` în lista parametrizată din `test_negativ_corect_pentru_statusuri_de_refuz`.

**4. Poarta anti-calcul**
- `test_poarta_anti_calcul_evita_embeddingul_si_cautarea` — rulează `run_evaluation` cu `RetrievalService`/`PostgresApprovedCatalogRepository`/`PostgresRetrievalRepository` mock-uite (monkeypatch pe numele din modul, la fel ca în `test_real_grounding_eval.py`) și un embedder fals care numără apelurile; verifică `retrieve()` nu e apelat deloc și `embed_query` are 0 apeluri pentru o întrebare „Calculează…”. Pică dacă poarta e mutată după căutare sau eliminată.

**5. Sumar**
- `test_sumar_calculeaza_acuratete_pe_tip_si_pe_document_si_recall` — date controlate manual (5 cazuri, rezultate cunoscute), verifică aritmetica exactă pentru acuratețe totală/pe tip/pe document, `recall@1`, `recall@5`. Pică la orice greșeală de calcul sau la schimbarea definiției „pozitiv” (exclude/include negativ).
- `test_plafonul_de_embeddinguri_blocheaza_al_treizecisiunulea_apel` — pică dacă `MAX_EMBEDDING_CALLS` sau `_CountingEmbedder` nu mai blochează al 31-lea apel.
- `test_eroare_de_provider_opreste_rularea_cu_cod_stabil_si_face_rollback` — al doilea caz nu mai e încercat, raportul nu se scrie, `rollback`/`close` apelate o dată; pică dacă fail-fast-ul e eliminat sau dacă raportul parțial ajunge pe disc.
- `test_iesirea_stdout_este_ascii_inclusiv_cand_sumarul_contine_diacritice` — folosește un `document_id` cu diacritice (`docă`) ca să forțeze conținut non-ASCII în sumar; verifică `\u0103` escapat în stdout și absența literei brute. Pică dacă `ensure_ascii=True` e schimbat la `False`. (Testul din varianta inițială, fără diacritice reale în sumar, ar fi trecut mereu — a fost înlocuit.)

**6. Raportul nu conține text normativ**
- `test_raportul_nu_publica_textul_normativ_al_dovezilor` — dovadă cu `content="TEXT NORMATIV NEPUBLICABIL"`; verifică absența completă din raportul serializat și că `dovezi` conține strict `document_id`/`articol_normalizat`. Pică dacă `_score` începe să includă `content` sau alt câmp intern în `dovezi`.

## Ce nu am acoperit și de ce
- Nu am testat integrarea reală cu Postgres/Voyage (interzis explicit — fără rețea/DB real); acoperirea de integrare rămâne pe rularea reală făcută deja de planner (`--run`, 30 cazuri, raport JSON).
- Nu am testat `_default_report_path()` (doar formatare de timestamp, fără valoare de risc) și nici branch-urile de eroare I/O din `main()` (`report_dir_error`) — sunt identice cu cele deja acoperite de `test_real_grounding_eval.py` pentru mecanismul comun de scriere atomică; nu le-am duplicat.
- Nu am construit un test end-to-end complet cu `RetrievalService` real (parser+repository reale) fiindcă ar necesita DB; matching-ul (`_score`/`_is_match`) e testat direct, ceea ce e suficient pentru comportamentul cerut la pct. 2.

## Comanda exactă pentru planner
```
cd D:\Omnia-MVP-r18-evaluare
python -m pytest tests/test_retrieval_eval.py -q
```
(și, dacă vrea confirmare că nu am stricat nimic din suita completă: `python -m pytest -q`).
