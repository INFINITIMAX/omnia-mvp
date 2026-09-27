# R14 — Raport Coder: chunker unificat, titluri ca context, curățare antete MO

## Fișiere create

- `chunking_core.py` (nou): singura implementare de chunking, funcție publică
  `creeaza_chunkuri(text: str) -> list[dict[str, str]]`, determinstă, fără I/O.
  Expune și `ultimele_statistici()` (stare la nivel de modul, nu thread-safe —
  suficient pentru scripturi CLI locale, care rulează secvențial).

## Fișiere modificate

- `populare_db.py`: import `from chunking_core import creeaza_chunkuri`; șters
  corpul vechi al `creeaza_chunkuri` și constantele devenite nefolosite
  (`PATTERN_ARTICOL`, `PATTERN_LINIE_CUPRINS`, `PATTERN_SUBPUNCT`,
  `PROCENT_MAXIM_CAUTARE_CUPRINS`, `LUNGIME_MINIMA_CHUNK`,
  `LUNGIME_PENTRU_SPLIT_SECUNDAR`). Am păstrat `PATTERN_ARTICOL_NORMALIZAT` și
  `PATTERN_SPATIERE_ARTICOL` (folosite de `normalizeaza_articol`, neatinsă).
  Restul fluxului (gate-uri, statusuri, embeddings, DB) neschimbat.
- `manual_ingestion_preflight.py`: import
  `from chunking_core import MAX_CHUNK_CHARS as _MAX_CHUNK_CHARS` și
  `from chunking_core import creeaza_chunkuri as _creeaza_chunkuri_locale`
  (păstrează exact numele folosit de teste și de `preflight_pdf`). Șters
  corpul vechi al `_creeaza_chunkuri_locale` și constantele devenite
  nefolosite (`_PATTERN_ARTICOL`, `_PATTERN_LINIE_CUPRINS`, `_PATTERN_SUBPUNCT`,
  `_LUNGIME_MINIMA_CHUNK`, `_LUNGIME_SPLIT_SECUNDAR`, `_MAX_CHUNK_CHARS` local).
  Am păstrat `_PATTERN_SPATIERE_ARTICOL`, `_PATTERN_ARTICOL_NORMALIZAT`
  (folosite de `_normalizeaza_articol`) și `_valideaza_chunkuri_locale`
  neatinsă (validează folosind `_MAX_CHUNK_CHARS` importat).
- `retrieval_core.py`:
  - `PostgresRetrievalRepository.find_exact`: dacă interogarea exactă
    întoarce 0 rânduri, cade pe `_find_children` (metodă nouă), care rulează
    `articol_normalizat LIKE %s` cu parametrul `articol_normalizat + "."` +
    `"%"` (parametrizat, fără escapare — formatul `[a-z0-9().-]+` nu conține
    `%`/`_`), ordonat identic cu varianta exactă. Ambele variante (cu și fără
    `document_id`) păstrate.
  - `ArticleParser._is_known_article`: adăugată `_is_known_in` (static) —
    un articol e cunoscut dacă e exact în set SAU dacă există un articol
    cunoscut care începe cu `articol + "."`.
  - `_has_ambiguous_article` și ruta semantică neatinse.

## Decizii pe puncte (1a–1e)

- **1a (antete MO):** `PATTERN_ANTET_MO` pe rând întreg, tolerant la spații
  între cuvinte (`\s+`) și la `Â`/`A` din ROMÂNIEI. Rândurile doar-cifre
  (1–4 cifre) sunt eliminate dacă sunt la ≤3 „pași” de un antet (un pas =
  un rând gol sau doar-cifre traversat), mergând în ambele direcții și
  oprindu-se la primul rând care nu e nici gol, nici doar-cifre. Rândurile
  doar-cifre fără antet în apropiere rămân neatinse (celule de tabel).
  `antete_eliminate` numără doar rândurile de antet propriu-zise, nu și
  numerele de pagină alăturate (cea mai simplă interpretare a cerinței).
- **1b (cuprins):** păstrat `PATTERN_LINIE_CUPRINS` (puncte de conducere).
  Adăugat `_gaseste_taietura_cuprins_pe_pagini`: caută pe rânduri, în primele
  20% din text, secvențe de ≥5 perechi consecutive „linie titlu numerotat” +
  „linie doar-cifre” (`PATTERN_TITLU_CUPRINS` / `PATTERN_NUMAR_PAGINA`); dacă
  găsește o astfel de secvență, taie textul până la finalul ei. Tăietura
  finală e maximul dintre cele două euristici (puncte de conducere vs. pagină
  pe rând separat), aplicată o singură dată.
- **1c (titluri romane):** `PATTERN_TITLU_ROMAN` (`^\s*[IVXLC]{1,6}\.\s+...`,
  un singur rând) + `_este_majoritar_majuscul` (majoritate literă mare din
  litere, nu din tot rândul). Rândul e pur și simplu eliminat din text
  înainte de parsarea articolelor — nu mai „lipeşte” de articolul anterior și
  nu intră în text; nu forțează explicit un chunk nou (nu era cerut), doar
  scoate titlul din conținut.
- **1d (titluri de secțiune ca context):** segmentele sunt construite în
  ordinea din document (`_extrage_segmente`, păstrează atât `articol` cu
  sufix, cât și `articol_baza` brut, pentru verificarea de „copil”).
  `_contopeste_titluri` marchează un segment titlu dacă: text pe un singur
  rând, ≤200 caractere, nu se termină în `.`/`;`/`:`, și segmentul *imediat
  următor* (în ordinea documentului) e copil (`startswith(prefix)` cu
  `prefix != articol_baza`). Titlul primește `"{prefix} {text}"` ca prefix pe
  toți copiii **direcți** — descendenții cu exact un nivel de numerotare
  suplimentar (`rest.count(".") == 1` pe restul după prefix), nu și
  nepoții. Un segment fără copil imediat rămâne chunk normal, exact ca-n
  cerință. `titluri_contopite` numără segmentele marcate titlu.
- **1e (dedup):** neschimbată ca logică („cea mai lungă variantă câștigă”),
  dar acum numără explicit `duplicate_eliminate` (orice segment înlocuit sau
  respins la același `articol`). Am ales `ultimele_statistici()` (stare de
  modul, resetată la fiecare `creeaza_chunkuri`) în loc de o valoare de
  retur secundară, ca semnătura publică să rămână exact cea cerută în task.

## Ordinea aplicată în `creeaza_chunkuri`

antete MO → cuprins (ambele euristici) → titluri romane → parsare segmente →
contopire titluri → filtrare `LUNGIME_MINIMA_CHUNK` + dedup pe articol →
split secundar pe subpuncte (`LUNGIME_PENTRU_SPLIT_SECUNDAR=2000`) → limitare
la `MAX_CHUNK_CHARS=1000`.

## Teste existente atinse

- Nu am modificat niciun fișier din `tests/`.
- `tests/test_populare_db.py` importă `modul_ingestie.creeaza_chunkuri` — numele
  a rămas expus (acum via `from chunking_core import creeaza_chunkuri` la
  nivel de modul), deci importurile nu se rup. Testele mici (cuprins simplu,
  dedup, sufix din citat, articol nequotat) ar trebui să rămână verzi — nu
  ating antete MO, cuprins pe pagină separată, titluri romane sau
  contopire de titluri.
  **Risc:** `test_chunking_documentelor_deja_validate_ramane_neschimbat` are
  numere de chunk-uri fixate per document (i5_2022, i7_2011 etc.) și e
  explicit gândit ca „nu are voie să se schimbe” — dar tocmai asta schimbă
  R14, intenționat (eliminare titluri-doar, antete MO, cuprins, plus limita
  de 1000 caractere aplicată acum și în `populare_db`). E marcat
  `skipif not (ROOT_PROIECT / "documente_noi").exists()`, iar în acest
  worktree `documente_noi/` nu există, deci testul se sare automat la
  `pytest` local. Planner-ul trebuie să recalculeze numerele reale (pe
  `documente_noi/<id>/extracted.txt`, în mediul cu date) și să le dea
  Tester-ului spre actualizare — nu am ghicit valori.
- `tests/test_manual_ingestion_preflight.py`: `_creeaza_chunkuri_locale`
  rămâne accesibil cu aceeași semnătură (via alias de import); testul care îl
  apelează direct (`test_chunker_implicit_limiteaza_articol_lung...`) ar
  trebui să rămână verde (limita de 1000 e păstrată identic).

## Riscuri deschise / de verificat de planner

- Nu am putut rula `pytest` sau compara chunk-urile pe documentele reale —
  toate deciziile de mai sus (praguri, euristici) sunt din citirea codului și
  a task-ului, nevalidate prin execuție.
- Euristica de cuprins pe „pagină pe rând separat” (1b) presupune că liniile
  de titlu din cuprins nu au ele însele mai mult de un rând — dacă PDF-ul
  produce wrap de linie în mijlocul titlului din cuprins, secvența de 5 s-ar
  putea rupe; nu am avut text real NP 010 la îndemână ca să validez exact.
- `_este_majoritar_majuscul` (1c) folosește diacritice standard Python
  (`str.isupper()`), care recunoaște `Ă/Â/Î/Ș/Ț` corect în UTF-8; nu am testat
  cazuri cu caractere speciale suplimentare din extragerea PDF.
- Antetul MO (1a) nu acoperă variante de rând cu spații nestandard (ex.
  spații non-breaking ` `/` `) în interiorul frazei antetului — am
  folosit doar `\s+` (care include totuși aceste caractere, deoarece `\s` din
  Python cu re implicit acoperă și non-breaking space în mod Unicode... de
  verificat explicit dacă antetele reale din NP 057/I7 diferă vizibil de
  forma exactă din task).
- `find_exact`/`_find_children` din `retrieval_core.py` presupune că testele
  există deja pentru contractul de mock DB folosit (`_evidence_from_row`);
  nu am verificat exact fixture-urile din `tests/test_retrieval_core.py`.

## Runda 2 — corecturi (27-09-2026)

Fișiere atinse: `chunking_core.py`, `retrieval_core.py`. Nu am atins `populare_db.py`,
`manual_ingestion_preflight.py` sau `tests/`.

1. **Introducere-titlu la split pe subpuncte** (`chunking_core._aplica_split_secundar`):
   am extras helper-ul comun `_este_titlu(text)` (un rând, nevid, ≤200 caractere, fără
   `.`/`;`/`:` final) folosit acum atât aici, cât și în `_contopeste_titluri`. Dacă
   `introducere` (textul dinaintea primului `(1)`) e titlu, nu mai devine chunk propriu:
   devine `"{articol} {introducere}"`, pus ca prim rând în textul fiecărui subpunct din
   același articol lung. Funcția întoarce acum `(chunkuri, titluri_contopite)`, iar
   `creeaza_chunkuri` adună acest număr la `titluri_contopite` din `_contopeste_titluri`
   — e conceptual același fenomen (titlu consumat ca context), deci l-am pus în aceeași
   statistică, nu una nouă. Decizie în plus, neexplicit cerută: am făcut `_este_titlu`
   să refuze explicit text gol (`bool(text)`); fără asta, un segment fără text deloc
   ar fi fost tratat greșit ca „titlu” și în `_contopeste_titluri` din Runda 1 — corectare
   mică de robustețe, aceeași funcție fiind acum comună.
2. **`find_exact` cu o singură interogare SQL:** am înlocuit cele două interogări
   separate din Runda 1 (`find_exact` + `_find_children`, metodă ștearsă acum) cu una
   singură: `WHERE ... AND (chunk.articol_normalizat = %s OR chunk.articol_normalizat
   LIKE %s)`, parametri `(article_normalized, article_normalized + ".%")` (plus
   `document_id` primul, când e dat). În Python, dacă există rânduri cu potrivire
   exactă (`articol_normalizat == article_normalized`), le păstrează doar pe acelea;
   altfel întoarce toate rândurile LIKE (copiii). Ambele variante (cu/fără
   `document_id`) păstrate, aceeași ordonare ca înainte.
   **Risc raportat, nu remediat de mine:** `tests/test_api_integration.py::
   test_api_p1_restrictia_cu_articol_cunoscut_pastreaza_ruta_exacta[exact-miss-*]`
   (6 variante) verifică textul SQL exact — `assert "chunk.document_id = %s AND
   chunk.articol_normalizat = %s" in sql` și `assert parameters == ("doc-1",
   "4.4.7.2")` (tuplu de exact 2 elemente). Cu interogarea unificată, SQL-ul conține
   condiția în paranteză cu `OR`, nu acel șir exact, iar parametrii sunt 3 elemente
   (`document_id, article_normalized, prefix_like`), nu 2. Testul chiar verifică
   textul SQL exact — exact cazul pe care task-ul îl cere raportat, nu rescris de
   mine. Tester-ul trebuie să actualizeze acele 6 asserții (substring SQL +
   tuplul de parametri) ca să reflecte noua interogare unificată.
3. **Colofonul MO de final de fascicul** (`chunking_core._elimina_colofon_mo`, nou):
   am citit finalul celor 4 fișiere indicate (`D:\Omnia-MVP\documente_noi\
   {i5_2022,i9_2022,i7_2011,p118_1_2025}\extracted.txt`) — colofonul e identic în
   toate patru, ancorat pe oricare din trei rânduri fixe: `„Monitorul Oficial” R.A.,
   Str. Parcului...`, `Tiparul: „Monitorul Oficial” R.A.` (doar la I7) sau `Acest
   număr al Monitorului Oficial al României a fost tipărit în afara abonamentului.`
   (apare uneori înainte de blocul de colofon, ca în I7, alteori la final, ca în
   I5/I9/P118-1). `PATTERN_COLOFON_MO` (MULTILINE) caută oricare dintre cele trei,
   dar **numai** în ultimii `LUNGIME_FEREASTRA_COLOFON = 4000` caractere ai textului
   (realiniat la început de linie, ca `^` să nu prindă o linie tăiată la mijloc) —
   dacă găsește o potrivire, taie tot de acolo până la finalul textului. Rulează
   după `_elimina_antete_mo` (antetul de pagină + „126”/„473” alăturate dispar deja)
   și înainte de `_elimina_cuprins`/titluri romane. Am ales 4000 ca prag generos:
   blocul de colofon are ~500–700 caractere; 4000 lasă loc și pentru eventuale
   rânduri de tabel/note terminale fără riscul de a ajunge în corpul propriu-zis al
   ultimului articol real (nu am putut testa exact pe date, e o alegere rezonabilă,
   nu verificată prin execuție).
4. **Date `ZZ.LL.AAAA` tratate ca articole** (`chunking_core._este_data_zi_luna_an`,
   nou): `PATTERN_DATA_ZI_LUNA_AN` (`^(0[1-9]|[12]\d|3[01])\.(0[1-9]|1[0-2])\.$`)
   verifică dacă grupul capturat de `PATTERN_ARTICOL` e exact „zi.lună.” (2 segmente,
   fără al treilea), iar dacă imediat după acesta urmează 4 cifre neîntrerupte de alt
   punct (anul), potrivirea e exclusă din lista de segmente înainte de a construi
   chunk-urile — nu devine articol, iar textul din jur rămâne atașat segmentului
   anterior valid (nu se pierde nimic, doar nu se mai rupe la acel punct). Am
   verificat concret pe P 118/1: „15.01.2024” (linie ruptă la extragerea PDF, textul
   începe cu „15.01.2024 al Comitetului...”) și „18.12.2024” (singur pe rând) — ambele
   ar fi produs articolul spuriu „15.01.”/„18.12.” fără acest filtru.
5. Nu am schimbat nimic altceva față de Runda 1.

## Runda 3 — marcajul „Art.” din P 118/1 (27-09-2026)

Fișiere atinse: doar `chunking_core.py`. Nu am atins `retrieval_core.py`,
`populare_db.py`, `manual_ingestion_preflight.py` sau `tests/`.

1. **Marcaj „Art.” nou** (`PATTERN_ARTICOL_ART`): `\n\s*„?\s*Art\.\s*(\d+\.\d+\.
   (?:\d+\.){0,4})\s*(?=[A-ZĂÂÎȘȚŞŢ]|\()` — cere explicit ca după număr să existe
   fie același rând cu spațiu + majusculă/`(` (cazul obișnuit, ex. „Art. 1.1.1.
   (1) Prezentul...”), fie doar spații/newline până la conținutul real de pe
   rândul următor (ex. „Art. 1.1.11.  \n(1) În prezentul...”, verificat concret
   la linia 981 din extracted.txt) — de-asta am folosit `\s*` (zero sau mai mult),
   nu un singur spațiu obligatoriu: `\s*` se oprește oricum la primul caracter
   ne-spațiu, deci un rând rupt ca „Art. 2.4.5.4.., ” sau „Art. 2.4.5.4., …”
   eșuează la verificare imediat (primul caracter după număr e „.”/„,”, nu
   spațiu, nu majusculă/`(`), fără cod separat pentru cele două exemple din
   task — regula unică le acoperă pe amândouă. Identificatorul segmentului
   rămâne exact numărul (fără „Art.”), la fel ca la marcajele numerice simple,
   ca regula 1d de contopire a titlurilor să funcționeze neschimbată (verificat
   pe exemplul din task: linia 7221 „2.3.6.1. Prevederi generale...” urmată de
   linia 7224 „Art. 2.3.6.1.1. Închiderile perimetrale...” — segmentul titlu
   „2.3.6.1.” își găsește copilul direct „2.3.6.1.1.” fără nicio modificare la
   `_contopeste_titluri`).
2. **Trimiteri rupte pe rând pentru marcajul numeric simplu**
   (`_este_referinta_rupta`, nou): pentru un segment al cărui `articol_baza` e
   pur numeric (`^\d+(?:\.\d+)*\.$`), dacă imediat după număr urmează `)`, `,`,
   `;` sau `.`, segmentul e exclus din listă înainte de construirea chunk-urilor
   — textul rămâne atașat segmentului anterior valid. Un număr urmat imediat de
   `(` (format `4.2.(7)`) nu intră în această verificare (nu e în lista de
   caractere respinse) și rămâne tratat ca până acum, prin mecanismul de sufix
   existent. Verificat concret pe P 118/1, linia 5313 („Art. 2.3.2.1.2.; 4 -
   planșeu...” — de fapt un marcaj „Art.” cu referință rerută imediat după, deja
   respins de propria regulă a punctului 1, dar am confirmat separat și cazuri
   pur numerice de acest tip în alte fișiere din corpus) și linia 26351
   („Art. 7.1.3.);” — respins tot de regula 1, nu de asta) — exemplul canonic
   pentru regula 2 e formatul generic descris în task (`2.3.6.1.7.), se
   poate…`), pe care l-am implementat literal, fără să găsesc o instanță
   identică de verificat separat în P 118/1 (marcajele numerice rupte din acest
   fișier sunt aproape toate pe formatul „Art.”, deja acoperite de punctul 1).
3. **`_extrage_segmente`** combină acum potrivirile din `PATTERN_ARTICOL` și
   `PATTERN_ARTICOL_ART` într-o singură listă, sortată după poziția din text
   (`sorted(..., key=lambda m: m.start())`), înainte de a aplica filtrele de
   date/referințe-rupte și de a construi segmentele. Restul pipeline-ului
   (`_contopeste_titluri`, dedup, split secundar, limita de 1000) e neschimbat
   — funcționează identic indiferent care pattern a produs segmentul, pentru
   că ambele expun aceeași formă de `re.Match` cu grupul 1 = doar numărul.
4. Nu am schimbat nimic altceva.

**Riscuri noi deschise:** `\s*` din `PATTERN_ARTICOL_ART` sare peste orice rulaj
de spații/newline-uri consecutive, nu doar peste un singur rând — dacă undeva
în corpus există un „Art. N.N.” urmat de mai multe rânduri goale înainte de
conținutul real, tot ar valida (probabil corect, dar nu e un caz verificat
explicit). Nu am rulat pytest și nu am comparat efectiv numărul de chunk-uri
înainte/după pe P 118/1 — doar am citit manual liniile relevante din
`extracted.txt` pentru fiecare regulă.

## Runda 4 — pierdere de conținut și D18 (27-09-2026)

Fișier atins: doar `chunking_core.py`. Nu am atins `retrieval_core.py`,
`populare_db.py`, `manual_ingestion_preflight.py` sau `tests/`.

1. **Regresie D18 corectată:** am rescris `_este_referinta_rupta` complet, ca
   verificare pozitivă (allow-list), nu deny-list ca în Runda 3. Pentru un
   marcaj numeric simplu, după număr (sărind orice spații inline) trebuie să
   urmeze: majusculă (inclusiv diacritice `ĂÂÎȘȚŞŢ`), „, `(`, o cifră, sau
   sfârșitul rândului/textului — altfel e trimitere ruptă. Excepție separată
   pentru virgulă (cerința D18): dacă imediat după număr urmează `,` **și**
   după virgulă nu mai e decât spații până la capătul rândului, marcajul e
   valid (virgula se elimină apoi prin mecanismul de sufix existent,
   neschimbat); dacă virgula e urmată de alt conținut pe același rând
   (`1.1.,text`), rămâne trimitere ruptă. Am verificat manual toate cele 5
   cazuri din `test_pipeline_implicit_valideaza_articolul_si_refuza_caractere_
   neacceptate` (fără să rulez testul): „1.1.\nText...” (valid, sfârșit de
   rând), „1.1.,\nText...” (valid, virgulă-delimitator), „1.1.(1),\nText...”
   (valid, neatins de regula asta — „(” apare imediat, nu virgula), „1.1./”
   și „1.1.,text” (ambele invalide → listă de segmente goală → `invalid_chunks`,
   același rezultat final ca înainte, doar prin alt mecanism intern: articolul
   nu mai apare deloc, în loc să apară invalid).
2. **Trimiteri cu literă mică** (P 118/1, ex. linia 5420 „2.3.2.1.2. lit. a);”
   — provine dintr-o linie ruptă la extragere: „...definiți la Art. ” + rând
   nou „2.3.2.1.2. lit. a); ”): aceeași funcție rescrisă de la punctul 1
   acoperă și asta — „l” (literă mică) nu e în allow-list, deci marcajul e
   respins direct, fără cod separat. Verificat manual pe liniile 5419-5420,
   5750-5751, 6063-6064.
3. **Cuprins fără numere de pagină** (P 118/1, liniile 175-234+: titluri unul
   sub altul, fără pagini): am rescris `_contopeste_titluri` (acum întoarce
   `(titluri_contopite, titluri_cuprins_eliminate)`). Pentru fiecare segment
   care „arată a titlu” (criteriul 1d neschimbat), verific întâi dacă numărul
   lui are **vreun** descendent oriunde în document (`bazele` = lista tuturor
   `articol_baza`, verificare `any(...)`, O(n) per titlu candidat — pe
   documente de câteva mii de segmente, acceptabil, nu am optimizat cu o
   structură indexată ca să nu adaug abstracții peste ce cere sarcina). Dacă
   nu are niciun descendent nicăieri → rămâne chunk normal, exact ca-nainte
   (comportament neschimbat pentru cazul de bază). Dacă are descendenți
   undeva: dacă segmentul imediat următor e chiar copilul lui → se contopește
   exact ca înainte (`contopite`); altfel → e marcat `este_titlu = True` și
   eliminat direct, fără propagare de context (`cuprins_eliminate`), fiindcă
   e o intrare de cuprins duplicat, nu titlul real. Statistica nouă
   `titluri_cuprins_eliminate` e expusă în `ultimele_statistici()`. Verificat
   pe exemplul din task: intrarea de cuprins „2.3.2.1. Pereți antifoc...”
   (linia 183, urmată imediat de altă intrare de cuprins „2.3.2.2....”, deci
   nu e copil) se elimină; intrarea reală din corp, cu același text (linia
   5164, urmată imediat de „Art. 2.3.2.1.1....”, care e copil direct) se
   contopește normal.
   **Risc explicit:** regula elimină orice titlu-candidat cu un descendent
   **oriunde** în document, nu doar în vecinătate. Dacă în alt document (nu
   verificat pe corpusul curent) o numerotare se reia coincidental în alt
   capitol (ex. „3.1.” fără copil imediat, dar există și un „3.1.5.”
   independent, întâmplător, în altă secțiune), acel „3.1.” ar fi eliminat
   integral, nu doar transformat — pierdere de conținut reală, nu doar
   context. Nu am găsit un asemenea caz în P 118/1, dar nu am verificat toate
   cele 8 documente din corpus.
4. **Prefix dublat la split pe subpuncte, corectat:** `_extrage_segmente`
   adaugă acum câmpul `are_context_parinte` (implicit `False`) pe fiecare
   segment; `_contopeste_titluri` îl setează `True` pe fiecare copil direct
   căruia îi prepend-uiește contextul părintelui. `creeaza_chunkuri` adună
   `articole_cu_context_parinte` (setul de valori `articol` cu acest flag) și
   îl transmite la `_aplica_split_secundar(chunkuri, articole_cu_context_
   parinte)`. Acolo, când `introducere` (textul dinaintea primului subpunct)
   arată a titlu ȘI articolul chunk-ului e în acest set, `introducere` devine
   context **ca atare** (fără `f"{chunk['articol']} "` în față) — pentru că
   introducerea respectivă e deja titlul părintelui injectat mai devreme de
   `_contopeste_titluri`, nu titlul propriu al articolului curent. Am ales să
   nu incrementez `titluri_contopite` în acest caz (nu e o contopire nouă, e
   aceeași injectată deja numărată la pasul 3d/Runda 2). Flag-ul e ținut
   separat, într-un `set` extern la nivel de `creeaza_chunkuri`, nu ca o cheie
   suplimentară pe dict-ul final de chunk — altfel aș fi rupt egalitatea
   exactă de dict așteptată de testele existente (`{"articol":..., "text":...}`).
5. Nu am schimbat nimic altceva.

**Nu am rulat pytest** și nu am comparat efectiv numărul de chunk-uri
înainte/după pe P 118/1 pentru Runda 4 — verificare doar prin citire manuală a
liniilor indicate din `extracted.txt` și urmărirea logicii pas cu pas pentru
fiecare caz din testul D18 menționat.

## Runda 5 — trimiteri rupte după „Art.” (27-09-2026)

Fișier atins: doar `chunking_core.py`. Nu am atins `tests/`.

1. **Regulă nouă** (`_linia_anterioara_se_termina_cu_trimitere`, apelată din
   `_este_referinta_rupta`, înaintea verificărilor existente): caută înapoi de
   la poziția marcajului, sărind rândurile goale, ultimul rând nevid; dacă
   acesta se termină (după `strip()` și lowercase) cu `art.`, `articolul`,
   `alin.`, `pct.`, `lit.` sau `conform`, marcajul e o continuare de trimitere
   ruptă și rămâne text. Am lowercase-uit rândul întreg înainte de verificare,
   deci lista de 6 cuvinte acoperă automat și „Art."/"Articolul" cu majusculă,
   fără să enumăr formele cu majusculă separat. Verificarea se aplică prin
   același guard existent (`baza` pur numerică) atât marcajelor numerice
   simple, cât și celor „Art. N.N....” — ambele produc un `articol_baza` pur
   numeric, deci funcția nu are nevoie să distingă sursa regexului.
2. Verificat explicit pe exemplul din task (rândurile 18975–18986, P 118/1):
   linia 18979 se termină cu „...se respectă prevederile Art. ”, iar linia
   18980 („2.3.2.1.2. (1) alin. a); parcajele...”) e acum respinsă corect —
   rămâne text al articolului „Art. 3.2.11.20.”, punctele b) și c) nu mai
   ajung într-un duplicat fals al lui 2.1.3.5.

**Tipuri de duplicate rezolvate de Runda 5 (verificate prin citire directă,
nu prin rulare):**
- **Trimiteri din legende de figuri, cu „conform” la capăt de rând** —
  cazul cel mai frecvent găsit: „Legendă Figura 32: ...perete antifoc
  conform\nArt. 2.3.2.1.2.” (linia 5295-5296), repetat identic la liniile
  5303-5304 și 5359-5360 — toate trei resping acum corect „Art. 2.3.2.1.2.”
  ca trimitere ruptă (linia anterioară se termină cu „conform”). Înainte de
  Runda 5, acestea creau 3 duplicate false ale articolului real de la linia
  5178, aruncate de dedup pe rând (deci non-determinist care variantă
  supraviețuia).
- **Trimiteri încrucișate „conform Art. N.N....” pe rând nou** — „Art.
  2.4.4.3.1. ... conform\nArt. 2.4.4.2.1. alin. (1).” (liniile 8556-8557) și
  „...conform\nArt. 2.3.1.2. și Tabelul 5.” (liniile 10019-10020) — ambele
  respinse acum corect, articolele reale (2.4.4.2.1. de la linia 8418,
  2.3.1.2. de la linia 5041) rămân singurele variante.
- **Trimiteri „prevederile Art.\nN.N....”** — exemplul canonic din task
  (linia 18979-18980), variantă fără „conform”, cu „Art.” însuși la capăt de
  rând anterior.

**Tipuri de duplicate care probabil rămân** (nu le-am putut verifica
exhaustiv fără rulare, doar prin eșantion de citire, pe primele ~250 din
811 marcaje „Art.” din P 118/1):
- Trimiteri rupte pe rând nou introduse de alte cuvinte decât cele 6 din
  listă — ex. „vezi”, „potrivit”, „menționate la”, „așa cum rezultă din” —
  dacă există în corpus și nu se termină cu unul din cuvintele acoperite,
  tot ar produce un duplicat fals. Nu am găsit un exemplu concret de acest
  tip în eșantionul citit, dar nu am verificat tot fișierul.
- Duplicate „legitime” rămase din alte cauze decât trimiteri rupte pe rând —
  ex. conținut reprodus identic în două locuri din text (nu am identificat
  un asemenea caz concret prin citire, doar semnalez posibilitatea).
- Nu am verificat celelalte 7 documente din corpus pentru tipare similare.

Nu am schimbat nimic altceva. Nu am rulat pytest.

## Runda 6 — numere de articol fără punct final (I7) (27-09-2026)

Fișier atins: doar `chunking_core.py`. Nu am atins `tests/`.

1. **Marcaj nou** `PATTERN_ARTICOL_FARA_PUNCT`: `\n\s*„?\s*(\d+\.\d+(?:\.\d+)
   {0,4})[ \t  ]+(?=[A-ZĂÂÎȘȚŞŢ„(])` — minimum 2 componente, fără
   punct după ultima, urmate obligatoriu de cel puțin un spațiu și apoi
   majusculă/diacritice/„/( (nu și cifră sau sfârșit de rând, spre deosebire
   de allow-list-ul general din `_este_referinta_rupta` — exact cum cerea
   task-ul, ca să nu confund valori zecimale cu articole).
2. **Coliziune cu marcajul vechi, rezolvată prin deduplicare pe poziție:**
   pentru „3.1.5.7 Amplasarea...”, `PATTERN_ARTICOL` (varianta cu punct)
   TOT potrivește parțial — prinde doar „3.1.5.” (se oprește la ultima
   componentă fără punct, care nu poate completa grupul opțional `(?:\d+\.)`
   care cere punct după cifră). Ambele marcaje pornesc din exact aceeași
   poziție (`\n` de dinaintea liniei). Am sortat toate potrivirile combinate
   (`PATTERN_ARTICOL` + `PATTERN_ARTICOL_ART` + `PATTERN_ARTICOL_FARA_PUNCT`)
   după `(start, -lungime_grup_capturat)` și am păstrat, pentru fiecare
   poziție de start, doar prima (deci cea cu grupul cel mai lung) —
   „3.1.5.7” (7 caractere) câștigă în fața lui „3.1.5.” (6 caractere).
   Verificat manual și pe „3.2.1 Generalități” (linia 1739): varianta veche
   ar fi prins doar „3.2.” (2 componente, fiindcă a treia cifră „1” nu are
   punct după ea), varianta nouă prinde „3.2.1” întreg — câștigă cea nouă.
3. **Identificator normalizat prin `_baza_articol`** (helper nou, folosit
   acum uniform în `_este_data_zi_luna_an`, `_este_referinta_rupta` și
   `_extrage_segmente`): adaugă punctul final dacă lipsește, o singură dată,
   înainte de orice altă verificare. Așa `3.1.5.7` devine intern identic cu
   `3.1.5.7.`, iar regulile din rundele 3-5 (trimitere ruptă, literă mică,
   rând anterior terminat în „conform”/„Art.” etc., dată ZZ.LL.AAAA) se aplică
   automat și marcajelor fără punct, fără cod duplicat — funcțiile lucrează
   pe același format normalizat, indiferent ce regex a produs potrivirea.
   Logica de sufix (citate cu virgulă) rămâne neatinsă pentru acest marcaj:
   fiindcă regex-ul cere explicit spațiu imediat după număr, poziția de
   după grupul capturat e mereu spațiu, deci sufixul `[^\s]+` nu se
   potrivește niciodată acolo — consistent cu comportamentul deja stabilit
   pentru marcajul „Art.” la rundele anterioare.
4. **Verificare prin citire pentru fals-pozitive** (cerută explicit la
   punctul 2 din task), pe I7, I5, I9, NP 057:
   - I5: zeci de titluri reale de secțiune fără punct final, cascadă întreagă
     în capitolul 6 („6.1 Clădiri de locuit”, „6.1.1 Ipoteze de proiectare”,
     „6.8.2.1 Ventilarea prin aspirație” etc.) — toate conținut real, niciun
     fals-pozitiv găsit.
   - NP 057: un singur caz găsit, „3.1.2.1.2 Evitarea vibrațiilor
     excesive...” (linia 367) — conținut real.
   - I9: niciun rând de acest tip în tot documentul (verificat cu grep pe
     întregul fișier) — regula nu are efect deloc aici.
   - **I7 — un fals-pozitiv real găsit:** liniile 218-219, în zona de cuprins
     de la începutul documentului: „5.1.1. Condiții de funcționare conform
     cu recomandările din SR HD 60364-5-51 úi SR HD” urmat de rândul nou
     „384.3 S2”. Acesta e un cod de standard rupt la extragerea PDF (`SR HD
     384.3-S2`), nu un articol. „384.3” (2 componente) + spațiu + „S2”
     (majusculă) satisface exact regula nouă și devine un marcaj fals.
     **Impact real, verificat prin citire (nu prin rulare):** textul „384.3
     S2” taie prematur textul segmentului cuprins „5.1.1.” (pierde „384.3
     S2” din coada lui), iar noul marcaj „384.3” capătă doar textul „S2”
     (2 caractere) — sub `LUNGIME_MINIMA_CHUNK` (15), deci e filtrat automat,
     nu devine chunk vizibil. Cum „5.1.1.” e oricum o intrare de cuprins
     (foarte probabil eliminată de mecanismul din Runda 4, having copii reali
     în corpul documentului), impactul practic pare minor — o pierdere de
     2 cuvinte („384.3 S2”) dintr-un fragment de cuprins care oricum nu
     ajunge chunk. Nu am schimbat regula pentru acest caz, fiindcă task-ul
     cerea doar verificare prin citire, nu o corecție suplimentară
     (`Nu schimba altceva`); îl semnalez explicit ca risc cunoscut.
5. Nu am schimbat nimic altceva. Nu am rulat pytest.

## Runda 7 — tăierea cuprinsului aruncă începutul I7 (27-09-2026)

Fișier atins: doar `chunking_core.py`. Nu am atins `tests/`.

1. **Ambele stiluri de cuprins recunoscute doar ca bloc**, nu la prima/ultima
   potrivire izolată: am scris `_capatul_primului_bloc_cuprins`, folosită de
   ambele euristici (`lungime_intrare=1` pentru puncte de conducere,
   `lungime_intrare=2` pentru titlu+pagină pe rândul următor). Acumulează
   indicii intrărilor găsite în primele 20% din text; între finalul unei
   intrări și începutul următoarei tolerează cel mult
   `DISTANTA_MAXIMA_INTRARE_CUPRINS = 3` rânduri **nevide** (titlurile lungi
   rupte pe 2-3 rânduri, ca la NP 057 rândurile 58-60 sau 73-75, nu întrerup
   blocul). Cere minimum `NUMAR_MINIM_INTRARI_CUPRINS = 5` intrări ca blocul
   să conteze; taie la finalul **primului** bloc care atinge pragul, nu la
   ultima potrivire din tot intervalul de 20%.
2. **`PATTERN_LINIE_CUPRINS` ridicat de la minimum 2 la minimum 4 puncte**
   consecutive (`\.{4,}`). Verificat exact pe exemplul din task: I7 rândul
   3808 „...cu timpi de declanúare între 150...500” are doar 3 puncte între
   „150” și „500” — cu pragul nou nici măcar nu mai e o potrivire candidată,
   deci nu poate porni sau extinde niciun bloc. Chiar dacă ar fi avut 4+
   puncte, tot n-ar fi tăiat nimic: e o potrivire complet izolată (fără alte
   4 potriviri în raza de 3 rânduri nevide), deci `len(bloc) < 5` și
   `_capatul_primului_bloc_cuprins` întoarce 0 pentru acel bloc.
3. **Verificat pe NP 057 (rândurile 51-109)** că blocul real de cuprins tot
   se detectează corect cu regula nouă, deși amestecă ambele stiluri: liniile
   52-75 și 78-109 sunt aproape toate „puncte de conducere” (peste pragul de
   4 puncte, majoritatea cu zeci de puncte), dar rândurile 76-77 („3.1.
   Rezistența și stabilitate” / „99”, fără puncte deloc) sunt stilul
   „pagină pe rândul următor” — un gol de 2 rânduri nevide pentru detectorul
   de puncte, sub pragul de 3, deci blocul de puncte trece peste ele fără să
   se rupă. Tăierea finală (`max` între cele două euristici, neschimbat)
   cade corect la finalul rândului 109 („Anexa 3.6. Documente conexe
   .................... 191”), exact cum descrie task-ul ca fiind deja
   corect înainte de rundă.
4. Nu am schimbat nimic altceva. Nu am rulat pytest — verificare doar prin
   citirea directă a celor două fișiere indicate și urmărirea logicii pas cu
   pas (numărat manual liniile, punctele și golurile pentru ambele exemple).
   Nu am verificat exhaustiv restul documentelor din corpus pentru cuprinsuri
   cu structuri și mai neregulate.

## Ce nu am făcut

- Nu am scris/modificat teste (conform constrângerilor); nu am rulat nicio
  comandă.
- Nu am atins `main.py`, `generation_core.py`, `access_control.py`,
  `static/`, `supabase/`, `.env`, `documente_noi/`.
