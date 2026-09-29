# R26-B — Raport coder: consolidarea P 118/2 și P 118/3

## Fișiere create
- `D:\Omnia-MVP-r26\consolidare_normative.py` — modulul nou (fără I/O implicit, fără rețea/DB; CLI la final).
- `D:\Omnia-MVP\documente_noi\p118_2_2013\manifest_6026_2018.json` — 64 de operații (Runda 3: item 24 din nou `manual: true`, cu nota discrepanței „al”/„ale”; restul, 63, aplicabile automat).
- `D:\Omnia-MVP\documente_noi\p118_3_2015\manifest_6025_2018.json` — 18 operații + `inlocuiri_globale` (Art. II).
- `D:\Omnia-MVP\documente_noi\p118_2_2013\metadata.json`
- `D:\Omnia-MVP\documente_noi\p118_3_2015\metadata.json`

Nu am atins niciun alt fișier Python, nici `baza.txt`/ordinele/`source.pdf`.

## Cum funcționează modulul (pe scurt)
1. `segmenteaza_ordin(text)` — taie Art. I…Art. II, apoi caută markerii `^N.` consecutivi (1, 2, 3…); fiecare item e împărțit în `instructiune` (până la „cuprins:” sau „se abrogă.”) și `text_nou` brut.
2. `aplica_operatii(baza, itemi, manifest)`:
   - verifică că mulțimea de `nr` din manifest coincide exact cu cea segmentată din ordin;
   - pentru fiecare operație (dacă nu e `manual`), verifică prin regex că `instructiune` conține cuvântul-cheie al tipului și numărul punctului/subunității declarate (cu toleranță pentru intervale „X—Y” și pentru cazul în care ordinul citează punctul-părinte, dar ținta reală e singurul lui copil, ex. 3.7.13 → 3.7.13.1 în P 118/3);
   - localizează fiecare țintă în `baza.txt` (regex ancorat la început de rând, exact o potrivire obligatorie, exclude liniile de cuprins via `chunking_core.PATTERN_LINIE_CUPRINS`);
   - verifică lipsa suprapunerilor, aplică de la sfârșit spre început, adaugă marcajul de proveniență pe rând propriu (regex-ul din `R26-C-coder.md`);
   - la final: fiecare `text_nou` normalizat apare literal în rezultat, textul vechi nu mai apare (cu excepția subșirurilor textului nou), iar numărul de marcaje din rezultat egalează numărul de ținte nemodificate global.
3. Reutilizează trei constante **publice** din `chunking_core` (`PATTERN_ANTET_MO`, `PATTERN_NUMAR_PAGINA`, `PATTERN_LINIE_CUPRINS`) ca să nu dubleze acea logică — nu modifică fișierul.
4. CLI: `python consolidare_normative.py --baza … --ordin … --manifest … --iesire … --raport …`, scriere atomică (temp file + `os.replace`) pentru ambele ieșiri.

## Manifeste — ancorele alese și deciziile
### P 118/2-2013 (Ordinul 6.026/2018, MO 966/15.11.2018)
- 63 de operații localizate prin numărul punctului/subunității (fără text copiat în manifest); doar 6 folosesc `inlocuieste_bloc` cu ancore text din `baza.txt`:
  - Tabelul 8.1: `"Tabelul 8.1"` → `"8.32. Densitatea de pulverizare a apei, proiectată, pentru stingerea incendiilor de produse"`.
  - Anexa 3: `"ANEXA NR. 3"` → `"ANEXA NR. 4"`.
  - Anexa 6: `"ANEXA NR.6"` → `"ANEXA NR. 7"`.
  - Observația 3 din Anexa 7: `"3. Pentru stabilirea debitelor la clădiri cu mai multe compartimente de incendiu, debitul se"` → `"4. Valorile din paranteze se aplică pentru construcțiile echipate cu instalații de stingere cu"`.
  - Anexa 8: `"ANEXA NR. 8"` → `"ANEXA NR.9"`.
  - Anexa 9: `"ANEXA NR.9"` → `"ANEXA NR.10"`.
  - Am verificat manual (grep) unicitatea fiecărei ancore în `baza.txt`; nu am citit integral fișierul (13232 rânduri) — planner ar trebui să confirme unicitatea la prima rulare reală (eroarea „N potriviri” e fail-closed, deci nu poate trece silențios).
- Itemi cu ținte multiple (`4.29`+`4.30`, `6.1` alin. (1)+(4), `7.60–7.62`, `12.11`+`12.12`, `13.21–13.23`, `13.31` lit. a)+f)): am declarat `marcaj_text_nou` explicit acolo unde textul din ordin e încadrat în ghilimele tipografice „ ” (stilul 6026), fiindcă ghilimeaua e lipită de primul marcaj și altfel căutarea „început de rând” ar rata prima țintă.
- **Item 24**: inițial marcat `manual: true`; în Runda 2 am adăugat tipul `inlocuieste_sintagma_in_bloc` și am scos flag-ul — vezi secțiunea „Runda 2” de mai jos pentru detalii și un risc semnalat (posibilă discrepanță „al”/„ale” între ordin și `baza.txt`).

### P 118/3-2015 (Ordinul 6.025/2018, MO 977/19.11.2018)
- 18 operații + `inlocuiri_globale` (Art. II: „instalații de detectare, semnalizare și avertizare” → „…și alarmare”, tolerant la spații via `\s+` între cuvinte).
- Item 6 (tabelele 3.4 și 3.5): tratat ca **un singur** `inlocuieste_bloc` (ordinul rescrie ambele tabele ca bloc contiguu) — ancore `"Tabelul 3.4"` → `"3.7.4 Amplasarea detectoarelor sub tavane/acoperișuri, platforme"`.
- Item 7: ordinul spune „punctul 3.7.13, alineatul (2)”, dar în `baza.txt` 3.7.13 e doar titlul secțiunii, iar alineatul (2) e de fapt sub `3.7.13.1` (singurul copil direct). Am declarat ținta ca `{"punct": "3.7.13.1", "alineat": "2"}` și am adăugat în modul o regulă de validare care acceptă acest caz (punctul declarat e copil direct al celui citat în instrucțiune).
- Item 15 (partea introductivă a 5.2.5) și item 16 (imbricat: 5.3.5 alin. (2) litera c)) — verificate manual în `baza.txt` (formatul chiar corespunde: „(2) Aceste cabluri sunt cele care asigură: a) … c) conectarea dintre ECS și panourile repetoare de semnalizare…”).
- Am verificat prin citire directă formatul punctelor de adâncime ≥3 fără punct final (`3.2.2`, `3.3.1`, `3.8.2.5` etc., cu spațiu în loc de punct) — regex-ul de localizare din modul (`punct + (?:\.|[ \t])`) le acoperă pe ambele stiluri.

## Ce nu am făcut / ambiguități
- **Nu am rulat modulul.** Nu am cum să confirm că fiecare din cele ~63+18 localizări chiar produce exact o potrivire în `baza.txt` — am verificat prin grep punctual doar o parte semnificativă (toate blocurile, toate subunitățile imbricate/introductive, câteva zeci de puncte simple), nu fiecare dintre cele ~80 de ținte individual. Planner-ul trebuie să ruleze CLI-ul pe ambele perechi bază+ordin+manifest și să citească raportul JSON — orice eroare „N potriviri” sau „nu apare literal” indică fie o ancoră greșită, fie un caz pe care nu l-am prins.
- **Item 24 (P118/2) rămâne nerezolvat**, marcat `manual: true` — vezi mai sus.
- Nu am scris teste (nu e rolul meu) — recomand tester-ului cazuri pentru: segmentare (ambele stiluri de numerotare a itemilor), split pe `marcaj_text_nou` cu ghilimele tipografice, localizare imbricată alineat→literă, `renumeroteaza_inlocuieste` (verificare că numărul nou nu există deja), `insereaza_dupa`, verificările finale fail-closed (marcaje lipsă/în plus, text vechi supraviețuitor).
- Nu am modificat `chunking_core.py`; import doar trei constante publice de-acolo (`PATTERN_ANTET_MO`, `PATTERN_NUMAR_PAGINA`, `PATTERN_LINIE_CUPRINS`).
- Localizarea „întinderii punctului” (`PATTERN_URMATOR_MARCAJ`) e o eurística generică (următorul marcaj `\d+(\.\d+){1,4}`/`ANEXA`/titlu simplu de capitol), nu identică cu logica mult mai elaborată din `chunking_core._extrage_segmente` (care tratează separat trimiteri rupte pe rând nou, cuprins, anexe imbricate etc.). Pentru operațiile noastre (toate cu ținte cunoscute și verificate punctual) ar trebui să fie suficientă, dar dacă planner-ul găsește o potrivire greșită la rulare, aici e primul loc de verificat.

## De verificat de planner
1. Rulare reală: `python consolidare_normative.py --baza documente_noi/p118_2_2013/baza.txt --ordin documente_noi/p118_2_2013/ordin_6026_2018.txt --manifest documente_noi/p118_2_2013/manifest_6026_2018.json --iesire <tmp> --raport <tmp>` (și analog pentru P118/3) — citește raportul JSON pentru fiecare operație.
2. Dacă apar erori de „N potriviri”, verifică ancora / punctul respectiv direct în `baza.txt`.
3. Decizie asupra item-ului 24 din manifestul P118/2 (tabelele 7.10—7.12) — rămâne `manual: true` (vezi „Runda 3”), discrepanța „al”/„ale” trebuie raportată lui Lucian.
4. După validare, `P118_2_2013_consolidat.txt` / `P118_3_2015_consolidat.txt` trebuie puse ca `extracted.txt` alături de `metadata.json` deja scris, pentru pipeline-ul de import (`populare_db.py` / `manual_ingestion_preflight.py`) — asta nu face parte din task-ul meu.

## Runda 3 (planner, 29-09-2026) — diagnostic complet, 5 eșecuri din 82 operații

Am citit și executat `docs/handoff/R26-B-coder-runda3.md`. Modificări, în ordinea din diagnostic:

### 1. P118/2 item 19 (`insereaza_dupa`, 6.40, după alineatul (1), nou (2))
Punctul 6.40 nu are nicio etichetă `(n)` — verificat direct în `baza.txt` (rândurile 1238–1244): un singur paragraf, fără `(1)`/`(2)` etc. Am adăugat funcția `_localizeaza_ancora_insereaza`: dacă `dupa_alineat == "1"` și punctul nu conține nicio etichetă `\(\d+\)`, inserarea se face la finalul întinderii punctului (alineatul „(1)” e implicit = tot conținutul punctului), iar intrarea din raport primește `"alineat_implicit": true`. Dacă punctul are etichete, comportamentul rămâne cel din Runda 1/2 (căutare exactă, o singură potrivire).

### 2. Întinderea alineatului nu se mai oprește la prima literă
Bug real: `_localizeaza_marcaj_in_regiune` folosea `PATTERN_URMATOARE_SUBUNITATE` (care se oprește și la `(n)`, și la `x)`) ca să bornuiască **inclusiv întinderea alineatului însuși** — deci un alineat cu litere imbricate (`(2) ...: a) b) c) d)`) își tăia propria regiune chiar înainte de prima literă, iar căutarea literei în acea sub-regiune (deja goală de litere) eșua mereu. Am adăugat `PATTERN_URMATOR_ALINEAT` (se oprește **doar** la următorul `(n)` sau la finalul punctului, nu la litere) și un parametru `urmator_pattern` în `_localizeaza_marcaj_in_regiune`; `_localizeaza_subunitate` îl folosește pentru localizarea alineatului (atât în ramura imbricată alineat+literă, cât și pentru alineat simplu — comportament acum uniform și corect și pentru abrogări/înlocuiri de alineate simple care conțin litere).
- Verificat că fixul rezolvă și itemul semnalat P118/3 (5.3.5 alin. (2) lit. c) — confirmat structural în `baza.txt` rândurile 1916–1928.
- Verificat manual (nu rulat) că P118/2 item 46 (13.31 lit. a/f — literă direct sub punct, nu imbricată) și item 10 (4.47 lit. c, idem) nu foloseau ramura imbricată și nu erau afectate de bug; le-am recitit oricum, fără nevoie de schimbare de manifest.

### 3. Numere de punct duplicate real în sursă (P118/2 itemii 48 și 49)
Adăugat câmp opțional `aparitie` (1-based) în țintă + `_localizeaza_punct(baza, punct, aparitie=...)`: alege a n-a potrivire din afara cuprinsului, dar **numai** dacă există efectiv ≥2 potriviri (dacă e una singură și `aparitie` e dat → eroare explicită, ca să nu ascundem tacit o mutare de conținut care nu există). `_valideaza_operatie` cere acum `justificare` obligatorie ori de câte ori `aparitie` e prezentă în manifest. Raportul include ambele câmpuri (`_adauga_aparitie`).
- Manifest actualizat: item 48 (`abroga_punct` 23.51) → `"aparitie": 1` + justificarea din runda 3 (conținutul primei apariții e mutat de ordin în noul 23.50 alin. (2), deci prima apariție se abrogă). Item 49 (`renumeroteaza_inlocuieste` 24.32→24.31) → `"aparitie": 1` + justificarea (textul nou din ordin corespunde primei apariții). Nu am reverificat eu însumi liniile ~7434/7439 și ~8107/8111 din `baza.txt` — justificările sunt cele date de planner în runda 3, transcrise ca atare în manifest.

### 4. P118/2 item 24 — rămâne `manual: true`
Am revertat manifestul la `manual: true` cu o `nota` care explică discrepanța „al”/„ale” (confirmată de planner, nu de mine — eu doar am semnalat-o în Runda 2). Codul pentru `inlocuieste_sintagma_in_bloc` **rămâne neschimbat** în modul (nu l-am șters), doar nu mai e folosit de manifestul P118/2 până la o decizie a lui Lucian.

### Ce nu am (re)verificat
Nu am rulat modulul (fără shell). Nu am reconfirmat eu însumi rândurile exacte (~7434/7439, ~8107/8111) din diagnosticul planner-ului pentru itemii 48/49 — am preluat coordonatele și justificările ca atare. Recomand planner-ului o nouă rulare a diagnosticului pe toate cele 82 de operații (nu doar cele 5 eșuate), fiindcă fixul de la punctul 2 schimbă comportamentul de localizare pentru **toate** alineatele (posibil să afecteze și operații care înainte "mergeau" din întâmplare pe o întindere greșită dar coincidental corectă).

## Runda 2 (planner, 29-09-2026) — cele două opriri fail-closed

Am citit și executat `docs/handoff/R26-B-coder-runda2.md`. Modificări:

### 1. Item 24 (P118/2) — tip nou `inlocuieste_sintagma_in_bloc`
- **Segmentare**: `_parseaza_item` are acum o a treia ramură (după „cuprins:” și „se abrogă.”) care recunoaște tiparul „sintagma „X” se înlocuiește cu sintagma „Y”.” (regex `PATTERN_SINTAGMA`, `re.DOTALL` — X/Y pot fi rupte pe rând). `ItemOrdin` are câmpuri noi opționale `sintagma_veche`/`sintagma_noua`, populate direct din instrucțiune (nu din `text_nou`, care rămâne gol pentru acest tip de item).
- **Tip nou de operație** `inlocuieste_sintagma_in_bloc`: manifestul dă doar `ancora_inceput`/`ancora_sfarsit` (ca la `inlocuieste_bloc`); modulul localizează blocul, aplică `_aplica_inlocuire_globala` (tolerant la rupturi de rând) **doar în interiorul lui**, cere ≥1 înlocuire (altfel eroare), raportează `numar_inlocuiri`, dar **nu adaugă marcaj** — la fel ca înlocuirile globale. Am adăugat un flag intern `_fara_marcaj` ca verificarea finală „numărul de marcaje == numărul de operații” să excludă corect aceste ținte (altfel ar fi picat mereu cu un marcaj lipsă).
- **Manifest**: am citit `baza.txt` în jurul tabelelor 7.10–7.12 (liniile 2228–2349) și am scos `manual: true`. Sunt 3 ținte separate (una per tabel), fiecare cu ancore proprii, ca să nu ating și prozele din puncte intermediare (7.104–7.106) care conțin aceeași sintagmă parțial. Tabelele 7.11 și 7.12 au titlul identic pe primul rând („Valorile minime de calcul ale densității (intensității) de stropire și ale ariei protejate la”) — am folosit ancore pe **două rânduri** (cu `\n` în JSON) ca să le disting.
- **Risc semnalat, neremediat de mine**: instrucțiunea din ordin scrie sintagma veche ca „Valorile minime de calcul **al** densității (intensității) de stropire” (singular „al”), dar în `baza.txt` titlurile celor trei tabele au „calcul **ale** densității” (plural, acordat cu „Valorile”). Dacă discrepanța e reală (nu o eroare de citire a mea), `_aplica_inlocuire_globala` nu va găsi sintagma exactă în bloc și modulul se va opri fail-closed cu „sintagma nu a fost găsită”. Planner trebuie să decidă: fie e o typo reală în MO 966 (caz în care sintagma din manifest ar trebui să fie cea din `baza.txt`, nu cea citată literal din ordin — dar asta ar încălca „X verificat literal în ordin”), fie am citit greșit ordinul și trebuie reverificat direct.

### 2. Localizarea primei subunități pe rândul punctului (`3.8.2.5 (1)Sunetul…`, `5.3.5 (1)Cablurile…`, `3.3.1 (1) Echiparea…`)
- `_localizeaza_marcaj_in_regiune` acceptă acum un `prefix_regex` opțional; pe lângă căutarea obișnuită „început de rând” din regiune, încearcă și potrivirea marcajului **imediat după prefixul punctului/alineatului-părinte**, pe primul rând al regiunii (funcție nouă `_cauta_marcaj_dupa_prefix`), cu sau fără spațiu între `)` și textul următor. Cele două căi sunt însumate și se cere tot „exact 1” candidat combinat (fail-closed neschimbat).
- `_localizeaza_subunitate` construiește `prefix_punct` (pentru alineat/literă direct sub punct) și `prefix_alineat` (pentru litera imbricată sub alineat) și le pasează mai departe.
- Am relaxat și `PATTERN_URMATOARE_SUBUNITATE` (nu mai cere spațiu după `)`/`)`, doar poziția de start contează pentru a bornui întinderea subunității curente) — corectează același gen de problemă și pentru cazuri similare neobservate direct de mine.

### 3. Recitire a tuturor operațiilor pentru aceeași clasă de problemă
Am recitit (grep + citire directă) toate țintele `alineat`/`litera`/`introductiva` din ambele manifeste ca să văd dacă vreuna are prima subunitate atașată pe rândul punctului, ca în exemplele din runda 2:
- **P118/2**: `4.36.(1)`, `4.47.` (literă c), `6.1.(1)/(4)`, `6.19.` (literă a), `6.25.(1)`/(2 țintă), `7.26.(1)`, `7.172.(1)`, `12.3.(1)`, `12.15.(1)`, `13.3.(1)`, `13.14.(1)`, `13.31.` (litere a/f), `28.3.(1)` — verificate prin grep (rezultatele sunt în raportul rundei 1): în toate cazurile alineatul **(1)** e chiar pe rândul punctului, dar operațiile noastre țintesc alineatul/litera cerut de ordin (nu neapărat „(1)”), care de regulă e pe rând propriu mai jos — fixul de mai sus acoperă totuși și acele cazuri dacă vreo țintă chiar coincide cu „(1)” de pe rândul punctului (ex. `4.36` alineat „1”, `6.1` alineat „1”, `7.26` alineat „1” nu e țintă dar `13.14` alineat „1” e țintă directă — verificat: linia 4257 `13.14. (1) Pompele de incendiu…`, deci acest fix era necesar și pentru itemul 41).
- **P118/3**: `3.3.6` literă c, `3.7.13.1` alineat 2 (verificat anterior, alineatul (2) e pe rând propriu, nu pe rândul punctului — fixul nu schimbă comportamentul aici), `3.8.2.5` alineat 1 (exact cazul semnalat de planner — verificat acum: `3.8.2.5 (1)Sunetul alarmei…`, corectat), `5.2.5` introductivă (neafectată, nu caută marcaj de alineat/literă), `5.3.5` alineat 2 + literă c (alineatul (2) e pe rând propriu — neafectat de fix, dar am verificat oricum).
- Nu am putut re-executa modulul (nu rulez comenzi) — planner trebuie să confirme la rulare reală că fix-ul rezolvă exact eroarea raportată și că nu a introdus potriviri duble (ex. dacă vreun punct are și un rând separat cu același marcaj, ar pica acum cu „2 potriviri” în loc de „0”; nu am găsit un asemenea caz la verificarea manuală, dar nu e o garanție exhaustivă).
