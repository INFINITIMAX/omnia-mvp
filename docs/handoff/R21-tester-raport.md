# R21 — Tester: raport

Fișiere modificate (doar `tests/`, cum era constrângerea):
- `D:\Omnia-MVP-r21-anexe\tests\test_populare_db.py`
- `D:\Omnia-MVP-r21-anexe\tests\test_chunking_core.py`

## 1. `NUMAR_CHUNKURI_ASTEPTAT_PER_DOCUMENT` (test_populare_db.py)

Actualizat la cifrele verificate de planner: `i9_2022` 790→**800**, `np057_02` 298→**290**, `p118_1_2025` 2862→**3554**. Restul (i5 768, i7 2214, np004 85, np010 356, spitale 616) neschimbate. Nu am atins `PRAG_ACOPERIRE_MINIM_PER_DOCUMENT` (task-ul nu a cerut-o, iar pragurile existente rămân sub cifrele reale raportate — p118 prag 0,99 < acoperire reală 0,996).

## 2. Test pe document real — `test_p118_toate_titlurile_de_anexa_din_corp_produc_chunk_si_niciun_identificator_fals` (test_populare_db.py, același `skipif` pe `documente_noi`)

- Definește „corpul" ca text de la primul marcaj `PATTERN_ARTICOL_ART` brut al documentului (nu de la un rând hardcodat), extrage cu regex propriu toate titlurile `ANEXA N[.M]` din acel corp — **independent de filtrele interne ale coder-ului**, ca să nu re-testeze implementarea.
- Verifică: exact 43 de titluri găsite; fiecare are cel puțin un chunk propriu sau un copil (`anexaN` sau `anexaN.xxx`) în identificatorii normalizați reali produși de `modul_ingestie.creeaza_chunkuri`; identificatorii falși `27.3`, `48.6`, `29.1`, `2.940` nu apar.
- Ar pica dacă: orice titlu de anexă din corp ar rămâne fără chunk (regresia rundelor 2-4), sau dacă vreun identificator fals ar reapărea.

**Corecție planner (după prima rulare, 1231 passed / 3 failed):** `7.8` a fost scos din lista de identificatori interziși — e un titlu de secțiune real din corpul P 118/1 („7.8. INSTALAȚII AFERENTE CONSTRUCȚIILOR", cu punct final), distinct de falsul original de la rândul 29752 („7.8 Prevenirea descărcărilor electrostatice…", fără punct, dintr-o anexă). Testul verifică acum sursa (textul), nu numărul: niciun chunk din afara unei anexe (`articol` care nu începe cu `ANEXA`) nu are voie să aibă `text` care începe cu „Prevenirea descărcărilor electrostatice", „Substrat - material" sau „Mj/kg" — cele trei fraze care proveneau exact din identificatorii falși semnalați în dovezile R21-coder.md. Celelalte două eșecuri raportate de planner (sufixele „lit.”/„la” prinse fals în „stabilit."/„verticala.") sunt bug-uri reale de implementare — nu le-am atins, le repară coder-ul.

## 3. Teste sintetice noi (test_chunking_core.py)

Toate independente de `documente_noi`, plasate la finalul fișierului:

1. `test_numar_fara_punct_final_nu_incepe_articol_in_document_cu_multe_art` — document cu exact 50 marcaje „Art.”; „48.6 Substrat…”/„27.3 Mj/kg…” nu deschid articol propriu, rămân în textul „Art. 1.1.”. Ar pica dacă `PATTERN_ARTICOL_FARA_PUNCT` ar rămâne activ peste prag (ar apărea >50 chunk-uri).
2. `test_cuprins_de_titluri_anexa_inaintea_primului_art_este_ignorat` — 3 titluri `ANEXA` înaintea a 50 de marcaje „Art.”; niciun chunk `ANEXA…`, exact 50 chunk-uri. Ar pica dacă regula „primul Art. acceptat” (runda 4) ar lipsi.
3. `test_titlu_de_anexa_urmat_de_continut_devine_chunk_propriu` — caz de bază, un singur titlu + conținut → chunk `ANEXA 2.1.`.
4. `test_marcaj_intern_de_anexa_devine_copil_si_nu_coincide_cu_articol_din_corp` — articol real `2.7.7.` în corp + `A.10. 2.7.7.` în `ANEXA 10` → identificatori distincți `2.7.7.` și `ANEXA 10.2.7.7.`, fără coliziune de dedup. Ar pica dacă marcajul intern n-ar primi prefixul anexei.
5. `test_bloc_de_titluri_anexa_cu_pagina_intre_ele_e_cuprins_si_e_ignorat` — stil NP010/I9 (fără prag de Art. atins): titlu urmat de alt titlu urmat de un număr de pagină izolat → ambele ignorate, fără mecanismul „primul Art.”.
6. `test_trimiteri_cu_virgula_sau_rupte_pe_rand_nou_nu_deschid_regiune_de_anexa` — „ANEXA 2.1, au caracter…” (virgulă) și „…și” ↵ „ANEXA 5.3.” rămân text, nu deschid regiune.
7. `test_titlu_de_anexa_precedat_de_legenda_terminata_in_litera_mica_deschide_regiune` — legendă de figură terminată în literă mică nu blochează titlul real care urmează (regresia rundei 4 — dacă „literă mică" ar reveni ca motiv de respingere, testul pică).
8. `test_marcaj_art_in_interiorul_unei_anexe_nu_inchide_regiunea` — „Art. 2.4.9.4. (2).” în interiorul „ANEXA 6” nu resetează `anexa_curenta`; marcajul intern de după el rămâne tot copil al anexei 6.
9. `test_acoperire_text_brut_elimina_marcajul_intern_de_anexa` — text minimal cu „A.10. 2.2.9. …” → `acoperire_text_brut` == 1.0. Ar pica (acoperire 0.0, verificat manual pe hârtie) dacă `_PATTERN_MARCAJ_ANEXA_INTERN_ACOPERIRE` ar lipsi din `_normalizeaza_pentru_acoperire`.

Notă tehnică importantă găsită în timpul scrierii: `_CUVINTE_CONTINUARE_ANEXA` verifică sufixul `"și"` cu diacritic (ș, nu s); testul 6 folosește explicit „și” cu diacritic — cu „si” fără diacritic testul ar fi trecut fals-pozitiv (ANEXA 5.3 ar fi devenit titlu real, dar din greșeală de scriere a testului, nu a codului). Nu e un bug în cod, dar planner-ul ar putea vrea să verifice dacă documentele reale au uneori diacritice pierdute la extragere PDF (risc de regresie reală, neverificat aici, în afara sarcinii mele).

## Ce nu am acoperit

- Nu am testat cazul I9 rândul 3037 direct pe text real (doar sintetic, punctul 6) — documentul real e acoperit de `NUMAR_CHUNKURI_ASTEPTAT_PER_DOCUMENT["i9_2022"] == 800` și de testele de acoperire/neconsecutive existente, dar nu există un test explicit „identificatorii ANEXA din I9 nu apar înainte de rândul 5162” pe text real (task-ul nu l-a cerut explicit ca test nou, doar ca verificare de planner).
- Nu am adăugat teste pentru rândurile 26351/29484/35900 (trimiterile „Art.” reale din P118) pe textul real — acoperite sintetic (punctul 8) și implicit de `test_p118_toate_titlurile_de_anexa_din_corp_produc_chunk...` (dacă regiunea s-ar închide greșit acolo, mai multe din cele 43 de titluri ar rămâne fără chunk).
- Nu am modificat `PRAG_ACOPERIRE_MINIM_PER_DOCUMENT` — nu era în sarcină.

## Suspiciuni de bug

Niciuna nouă. Am recalculat manual (nu rulat) traseul regex pentru fiecare test înainte de a-l scrie, verificând potrivirile `PATTERN_TITLU_ANEXA`/`PATTERN_MARCAJ_ANEXA_INTERN`/`PATTERN_ARTICOL_ART` linie cu linie pe textele sintetice.

## Comanda pentru planner

```powershell
cd D:\Omnia-MVP-r21-anexe
python -m pytest -q
```

(testele pe `documente_noi` rămân sărite fără link-ul temporar, ca înainte).
