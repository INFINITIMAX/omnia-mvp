# R14 — Raport Tester

## Fișiere atinse

- **Nou:** `tests/test_chunking_core.py` (32 teste sintetice, fără dependență de `documente_noi`).
- **Modificat:** `tests/test_api_integration.py` — actualizat `test_api_p1_restrictia_cu_articol_cunoscut_pastreaza_ruta_exacta` (asserțiile de SQL/parametri pentru ruta unificată).
- **Modificat:** `tests/test_retrieval_core.py` — actualizat testul SQL existent pentru `find_exact`; adăugate 5 teste noi (3 pentru `find_exact`, 2 pentru `_is_known_article`/`_is_known_in`).
- **Modificat:** `tests/test_populare_db.py` — actualizate numerele fixe per document; adăugate 2 teste noi (acoperire per document, 811/811 articole „Art.” în P 118/1).

Nu am atins cod de producție. Nu am rulat comenzi.

## `tests/test_api_integration.py`

`test_api_p1_restrictia_cu_articol_cunoscut_pastreaza_ruta_exacta` — actualizat substring-ul SQL așteptat la
`"chunk.document_id = %s AND (chunk.articol_normalizat = %s OR chunk.articol_normalizat LIKE %s)"` și
`parameters == ("doc-1", "4.4.7.2", "4.4.7.2.%")`. Ar pica dacă interogarea unificată ar reveni la forma veche
sau dacă parametrul `LIKE` ar dispărea. Restul testului (status, citări, apeluri semantice, buget) neschimbat.

## `tests/test_retrieval_core.py`

- **Actualizat** `test_repository_exact_foloseste_numai_sql_parametrizat_cu_document_optional`: verifică acum
  SQL-ul unificat `(articol_normalizat = %s OR articol_normalizat LIKE %s)` cu parametrii `(doc, articol,
  articol+".%")`, atât cu cât și fără `document_id`, plus `ORDER BY chunk.document_id, chunk.chunk_order,
  chunk.id` pentru varianta fără document. Ar pica dacă SQL-ul ar reveni la forma veche sau dacă LIKE/parametrul
  de prefix ar lipsi.
- **Nou** `test_repository_exact_cu_potrivire_exacta_ignora_copiii_din_acelasi_rezultat`: dat un set de rânduri
  care conține atât potrivirea exactă cât și copii, `find_exact` trebuie să păstreze doar rândul exact. Ar pica
  dacă implementarea ar întoarce toate rândurile quando există o potrivire exactă.
- **Nou** `test_repository_exact_fara_potrivire_exacta_intoarce_copiii_in_ordinea_data_de_db`: fără potrivire
  exactă, `find_exact` cade pe copii, păstrați exact în ordinea întoarsă de cursor (Python nu re-sortează). Ar
  pica dacă ar întoarce listă goală în loc de copii, sau dacă ar reordona rândurile.
- **Nou** `test_repository_exact_fara_niciun_rand_intoarce_lista_goala`: niciun rând → `[]`, nu excepție. Ar
  pica dacă implementarea ar presupune minim un element.
- **Nou** `test_articol_sectiune_fara_chunk_propriu_e_cunoscut_prin_copiii_lui`: prin `parse()` public, un
  articol-secțiune (`4.4.7`) fără chunk propriu, dar cu copii cunoscuți (`4.4.7.2`, `4.4.7.9`), e recunoscut. Ar
  pica dacă `_is_known_article`/`_is_known_in` ar cere potrivire exactă, fără fallback pe prefix.
- **Nou** `test_prefix_fara_punct_nu_e_confundat_cu_articol_cunoscut`: articol cunoscut `4.4.11.2`, interogat cu
  `4.4.1` — nu trebuie recunoscut ca fiind cunoscut. E adversarial ales: o implementare naivă care ar verifica
  `known.startswith(article)` fără să adauge punctul de separare (`article + "."`) ar recunoaște greșit
  `"4.4.11.2".startswith("4.4.1")` (adevărat ca substring, greșit ca prefix de secțiune). Ar pica exact pe acest
  bug.

Notă: nu am putut folosi exemplul literal din task („4.4 vs 4.41.”) — `_UNMARKED_ARTICLE`/regex-ul de căutare
fără marker necesită minimum 3 componente numerice (`{2,}` repetiții după primul grup), deci un articol de 2
componente ca „4.4” nu ajunge niciodată la `_is_known_article` prin API-ul public. Am reconstruit un exemplu
adversarial echivalent cu 3+ componente, care testează exact aceeași clasă de bug (lipsa punctului de separare
la verificarea de prefix).

## `tests/test_populare_db.py`

- **Numere actualizate** în `NUMAR_CHUNKURI_ASTEPTAT_PER_DOCUMENT` conform cifrelor verificate de planner: i5
  786, i7 2229, i9 769, np004_03 84, np010_2022 438, np057_02 300, p118_1_2025 3005, spitale_2022 634.
- **Nou** `test_acoperirea_continutului_brut_ramane_peste_prag` (parametrizat pe 8 documente, `skipif` pe
  `documente_noi`): calculează procentul de rânduri brute ≥50 caractere (excluzând „MONITORUL OFICIAL”) al căror
  prefix de 45 caractere normalizat (fără marcaje de articol/`(N)`/spații multiple) apare în textul concatenat al
  chunk-urilor, și verifică pragurile din handoff: i5 ≥97%, i7 ≥95%, i9 ≥96%, np004 ≥90%, np010 ≥99%, np057
  ≥87%, p118 ≥99%, spitale ≥97%. Ar pica dacă o regulă de curățare (antet/cuprins/colofon/titlu) ar deveni prea
  agresivă și ar arunca text real.
- **Nou** `test_p118_toate_articolele_art_devin_chunk_propriu` (`skipif` pe `documente_noi`): extrage toate
  potrivirile `chunking_core.PATTERN_ARTICOL_ART` din textul brut P 118/1 (așteptat 811, verificat exact),
  apoi verifică că toate apar ca articol propriu în chunk-uri. Ar pica dacă vreun filtru de trimitere-ruptă/dedup
  ar arunca un articol „Art.” real.

## `tests/test_chunking_core.py` (nou, 32 teste)

Organizat pe reguli, câte un test pozitiv/negativ unde task-ul cere explicit:

| Regulă | Teste | Ce l-ar face să pice |
|---|---|---|
| 1a antet MO | `test_antet_mo_si_paginile_alaturate_sunt_eliminate`, `test_numar_singur_fara_antet_in_apropiere_ramane_neatins`, `test_referinta_la_monitorul_oficial_in_text_ramane` | Antet/pagină nu eliminate, sau eliminare prea agresivă a celulelor de tabel/referințelor |
| Colofon MO | `test_colofonul_mo_de_final_este_eliminat` | Colofonul rămâne atașat ultimului articol |
| 1b cuprins puncte | `test_cuprins_cu_puncte_de_conducere_ca_bloc_este_eliminat`, `test_interval_numeric_izolat_cu_puncte_nu_taie_nimic` | Bloc de cuprins nu e sărit, sau un interval numeric izolat (regresia I7) taie text real |
| 1b cuprins pagină pe rând | `test_cuprins_cu_numar_de_pagina_pe_randul_urmator_este_eliminat` | Intrările NP 010 rămân ca articole |
| 1c titlu roman | `test_titlu_de_capitol_roman_nu_intra_in_textul_articolului_anterior` | Titlul se lipește de articolul anterior sau dispare articolul următor |
| 1d titlu → context | `test_titlu_de_sectiune_se_contopeste_ca_prim_rand_in_copiii_directi`, `test_titlu_fara_copii_ramane_chunk_normal`, `test_titlu_fara_pagini_in_cuprins_este_eliminat_ca_duplicat` | Titlul rămâne chunk separat, sau nu ajunge context la copii, sau conținut fără copii dispare, sau duplicatul de cuprins nu e eliminat |
| Split secundar | `test_introducere_titlu_la_split_nu_devine_chunk_separat`, `test_split_secundar_nu_dubleaza_prefixul_titlului_deja_contopit` | Introducerea-titlu devine chunk propriu, sau prefixul apare dublat |
| Marcaj „Art.” | `test_marcaj_art_cu_trei_componente_este_recunoscut`, `test_marcaj_art_urmat_de_litera_mica_sau_punctuatie_ramane_trimitere` | „Art. N.N.N.” nerecunoscut, sau o trimitere ruptă devine articol fals |
| Trimiteri rupte (numeric) | `test_numar_urmat_de_litera_mica_e_trimitere_articolul_real_nu_se_pierde`, `test_rand_anterior_terminat_in_conform_face_marcajul_urmator_trimitere` | Articolul real e aruncat prin dedup fals (regresiile P 118/1 2.3.2.1.2 și 3.2.11.20) |
| D18 virgulă | `test_d18_virgula_la_final_de_rand_e_articol_valid_fara_virgula`, `test_d18_virgula_urmata_de_text_pe_acelasi_rand_nu_e_articol` | Regresia D18 revine |
| Numere fără punct (I7) | `test_numar_fara_punct_final_urmat_de_majuscula_e_articol`, `test_zecimal_cu_litera_mica_dupa_nu_e_articol` | „3.1.5.7” nerecunoscut, sau „0.4 kV” confundat cu articol |
| Date | `test_data_zi_luna_an_nu_e_articol` | „15.01.2024” devine articol fals |
| Limită/statistici | `test_limita_de_1000_caractere_pe_chunk`, `test_ultimele_statistici_numara_corect_pe_exemplu_mic` | Chunk peste 1000 caractere, sau statistici (`antete_eliminate`, `titluri_contopite`, `duplicate_eliminate`, `titluri_cuprins_eliminate`) greșite pe un exemplu mic controlat |

Fiecare test e construit din text sintetic minim, verificat manual (citind `chunking_core.py` linie cu linie
pentru fiecare regex/prag implicat), nu din texte reale — planul cerea explicit texte mici sintetice pentru
acest fișier.

### Atenție specială la lungimi (risc de fragilitate)

Patru teste depind de praguri de lungime din cod și au nevoie de text suficient de lung ca să treacă exact
pragul relevant, dar nu mai mult:
- cele două teste de „bloc de cuprins” (`.......... ` și „pagină pe rând următor”) — blocul de cuprins trebuie
  să rămână în primele 20% din documentul total (`PROCENT_MAXIM_CAUTARE_CUPRINS`), deci am folosit intrări
  scurte de cuprins + un corp real generos (dar sub 1000 caractere, ca să rămână un singur chunk).
- cele două teste de split secundar (introducere-titlu, prefix dublat) — segmentul înainte de split trebuie să
  depășească 2000 caractere (`LUNGIME_PENTRU_SPLIT_SECUNDAR`), dar fiecare subpunct final (cu context
  prepend-uit) trebuie să rămână sub 1000 caractere (`MAX_CHUNK_CHARS`), altfel `_aplica_limita_caractere` l-ar
  tăia suplimentar și ar rupe egalitatea exactă a listei de articole așteptate. Am folosit 3 subpuncte (nu 2)
  tocmai pentru că marja cu doar 2 subpuncte era prea strânsă (imposibil matematic să satisfacă ambele
  constrângeri simultan cu doar 2, conform calculului meu pe lungimea propozițiilor folosite).

Am calculat manual (număr de caractere pe cuvinte) lungimile textelor sintetice ca să mă asigur că pragurile
sunt respectate cu marjă confortabilă (zeci-sute de caractere), dar nu am putut rula testele ca să confirm
exact. Dacă planner-ul găsește vreunul din aceste 4 teste picând din motive de prag (nu de logică), e cel mai
probabil o eroare de numărare a mea, nu un bug real în cod — raportați-mi lungimea exactă și ajustez.

## Ce nu am acoperit

- Nu am scris teste separate pentru interacțiunea `retrieval_core` ↔ DB reală (rămâne acoperit de testele
  existente de integrare, neatinse aici decât unde task-ul cerea explicit).
- Nu am adăugat teste pentru combinații mai adânci ale regulilor din `chunking_core` (ex. titlu de secțiune +
  marcaj „Art.” + trimitere ruptă simultan) — task-ul cerea câte un test pozitiv/negativ per regulă, nu produsul
  cartezian al tuturor regulilor; riscul e că o interacțiune neprevăzută între două reguli ar putea rupe ceva ce
  niciun test individual nu prinde.
- Nu am atins `test_doua_procese_nu_pot_rezerva_ambele_ultimul_slot` (interzis explicit) și nici
  `tests/test_manual_ingestion_preflight.py` (nu era cerut).
- Testele parametrizate pe `documente_noi` (acoperire per document, 811/811 P118) rulează doar în mediul cu
  date reale — în worktree-ul curent se sar automat (`skipif`).

## Bug-uri suspectate

Niciunul nou, dincolo de riscurile deja semnalate de coder în raportul lui (ex. regula „titlu cu descendent
oriunde în document” din Runda 4, care ar putea elimina greșit un titlu coincidental în alt document). Nu am
găsit dovezi concrete ale acestui risc în textele sintetice construite.

## Corectură după rularea planner-ului (79 teste cu documente_noi, 78 passed / 1 failed)

`test_p118_toate_articolele_art_devin_chunk_propriu` pica: comparam `articole_asteptate` (identificatori bruți
din regex) direct cu `chunk["articol"]`, dar articolele lungi împărțite de split-ul secundar apar cu sufix de
subpunct (`2.3.2.1.6.(1)`, `2.3.2.1.6.(2)` etc.), nu ca `2.3.2.1.6.` — comportament corect, nu bug. Am corectat
comparația să folosească identificatorul de bază: `chunk["articol"].split("(")[0]`, păstrând cerința 811/811
nealterată (pragul `len(articole_asteptate) == 811` rămâne neschimbat). Am modificat doar acest test, nimic
altceva; nu am rulat comenzi.

## Comanda pentru planner

```powershell
python -m pytest -q
```

sau, pentru fișierele atinse de mine izolat:

```powershell
python -m pytest -q tests/test_chunking_core.py tests/test_retrieval_core.py tests/test_api_integration.py tests/test_populare_db.py
```
