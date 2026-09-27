# R16 — Coder: articole ambigue rămase după reimport + bug de afișare

Worktree: `D:\Omnia-MVP-r16-dedup`, branch `fix/r16-dedup-normalizat` (din `main` `6adf199`: R14 + R15). Aprobat de Lucian 27-09-2026.

## Context (dovezi planner, DB producție read-only după reimportul R15)
Toate cele 9 documente `approved` au fost reimportate cu chunker-ul R14 (acoperire 0,882–0,999). Rămân **63 de articole** al căror `articol_normalizat` apare în chunk-uri **neconsecutive** (ruta exactă le refuză ca `ambiguous_article`): I5 15, NP 010 25, P 118/1 12, I7 5, NP 015 5, NP 057 1 (înainte de R14: 292). Două cauze identificate:

1. **Dedup pe identificatorul brut, nu pe cel normalizat.** Exemple I5: `6.1.1@401` și `6.1.1.@621`, `6.1.2@402` și `6.1.2.@639,640`, `6.8.1.2@408` și `6.8.1.2.@753`. Forma fără punct (o listă de la începutul capitolului 6, chunk-urile 401–409) și forma cu punct (articolul real) sunt chei diferite în dedup, dar `articol_normalizat` identic.
2. **Capitole cu un singur nivel de numerotare nu sunt separatoare.** I5, `documente_noi/i5_2022/extracted.txt` rândurile ~2124–2180: după articolul `3.2.5.2.` (subpunctele (1)–(7)) urmează `4. Elemente generale de calcul` cu propriile subpuncte `(1)…`, apoi `4.1. Parametrii interiori…`. Rândul `4. Elemente…` nu e recunoscut (marcajele cer ≥2 componente), deci introducerea capitolului 4 se lipește de `3.2.5.2.` și apare `3.2.5.2.(1)` de două ori (chunk-urile 158 și 165).
3. **Bug de afișare în `reimport_approved.py`:** `main()` tipărește rezultatul JSON după commit; pe consola Windows (cp1252) un caracter ca „Ț” ridică `UnicodeEncodeError` → cod de ieșire 1 **după un commit reușit** (s-a întâmplat la P 118/1).

## Sarcina
1. În `chunking_core.py`, deduplicarea folosește **identificatorul normalizat** (același contract ca `_normalizeaza_articol` / `normalizeaza_articol`) drept cheie; regula „cea mai lungă variantă câștigă” și contorul `duplicate_eliminate` rămân. `articol` păstrat în chunk = forma variantei câștigătoare.
2. Titlu de capitol cu un singur nivel: un rând `N. Titlu` (N = 1–2 cifre, titlu pe un singur rând, ≤120 caractere, începe cu majusculă, fără `.`/`;`/`:` final) este titlu de secțiune **numai dacă** următorul marcaj de articol recunoscut este un copil al lui (`N.1.`, `N.2.`…). Tratează-l ca titlurile din regula 1d: rândul titlu devine context (prim rând) pentru copiii direcți; textul dintre titlu și primul copil (introducerea capitolului, ex. „(1) Dimensionarea instalațiilor…”) devine un chunk cu `articol` = `N.` (cu subpunctele lui, prin split-ul secundar existent). Nu trata ca titlu enumerările din corpul articolelor (`1. text…` urmate de `2. text…`, fără copil `1.1.`).
3. În `reimport_approved.py`, ieșirea finală a `main()` nu mai poate eșua din cauza codificării consolei (ex. `json.dumps(..., ensure_ascii=True)` sau echivalent minim). Nu schimba altceva în script.
3b. **(Adăugat de planner în timpul lucrului) Numerotare de subpuncte care reîncepe în același articol.** Verificare locală (`chunking_core` actual pe textele reale) reproduce exact cele 63 de cazuri și arată a treia cauză: NP 010 `4.6.(1)` apare la pozițiile 117, 127, 133, 136, 141… (numerotarea `(1)…` reîncepe pentru fiecare sub-secțiune nenumerotată); la fel P 118/1 `1.2.1.(1..3)`, NP 015 `5.8.(1..3)`, I7 `4.1.1.(3)`. Regulă: split-ul secundar pe subpuncte se aplică **numai** dacă numerele subpunctelor din articol sunt strict crescătoare fără reluare (1, 2, 3…); dacă numerotarea reîncepe sau se repetă, articolul **nu** se împarte pe subpuncte — rămâne o unitate cu `articol` = articolul de bază, tăiată apoi de limita de 1000 de caractere în bucăți consecutive. Nu inventa identificatori noi.
4. Nu schimba altceva. Nu atinge `retrieval_core.py`, `main.py`, `generation_core.py`, `supabase/`, `.env`, `documente_noi/`.

## Criterii de acceptare (planner-ul verifică)
- Pe textele reale: niciun `articol_normalizat` în chunk-uri neconsecutive pentru cele 8 documente cu `extracted.txt` (și NP 091 din PDF), sau fiecare caz rămas explicat în raport.
- Acoperirea față de textul brut nu scade sub valorile curente (p118 0,993; i7 0,971; i5 0,978; i9 0,969; np004 0,923; np010 0,999; np057 0,882; spitale 0,982; np091 0,989) și toate trec poarta D24 în dry-run.
- `python -m pytest -q` verde (planner-ul rulează; numerele fixe de chunk-uri le actualizează Tester-ul).

## Runda 2 — regresie NP 010 (27-09-2026)

Dovezi planner după runda 1: articole normalizate neconsecutive **0** în toate cele 9 documente (față de 63). Acoperire neschimbată sau mai bună, cu **o excepție: NP 010 0,999 → 0,980** (sub pragul D24 de 0,99), 438 → 343 chunk-uri, `duplicate_eliminate` 0 → 22. Pytest: 1080 passed (singurul eșec e testul intermitent al worker-ului, în afara scope-ului).

Cauza: `documente_noi/np010_2022/extracted.txt` rândurile 3019–3020: „…cu respectarea prevederilor de la punctele↵4.2.4.5 și 4.2.4.6”. Rândul `4.2.4.5 și 4.2.4.6` produce un articol fals `4.2.4.5` (chunk cu text „5 și 4.2.4.6 Tabelul 4.21…”). Înainte de R16 era cheie separată de articolul real `4.2.4.5.`; acum dedup-ul normalizat îi pune în aceeași cheie și varianta falsă, mai lungă, **înlocuiește articolul real** („Pentru reducerea riscului de accidentare a elevilor…”, rândurile 1575+).

1. Un marcaj numeric urmat **imediat** (fără spațiu) de o cifră este prefixul unui număr mai lung, nu început de articol (ex. `4.2.4.` + `5 și…`). Verifică în `_este_referinta_rupta` / allow-list că cifra lipită nu mai e acceptată; cifra după spațiu rămâne cum e.
2. Adaugă la lista cuvintelor de final de rând care anunță o trimitere: `punctele`, `punctul`, `punctelor`, `articolele`, `articolelor`, `prevederile`, `prevederilor` (comparare fără diacritice/majuscule, ca lista existentă).
3. Verifică prin citire că NP 010 nu mai are alte articole false de același tip. Nu schimba altceva. Actualizează raportul cu „Runda 2”.

## Constrângeri dure
Nu rula comenzi. Nu scrie teste (Tester-ul). Fără comentarii inutile. Raport în `docs/handoff/R16-coder-raport.md`: fișiere, decizii, riscuri.
