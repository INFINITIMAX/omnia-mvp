# R14 — Coder: chunker unificat, titluri ca context, curățare antete MO

Worktree: `D:\Omnia-MVP-r14-chunker`, branch `feat/r14-chunker-unificat` (din `main` `fbf5177`).
Aprobat de Lucian 27-09-2026: titlurile devin context pentru articolele copil; „art. 4.4” întoarce copiii; chunkerele se unifică.

## Problema (dovezi din DB read-only, 27-09)
- ~450 de chunk-uri din documentele `approved` sunt doar titluri de secțiune („4.4. Dimensionarea conductelor de aer”, „3.3. Siguranța la foc”): NP 057 18,5%, I7 13%, NP 010 9,6%, I5 8,8%, NP 015 8,3%. În normativele RO, titlurile și articolele au aceeași numerotare; `PATTERN_ARTICOL` le tratează la fel, iar singurul filtru e `LUNGIME_MINIMA_CHUNK = 15`.
- Antetul de pagină MO și numerele de pagină intră în text: rândul `MONITORUL OFICIAL AL ROMÂNIEI, PARTEA I, Nr. 204 bis/10.III.2025`, cu 1–2 rânduri doar-cifre imediat alăturate (separate eventual de rânduri goale). Exemplu real: „…vizibile. 88 MONITORUL OFICIAL AL ROMÂNIEI, PARTEA I…”, „Etanșeitatea 39”.
- Titluri de capitol cu cifre romane, la început de rând („II. POMPELE DE DISTRIBUȚIE A CARBURANȚILOR”), se lipesc la finalul articolului anterior.
- Două chunkere copiate și divergente: `populare_db.creeaza_chunkuri` (fără limită de 1000, fără sufix) și `manual_ingestion_preflight._creeaza_chunkuri_locale` (cu limită `_MAX_CHUNK_CHARS = 1000` și tratare sufix).

## Sarcina
1. **Modul nou `chunking_core.py`**, cu o singură funcție publică `creeaza_chunkuri(text: str) -> list[dict[str, str]]` (chei `articol`, `text`), deterministă, fără I/O, DB sau rețea. Pornește de la `_creeaza_chunkuri_locale` (varianta mai strictă: tratare sufix, limită 1000, split secundar pe subpuncte) și adaugă, în ordine:
   a. **Curățare antete MO:** elimină rândurile care se potrivesc cu antetul MO (`^\s*MONITORUL OFICIAL AL ROMÂNIEI, PARTEA I, Nr\. .+$`, tolerant la spații) și rândurile doar-cifre (1–4 cifre) aflate la cel mult 3 rânduri de antet, cu doar rânduri goale sau doar-cifre între ele. **Nu** elimina rânduri doar-cifre fără antet în apropiere (sunt celule de tabel). Referințele din text („publicat în Monitorul Oficial al României, Partea I, nr. 34”) nu sunt antete și rămân.
   b. **Cuprins:** păstrează detectarea existentă (`linie ... 12`) și adaug-o pe cea cu numărul de pagină pe rândul următor (NP 010: „1.1. Obiect și domeniul de aplicare\n3\n1.2. …\n4”). Criteriu acceptat: în primele 20% din text, o succesiune de ≥5 intrări consecutive de tip „număr articol + titlu scurt + rând doar-cifre” e cuprins și se sare.
   c. **Titluri de capitol romane** (`^\s*[IVXLC]{1,6}\.\s+` urmat de text majoritar cu majuscule, pe un singur rând) sunt separatoare: închid articolul curent și nu intră în textul lui.
   d. **Titluri de secțiune:** un segment numerotat este titlu dacă textul lui e pe un singur rând, are ≤ 200 de caractere, nu se termină cu `.`, `;` sau `:`, **și** următorul segment numerotat este copil al lui (numărul lui începe cu numărul titlului + cifră, ex. `4.4.` → `4.4.1.`). Titlul nu devine chunk; textul lui (`"{numar} {titlu}"`, ex. `4.4. Dimensionarea conductelor de aer`) se pune ca **primul rând** în textul fiecărui copil direct. Un segment care arată a titlu, dar nu are copii, rămâne chunk normal (nu pierdem conținut).
   e. Deduplicarea „cea mai lungă variantă câștigă” rămâne, dar **numără și întoarce** variantele eliminate, ca să nu mai fie pierdere silențioasă: expune `ultimele_statistici()` sau un rezultat secundar echivalent (`duplicate_eliminate`, `titluri_contopite`, `antete_eliminate`); alege forma cea mai simplă.
2. **`populare_db.py` și `manual_ingestion_preflight.py`** folosesc `chunking_core.creeaza_chunkuri`; șterge implementările vechi și constantele/pattern-urile devenite nefolosite. Nu schimba altceva în fluxurile de import (gate-uri, statusuri, embeddings, DB).
3. **`retrieval_core.py`:**
   - `PostgresRetrievalRepository.find_exact`: dacă nu există niciun chunk cu `articol_normalizat` exact, întoarce copiii secțiunii: `articol_normalizat LIKE articol || '.%'` (parametrizat; escapează `%`/`_` nu e necesar, formatul e `[a-z0-9().-]+`), ordonați după `document_id, chunk_order, id`. Păstrează ambele variante (cu și fără `document_id`).
   - `ArticleParser._is_known_article`: un articol e cunoscut și dacă există un articol cunoscut care începe cu `articol + "."`.
   - Nu modifica `_has_ambiguous_article` și nici ruta semantică.

## Criterii de acceptare (planner-ul le verifică)
- Pe textele reale (`documente_noi/<id>/extracted.txt`) planner-ul rulează o comparație vechi/nou; pentru NP 057, I7, I5, NP 010, NP 015: zero chunk-uri care sunt doar titlu cu copii; zero apariții ale antetului MO în chunk-uri; NP 010 fără intrări de cuprins ca chunk-uri.
- Niciun conținut pierdut: orice text de articol din vechiul rezultat se regăsește (normalizat pentru spații) în noul rezultat, cu excepția antetelor MO, numerelor de pagină și titlurilor contopite.
- `python -m pytest -q` verde (planner-ul rulează).

## Constrângeri dure
- Nu rula comenzi (doar planner-ul rulează). Nu scrie teste noi (le scrie Tester-ul); actualizează doar testele existente care importă funcții șterse sau pe care le rupi direct, și raportează-le.
- Nu atinge: `main.py`, `generation_core.py`, `access_control.py`, `static/`, `supabase/`, `.env`, `documente_noi/`.
- Fără DB, Voyage, Anthropic, rețea. Fără comentarii inutile; în română ca restul codului.
- Nu adăuga abstracții peste ce cere sarcina.

## Predare
Scrie `docs/handoff/R14-coder-raport.md`: fișiere modificate, ce ai decis la fiecare punct 1a–1e (inclusiv euristici și praguri), testele existente atinse și de ce, riscuri deschise.

## Runda 2 — corecturi după verificarea planner-ului (27-09-2026)

Dovezi rulate de planner pe textele reale (vechi → nou): chunk-uri I5 701→810, I7 1444→1986, P 118/1 1401→2732 (limita de 1000 e așteptată). Titluri-cu-copii rămase ca chunk: I5 51→28, NP 015 37→27, NP 010 17→13, I7 122→8, NP 057 34→1. Pytest: 6 teste `test_api_p1_restrictia_cu_articol_cunoscut_pastreaza_ruta_exacta[exact-miss-*]` pică (`assert len(exact_calls) == 1`, acum 2). `test_doua_procese_nu_pot_rezerva_ambele_ultimul_slot` pică și pe `main` — **nu e al tău, nu-l atinge**.

1. **Introducerea-titlu la split-ul pe subpuncte.** Cauza titlurilor rămase: articol lung (≥2000) împărțit pe `(1)`, `(2)`…, a cărui introducere e doar titlul (ex. `1.1.` → „Obiect și domeniul de aplicare”, urmat de `1.1.(1)`). Dacă introducerea respectă criteriul de titlu din 1d (un rând, ≤200 caractere, fără `.`/`;`/`:` final), nu o emite ca chunk: pune `"{articol} {introducere}"` ca prim rând în textul fiecărui subpunct. Altfel comportamentul rămâne cel de acum.
2. **`find_exact` cu o singură interogare SQL:** `(chunk.articol_normalizat = %s OR chunk.articol_normalizat LIKE %s)`, apoi în Python: dacă există rânduri cu potrivire exactă, păstrează doar pe acelea; altfel întoarce copiii. Păstrează ordonarea și ambele variante (cu/fără `document_id`). Testele `exact-miss` trebuie să treacă fără să le modifici; dacă vreun test verifică textul SQL exact, raportează-l, nu-l rescrie.
3. **Colofonul MO de la finalul documentului** se lipește de ultimul articol (I5 `10.6.(4)`, I9 `ANEXA 5.5.`, I7 `6.10.5.6.2`, P 118/1). Conține rânduri ca „Tiparul: „Monitorul Oficial” R.A.”, „…actele pe site, la: https://www.monitoruloficial.ro…”, „Monitorul Oficial al României, Partea I, nr. 108 bis/8.II.2023 conține 128 de pagini”. Citește finalul fișierelor `D:\Omnia-MVP\documente_noi\{i5_2022,i9_2022,i7_2011,p118_1_2025}\extracted.txt` și elimină blocul de colofon cu o regulă ancorată pe aceste rânduri, aplicată doar în ultima parte a textului. Referințele din corp („publicat în Monitorul Oficial al României, partea I, nr. 15 din 8 ianuarie 2004”) **rămân**.
4. **Date tratate ca articole:** în P 118/1 apar articole `15.01.2024` și `18.12.2024` (date din preambulul ordinului). Un număr de forma `ZZ.LL.AAAA` (zi 01–31, lună 01–12, an 4 cifre) nu e articol.
5. Nu schimba nimic altceva. Actualizează `R14-coder-raport.md` cu o secțiune „Runda 2”.

## Runda 3 — marcajul „Art.” din P 118/1 (27-09-2026)

Dovezi planner, după runda 2: titluri-cu-copii rămase I5 0, NP 010 0, P 118/1 0, NP 015 3, NP 057 1, I7 8; zero antete MO. Testele care verifică textul SQL/parametrii (`exact-*`, `test_repository_exact_foloseste_numai_sql_parametrizat_cu_document_optional`) le actualizează Tester-ul; nu le atinge.

Problemă nouă, preexistentă și gravă: în `documente_noi/p118_1_2025/extracted.txt` articolele sunt marcate „Art. 2.3.6.1.8. La construcțiile…” (830 de rânduri), iar titlurile de secțiune sunt numere simple („2.3.6.1.”, 409 rânduri). `PATTERN_ARTICOL` nu recunoaște „Art. N.N.”, deci toate articolele unei secțiuni ajung sub numărul secțiunii. Celelalte 7 documente nu au deloc „Art. N.N.” la început de rând.

1. **Marcaj „Art.”:** un rând care începe (după spații și un eventual „) cu `Art.` + spații + număr de articol (`\d+\.\d+\.(\d+\.){0,4}`) este început de articol cu identificatorul = numărul, **numai dacă** după număr urmează spațiu și apoi o majusculă (inclusiv diacritice) sau `(`. Altfel e o trimitere încadrată pe rând nou („Art. 2.4.5.4.. ”, „Art. 2.4.5.4., …”) și rămâne text.
2. **Trimiteri rupte pe rând:** un număr simplu la început de rând urmat **imediat** de `)`, `,`, `;` sau `.` (ex. `2.3.6.1.7.), se poate…`) nu este început de articol; rămâne text al articolului curent. Numărul urmat imediat de `(` (format `4.2.(7)`) rămâne valid, ca acum.
3. Titlurile de secțiune numerotate simplu, urmate de articole „Art.” copii, trebuie contopite ca titluri prin regula 1d existentă (verifică pe exemplul `2.3.6.1.` → `Art. 2.3.6.1.1.`).
4. Actualizează raportul cu „Runda 3”. Nu rula comenzi, nu atinge `tests/`.

## Runda 4 — pierdere de conținut și D18 (27-09-2026)

Dovezi planner după runda 3: P 118/1 are acum 811/811 articole „Art.” ca articole proprii (față de 33). Dar:

1. **Regresie D18:** `tests/test_manual_ingestion_preflight.py::test_pipeline_implicit_valideaza_articolul_si_refuza_caractere_neacceptate` pică. Decizia aprobată D18 cere ca `1.1.,` urmat de **sfârșit de rând** să fie articol valid (virgula delimitatoare se elimină), iar `1.1.,text` să fie refuzat. Regula din runda 3 punctul 2 trebuie restrânsă: `,` imediat după număr și urmată doar de spații până la sfârșitul rândului = delimitator D18 (articol valid, fără virgulă); orice altă formă rămâne referință ruptă. Testul trebuie să treacă fără să fie modificat.
2. **Pierdere de conținut prin trimiteri cu literă mică:** în P 118/1, rândul `2.3.2.1.2. lit. a). …` (trimitere încadrată pe rând nou) e tratat ca al doilea început al articolului 2.3.2.1.2; dedup-ul „cea mai lungă variantă” păstrează segmentul fals și **aruncă articolul real** „Art. 2.3.2.1.2. Pereții antifoc … a) minimum valoarea structurii de rezistență…” (rândul 5178 din `extracted.txt`). Statistica: `duplicate_eliminate` = 114 în P 118/1. Regulă nouă, pentru marcajele numerice simple: după număr (și spații) trebuie să urmeze majusculă (inclusiv diacritice), `„`, `(`, cifră sau sfârșit de rând; dacă urmează literă mică, e trimitere și rămâne text.
3. **Cuprins fără numere de pagină** (P 118/1, rândurile ~183+: doar titluri una sub alta). Regulă: un segment care arată a titlu (criteriul 1d) și al cărui număr are articole copil **oriunde** în document nu devine niciodată chunk separat — fie e contopit cu copiii (ca acum), fie e eliminat ca intrare de cuprins. Numără-le în statistici (ex. `titluri_cuprins_eliminate`).
4. **Prefix dublat la split pe subpuncte:** apar texte „2.3.2.1.6. 2.3.2.1. Pereți antifoc…”. Când introducerea unui articol împărțit pe subpuncte e doar titlul părinte deja contopit, pune rândul acela ca atare, fără să mai adaugi `"{articol} "` în față.
5. Actualizează raportul cu „Runda 4”. Nu rula comenzi, nu atinge `tests/`.

## Runda 5 — trimiteri rupte după „Art.” (27-09-2026)

Dovezi planner după runda 4: titluri-cu-copii ca chunk 0 în toate documentele, antete MO 0, testul D18 trece. `duplicate_eliminate`: P 118/1 107, I5 102, I7 72, NP 015 17, I9 12. Pierdere reală confirmată în P 118/1: `Art. 3.2.11.20.` (rândurile ~18975–18986 din `extracted.txt`) conține „…prevederile Art.↵2.1.3.5. (1) alin. a); …”. Rândul `2.1.3.5. (1) alin. a); …` e luat drept început al articolului 2.1.3.5, punctele b) și c) din 3.2.11.20 ajung într-un duplicat al lui 2.1.3.5, iar dedup-ul le aruncă.

1. **Regulă nouă, pentru ambele tipuri de marcaje (numeric simplu și „Art.”):** dacă ultimul rând nevid dinaintea marcajului se termină (ignorând spațiile) cu `Art.`, `art.`, `Articolul`, `articolul`, `alin.`, `pct.`, `lit.` sau `conform`, marcajul este continuarea unei trimiteri și rămâne text al articolului curent.
2. Nu schimba altceva. Actualizează raportul cu „Runda 5”, inclusiv o listă scurtă cu ce tipuri de duplicate rămân eliminate, dacă le poți identifica prin citirea textelor. Nu rula comenzi, nu atinge `tests/`.

## Runda 6 — numere de articol fără punct final (I7) (27-09-2026)

Dovezi planner după runda 5, cu acoperirea rândurilor din textul brut (rânduri ≥50 caractere regăsite în chunk-uri; vechi → nou): P 118/1 3,7% → 0,4% lipsă, I5 6,5% → 2,1%, NP 057 16,2% → 11,4%, **I7 20,2% → 12,3%**. Fraza „3.000 m2” e acum în `3.2.11.20.`. Restul lipsurilor din P 118/1, NP 015, I5, I9 = preambul ordin + colofon (intenționat).

Cauza lipsei din I7: articolele de adâncime ≥3 nu au punct după ultima cifră: `3.1.5.7 Amplasarea contoarelor…`, `3.2.1 Generalităţi`, `3.2.1.1  Determinarea puterii…` (`documente_noi/i7_2011/extracted.txt`, rândurile ~1728–1745). `PATTERN_ARTICOL` cere punct după fiecare componentă, deci prinde `3.1.5.` și lasă „7 Amplasarea…” ca text; toate 3.1.5.x devin duplicate ale lui `3.1.5.` și dedup-ul le aruncă (`duplicate_eliminate` I7 = 72).

1. Acceptă și numere de articol cu **ultima componentă fără punct**, cu minimum 2 componente (`\d+\.\d+(?:\.\d+){0,4}` fără punct final), **numai dacă** după număr urmează cel puțin un spațiu și apoi un început valid de articol conform regulilor existente (majusculă cu diacritice, `„`, `(`). Identificatorul rezultat trebuie să fie același ca pentru forma cu punct (`3.1.5.7` ≡ `3.1.5.7.` după normalizare). Toate regulile din rundele 3–5 (trimiteri rupte, literă mică, rând anterior terminat în `Art.` etc.) se aplică și acestei forme.
2. Atenție la fals-pozitive: valori zecimale la început de rând („0.4 kV …”, „2.5 m …”) încep cu cifră/literă mică după număr și sunt deja respinse de regula allow-list; verifică prin citire că nu apar articole noi absurde în I7, I9, I5.
3. Nu schimba altceva. Actualizează raportul cu „Runda 6”. Nu rula comenzi, nu atinge `tests/`.

## Runda 7 — tăierea cuprinsului aruncă începutul I7 (27-09-2026)

Dovezi planner după runda 6: I7 13,2% rânduri lipsă (12,3% înainte), secțiunile 3.1.5.x și 3.2.1.x lipsesc **complet** din chunk-uri. Cauza, preexistentă și în producție: detectarea cuprinsului cu puncte de conducere caută ultima potrivire `\.{2,}\s*\d{1,4}` în primele 20% din text și aruncă tot ce e înainte. În I7 ultima potrivire e la rândul 3808/35337, în corp: „…cu timpi de declanșare între 150...500 …” (interval numeric). Rezultat: primele ~11% din I7 sunt aruncate. În NP 057 cuprinsul real se termină corect la rândul 109.

1. Cuprinsul cu puncte de conducere se recunoaște numai ca **bloc**: cel puțin 5 rânduri de cuprins (rând care se termină cu **minimum 4 puncte** consecutive, eventual cu spații/NBSP, urmate de număr de pagină de 1–4 cifre la sfârșit de rând), fiecare la cel mult 3 rânduri nevide de precedentul, în primele 20% din text. Tăierea se face la finalul **primului** astfel de bloc, nu la ultima potrivire izolată. Potrivirile izolate (ex. „150...500”) nu taie nimic.
2. Aplică aceeași logică de bloc și la cuprinsul cu număr de pagină pe rândul următor (runda 1b), dacă nu e deja așa.
3. Nu schimba altceva. Actualizează raportul cu „Runda 7”. Nu rula comenzi, nu atinge `tests/`.
