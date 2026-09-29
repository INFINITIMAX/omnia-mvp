# R26-D — Coder: raport (marcajul de proveniență în toate bucățile unui articol)

## Fișiere modificate

### `chunking_core.py`
- `PATTERN_MARCAJ_PROVENIENTA` extins: recunoaște acum și forma la nivel de articol
  (`Articol cu text modificat/introdus/abrogat prin Ordinul nr. …`), pe lângă forma
  originală (`Text modificat`/`Text introdus`/`Abrogat`). Am transformat cele două
  segmente relevante în grupuri capturate (`(Text modificat|...|modificat|...)` și
  `(prin Ordinul nr\. ...)`), fără să schimb comportamentul folosirii existente din
  `_aplica_limita_caractere` (acolo se folosesc doar `match.start()`/`match.end()`).
- Adăugate: `_PATTERN_SUFIX_ALINEAT_PROVENIENTA` (strip sufix `(N)` de la finalul
  identificatorului, pus de `_aplica_split_secundar`), `_baza_articol_provenienta`,
  `_adjectiv_provenienta` (normalizează tipul capturat la adjectivul folosit în
  marcajul de articol: `Text modificat`/`modificat` → `modificat`, `Abrogat`/`abrogat`
  → `abrogat`), și funcția principală `_propaga_marcaj_provenienta(chunkuri)`.
- `_propaga_marcaj_provenienta`: grupează bucățile după articolul de bază (identic cu
  identificatorul complet dacă nu are sufix de alineat). Pentru fiecare grup, colectează
  marcajele distincte (cheie = `(adjectiv, rest_dupa_"prin")`) găsite în oricare bucată a
  grupului, în ordinea primei apariții, apoi adaugă la fiecare bucată din grup, pe rânduri
  finale proprii, marcajul echivalent la nivel de articol pentru fiecare cheie pe care
  bucata respectivă nu o are deja (verificat tot cu `PATTERN_MARCAJ_PROVENIENTA`, ca să
  prindă atât forma originală cât și una deja propagată). Grupurile fără niciun marcaj nu
  sunt atinse deloc — textul rămâne identic byte cu byte.
- Apelată în `creeaza_chunkuri`, imediat după `_aplica_limita_caractere` (pasul final cerut).

### `generation_core.py`
- `_MODIFICATION_MARKER` extins să accepte și forma `Articol cu text (modificat|
  introdus|abrogat) prin Ordinul nr. …` (prefix opțional `Articol cu text `, plus
  adjectivele bare pe lângă formele originale). `_modification_markers` (neschimbată)
  extrage în continuare tot conținutul dintre paranteze, deci `modificari` conține fie
  „Text modificat prin …”, fie „Articol cu text modificat prin …”, după bucata citată.
- Regula 11 din prompt actualizată să menționeze explicit ambele forme de marcaj și
  faptul că se poate referi fie la prevedere, fie la articolul din care face parte.

### `docs/DECISIONS.md`
- Adăugată „Runda 2 (29-09-2026)” la secțiunea D27: descrie problema (marcajul ajunge
  doar în ultima bucată a unui articol despărțit pe alineate/limită de caractere) și
  decizia (propagarea unui marcaj echivalent la nivel de articol de către
  `chunking_core`, recunoscut de `modificari`/prompt în ambele forme).

## Decizii neincluse explicit în task
- Cheia de deduplicare/identitate a unui „marcaj distinct” este perechea
  `(adjectiv_normalizat, text_dupa_"prin")`, nu doar textul de după „prin” — am ales
  asta ca să nu se piardă un marcaj dacă, teoretic, același ordin ar aplica atât o
  modificare cât și o abrogare unor bucăți diferite ale aceluiași articol de bază.
- Am folosit `dict(chunk)` pentru copiere shallow în `_propaga_marcaj_provenienta`, ca
  să nu mut lista/dict-urile primite ca parametru din `_aplica_limita_caractere`.

## Ce nu am făcut
- Nu am scris teste (nu e rolul meu) — un alt agent scrie acum teste de chunking în
  `tests/`; nu am atins acel director.
- Nu am atins `consolidare_normative.py`, `extragere_mo_bis.py`, `diacritice.py`,
  `populare_db.py`, `main.py`, `static/`.
- Nu am rulat nimic (nu am acces la shell).

## Ce ar trebui verificat de planner
- Rulare `creeaza_chunkuri` pe un text sintetic cu articol despărțit pe alineate și
  marcaj doar pe ultima bucată (cazul P 118/3, 3.3.1) — confirmă că toate celelalte
  bucăți primesc rândul „[Articol cu text modificat prin Ordinul nr. …]”.
- Rulare pe restul celor 9 documente (fără marcaje de proveniență) — confirmă că
  `chunkuri` rezultate sunt byte-identice cu înainte de această schimbare (nicio bucată
  nu trebuie atinsă când niciun marcaj nu există în articol).
- Verificare că `_aplica_limita_caractere` (tăietura la 1000 caractere) tot nu rupe un
  marcaj de tip „Articol cu text …” dacă un asemenea text ar apărea vreodată înainte de
  pasul de propagare (situație teoretică — propagarea rulează după tăietură, deci în
  mod normal nu se întâmplă, dar pattern-ul extins acoperă și acest caz).
- Testele tester-ului din `tests/` pentru chunking — verifică acoperirea exact a
  cazului din spec (P 118/3, 3.3.1) și a cazului „mai multe ordine/tipuri pe același
  articol” (deduplicare + ordine de apariție).
