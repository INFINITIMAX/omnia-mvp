# R23 — Coder: evaluare completă cu generare (mod nou în `retrieval_eval.py`)

Worktree: `D:\Omnia-MVP-r23-gen`, branch `feat/r23-evaluare-completa` (din `main` `45a82db`). Aprobat de Lucian 28-09-2026, cost < 1 $ pe rulare.

## Context
- `retrieval_eval.py` (R18) măsoară doar căutarea pe `evaluare/set_aur.json` (30 de cazuri; acum 28/30).
- Generarea în producție: `GenerationService(generator).generate(question, evidence)` (`generation_core.py:185`) întoarce `GenerationResult` cu `status` `answered` (cu ≥1 citare obligatorie) sau `not_found` (doar când nu există dovezi). Erorile: `UngroundedReferenceError` (în API → `unsupported_answer`), orice altă `GenerationValidationError` (ex. `MissingCitationError`, pasaj invalid → în API **503**), erori de provider.
- **Gol de design de măsurat:** modelul nu are un refuz structurat. La o întrebare fără răspuns în dovezi, fie răspunde citând ceva (eventual spunând în text că informația lipsește), fie nu citează → `MissingCitationError` → 503 pe site.
- Adaptorul Anthropic pentru evaluări există în `real_grounding_eval.py` (`_build_runtime_generator`, `timeout=30, max_retries=0`, `_CountingGenerator`) — reutilizează-l prin import.

## Sarcina
1. Opțiune nouă `--generare` (doar împreună cu `--run`): după căutare, pentru cazurile cu `status == "found"`, apelează `GenerationService` cu generatorul de evaluare. Plafon: maximum 30 de generări pe rulare (reîncercarea internă pentru referințe nesusținute se numără). Fără `--generare`, comportamentul actual rămâne **identic** (inclusiv raportul și sumarul).
2. Rezultat final per caz (`rezultat_final`): `refuz_cautare` (status de refuz al căutării sau `out_of_scope`), `raspuns` (generare `answered`), `refuz_generare_unsupported` (`UngroundedReferenceError`), `eroare_generare:<ClasaExceptiei>` (alte `GenerationValidationError`). O eroare de **provider/DB** oprește rularea ca acum; erorile de validare a generării **nu** opresc rularea.
3. Metrici per caz, în raport:
   - `citeaza_asteptat` (pozitive): răspuns cu cel puțin o citare pe articolul așteptat (același `document_id` și `articol` normalizat egal sau copil — aceeași regulă ca potrivirea din căutare; pentru citări folosește `articol` + documentul dovezii citate);
   - `citate_literale`: fiecare `citat` apare literal (spații normalizate) în textul dovezii citate;
   - `declara_lipsa` (euristică, pentru revizie umană): textul răspunsului conține formulări de tipul „nu conțin(e)”, „nu există informații”, „nu am găsit”, „nu se precizează”, „nu sunt specificate”, „informația lipsește” (listă explicită în cod, fără diacritice obligatorii);
   - pentru revizie umană: textul răspunsului și citările (id, cod document, articol, primele 300 de caractere din citat) — raportul e local, în `evaluare/rapoarte/` (gitignored).
4. Sumar nou (doar cu `--generare`): pozitive — câte `raspuns` și câte `citeaza_asteptat`; negative — distribuția `rezultat_final` și câte `declara_lipsa`; număr total de erori de generare pe clasă; `citate_literale` (câte răspunsuri au toate citatele literale); numărul de embedding-uri și generări. Stdout ASCII.
5. Nu atinge `generation_core.py`, `retrieval_core.py`, `main.py`, `chunking_core.py`, `real_grounding_eval.py` (doar import), `evaluare/set_aur.json`, `supabase/`, `.env`, `documente_noi/`.

## Constrângeri dure
Nu rula comenzi. Nu scrie teste noi (Tester-ul). Fără chei sau secrete în raport. Raport: `docs/handoff/R23-coder-raport.md`.
