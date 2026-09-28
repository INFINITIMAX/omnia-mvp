# R19 — raport Reviewer (transcris integral de planner, 28-09-2026)

VERDICT: APROBAT

Am citit R19-coder.md (incl. Runda 2), R19-coder-raport.md, R19-tester.md, R19-tester-raport.md, DECISIONS.md (D25, D11-D14, D23), migrațiile din supabase/migrations, și codul: normative_codes.py, generation_core.py, retrieval_core.py (ArticleParser.parse, RetrievalService.retrieve, _has_ambiguous_article, _grouped_by_article, _limit_context), plus tests/test_normative_codes.py, tests/test_retrieval_core.py, tests/test_multi_document_retrieval.py, tests/test_generation_core.py.

## Coder — verificat

1. **Mutare în normative_codes.py**: curată, fără duplicare (am confirmat cu grep că vechile simboluri au dispărut complet din generation_core.py). Fără import circular: normative_codes.py nu importă nimic intern; generation_core.py și retrieval_core.py importă din el direct, iar generation_core.py importă retrieval_core.py doar pentru `Evidence` (lanț aciclic). `_normative_references` e wrapper subțire, byte-identic cu vechiul comportament (`answer[start:end].strip()` == vechiul `match.group(0).strip()`).

2. **Refuzul D25 în `ArticleParser.parse`**: implementat corect, înaintea oricărei alte logici (inclusiv verificarea de ambiguitate a aliasurilor și orice embedding). Am verificat manual mai multe cazuri de falsuri-pozitive cerute explicit de planner:
   - Coduri aprobate scrise diferit (spații/cratime/slash) — `_ALIAS_SEPARATOR` e flexibil la orice combinație de separatori, deci „P118-1/2025" se potrivește oricum cu aliasul „P 118/1-2025"; nicio regresie aici.
   - Fals-pozitive obișnuite (tabele, ani, „[C1]", „p. 12-14", „ANEXA I 5") — corect excluse de tiparele existente + `_CUVINTE_DE_STRUCTURA`, neschimbate.
   - **Risc real identificat (deja semnalat de coder în raport, nu ascuns)**: un cod aprobat scris cu o eroare reală de cifre (ex. „NP10-2022" cu zero lipsă, față de aliasul oficial „NP 010-2022") nu se potrivește cu niciun alias (regex-ul de aliasuri cere șirul de cifre identic, fără toleranță la zero nesemnificativ), dar e detectat de `gaseste_referinte_normative` ca formă de cod → refuzat ca `ambiguous_reference` în loc să cadă pe căutare semantică globală, cum s-ar fi întâmplat înainte de R19. Acesta e un efect secundar al politicii D25 aprobate de Lucian, nu o eroare de implementare a task-ului — dar merită semnalat planner-ului ca limitare de produs (poate un candidat pentru o normalizare suplimentară a cifrelor, decizie separată).

3. **Runda 2** (`retrieval_core.py` ~504-612): ruta exactă păstrează `_has_ambiguous_article` neschimbat; ruta semantică folosește `_grouped_by_article`, care grupează pe `(document_id, articol_normalizat)`, păstrează poziția primei apariții (deja cea mai bună după scor, fiindcă intrarea vine sortată) și reordonează intern după `chunk_order`. Aplicată înainte de `_limit_context`, care rămâne neatins. Justificarea pe invariantul R16 e solidă și verificabilă.

4. `SEMANTIC_TOP_K = 10` — schimbare punctuală, singura linie atinsă din constante; impactul asupra costului de generare nemăsurat empiric, dar corect semnalat ca risc deschis în raport, nu ca fapt ascuns.

Nimic nenecesar: fișierele atinse respectă exact lista din task (`normative_codes.py` nou, `generation_core.py`, `retrieval_core.py`); `main.py`, `chunking_core.py`, `static/`, `supabase/`, `.env`, `evaluare/`, `SEMANTIC_MIN_SCORE` neatinse.

## Tester — verificat

Testele actualizate/noi nu sunt tautologice — fiecare are o schimbare de cod concretă care l-ar pica (verificat direct: `test_semantic_grupeaza_fragmentele_neconsecutive...` verifică ordinea exactă `hash-c, hash-a, hash-b` / `chunk_order 40,42,10`, nu doar `status=="found"`; `test_exact_refuza_...cu_gol_intre_pozitii` e regresie explicită pe ruta exactă; blocul D25 (5 teste) acoperă exact cele 4 cazuri cerute + apel embedder/repository=0). `test_multi_document_alias_slash_*` separă corect cele 3 tokenuri nedetectate de cele 3 detectate-dar-nesuprapuse, cu raționament verificat manual pe regex. Testele `top_k` folosesc constanta `SEMANTIC_TOP_K`, nu valoare hardcodată — corect, rezistent la refactorizare ulterioară a valorii. Testul de echivalență wrapper (`generation_core`) verifică poziții + text reconstruit, nu doar `isinstance`/`isDefined`. Nu am găsit teste redundante sau aserțiuni slabe.

## Concluzie
Nicio problemă blocantă. O singură observație non-blocantă pentru planner: limitarea D25 pe coduri aprobate scrise cu eroare numerică reală (zero lipsă etc.) transformă un fallback silențios anterior într-un refuz explicit — comportament intenționat conform D25, dar merită o notă în DECISIONS.md dacă Lucian vrea să-l accepte explicit ca atare sau să ceară toleranță suplimentară la normalizare.

---

## Decizia planner-ului
- R19 acceptat; limitarea „cod aprobat scris fără zerouri inițiale” notată în D25 și propusă lui Lucian ca decizie separată (toleranță la zerouri inițiale în aliasuri).
- PR către `main`; merge și deploy cu aprobarea lui Lucian.
