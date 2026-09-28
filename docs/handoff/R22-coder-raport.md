# R22 — Coder: raport

## Fișiere modificate

- `diacritice.py`: adăugat `_SUBSTITUIRI_PDF_LA_DIACRITICE` (tabelă `str.maketrans`) și funcția
  `corecteaza_substituiri_pdf(text)`, alături de `normalizeaza_diacritice` existentă, fără să-i
  ating comportamentul. Mapează `Ġ`(U+0120)→`ț`, `ú`(U+00FA)→`ș`, `ğ`(U+011F)→`Ț`,
  `\u070A`→`ț`, `\u0708`→`ș`. `\x98` nu e mapat (nu e diacritică, ci simbol de formulă).
- `procesare_documente.py`: `extrage_text` aplică acum `corecteaza_substituiri_pdf` înainte de
  `normalizeaza_diacritice`, pe tot textul, înainte de `_repara_np091_verificat`. Import adăugat.
- `chunking_core.py`: import `corecteaza_substituiri_pdf` din `diacritice`. `creeaza_chunkuri`
  aplică funcția pe `text` la intrare, primul lucru din funcție. `acoperire_text_brut` aplică
  aceeași funcție pe parametrul `text` (textul brut) înainte de a-l compara cu textul concatenat
  al chunk-urilor (care e deja normalizat, provenind fie din `extrage_text` nou, fie din
  `creeaza_chunkuri`).

## Verificare formă majusculă coruptă a lui Ș (punctul 2 din task)

Am căutat în `D:\Omnia-MVP\documente_noi\i7_2011\extracted.txt` cu regex pentru caractere
non-ASCII lipite între litere majuscule. Singurul caracter corupt găsit în cuvinte cu majuscule
e `ğ` (deja mapat, corespunde lui `Ț`, nu `Ș`) — apare în `INSTALAğIILOR`, `PROTECğII`,
`SECURITĂğII`, `ÎNTREğINEREA`, `FUNCğIE`, `IZOLAğIE`, `TELECOMUNICAğII` etc. Nu am găsit nicio
altă substituție în cuvinte majuscule care ar corespunde unei forme corupte a lui `Ș` (ex.
cuvinte precum „SECURITATE”, „ROMÂNIEI” apar corect, fără caractere străine). Concluzie: **nu
există dovadă** de formă majusculă coruptă separată a lui `Ș` în I7 — nu am adăugat nicio
mapare nedovedită pentru asta.

## Decizii neincluse explicit în task

- Am ales să aplic `corecteaza_substituiri_pdf` **înaintea** lui `normalizeaza_diacritice` în
  `extrage_text` (ordinea nu contează funcțional — seturile de caractere sunt disjuncte — dar
  am păstrat-o logic: mai întâi corectez substituirile PDF specifice, apoi sedila generică).
- Nu am modificat docstring-ul funcției `normalizeaza_diacritice` sau contractul ei; am adăugat
  doar comentarii/docstring pentru funcția nouă.

## Ce nu am făcut

- Nu am atins `retrieval_core.py`, `main.py`, `generation_core.py`, `supabase/`, `.env`,
  `documente_noi/` (conform constrângerilor).
- Nu am rulat nimic (extragere PDF, teste, pytest) — conform rolului meu.
- Nu am scris teste.

## Ce ar trebui verificat de planner

- `pytest` complet (în special testele de acoperire/chunking pentru toate cele 9 documente).
- Regenerare `extracted.txt` pentru I7 (sau verificare directă pe chunk-urile din
  `creeaza_chunkuri` aplicat pe fișierul curent) — confirmă zero `Ġ`/`ú`/`ğ`/`܊`/`܈` în chunk-uri
  și acoperire ≥ valoarea curentă.
- Confirmă că celelalte 8 documente au număr de chunk-uri și acoperire identice (funcția nouă
  e no-op pe text fără aceste caractere, dar merită verificat empiric).
- Verifică că nu există import circular real la rulare (`chunking_core` importă acum din
  `diacritice`; `diacritice.py` nu importă nimic din proiect, deci nu ar trebui să fie problemă).
