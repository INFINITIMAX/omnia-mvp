# R26-B — Tester: consolidarea cu ordine de modificare

Worktree `D:\Omnia-MVP-r26`, commit `16d4c2d`. Citește `R26-B-coder.md` + rundele 2–3, `R26-B-coder-raport.md`, `R26-spec.md`, `R26-C-coder.md` (formatul marcajului).

## Starea verificată de planner
- Rulare reală: **P 118/2**: 63/64 operații aplicate (item 24 `manual` — sintagma din ordin „calcul **al** densității” nu coincide cu baza „calcul **ale**”, decizie Lucian), 71 de marcaje; **P 118/3**: 18/18, 20 de marcaje, Art. II → 30 de înlocuiri (26 minuscule + 4 majuscule).
- Corecturi **planner** după coder (verifică-le și pe ele):
  1. `consolidare_normative.aplica_operatii`: la aplicare, dacă textul nou nu se termină cu `\n` și restul nu începe cu `\n`, se adaugă `\n` (bug: „…]3.2.3 Dimensionarea” — punctul următor se lipea de marcaj și dispărea ca articol).
  2. `_verifica_final`: textul nou/vechi e comparat **după** înlocuirile globale ale aceluiași ordin (textul nou al 3.3.19 conține el însuși „semnalizare și avertizare”, înlocuit legitim de Art. II).
  3. Manifest P 118/3: înlocuirile globale restrânse la `detectare, semnalizare și avertizare` + varianta cu majuscule (Art. II se aplică în toate formele flexionate).
  4. `chunking_core._aplica_limita_caractere`: tăietura la 1000 de caractere nu mai cade **în interiorul** unui marcaj (`PATTERN_MARCAJ_PROVENIENTA`); bucata poate depăși limita cu cel mult lungimea marcajului. Înainte, 4 marcaje erau tăiate în două.
- `python -m pytest -q`: 1286 passed. Rezultat chunker pe textele consolidate: 70/71 marcaje în chunk-uri (lipsește cel al primului „23.51” abrogat — numărul e duplicat în sursa MO și chunker-ul păstrează punctul 23.51 încă în vigoare; acceptat).

## Sarcina — teste în `tests/test_consolidare_normative.py` (nou) și `tests/test_chunking_core.py` (sau fișierul existent de chunking), sintetice, fără fișierele reale
1. Segmentare: ambele stiluri de numerotare (număr pe rând propriu / pe același rând), oprire la „Articolul II”/„Art. II”, eliminare anteturi MO/numere de pagină/rânduri „...”, numerotare neconsecutivă → eroare, item nerecunoscut → eroare, item „sintagma „X” se înlocuiește cu sintagma „Y”.”.
2. Fiecare tip de operație (inclusiv imbricat alineat→literă cu litere în interiorul alineatului, prima subunitate pe rândul punctului cu/fără spațiu, alineat implicit la `insereaza_dupa`, `aparitie`+`justificare` — permis doar la ≥2 potriviri, `renumeroteaza_inlocuieste` cu număr nou existent → eroare, punct fără punct final `3.3.1 (1)…`, cuprins ignorat).
3. Fail-closed: țintă cu 0 sau ≥2 potriviri, suprapuneri, manifest ≠ segmentare, instrucțiune care nu menționează punctul, text nou absent, text vechi rămas, număr de marcaje greșit.
4. Marcajul: format exact, pe rând propriu, niciodată imediat după numărul punctului; punctul următor rămâne la început de rând (regresie pentru corectura 1); înlocuirile globale se aplică și în textul nou (corectura 2).
5. Chunker: un text lung cu marcaj peste granița de 1000 → marcajul apare întreg într-o singură bucată; textele fără marcaj se taie exact ca înainte (regresie).
6. Opțional (skip dacă lipsesc fișierele, ca testele existente cu documente reale): pe `documente_noi/p118_*/baza.txt` + ordin + manifest, consolidarea reușește și numărul de marcaje e 71, respectiv 20.

Scrii doar în `tests/`. Nu rula comenzi. Fiecare test poate pica. Raport: `docs/handoff/R26-B-tester-raport.md`.
