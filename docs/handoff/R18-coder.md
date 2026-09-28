# R18 — Coder: runner pentru setul permanent de evaluare a căutării

Worktree: `D:\Omnia-MVP-r18-evaluare`, branch `feat/r18-set-evaluare` (din `main` `1e55fb6`). Aprobat de Lucian 28-09-2026: set permanent de **30 de întrebări** cu articolul corect cunoscut, ca să măsurăm corectitudinea cu cifre după fiecare schimbare.

## Context
- Căutarea: `retrieval_core.RetrievalService.retrieve(question)` → `RetrievalResult(status, evidence)`; `Evidence` are `document_id`, `articol_normalizat`, `chunk_order` etc. Rutele: exactă (fără embedding) și semantică (un embedding Voyage, `SEMANTIC_TOP_K = 5`). Compunerea în producție: `main.py` ~902–906 (catalog → parser, `PostgresRetrievalRepository`, embedder).
- Runner-ul R05 (`real_grounding_eval.py`) rulează generarea completă și nu are „răspuns așteptat”; nu îl modifica. Reutilizează din el (prin import) ce se potrivește: adaptorul Voyage cu `timeout=30, max_retries=0`, conexiunea `readonly`, scrierea atomică a raportului, contorul de apeluri.
- Setul de întrebări (gold) îl scrie planner-ul în `evaluare/set_aur.json`; nu îl crea tu.

## Format `evaluare/set_aur.json`
```json
{"versiune": 1, "cazuri": [
  {"id": "P118-01", "tip": "exact|semantic|negativ", "intrebare": "…",
   "asteptat": [{"document_id": "p118_1_2025", "articol": "2.3.2.1.2"}]}
]}
```
`asteptat` conține unul sau mai multe articole acceptate (oricare e corect); gol pentru `negativ` (se așteaptă refuz: `not_found`, `ambiguous_reference` sau `out_of_scope`). `articol` e comparat după normalizare cu `articol_normalizat` al dovezii; o dovadă al cărei `articol_normalizat` e un copil al articolului așteptat (începe cu `articol + "."` sau `articol + "("`) se consideră potrivire.

## Sarcina — script nou `retrieval_eval.py`
1. CLI: `--set <cale>` (implicit `evaluare/set_aur.json`), `--raport <cale>` (în `evaluare/rapoarte/`, gitignored), `--run` obligatoriu pentru apeluri reale (fără el: validează setul și iese, fără DB/Voyage).
2. Validează setul strict (chei exacte, `id` unic, tip valid, `asteptat` nevid pentru non-negative, gol pentru negative); maximum 30 de cazuri; oprește la invalid, fără apeluri.
3. Rulare: o singură conexiune DB `readonly`; compunere identică cu producția (catalog aprobat → parser, repository, `RetrievalService` cu valorile implicite); aplică și poarta anti-calcul (`scope_core.is_engineering_calculation_request`) înainte de căutare, ca ruta publică (rezultat `out_of_scope`). **Fără generare Anthropic.** Plafon: maximum 30 de embedding-uri pe rulare.
4. Metrici pe caz: `status`, dacă un articol așteptat apare în dovezi (`gasit`), rangul primei potriviri (1 = prima dovadă), numărul de dovezi. Pentru negative: `corect` dacă statusul e unul dintre refuzuri.
5. Raport JSON atomic: per caz (`id`, `tip`, `status`, `gasit`, `rang`, `dovezi` = listă scurtă `document_id`+`articol_normalizat`, fără text), plus sumar: acuratețe totală, pe tip, pe document; `recall@1`, `recall@5`; număr de embedding-uri. Afișează sumarul pe stdout **ASCII** (`ensure_ascii=True`). Nu opri rularea la primul caz greșit (spre deosebire de R05) — o eroare de provider/DB oprește însă tot, cu cod stabil.
6. Adaugă `evaluare/rapoarte/` în `.gitignore`.

## Constrângeri dure
- Nu rula comenzi. Nu scrie teste (Tester-ul).
- Nu modifica `real_grounding_eval.py`, `main.py`, `retrieval_core.py`, `generation_core.py`, `chunking_core.py`, `supabase/`, `.env`, `documente_noi/`. Doar `retrieval_eval.py`, `.gitignore` și raportul.
- Nicio cheie în loguri/rapoarte; rapoartele nu conțin text normativ.

## Predare
`docs/handoff/R18-coder-raport.md`: fișiere, flux, coduri de eroare, ce ai reutilizat.
