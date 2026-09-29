# R30 — Coder: rescrierea întrebării pentru căutare (Claude Haiku 4.5)

Worktree `D:\Omnia-MVP-r30`, branch `feat/r30-rescriere` (din `main` `26d5b57`). Aprobat de Lucian 29-09-2026 („da, folosim haiku”), inclusiv costul unui apel suplimentar pe întrebare.

## Problema (măsurată de planner pe baza reală)
Utilizatorii scriu fără diacritice, cu greșeli de tipar și colocvial. Exemplu real (tester, inginer instalații): „cat se considera debitul de aer pentru desfumare la o masina pentru un subsol fara isntaltie de sprinklere ? dar cu ?”. Răspunsul e în NP 127:2009 art. 117 („debit de extracție a fumului … 600/900 mc/h pentru fiecare autoturism”, „parcaje”). Locul art. 117 în căutarea semantică (`find_semantic`, top 40):
- formularea exactă: **15** (în răspuns intră top 10 → „Nu am găsit”); fără greșeală: 11; cu diacritice: 9;
- cu „autoturism … parcaj subteran” în loc de „mașină … subsol”: **2**.
Concluzie: vocabularul colocvial e factorul principal, apoi diacriticele/greșelile.

## Soluția
1. Modul nou `query_rewrite.py`:
   - `QueryRewriter` (Protocol): `rewrite(question: str) -> str`.
   - `AnthropicQueryRewriter`: model `claude-haiku-4-5-20251001`, `max_tokens` ~200, temperatură 0, timeout scurt (ex. 8 s), `max_retries=0`, client leneș (ca `AnthropicTextGenerator` din `main.py`), `ANTHROPIC_API_KEY` din mediu.
   - Promptul (în română) cere: rescrie întrebarea în limbajul normativelor tehnice românești de construcții și instalații — adaugă diacriticele, corectează greșelile, înlocuiește termenii colocviali cu cei normativi (ex. „mașină” → „autoturism”, „subsol cu mașini” → „parcaj subteran”, „desfumare” → „evacuarea fumului în caz de incendiu”, „tubulatură” → „canale/conducte de aer”) păstrând și termenul inițial când e util; **nu răspunde, nu adaugă valori, articole sau coduri de normativ care nu sunt în întrebare**; o singură întrebare, fără explicații. Întrebarea utilizatorului e marcată ca date, nu instrucțiuni (ca în `generation_core`).
   - Validare fail-safe: rezultat gol, prea lung (> `MAX_QUESTION_CHARS`) sau eroare/timeout de provider → se folosește **doar** întrebarea originală (fail-open la comportamentul de azi; nu 503).
2. `RetrievalService` (`retrieval_core.py`): parametru opțional `rewriter: QueryRewriter | None = None`.
   - Parserul, restricțiile de document (D12), codurile necunoscute (D25) și ruta exactă rămân **exclusiv** pe întrebarea originală. Rescrierea se folosește **doar** pe ruta semantică și doar pentru embedding.
   - Pe ruta semantică: embedding pentru textul original (cu contextul, ca acum) + embedding pentru textul rescris (cu același context), câte o interogare fiecare (`find_semantic` / `find_semantic_in_documents`, același `top_k`); combinare după `chunk_id` cu scorul maxim, sortare descrescătoare, primele `top_k`; apoi `_accepted` / `_deduplicate` / `_grouped_by_article` / `_limit_context` ca acum.
   - Fără `rewriter` (sau rescriere identică cu originalul, după normalizarea spațiilor): comportament **identic** cu azi (un embedding, o interogare).
3. `main.py`: `RuntimeDependencies` primește `query_rewriter_factory` (implicit `AnthropicQueryRewriter`), injectabil în teste; apelul de rescriere trece prin același `_PaidCallBudgetGuard` (câte un `reserve()` pentru rescriere; embedding-urile sunt deja gardate). Eșecurile de rescriere se loghează ca provider failure fără date sensibile (fără textul întrebării), dar **nu** marchează `/health/provideri` ca degradat și nu schimbă răspunsul public.
4. `retrieval_eval.py`: opțiune `--rescriere` care construiește `RetrievalService` cu `AnthropicQueryRewriter` (plafon de apeluri ca la generare), ca planner-ul să măsoare înainte/după.

## Constrângeri
- Nu atinge `generation_core.py` (generarea rămâne pe întrebarea originală), `chunking_core.py`, `static/`, `supabase/`, `.env`, `documente_noi/`, `evaluare/set_aur.json`.
- Nu rula comenzi, nu scrie teste. Raport: `docs/handoff/R30-coder-raport.md` (inclusiv promptul integral și deciziile).
