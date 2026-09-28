# R21 — Coder: raport

Fișier modificat: `D:\Omnia-MVP-r21-anexe\chunking_core.py` (singurul atins, conform constrângerilor).

## Ce am schimbat

1. **`PATTERN_ARTICOL`**: am scos alternativa `ANEXA\s+\d+\.\d+\.` — e înlocuită complet de mecanismul nou de regiuni de anexă (pct. 2). Comentariul actualizat.

2. **Prag „Art.” (regula 1)**: constantă nouă `PRAG_MARCAJE_ART = 50`. În `_extrage_segmente`, numărul de marcaje brute `PATTERN_ARTICOL_ART` din document decide dacă `PATTERN_ARTICOL_FARA_PUNCT` mai intră în lista de candidați:
   - dacă `len(marcaje_art) >= 50` → `PATTERN_ARTICOL_FARA_PUNCT` exclus complet din `toate` (P 118/1: 811+ marcaje „Art.” brute, deci exclus);
   - altfel → activ ca înainte (I7, I9, NP 057).
   Am verificat direct pe dovezi: toți identificatorii falși din dovezi (`27.3.`, `6.1.38.`, `3.2.11.`, `7.8.`, `1.25.`, `3.9.1.`, `48.6.`, `29.1.`, `8.7.`, `2.940.`) au forma cu punct final adăugat de `_baza_articol`, deci provin exclusiv din `PATTERN_ARTICOL_FARA_PUNCT` — dezactivarea lui îi elimină pe toți direct, fără nicio logică suplimentară.
   Notă: pragul se calculează pe **numărul brut** de potriviri `PATTERN_ARTICOL_ART` (înainte de filtrarea trimiterilor rupte), nu pe cele „recunoscute” final — evită dependența circulară (filtrarea unei potriviri foloseşte deja tot pipeline-ul). Diferența practică e nulă: documentele cu convenția P 118/1 au sute de marcaje brute, cele fără au zero.

3. **Regiuni de anexă (regula 2)**: două regex-uri noi.
   - `PATTERN_TITLU_ANEXA`: `\n[ \t]*ANEXA[ \t]+(\d+(?:\.\d+)?(?:\.?\([A-Za-z]\))?[A-Za-z]?)\.?[ \t]*` cu lookahead `(?=[\-–]|[A-ZĂÂÎȘȚŞŢ]|$)`, `re.MULTILINE`. Acoperă: `ANEXA 1  -`, `ANEXA 10 - CONSTRUCȚII EXISTENTE`, `ANEXA 2.1 -`, `ANEXA 1.` (NP 057, urmat de titlu pe rând nou), `ANEXA 1  ` (I9, urmat direct de `ANEXA 1.1  `), `ANEXA 3.4.(A).`. O virgulă sau literă mică după număr (`ANEXA 2.1, au caracter...`, I9) nu satisface niciuna din alternativele lookahead-ului → exclusă automat, fără verificare separată.
   - `PATTERN_MARCAJ_ANEXA_INTERN`: `\n[ \t]*A\.\d+\.[ \t]*(\d+(?:\.\d+){1,4}\.)[ \t]+(?=[A-Z...])` — prinde exact formatul `A.10. 2.7.7. Text...` din Anexa 10 P 118/1. Grupul include punctul final (ca la `PATTERN_ARTICOL_ART`), altfel logica de sufix lipit din `_extrage_segmente` ar fi dublat punctul (`ANEXA 10.2.7.7..`) — verificat manual pe exemplul de la rândul 37875.
   - În `_extrage_segmente`: stare secvențială `anexa_curenta` (inițial `None`), actualizată la fiecare potrivire `PATTERN_TITLU_ANEXA` (devine chunk propriu `articol_baza = "ANEXA {n}."`). Orice altă potrivire, cât timp `anexa_curenta` e activă, capătă `articol_baza` prefixat: `"ANEXA {n}." + baza_normala`. Practic, pentru P 118/1 (unde `PATTERN_ARTICOL_FARA_PUNCT` e dezactivat), singurul marcaj intern posibil e `PATTERN_MARCAJ_ANEXA_INTERN` (Anexa 10) — restul conținutului anexelor devine un singur chunk sub identificatorul anexei, ceea ce satisface direct criteriul „conținutul anexelor are identificatori anexa…”.
   - Titlurile/marcajele de anexă sunt scutite de `_este_data_zi_luna_an`/`_este_referinta_rupta` (au propria validare prin lookahead) și de `_este_titlu_capitol_simplu_valid` (nu se aplică).
   - Nu am adăugat propagare de context separată pentru titlul anexei: mecanismul existent `_contopeste_titluri` (nemodificat) o face deja generic, pe baza `articol_baza` cu prefix comun — funcționează identic cu titlurile de secțiune din R14, fără cod nou.

## Praguri și cazuri limită observate (I9, NP 057)

- **I9** folosește în continuare `PATTERN_ARTICOL_FARA_PUNCT` activ (sub prag), deci marcaje interne reale din corp (ex. „11.7”) rămân neschimbate acolo unde nu sunt în interiorul unei anexe; în interiorul unei anexe devin copii ai ei (`ANEXA N.11.7` etc.), evitând coliziunea cu articolul de corp cu același număr.
- **Caz limită neacoperit explicit, semnalat pentru tester/planner**: la I9, rândul 3037, textul „...utilizând standardul SR EN 12056-2 și\nANEXA 5.3.” e o trimitere ruptă pe rând nou (nu titlu), dar cu majusculă „ANEXA” (nu „Anexa” ca în P 118/1) — regex-ul de titlu o poate confunda cu un titlu real, pentru că fraza anterioară nu se termină cu unul din cuvintele-semnal existente (`art.`, `conform` etc., listate pentru marcaje numerice, nu pentru „ANEXA”). Nu am adăugat o euristică nouă pentru asta (nu era cerută explicit, risc de a strica titluri reale precedate de antete fără punctuație finală, ex. „ANEXE la Normativul... clădirilor” înainte de I9 `ANEXA 1`). Plasă de siguranță parțială: dacă documentul are și un titlu real „ANEXA 5.3” mai lung în altă parte, dedup-ul din `creeaza_chunkuri` (păstrează chunk-ul mai lung per identificator normalizat) elimină automat fragmentul fals, dar merită verificat explicit de tester (acoperire + numărul de chunk-uri pe I9).
- **NP 057** ("ANEXA 1.", titlu pe rând separat, urmat de titlul propriu-zis pe rândul următor): funcționează prin regula „sfârșit de rând” a lookahead-ului; textul propriu-zis al anexei (inclusiv linia de titlu text, ex. „TIPOLOGIA CLĂDIRILOR DE LOCUIT”) intră ca prim rând al conținutului anexei, nu separat.
- **`ANEXA 3.4.(A).`** (NP 057) normalizează la `anexa3.4.(a)` — validat că trece prin `_PATTERN_ARTICOL_NORMALIZAT` (`[a-z0-9().-]+`), fără caractere respinse.

## Ce nu am făcut

- Nu am scris/rulat teste (rol tester) și nu am rulat nimic (evaluare, preflight, reimport) — planner-ul verifică.
- Nu am atins `retrieval_core.py`, `main.py`, `generation_core.py`, `documente_noi/`, `evaluare/`.
- Nu am adăugat verificare specifică pentru rândul-tip 3037 din I9 (motiv detaliat mai sus) — recomand testerului un caz explicit pe acest tipar (referință ruptă pe rând nou cu „ANEXA” majuscul, fără cuvânt-semnal cunoscut înainte).

## Runda 2 — regresia „regiunea de anexă înghite corpul”

Cauza (confirmată pe text): titlul de la rândul 556 „ANEXA 10 - CONSTRUCȚII EXISTENTE”, din **cuprinsul** anexelor (rândurile 408–~600), nu era prins de regulile literale 1 și 2 din task (rândul următor „SECȚIUNEA I” nu e nici titlu, nici pagină; rândul anterior „ANEXA 9.2 - PUTERI CALORIFICE PENTRU CABLURI” nu se termină cu literă mică/virgulă/cuvânt de legătură) — rămânea acceptat ca titlu real, `anexa_curenta="10"` rămânea activ prin tot restul cuprinsului și prin tot corpul (capitolele 1–9, rândurile ~600–26219, 811 marcaje „Art.”) până la primul titlu real de anexă (rândul 26220). Am verificat manual: cel puțin rândurile 410 (`ANEXA 2.1`), 414 (`ANEXA 2.3`) și 420 (`ANEXA 3.2`) din cuprins scapă și ele de regulile 1+2 aplicate strict (rândul următor e text descriptiv, nu titlu/pagină; rândul anterior se termină cu majusculă) — dar rămân captivități scurte (2–4 rânduri), nu catastrofale, pentru că sunt urmate curând de un alt titlu (real sau de cuprins) care resetează starea.

Am implementat regulile 1 și 2 exact cum sunt descrise (`_este_titlu_anexa_de_cuprins` — rândul nevid următor e tot un titlu de anexă sau doar un număr de pagină; `_linia_anterioara_indica_continuare_anexa` — rândul nevid anterior se termină cu virgulă, literă mică sau unul din cuvintele „și, sau, din, la, în” ori din lista existentă `_CUVINTE_TRIMITERE_RUPTA`). Confirmat: acestea rezolvă cazul I9 rândul 3037 (rândul anterior se termină cu „și”).

**Plasă de siguranță suplimentară, nespecificată explicit în task, adăugată pentru că regulile 1+2 nu închid garantat cazul rândul 556** (verificat mai sus că scapă de ambele): în `_extrage_segmente`, orice potrivire `PATTERN_ARTICOL_ART` ([„Art. N.N.”, format exclusiv P 118/1) resetează `anexa_curenta = None` înainte de a-și calcula propriul `articol_baza`. Motivație: anexele P 118/1 nu-și încep niciodată propriile rânduri cu „Art. N.N.” (folosesc „A.N.” sau numere simple, verificat pe toate exemplele din dovezi) — deci întâlnirea unui asemenea marcaj e dovadă certă că am ieșit din orice regiune de anexă, indiferent dacă titlul care a deschis-o eronat a fost sau nu prins de regulile 1/2. Efectul: chiar dacă rândul 556 (sau alt titlu de cuprins nedetectat) rămâne acceptat greșit, starea se închide la primul „Art.” real întâlnit — adică imediat ce începe corpul propriu-zis (capitolul 1), nu după 25000+ rânduri. Rămân posibile câteva fragmente mici greșit etichetate `anexa10.xxx` strict în interiorul cuprinsului (rândurile 556–~600, înainte de primul „Art.” real), nu în corp.

**Nu am extins** aceeași plasă de siguranță la `PATTERN_ARTICOL_FARA_PUNCT`/`PATTERN_ARTICOL` pentru celelalte documente (I9, NP 057): dovezile Rundei 2 nu raportează o regresie de tip „înghițire totală” pentru ele (I9 era cazul izolat de la rândul 3037, deja acoperit de regula 2; NP 057 avea acoperire neschimbată) — nu am adăugat cod neverificat de nicio dovadă.

Actualizat: `chunking_core.py` — două funcții noi (`_este_titlu_anexa_de_cuprins`, `_linia_anterioara_indica_continuare_anexa`, plus helper `_urmatorul_rand_nevid` și constanta `_CUVINTE_CONTINUARE_ANEXA`), aplicate în filtrul din `_extrage_segmente`, plus resetul pe `PATTERN_ARTICOL_ART` descris mai sus.

## Runda 3 — acoperire și cuprinsul rupt pe două rânduri

1. **`acoperire_text_brut`**: regex nou `_PATTERN_MARCAJ_ANEXA_INTERN_ACOPERIRE = re.compile(r"A\.\d+\.")`, aplicat în `_normalizeaza_pentru_acoperire` înainte de `_PATTERN_MARCAJ_ARTICOL_ACOPERIRE`, ca să elimine prefixul „A.10.” din liniile brute din Anexa 10 — la fel cum chunker-ul îl mută deja în identificator. Nu am atins pragurile D24.
2. **Cuprins rupt pe două rânduri (P 118/1, ex. rândul 414 → titlul continuă la 415-416):** regulile din runda 2 nu-l prind (rândul următor nu e alt titlu imediat). Aplicat exact cerința: în `_extrage_segmente`, calculez `ultimul_art_start` = poziția ultimei potriviri `PATTERN_ARTICOL_ART` din document, doar când pragul e atins (`not fara_punct_activ`); orice `PATTERN_TITLU_ANEXA` cu `start() < ultimul_art_start` e ignorat complet (nu ajunge în `potriviri`, deci nu produce chunk și nu deschide regiune) — adăugat ca a treia condiție de respingere, alături de cele din runda 2. În documentele sub prag (I9, NP 057, I7), `ultimul_art_start` rămâne `None`, deci regula nu se aplică — comportament neschimbat față de runda 2.

Plasa de siguranță pe `PATTERN_ARTICOL_ART` din runda 2 rămâne neschimbată (acceptată de planner) — acum e redundantă parțial cu regula nouă (titlurile din cuprins sunt deja ignorate la sursă), dar am păstrat-o ca protecție suplimentară, fără cost.

## Runda 4 — „primul Art. acceptat”, fără plasa de resetare, continuare doar pe virgulă/cuvinte

1. **„ultimul marcaj Art.” → „primul marcaj Art. acceptat”**: în `_extrage_segmente`, `prim_art_start` e poziția primului `PATTERN_ARTICOL_ART` care nu e trimitere ruptă/dată (`_este_data_zi_luna_an`/`_este_referinta_rupta`, aceleași filtre ca pentru marcajele normale), calculat doar când pragul e atins. Motiv: în regiunea reală a anexelor apar trimiteri „Art.” (verificat: rândul 26351 `Art. 7.1.3.);`, 29484 `Art. 2.4.9.4. (2).`, 35900 `Art. 2.1.3..` — toate în corpul anexelor, nu în cuprins), deci „ultimul” marcaj brut împingea limita până aproape de sfârșitul documentului, ignorând 18 titluri reale de anexă (ANEXA 1, 2, 2.1–2.4, 3, 3.1–3.3 etc.).
2. **Am scos plasa din runda 2** (resetarea `anexa_curenta = None` la orice `PATTERN_ARTICOL_ART`): cu regula „primul Art. acceptat” nu mai e necesară pentru cuprins, iar rândurile 26351/29484/35900 sunt exact cazul pe care îl bloca greșit — trimiteri „Art.” în interiorul unei anexe reale ar fi închis regiunea la mijlocul ei.
3. **`_linia_anterioara_indica_continuare_anexa`**: am scos condiția „se termină cu literă mică”; rămân doar virgula și cuvintele de trimitere/legătură (`_CUVINTE_TRIMITERE_RUPTA`, `_CUVINTE_CONTINUARE_ANEXA`). Verificat pe legenda de la rândul dinaintea `ANEXA 4.5` („Figura 173 - Stație de pompare - Acces pe scara verticală” — se termina cu literă mică, respingea greșit titlul real). Cazul I9 3036–3037 rămâne respins („...și” e în `_CUVINTE_CONTINUARE_ANEXA`).

## Runda 5 — potrivire pe cuvânt întreg, nu pe sufix

Bug real preexistent (R14 runda 5), semnalat de teste: `_linia_anterioara_se_termina_cu_trimitere` și `_linia_anterioara_indica_continuare_anexa` foloseau `cuvant.endswith(sufix)` pe tot rândul lowercased, deci un cuvânt ca „stabilit.” era confundat cu trimiterea „lit.” (sufix, nu cuvânt). Am adăugat `_PATTERN_ULTIMUL_CUVANT_RAND` + helper `_ultimul_cuvant(linie)`: extrage ultimul cuvânt întreg al rândului (precedat de început de rând sau de un caracter care nu e literă, cu punctul final păstrat — „art.”, „lit.”, „pct.”, „alin.” rămân cuvinte cu punct), apoi ambele funcții verifică apartenența exactă la listele existente (`in`, nu `endswith`). Nu am schimbat listele de cuvinte (`_CUVINTE_TRIMITERE_RUPTA`, `_CUVINTE_CONTINUARE_ANEXA`) și nimic altceva.

## Ce ar trebui verificat de planner

- Rulare `pytest tests/test_chunking_core.py` și `tests/test_populare_db.py` (după ce testerul actualizează numerele fixe de chunk-uri, cum era deja anticipat în task).
- Preflight/import pe cele 9 documente, verificând: P 118/1 — 811/811 „Art.” proprii, acoperire ≥ 0,993, 0 articole `27.3`/`48.6`/`7.8`/`29.1`/`2.940`; I9 fără identificatori `ANEXA` pentru conținut dinainte de rândul 5162; celelalte documente cu acoperirea de dinainte de R21 (i5 0,979; i7 0,971; i9 0,969; np004 0,923; np010 0,999; np057 0,882; spitale 0,982; np091 0,989) și 0 neconsecutive.
- Toate cele 43 de titluri de anexă din corpul P 118/1 (după rândul 26220) produc cel puțin un chunk cu prefixul lor.
- Rândurile 26351/29484/35900 (trimiteri „Art.” în interiorul anexelor) nu mai închid greșit regiunea — verificat că anexele care le conțin rămân complete.
- Rândurile 410/414/420 din cuprinsul P 118/1 — verificat că devin fragmente mici, eliminate de dedup (nu apar ca `articol` final în chunk-urile importate).
- Reimport + evaluare pe setul de aur (≥ 27/30).
