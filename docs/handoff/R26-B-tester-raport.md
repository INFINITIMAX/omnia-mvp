# R26-B — Raport tester: consolidarea cu ordine de modificare

Nu am rulat nimic (fără shell). Am scris doar în `tests/`:

- **`D:\Omnia-MVP-r26\tests\test_consolidare_normative.py`** (nou, 32 de teste) — sintetic, fără fișierele reale din `documente_noi/`.
- **`D:\Omnia-MVP-r26\tests\test_chunking_core.py`** — am adăugat 2 teste, restul fișierului neatins (nu am atins testele de antete MO / diacritice / populare_db — sunt în `test_diacritice.py`, `test_glyph_mapping.py`, `test_populare_db.py`, pe care nu le-am deschis).

## `test_consolidare_normative.py` — ce verifică fiecare grup

### 1. Segmentare
- `test_segmenteaza_ambele_stiluri_de_numerotare` — „N. text pe același rând” și „N.\ntext pe rândul următor” în același ordin. Ar pica dacă oricare stil ar fi ratat sau dacă `text_nou` brut al itemului 2 n-ar conține citatul.
- `test_segmenteaza_se_opreste_la_articolul_ii` — folosește forma lungă „Articolul II”; itemul de după nu trebuie citit. Ar pica dacă `PATTERN_START_ART_II` nu ar recunoaște „Articolul II” sau dacă tăietura corpului ar include text de după el.
- `test_segmenteaza_elimina_antet_mo_numar_pagina_si_linie_de_puncte` — antet MO, linie doar-cifre, linie doar-puncte în `text_nou`; toate trei trebuie eliminate de `_curata_segment`, textul relevant din jur păstrat. Ar pica dacă oricare dintre cele trei reguli de curățare ar fi eliminată sau slăbită.
- `test_segmenteaza_numerotare_neconsecutiva_esueaza_la_validare` — **notă importantă**: `segmenteaza_ordin` însuși NU detectează un gol de numerotare (1 → 5, sărind 2-4) — itemul 1 înghite tacit tot restul corpului până la Art. II, fără eroare. Testul verifică fail-closed-ul real, care se întâmplă un nivel mai sus, în `aplica_operatii` (mismatch manifest ↔ segmentare, `nrs_ordin={1} != nrs_manifest={1,5}`). Dacă planner-ul vrea o eroare explicită chiar în `segmenteaza_ordin` la prima detectare a golului, asta lipsește azi din cod — semnalez, nu repar.
- `test_segmenteaza_item_nerecunoscut_ridica_eroare` — item fără „cuprins:”/„se abrogă.”/tipar de sintagmă.
- `test_segmenteaza_item_sintagma_se_inlocuieste_cu_sintagma` — inclusiv sintagma ruptă pe rând (verifică `re.DOTALL`).

### 2. Fiecare tip de operație
- `test_inlocuieste_punct_simplu`
- `test_inlocuieste_subunitate_imbricata_alineat_cu_litere_interioare` — regresie directă Runda 3 (alineat cu litere a)/b)/c) imbricate, fiecare pe rând propriu ca în `baza.txt` real); ar pica dacă `PATTERN_URMATOR_ALINEAT` ar reveni la fostul comportament (oprire la prima literă).
- `test_prima_subunitate_pe_randul_punctului_fara_spatiu` — „3.8.2.5 (1)Sunetul…” (regresie Runda 2, exact cazul citat în raport).
- `test_prima_subunitate_pe_randul_punctului_cu_spatiu_si_punct_fara_punct_final` — „3.3.1 (1) …”, punctul fără punct final.
- `test_insereaza_dupa_alineat_implicit_cand_punctul_nu_are_etichete` — regresie Runda 3 (`alineat_implicit` în raport).
- `test_aparitie_permisa_doar_cand_exista_cu_adevarat_doua_potriviri` — abrogă doar prima apariție reală (23.51 dublu în sursă), a doua rămâne intactă.
- `test_aparitie_pe_punct_unic_ridica_eroare` — `aparitie` pe un punct cu o singură potrivire → eroare explicită.
- `test_aparitie_fara_justificare_ridica_eroare` — `aparitie` fără `justificare` → `_valideaza_operatie` respinge înainte de localizare.
- `test_renumeroteaza_cu_numar_nou_deja_existent_ridica_eroare`
- `test_cuprins_ignorat_la_localizarea_punctului` — o linie de cuprins cu același număr de punct nu trebuie confundată cu punctul real.
- `test_inlocuieste_bloc_intre_ancore`
- `test_inlocuieste_sintagma_in_bloc_nu_adauga_marcaj` — combină segmentarea reală a sintagmei cu aplicarea în bloc; verifică explicit că nu se adaugă marcaj de proveniență (spre deosebire de celelalte tipuri) și că `numar_inlocuiri` e corect raportat.

### 3. Fail-closed
- 0 potriviri, 2 potriviri fără `aparitie` (pe `_localizeaza_punct` direct).
- `test_tinte_suprapuse_ridica_eroare` — două operații pe exact același punct.
- `test_instructiune_care_nu_mentioneaza_punctul_ridica_eroare` (pe `_valideaza_operatie` direct).
- `test_verifica_final_text_nou_absent_ridica_eroare`, `test_verifica_final_text_vechi_ramas_ridica_eroare`, `test_verifica_final_numar_de_marcaje_gresit_ridica_eroare` — apelează `_verifica_final` **direct** (funcție privată), pentru că prin API-ul public aceste trei erori sunt practic irealizabile cu un manifest corect (segmentul chiar inserat e mereu prezent prin construcție) — sunt plase de siguranță pentru manifeste/coduri viitoare, nu bug-uri curente. Am ales să testez contractul funcției direct, cu dicționare construite manual.

### 4. Marcajul
- `test_marcaj_are_formatul_exact` — compară string-ul exact produs cu regex-ul de referință din `R26-C-coder.md`.
- `test_marcaj_niciodata_lipit_de_punctul_urmator` — **regresie corectura 1** a planner-ului: fără fix, marcajul s-ar lipi direct de „1.3.” (`]1.3.` fără `\n`). Testul verifică ambele: prezența `]\n1.3.` și absența `]1.3.`.
- `test_inlocuiri_globale_se_aplica_si_in_textul_nou` — **regresie corectura 2**: dacă `_verifica_final` ar compara `text_nou_norm` brut (neînlocuit global) cu rezultatul deja înlocuit global, ar ridica fals „text_nou nu apare literal” — testul ar pica cu excepție neprinsă dacă fix-ul ar dispărea.

## `test_chunking_core.py` — cele 2 teste adăugate (după `test_limita_de_1000_caractere_pe_chunk`)
- `test_marcaj_de_provenienta_nu_este_taiat_la_limita_de_1000_caractere` — construiește un text cu marcajul de proveniență poziționat exact peste tăietura de 1000 de caractere (calculat ca ultimul spațiu găsit ≤1000 să cadă în interiorul marcajului); verifică marcajul întreg într-o singură bucată, nicio bucată cu marcaj trunchiat.
- `test_text_fara_marcaj_de_provenienta_se_taie_la_limita_ca_inainte` — regresie: fără marcaj, tăietura rămâne exact la ultimul spațiu găsit (nu extinsă).

## Ce nu am acoperit și de ce
- Fișierele reale `documente_noi/p118_2_2013/*` / `p118_3_2015/*` (secțiunea 6 din task, opțională) — am sărit, exact ca testele existente cu documente reale (planner rulează separat rularea reală, deja descrisă în raportul coderului).
- `abroga_subunitate` ca tip separat — nu are test dedicat (verificată doar indirect prin structura similară cu `inlocuieste_subunitate`/`abroga_punct`); dacă planner-ul vrea acoperire explicită, e ușor de adăugat după același tipar.
- Nu am testat exhaustiv toate combinațiile `marcaj_text_nou` cu ghilimele tipografice pentru ținte multiple pe același item (`_segmenteaza_text_nou`/`_imparte_pe_marcaje`) — am acoperit doar cazul cu o singură țintă per item în toate testele mele; e o zonă cu risc redus (verificată manual de coder pe manifestele reale), dar netestată sintetic.

## Suspiciune de bug (nu am reparat, doar semnalat)
`segmenteaza_ordin` nu detectează explicit o numerotare neconsecutivă (item lipsă) — itemul precedent înghite tacit tot restul corpului ordinului. Fail-closed-ul real vine abia din `aplica_operatii` (mismatch nr. manifest vs. nr. segmentare), ceea ce funcționează **doar dacă** manifestul chiar declară itemii lipsă separat (ca în cazul curent, unde manifestele coderului au avut exact 63/18/82 operații verificate manual). Dacă un ordin viitor ar avea un gol de numerotare nedetectat de om la scrierea manifestului, pipeline-ul nu s-ar opri la segmentare, ci ar produce un item cu conținut greșit/înghițit. Testul `test_segmenteaza_numerotare_neconsecutiva_esueaza_la_validare` documentează comportamentul actual (validare la nivel de manifest, nu la segmentare).

## Comanda pentru planner
```
cd D:\Omnia-MVP-r26
python -m pytest tests/test_consolidare_normative.py tests/test_chunking_core.py -q
```
(sau `python -m pytest -q` pentru tot setul, ca să confirme și cele 1286 existente + noile 34.)
