# R16 — Tester: raport

Scris doar în `tests/`. Nu am rulat nimic (fără unelte de shell).

## Fișiere modificate

### `tests/test_populare_db.py`

1. **Task 1** — `NUMAR_CHUNKURI_ASTEPTAT_PER_DOCUMENT` actualizat la cifrele verificate de planner: i5_2022 768, i7_2011 2214, i9_2022 790, np004_03 85, np010_2022 356, np057_02 298, p118_1_2025 2862, spitale_2022 616. Testul existent `test_chunking_documentelor_deja_validate_ramane_neschimbat` va folosi acum aceste valori. Ar pica dacă numărul de chunk-uri produs pe oricare din cele 8 documente s-ar schimba față de cifrele confirmate de planner (regresie de fragmentare → content_hash-uri schimbate → reimport masiv necesar).
   - Am lăsat `PRAG_ACOPERIRE_MINIM_PER_DOCUMENT` neschimbat: valorile curente (0.97/0.95/0.96/0.90/0.99/0.87/0.99/0.97) sunt deja praguri minime, sub cifrele reale verificate de planner (0,979/0,971/0,969/0,923/0,999/0,882/0,993/0,982) — nu erau cerute de task, nu le-am atins.

2. **Task 2** — test nou `test_articole_normalizate_nu_apar_in_pozitii_neconsecutive`, parametrizat pe cele 8 documente cu `extracted.txt`, cu același `skipif` pe `documente_noi`. Rulează `creeaza_chunkuri` pe textul real, normalizează fiecare `articol` cu `modul_ingestie.normalizeaza_articol` (funcția reală a importerului, nu o reimplementare), și verifică că fiecare valoare normalizată apare doar în poziții consecutive ale listei de chunk-uri. Ar pica dacă dedup-ul ar reveni la cheia brută (nenormalizată) sau dacă vreo regulă nouă ar reintroduce o coliziune de identificator la distanță — exact regresia raportată de planner (63 de articole neconsecutive înainte de R16).

### `tests/test_chunking_core.py`

Adăugat `import pytest` la vârf (lipsea; necesar pentru `@pytest.mark.parametrize`).

Teste noi, toate sintetice, fără dependență de `documente_noi`:

1. **Dedup pe forma normalizată** (task 3, punct 1):
   - `test_dedup_pe_forma_normalizata_variante_care_difera_doar_prin_majuscula` — „3.2.(B).” vs „3.2.(b).”: acesta e testul care izolează *cu adevărat* nevoia de cheie normalizată (dedup pe cheia brută, case-sensitivă, nu le-ar fi unit). Ar pica dacă dedup-ul ar reveni la cheia brută.
   - `test_dedup_forme_diferite_dar_neechivalente_normalizat_raman_separate` — control negativ, litere diferite (b/c) rămân chei diferite. Ar pica dacă normalizarea ar confunda articole diferite.
   - `test_dedup_exemplul_din_handoff_varianta_fara_punct_si_cu_punct` — exemplul literal cerut în task („6.1.1 Titlu…” / „6.1.1. Text real…”). Notă onestă: în implementarea curentă, `_baza_articol` adaugă întotdeauna punctul final indiferent care pattern a prins marcajul, deci acest exemplu specific produce deja `articol` identic pentru ambele variante chiar și cu dedup pe cheia brută — nu izolează singur fix-ul de normalizare (de-asta am adăugat și testul de mai sus cu (B)/(b), care chiar depinde de normalizare). L-am păstrat fiindcă a fost cerut explicit și tot verifică un comportament real (varianta mai lungă câștigă).

2. **Titlu de capitol cu un singur nivel** (task 3, punct 2):
   - `test_titlu_capitol_simplu_cu_copil_direct_devine_context_iar_introducerea_nu_se_lipeste` — reproduce exact structura I5 (`3.2.5.2.` → „4. Elemente generale de calcul” → „(1) …” → „4.1. …”). Verifică 3 lucruri simultan: „4.” devine marcaj propriu (nu se lipește de 3.2.5.2.), introducerea rămâne chunk cu articol „4.”, titlul se propagă ca prefix pe „4.1.”. Ar pica dacă oricare din cele trei ar regresa.
   - `test_enumerare_simpla_fara_copil_1_1_nu_e_tratata_ca_titlu_de_capitol` — „1. text… 2. text…” fără copil „1.1.” rămâne text normal, nu devine marcaj. Ar pica dacă regula ar deveni prea permisivă (orice „N. Majusculă” tratat ca titlu).

3. **Subpuncte care reîncep** (task 3, punct 3 / task 3b din handoff-ul coder-ului):
   - `test_subpuncte_care_reincep_nu_se_imparte_pe_subpuncte` — numerotare (1)(2)(1)(2): articolul rămâne o unitate, tăiată doar de limita de 1000 caractere. Ar pica dacă split-ul secundar ar continua să taie pe subpuncte cu numerotare care se repetă.
   - `test_subpuncte_strict_crescatoare_neconsecutive_se_impart_normal` — control pozitiv cu (1)(2)(4)(7): confirmă interpretarea coder-ului („strict crescător”, nu neapărat +1) — split normal pe 4 subpuncte. Ar pica dacă implementarea ar cere pas exact +1, sau dacă nu ar mai împărți deloc.

4. **Cifră lipită după marcaj** (task 3, punct 4):
   - `test_cifra_lipita_dupa_marcaj_precedat_de_punctele_nu_e_articol` — exemplul literal din handoff (,,…de la punctele\n4.2.4.5 și 4.2.4.6”). Ar pica dacă articolul fals „4.2.4.5” ar reapărea și ar fura, prin dedup, textul articolului real.
   - `test_cifra_lipita_dupa_marcaj_fara_cuvant_de_trimitere_tot_nu_e_articol` — aceeași structură, dar fără niciun cuvânt din lista de trimitere pe rândul anterior (rândul anterior se termină cu „sunt”), izolând regula generică pe cifra lipită imediat (regăsită de coder separat, pe NP 010 rândul 2817). Ar pica dacă doar lista de cuvinte ar respinge trimiterile rupte, nu și regula generică.

5. **Cuvinte noi de final de rând** (task 3, punct 5):
   - `test_cuvinte_noi_de_trimitere_rupta_fac_marcajul_urmator_trimitere`, parametrizat pe toate cele 7 cuvinte noi (`punctele`, `punctul`, `punctelor`, `articolele`, `articolelor`, `prevederile`, `prevederilor`). Marcajul de pe rândul următor e altfel perfect valid (spațiu + majusculă) — respins doar din cauza cuvântului anterior. Ar pica pentru orice cuvânt lipsă din listă în implementare.

### `tests/test_reimport_approved.py`

- `test_main_tipareste_json_ascii_pentru_rezultat_cu_t_cu_sedila` (task 4): monkeypatch pe `module.dry_run` ca să întoarcă un rezultat cu „Ț” în el, apelează `module.main(...)`, capturează stdout prin `capsys`. Verifică: `main()` întoarce 0 (nu explodează), linia de ieșire se poate encoda ASCII fără eroare (`.encode("ascii")` — exact eroarea reală de pe consola cp1252), conținutul JSON se poate reparsa corect, și că „Ț” apare escapat (`Ț`), nu brut. Ar pica dacă `ensure_ascii` ar reveni la `False`.

## Ce NU am acoperit și de ce

- Nu am testat exhaustiv toate cele 9 documente reale la nivel de poziții neconsecutive — DB-ul de producție (read-only) nu e accesibil de aici; testul de la task 2 rulează pe `documente_noi/extracted.txt` local, cum a cerut planner-ul, și e skip-uit dacă folderul lipsește din worktree.
- Nu am scris test sintetic separat pentru „titlu.” cu context la split secundar interacționând cu titlul de capitol simplu (combinație task 2 + split secundar pe articol lung) — nu a fost cerut explicit și ar fi adăugat complexitate fără un caz real citat.
- Riscul semnalat de coder în raport (regex `PATTERN_TITLU_CAPITOL_SIMPLU` generic, posibile fals-pozitive pe NP 004/I9/NP 091 neexemplificate) e acoperit indirect de testul de neconsecutivitate + numărul fix de chunk-uri pe acele documente (task 1/2), nu printr-un test sintetic dedicat — orice fals-pozitiv ar schimba numărul de chunk-uri sau ar produce coliziuni neconsecutive, deci ar pica deja unul din cele două teste existente.

## Suspiciuni de bug

Niciuna nouă găsită în codul livrat de coder, dincolo de riscurile deja semnalate de coder însuși în raportul lui (regex generic pentru titlu de capitol simplu, neverificat pe toate documentele).

## Comanda exactă pentru planner

```
python -m pytest -q
```

sau, pentru doar fișierele atinse aici:

```
python -m pytest -q tests/test_populare_db.py tests/test_chunking_core.py tests/test_reimport_approved.py
```
