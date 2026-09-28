# R21 — raport Reviewer (transcris integral de planner, 28-09-2026)

**Verdict: APROBAT** (cod coder + teste tester)

## Ce am verificat
- Am citit integral `R21-coder.md` (rundele 1-5), `R21-coder-raport.md`, `R21-tester.md`, `R21-tester-raport.md`, D18/D24/D25 din `docs/DECISIONS.md`.
- Am citit `chunking_core.py` complet (D:\Omnia-MVP-r21-anexe\chunking_core.py).
- Am verificat pe textul real `D:\Omnia-MVP\documente_noi\p118_1_2025\extracted.txt` ocurențele marcajului intern `A.\d+\.` — vezi finding minor mai jos.
- Am citit toate testele noi din `test_chunking_core.py` (liniile 734-935) și testul pe document real din `test_populare_db.py` (579-640+).

## Codul coder-ului (chunking_core.py)
Nimic ce blochează. Constatări:
- Logica celor 5 runde e implementată exact cum descrie raportul: prag 50 marcaje „Art.” brute dezactivează `PATTERN_ARTICOL_FARA_PUNCT`; regiunile de anexă (`PATTERN_TITLU_ANEXA`, `PATTERN_MARCAJ_ANEXA_INTERN`) prefixează corect copiii; regula „primul Art. acceptat” elimină corect cuprinsul; plasa din runda 2 (reset pe orice `Art.`) e complet scoasă — am confirmat, nu există niciun `anexa_curenta = None` rămas în afara potrivirii titlului de anexă (linia 580-582). Nu există cod mort/rezidual din rundele anterioare.
- Bug-ul de potrivire pe sufix (endswith) e corect reparat prin `_ultimul_cuvant`/`_PATTERN_ULTIMUL_CUVANT_RAND` (linii 364-413), aplicat consecvent în ambele funcții afectate.
- **Minor / informativ, nu blochează**: `_PATTERN_MARCAJ_ANEXA_INTERN_ACOPERIRE = re.compile(r"A\.\d+\.")` (chunking_core.py:92) e neancorat — pe P 118/1 real apar zeci de ocurențe `A.10. X.Y.` **în mijlocul frazei** (referințe încrucișate, ex. rândul 26253 „conform A.10. 2.3.4. (1)”, rândul 26375 etc.), nu doar la început de rând ca marcajul real. Regex-ul le elimină și pe acestea din calculul acoperirii, în timp ce marcajul de chunking (`PATTERN_MARCAJ_ANEXA_INTERN`, ancorat pe `\n`) nu le atinge — rămân text normal în chunk. Fiindcă normalizarea e aplicată simetric pe ambele părți ale comparației (rând brut vs. text concatenat), nu am găsit dovadă concretă de inflație falsă a acoperirii; e consistent cu convenția deja existentă (`_PATTERN_MARCAJ_ARTICOL_ACOPERIRE` e la fel de neancorat). Recomand doar ca planner-ul să țină minte riscul teoretic (coliziune de prefix la potrivire de substring) dacă acoperirea pe documente viitoare cu multe trimiteri interne pare suspect de optimistă.

## Testele tester-ului
Bune, fiecare test verificat manual poate să pice pe o schimbare de cod plauzibilă:
- Testele sintetice (`test_chunking_core.py:734-935`) acoperă exact cazurile-limită din runde: pragul de 50 (testat chiar la limită), cuprinsul înaintea primului Art., titlu simplu, marcaj intern copil, cuprins stil I9/NP057, trimiteri cu virgulă/rupte pe rând nou, legendă cu literă mică care NU mai blochează titlul (regresia rundei 4), Art. în interiorul unei anexe care nu închide regiunea, acoperire cu marcaj intern eliminat. Toate au assertion-uri specifice de valoare, nu doar `is not None`.
- Testul pe document real (`test_populare_db.py:579-640+`) verifică sursa textului (fraze specifice), nu doar numărul — corect a exclus `7.8` din lista de falși după ce a distins corect titlul real de secțiune de falsul original (bună muncă de investigație, documentată în raport).
- Actualizarea `NUMAR_CHUNKURI_ASTEPTAT_PER_DOCUMENT` reflectă cifrele verificate de planner pe text real, nu valori inventate.
- Nota tehnică a testerului despre `_CUVINTE_CONTINUARE_ANEXA` folosind „și” cu diacritic e utilă și corect semnalată ca risc pentru planner, nu ca bug de cod.

Nimic redundant sau garantat să treacă indiferent de cod găsit.

---

## Decizia planner-ului
- R21 acceptat; PR către `main`. Riscul teoretic al metricii neancorate e notat; se reevaluează dacă acoperirea unui document nou pare suspect de mare.
- Nota despre „și” cu diacritic: textele sunt normalizate la diacritice cu virgulă (`diacritice.py`); documentele cu diacritice corupte (I7) sunt tratate în R22, care pornește din branch-ul R21 (același fișier).
- Merge-ul R21 și reimportul (P 118/1, apoi I7 după R22) cer aprobarea lui Lucian; R21 singur nu schimbă producția până la reimport.
