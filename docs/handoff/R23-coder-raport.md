# R23 — Coder: raport

## Fișier modificat
`retrieval_eval.py` (singurul fișier atins).

## Ce am adăugat
- Import din `generation_core`: `GenerationService`, `GenerationValidationError`, `PublicCitation`, `UngroundedReferenceError`; import suplimentar din `real_grounding_eval`: `_build_runtime_generator` (adaptorul Anthropic, timeout=30, max_retries=0, reutilizat ca atare).
- `MAX_GENERATION_CALLS = 30` — plafon separat de `MAX_GENERATION_CALLS = 16` din `real_grounding_eval.py` (nu am reutilizat clasa lor `_CountingGenerator`, care are limita hardcodată la 16; am scris o clasă locală `_CountingGenerator` cu `limit` parametrizat, în oglindă cu `_CountingEmbedder` existent în fișier).
- Opțiune CLI nouă `--generare` (store_true). Validare: dacă e dat fără `--run`, ieșire cod 2 cu `generare_requires_run` pe stderr, înainte de verificarea existentă `not arguments.run`.
- `run_evaluation` primește acum `generation: bool = False` și `generator_factory: Callable[[], object] | None = None`. Fără `--generare`, aceste căi rămân neatinse (nicio cheie nouă în `evaluated`/`public_case`/`sumar`) — am verificat că blocul de generare e complet condiționat de `generation_service is not None` / `if generation:`.
- Pentru fiecare caz, dacă generarea e activă:
  - `status in _REFUSAL_STATUSES` (inclusiv `out_of_scope`) → `rezultat_final = "refuz_cautare"`, fără apel de generare.
  - altfel (`status == "found"`) → `_run_generation(...)` apelează `GenerationService(generator).generate(...)`:
    - `UngroundedReferenceError` → `"refuz_generare_unsupported"`;
    - alt `GenerationValidationError` → `f"eroare_generare:{type(error).__name__}"`;
    - succes → `"raspuns"`, cu `citeaza_asteptat`, `citate_literale`, `declara_lipsa` calculate.
  - Orice altă excepție (provider/DB, inclusiv `cost_limit` de la contorul de generări) oprește rularea: `RealEvaluationError` se repropagă neschimbată, restul devin `case_failed:<id>:execution_error`, la fel ca la căutare.
- `citeaza_asteptat`: mapez fiecare `PublicCitation.id` (`"C<n>"`) înapoi la `evidence[n-1]` (ordinea e garantată de `GenerationService`, care asignează id-urile `C1..Cn` în ordinea evidence-ului primit) și compar `document_id`/`articol_normalizat` cu aceeași regulă `_is_match` folosită la scorul căutării.
- `citate_literale`: compar fiecare `citat` cu conținutul dovezii citate, spații normalizate (`" ".join(text.split())`, redefinit local — nu am importat funcția privată omonimă din `generation_core`).
- `declara_lipsa`: euristică fără diacritice, listă explicită de tipare (`nu contin`, `nu exista informatii`, `nu am gasit`, `nu se precizeaza`, `nu sunt specificate`, `informatia lipseste`), verificată case-insensitive pe text fără diacritice.
- Raport per caz (doar cu `--generare`): `rezultat_final`, `citeaza_asteptat`, `citate_literale`, `declara_lipsa`, `raspuns` (text sau `None`), `citari` (listă de `{id, cod_document, articol, citat}` cu citatul tăiat la primele 300 caractere) — pentru revizie umană locală.
- Sumar nou (doar cu `--generare`), adăugat în `sumar.generare`: `raspunsuri` (câte `"raspuns"`), `citeaza_asteptat` (câte din acelea au citare pe articolul așteptat), `rezultat_final_distributie` (dict cu numărătoare per valoare), `declara_lipsa`, `erori_generare` (dict per clasă de excepție), `citate_literale`. Plus `sumar.generation_calls` la nivelul de sus, alături de `embedding_calls` existent.

## Decizii neincluse explicit în task
- Nu am reutilizat clasa `_CountingGenerator` din `real_grounding_eval.py` fiindcă are `MAX_GENERATION_CALLS = 16` fix, incompatibil cu plafonul de 30 cerut aici; am scris echivalentul local parametrizat, la fel cum există deja `_CountingEmbedder` local aici (nu din `real_grounding_eval.py`).
- Am presupus, pe baza contractului `RetrievalService`/`main.py`, că `status == "found"` implică `evidence` nevid, deci nu am mai dublat verificarea `not evidence` din `real_grounding_eval.py`.
- `declara_lipsa` e calculat doar pentru cazurile cu `rezultat_final == "raspuns"` (nu există text de analizat pentru celelalte rezultate).

## Ce NU am făcut
- Nu am scris teste (rol Tester).
- Nu am atins `generation_core.py`, `retrieval_core.py`, `main.py`, `chunking_core.py`, `real_grounding_eval.py` (doar import), `evaluare/set_aur.json`, `supabase/`, `.env`, `documente_noi/`.

## Ce ar trebui verificat de planner
- Sintaxă/import: `python -c "import retrieval_eval"` (fără `--run`, nu atinge DB/Voyage/Anthropic).
- `python retrieval_eval.py` (fără `--run`) trebuie să tipărească în continuare `set_valid` — comportament neschimbat.
- `python retrieval_eval.py --generare` (fără `--run`) trebuie să iasă cu cod 2 și `generare_requires_run` pe stderr.
- O rulare reală `--run --generare` (cost < 1$, aprobat) pentru verificarea end-to-end a plafonului de 30 de generări și a câmpurilor noi din raport.
- Risc: dacă vreodată `status == "found"` ajunge cu `evidence` gol (contract încălcat), `_run_generation` va clasifica rezultatul ca `"raspuns"` cu textul implicit `"Nu am găsit..."` din `GenerationService`, nu ca refuz — merită un test explicit al tester-ului pentru acest caz limită, dacă e considerat plauzibil.

## Runda 2 — adaptorul de producție, erorile vizibile nu opresc rularea (28-09-2026)

Dovada planner-ului: rularea `--run --generare` cu adaptorul R05 (`real_grounding_eval._RuntimeGenerator`) s-a oprit fatal la `invalid_generation` pentru un răspuns tăiat la `max_tokens` sau tool_use malformat — exact tipul de eroare pe care producția o transformă într-un răspuns 503 pentru utilizator, nu o indisponibilitate reală. Am aplicat exact cerințele:

1. **Adaptor de producție, nu R05.** Am scos importul `_build_runtime_generator` din `real_grounding_eval`. Am adăugat `_build_production_generator()`, care întoarce direct `main.AnthropicTextGenerator()` — clientul Anthropic real, construit lazy cu `timeout`/`max_retries` ale runtime-ului R17 (constantele din `main.py`, nu o copie separată). `main()` folosește acest factory pentru `--generare`. Am importat suplimentar `AnthropicTextGenerator` și `ProviderUnavailableError` din `main`.

2. **Distincția „eroare vizibilă” vs „provider indisponibil real”, ambele `ProviderUnavailableError`.** `main.AnthropicTextGenerator._validated_tool_response` ridică `ProviderUnavailableError("răspuns Anthropic invalid")` **fără** `raise ... from`, atât pentru `stop_reason == "max_tokens"` cât și pentru un `tool_use` malformat — acest `raise` are loc *în afara* blocului `try/except` care prinde `AnthropicError`, deci nu există nicio excepție activă și `error.__cause__` e `None`. În schimb, eșecul real de rețea/credit e prins explicit cu `except AnthropicError as error: ... raise ProviderUnavailableError(...) from error`, deci `error.__cause__` e chiar `AnthropicError`-ul. Am folosit exact acest semnal în `_run_generation`: `ProviderUnavailableError` cu `__cause__ is None` → `eroare_generare:ProviderUnavailableError`, nu oprește rularea; cu `__cause__` setat → `raise` (oprește rularea, ca înainte). Restul claselor `GenerationValidationError` (inclusiv `UngroundedReferenceError`) rămân neschimbate ca înainte (Runda 1).
3. **Câmp nou `vizibil_utilizator`** pe fiecare caz din raport (doar cu `--generare`), calculat în `_vizibil_utilizator(rezultat_final)`, după maparea din `main.py` (`/intreaba`):
   - `refuz_generare_unsupported` → `{"http_status": 200, "status_api": "unsupported_answer"}`;
   - orice `eroare_generare:<Clasa>` → `{"http_status": 503, "status_api": None}` (mesajul generic „Serviciul este temporar indisponibil.”, fără cod API distinct — producția nu diferențiază subtipul în răspunsul public);
   - pentru `raspuns` și `refuz_cautare` → `None` (nu e o eroare vizibilă ca eroare).
   Extras din codul comun `_refused_generation_result(rezultat_final)`, refolosit și pentru `refuz_cautare`, ca schema JSON per caz să rămână uniformă.

### Fișier modificat suplimentar față de Runda 1
Tot `retrieval_eval.py` — nu am atins niciun alt fișier din constrângerile dure.

### Ce ar trebui verificat de planner (Runda 2)
- O rulare reală `--run --generare` pe cel puțin un caz unde Anthropic taie răspunsul la `max_tokens` sau întoarce tool_use malformat, ca să confirme că rularea continuă (nu se mai oprește fatal) și că `rezultat_final` = `eroare_generare:ProviderUnavailableError` cu `vizibil_utilizator = {"http_status": 503, ...}`.
- Confirmă că o eroare reală de rețea/credit Anthropic (dacă poate fi simulată) tot oprește rularea ca înainte.

## Runda 3 — completare listă `declara_lipsa` (28-09-2026)

Rulare reală planner: 30 cazuri, 24 generări, 21 răspunsuri, 3 `eroare_generare:ProviderUnavailableError` (max_tokens la 1200, se repară în R24). Euristica `declara_lipsa` a ratat NEG-04 („nu se regăsește în niciuna dintre dovezile furnizate”). Am adăugat în `_DECLARA_LIPSA_TIPARE` (fără diacritice, ca restul): `nu se regaseste`, `nu se regasesc`, `nu figureaza`, `lipsesc dovezile`. Nimic altceva schimbat; tot `retrieval_eval.py`.
