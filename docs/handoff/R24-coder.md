# R24 — Coder: limita de răspuns și refuzul onest structurat (D26)

Worktree: `D:\Omnia-MVP-r24`, branch `feat/r24-limita-refuz` (din `main` `45a82db`). Aprobat de Lucian 28-09-2026 (ambele puncte).

## Dovezi (evaluarea completă R23, adaptorul de producție)
- 30 de întrebări: 24 ajung la generare; **3 dau eroare 503 pe site** (P118-02, P118-05, I5-01). Diagnostic planner: `stop_reason: max_tokens` la exact **1200** tokeni de ieșire (`MAX_ANSWER_TOKENS`, `generation_core.py:13`); `AnthropicTextGenerator._validated_tool_response` (`main.py:334–335`) respinge corect răspunsul trunchiat → `ProviderUnavailableError` → 503. Intrare ~4 600–5 800 tokeni (10 dovezi, R19) + răspuns separat pe fiecare normativ (R12) ⇒ răspunsurile corecte depășesc 1200.
- **NEG-04** („grosimea stratului de uzură din asfalt pe drumurile județene”, subiect absent din corpus): modelul scrie corect „Informația solicitată … nu se regăsește în niciuna dintre dovezile furnizate”, dar contractul (`answered` cere ≥1 citare, `generation_core.py`, `_validated_used_ids`) îl obligă să citeze → 4 citări irelevante (NP 057, P 118/1, I7). Dacă nu citează → `MissingCitationError` → 503.
- API: `/intreaba` are deja statusul `not_found` cu mesajul `_NOT_FOUND` („Nu am găsit această informație în documentele aprobate.”, `main.py:725`) folosit când căutarea nu găsește nimic (`main.py:910–913`); interfața îl afișează deja.

## Sarcina
1. **`MAX_ANSWER_TOKENS = 2000`** (`generation_core.py:13`). Nicio altă schimbare de limită.
2. **Refuz structurat (D26):**
   - schema tool-ului `return_grounded_answer` (`main.py` ~284–300): câmp nou **obligatoriu** `gasit` (boolean), alături de `raspuns` și `pasaje`;
   - promptul (`generation_core.py`, regulile): dacă dovezile **nu conțin** răspunsul la întrebare, `gasit=false`, `pasaje=[]` și `raspuns` o frază scurtă; dacă conțin măcar o parte, `gasit=true` cu citări, iar lipsurile se spun explicit (regula 4 existentă rămâne);
   - validarea pachetului (`generation_core.py` ~261): cheile acceptate devin exact `{"raspuns", "pasaje", "gasit"}`; `gasit` trebuie să fie boolean; cu `gasit=false`, `pasaje` trebuie să fie listă goală și textul răspunsului **nu** conține identificatori `[Cn]` — altfel eroare de validare (fail-closed ca acum);
   - cu `gasit=false`, `GenerationService.generate` întoarce `GenerationResult("not_found", <mesajul standard>, ())` **fără** reîncercarea pentru referințe nesusținute și fără citări; cu `gasit=true` totul rămâne exact ca acum (D20: pasaj literal verificat; ≥1 citare obligatorie);
   - `main.py` `/intreaba`: un `GenerationResult` cu status `not_found` produce același răspuns public ca `not_found` de la căutare (`status="not_found"`, `raspuns=_NOT_FOUND`, `citari=[]`), cu cota consumată normal (a existat un apel plătit).
3. **`docs/DECISIONS.md`:** adaugă D26 deasupra D25 (textul de mai jos).
4. Nu atinge `retrieval_core.py`, `chunking_core.py`, `retrieval_eval.py`, `static/`, `supabase/`, `.env`, `documente_noi/`. `real_grounding_eval.py` folosește `AnthropicTextGenerator._TOOL` — verifică doar că rămâne importabil.

## D26 (de inserat în `docs/DECISIONS.md`)
> ### D26 — refuz onest structurat și limita de răspuns, aprobat Lucian (28-09-2026)
> Evaluarea completă R23 a arătat: (1) 3 din 24 de generări tăiate la 1200 de tokeni → 503 pe site; (2) la o întrebare fără răspuns în corpus, modelul spunea corect că informația lipsește, dar contractul îl obliga să citeze articole irelevante. Decizii: `MAX_ANSWER_TOKENS` = 2000; tool-ul `return_grounded_answer` are câmpul obligatoriu `gasit` (boolean); `gasit=false` ⇒ fără pasaje și fără `[Cn]`, iar serverul răspunde `not_found` cu mesajul standard, fără citări. `gasit=true` păstrează neschimbate D20/D22 (pasaj literal verificat, ≥1 citare). Modifică D22 doar prin adăugarea câmpului `gasit`.

## Constrângeri dure
Nu rula comenzi. Nu scrie teste noi (Tester-ul; testele care verifică schema sau limita veche le actualizează el). Fără comentarii inutile. Raport: `docs/handoff/R24-coder-raport.md`.
