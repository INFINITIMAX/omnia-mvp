# R16 — Coder: raport

## Runda 2 — regresie NP 010 (27-09-2026)

Fișier modificat: `chunking_core.py` (`_este_referinta_rupta`, `_CUVINTE_TRIMITERE_RUPTA`). Nimic altceva atins.

1. **Cifră lipită imediat de marcaj → trimitere ruptă.** În `_este_referinta_rupta`, după calculul `pas` (numărul de spații sărite după marcaj) și `rest` (primul caracter rămas): dacă `pas == 0` (nicio whitespace reală între marcaj și caracterul următor) și `rest[:1]` e cifră, funcția întoarce acum `True` (marcaj respins ca trimitere ruptă, articolul fals nu se mai creează), înainte de verificarea generică `_PATTERN_CARACTER_VALID_DUPA_NUMAR` (care încă acceptă cifra dacă e precedată de un spațiu real — comportament neschimbat pentru acel caz, cum cere task-ul). Exemplu real, NP 010 rândurile 3019–3020: „…de la punctele\n4.2.4.5 și 4.2.4.6” — `PATTERN_ARTICOL` prinde baza `4.2.4.` (ultimul „.5” nu are punct final, deci nu intră în captură), iar cifra „5” lipită imediat după e acum respinsă ca trimitere ruptă, nu se mai construiește articolul fals „4.2.4.5” care înainte fura, prin dedup normalizat, articolul real de la rândul 1575 (`4.2.4.5.` „Prevederi specifice de siguranță pentru zonele de recreație la exterior”).
2. **Cuvinte noi de trimitere ruptă.** Adăugate la `_CUVINTE_TRIMITERE_RUPTA`: `punctele`, `punctul`, `punctelor`, `articolele`, `articolelor`, `prevederile`, `prevederilor` (comparare case-insensitive, ca lista existentă). Rândul 3019 se termină chiar cu „…de la punctele”, deci acest cuvânt singur ar fi respins deja marcajul de pe rândul următor prin `_linia_anterioara_se_termina_cu_trimitere`; păstrat totuși explicit, cum cere task-ul, ca strat suplimentar de siguranță pentru cazuri unde fix-ul 1 (cifră lipită) nu s-ar aplica (ex. un marcaj complet, cu toate componentele punctate, aflat totuși pe o trimitere ruptă după unul din aceste cuvinte).
3. **Verificare prin citire pe NP 010.** Am căutat în `documente_noi/np010_2022/extracted.txt` toate liniile care încep cu un marcaj numeric urmat imediat (fără spațiu) de o altă cifră (`^\d+\.\d+(\.\d+)*\.\d`). Doar două potriviri în tot documentul:
   - rândul 3020 (`4.2.4.5 și 4.2.4.6`) — cazul din dovada planner-ului, rezolvat de fix-ul 1.
   - rândul 2817 (`4.2.2, (30), se recomandă…`) — caz suplimentar găsit prin verificare, nemenționat explicit în dovezi: marcajul fals ar fi fost „4.2.2” (baza `4.2.2.` prinsă de `PATTERN_ARTICOL` ca „4.2.” + sufix glue „2,” → „4.2.2”), coliziune cu titlul real de capitol `4.2.2.` de la rândurile 61/1021 („Siguranța circulației interioare”). Linia anterioară nu se termină cu niciunul din cuvintele de trimitere (se termină cu „la”), deci doar fix-ul 1 (cifră lipită) îl rezolvă — confirmă că regula generică, nu doar lista de cuvinte, era necesară.
   Nu am găsit alte cazuri de acest tip în document.

## Fișiere modificate

### `chunking_core.py`

1. **Dedup pe identificator normalizat (task 1).**
   - Nou: `_normalizeaza_pentru_dedup(articol)` — același contract ca `normalizeaza_articol`/`_normalizeaza_articol` (colaps spații, minuscule, `rstrip(".")`), fără validarea caracterelor (validarea rămâne la import).
   - `_este_articol_normalizabil` refactorizat să folosească această funcție (comportament neschimbat).
   - În `creeaza_chunkuri`, dicționarul de dedup e acum cheiat pe `_normalizeaza_pentru_dedup(articol)` în loc de `articol` brut. Regula „cea mai lungă variantă câștigă” (comparație pe lungimea `text`-ului segmentului) și `duplicate_eliminate` rămân neschimbate; `articol` păstrat în chunk e forma brută a variantei câștigătoare (nu cea normalizată) — normalizarea se face în continuare doar la scriere în DB.

2. **Titlu de capitol cu un singur nivel (task 2).**
   - Pattern nou `PATTERN_TITLU_CAPITOL_SIMPLU = r"\n\s*(\d{1,2}\.)[ \t]+([A-ZĂÂÎȘȚŞŢ].*)"` — grup 1 = numărul cu punct (convenție comună cu celelalte marcaje), grup 2 = textul rândului rămas (titlul).
   - Adăugat ca a patra sursă de marcaje în `_extrage_segmente`.
   - Filtrare nouă `_este_titlu_capitol_simplu_valid(potrivire, candidate, index)`: respinge dacă titlul (după `rstrip()`) are peste 120 caractere sau se termină cu `.`/`;`/`:`, sau dacă marcajul recunoscut imediat următor din `candidate` nu e copil direct (`baza_urmator` începe cu `prefix` și diferă, cu exact un punct suplimentar). Filtrarea rulează în aceeași buclă cu `_este_data_zi_luna_an`/`_este_referinta_rupta`, înainte de construirea segmentelor — un candidat respins dispare complet din `potriviri`, textul rămânând atașat segmentului anterior, exact ca înainte de R16 (comportamentul pentru enumerări simple gen „1. text… 2. text…” e neschimbat).
   - Fiecare segment primește acum și câmpul `titlu_capitol` (textul titlului validat, sau `None`).
   - Funcție nouă `_propaga_titluri_capitol_simplu(segmente)`, apelată în `creeaza_chunkuri` imediat după `_extrage_segmente` (înainte de `_contopeste_titluri`): pentru fiecare segment cu `titlu_capitol` setat, prepend `"{prefix} {titlu}"` ca prim rând la textul copiilor direcți (aceeași buclă/condiție `rest.count(".") == 1` ca în `_contopeste_titluri`), marcând `are_context_parinte = True` pe copii. Spre deosebire de titlurile „1d” obișnuite, segmentul-titlu însuși **nu** e marcat `este_titlu` — rămâne un chunk normal, cu articolul `N.` și textul lui fiind introducerea capitolului (ex. „(1) Dimensionarea instalațiilor…”), tăiată ulterior de split-ul secundar existent (`_aplica_split_secundar`) dacă depășește 2000 caractere, la fel ca orice alt articol.
   - `_contopeste_titluri` sare acum peste segmentele cu `titlu_capitol is not None` (skip explicit la începutul buclei), ca să nu fie procesate a doua oară de mecanismul generic 1d dacă textul rămas (introducerea) arată accidental a titlu pur (o singură linie, fără punctuație finală).
   - Verificat manual pe `documente_noi/i5_2022/extracted.txt` (rândurile ~2124–2180, oferite ca dovadă): „3.2.5.2.” rămâne segment separat; „4. Elemente generale de calcul” devine marcaj propriu (`articol_baza = "4."`), validat pentru că următorul marcaj recunoscut e „4.1.” (copil direct); textul „(1) Dimensionarea…(a)…(c)…” devine chunk cu `articol = "4."`; titlul se propagă ca prim rând la „4.1.”. Bug-ul „3.2.5.2.(1)” dublat nu se mai poate reproduce, fiindcă subpunctele capitolului 4 nu se mai lipesc de „3.2.5.2.”.

3. **Numerotare de subpuncte care reîncepe (task 3b, adăugat în timpul lucrului).**
   - În `_aplica_split_secundar`, după `PATTERN_SUBPUNCT.split`, se extrag numerele subpunctelor (`numere_subpunct`) și se verifică strict-crescător (`numere_subpunct[i] > numere_subpunct[i-1]` pentru toți i). Dacă nu — numerotare care reîncepe sau se repetă — chunk-ul e păstrat ca unitate unică (nu se mai împarte pe subpuncte), la fel ca la `len(subpuncte) == 1`; va fi tăiat ulterior doar de `_aplica_limita_caractere` (bucăți de max. 1000 caractere), fără identificatori noi inventați.
   - Verificarea se aplică doar chunk-urilor care oricum ating pragul `LUNGIME_PENTRU_SPLIT_SECUNDAR = 2000` (neschimbat) — pentru chunk-uri mai scurte nu se ajunge la split secundar deloc, comportament identic cu înainte.

### `reimport_approved.py`

- Task 3: `json.dumps(rezultat, ensure_ascii=False, ...)` → `ensure_ascii=True`. Nimic altceva schimbat în funcția `main` sau în restul fișierului.

## Decizii care nu erau explicit în task

- Pentru dedup (task 1), am păstrat `articol` (forma brută afișată/scrisă) ca fiind cea a variantei câștigătoare (text mai lung), nu forma normalizată — normalizarea rămâne strict o cheie internă de comparare, ca să nu schimb formatul stocat în DB (contract existent, `normalizeaza_articol` rulează oricum la import).
- Pentru task 2, am ales să NU marchez segmentul-titlu (`N.`) drept `este_titlu`, spre deosebire de titlurile „1d” obișnuite, fiindcă task-ul cere explicit ca introducerea capitolului să rămână un chunk propriu cu `articol = N.` — dacă l-aș fi tratat identic cu 1d (marcat `este_titlu`, eliminat), conținutul intro s-ar fi pierdut.
- Am adăugat un câmp nou (`titlu_capitol`) pe fiecare segment în loc să reutilizez `este_titlu`/`articol_baza` existente, ca să pot distinge explicit acest caz de titlurile pure în `_contopeste_titluri` (evită procesare dublă) fără să schimb semantica altor câmpuri deja folosite în alte fișiere.
- Filtrarea `_este_titlu_capitol_simplu_valid` verifică doar marcajul **imediat următor** din `candidate` (înainte de filtrarea finală de `_este_data_zi_luna_an`/`_este_referinta_rupta`), nu „are copil undeva” ca la 1d — exact cum cere task-ul („numai dacă următorul marcaj de articol recunoscut este un copil al lui”), ca să resping corect enumerările simple din corpul articolelor.
- Pentru task 3b, am interpretat „strict crescătoare” ca fiecare număr > precedentul (nu neapărat consecutiv +1), conform formulării „nu se face split... dacă numerotarea reîncepe sau se repetă” — o secvență 1,2,4,7 rămâne validă pentru split; doar reluarea/repetarea (ex. 1,2,3,1,2,3) blochează split-ul.

## Ce NU am făcut

- Nu am scris/modificat teste (rol Tester).
- Nu am rulat nimic (pytest, reimport dry-run) — nu am unelte de shell.
- Nu am atins `retrieval_core.py`, `main.py`, `generation_core.py`, `supabase/`, `.env`, `documente_noi/`, nici alte fișiere din `populare_db.py`/`manual_ingestion_*.py` (dedup-ul lor rulează pe alt cod, neatins).

## Ce ar trebui verificat de planner

- `python -m pytest -q` — mă aștept ca testele existente pentru `duplicate_eliminate` (cazuri unde identificatorul brut diferă dar cel normalizat e identic) să treacă acum diferit (mai multe deduplicări); Tester-ul trebuie să actualizeze numerele fixe de chunk-uri, cum e menționat deja în task.
- Reimport dry-run pe toate cele 9 documente aprobate (mai ales I5, NP 010, P 118/1, I7, NP 015, NP 057 — cele 63 de articole ambigue raportate) — verificați că nu mai apar `articol_normalizat` neconsecutive și că acoperirea nu scade sub pragurile din tabel.
- Verificare specifică pe I5 rândurile ~2124–2180 (capitolul „4. Elemente generale de calcul”) și pe alte capitole cu numerotare pe un singur nivel din celelalte documente — posibil să existe și alte cazuri similare (nu am putut scana exhaustiv toate cele 8 `extracted.txt`, doar exemplul dat ca dovadă).
- Risc: regex-ul `PATTERN_TITLU_CAPITOL_SIMPLU` e generic („\d{1,2}\. Majusculă…”) — dacă vreun document are un rând scurt, cu majusculă la început, fără punctuație finală, urmat întâmplător de un marcaj „N.1.” fără legătură (coincidență de numerotare), ar putea fi tratat greșit ca titlu de capitol. Nu am găsit un asemenea caz în textele verificate, dar planner-ul ar trebui să valideze acoperirea și pe documentele neexemplificate explicit în handoff (NP 004, I9, NP 091).
- Risc task 3b: nu am putut verifica manual toate cele 4 exemple citate (NP 010 `4.6.(1)`, P 118/1 `1.2.1.`, NP 015 `5.8.`, I7 `4.1.1.`) contra textelor reale — logica e generică (orice chunk ≥2000 caractere cu subpuncte nu strict crescătoare rămâne nesplitat), dar merită confirmare pe acoperire că unificarea în chunk-uri de 1000 caractere nu scade sub prag.
