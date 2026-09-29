# R27 — Coder: raport

## Fișiere modificate

### `chunking_core.py`
1. Adăugat lângă `_PATTERN_CARACTER_VALID_DUPA_NUMAR` (linia ~360):
   - `_PATTERN_LITERA_MICA_DUPA_NUMAR = re.compile(r"^[a-zăâîșțşţ]")`
   - `_PATTERN_CRATIMA_DEFINITIE = re.compile(r"[-–]")`
   - `_LUNGIME_FEREASTRA_CRATIMA_DEFINITIE = 120`
2. `_este_referinta_rupta`: restructurat finalul funcției. Înainte:
   `return not _PATTERN_CARACTER_VALID_DUPA_NUMAR.match(rest)`.
   Acum:
   ```python
   if _PATTERN_CARACTER_VALID_DUPA_NUMAR.match(rest):
       return False
   if _PATTERN_LITERA_MICA_DUPA_NUMAR.match(rest) and _PATTERN_CRATIMA_DEFINITIE.search(
       urmator[:_LUNGIME_FEREASTRA_CRATIMA_DEFINITIE]
   ):
       return False
   return True
   ```
   Logica veche e neschimbată (echivalentă), doar cu o ramură nouă: dacă primul
   caracter nevalid e literă mică ȘI apare o cratimă/en dash în primele 120 de
   caractere ale restului rândului (indiferent dacă e lipită de cuvânt, precedată
   de paranteză, sau mutată pe rândul fizic următor), marcajul rămâne articol
   valid — nu mai e tratat ca trimitere ruptă.

**Decizie**: am ales varianta simplă cerută în task (doar cratimă/en dash în
fereastră de 120 caractere), **fără** criteriul secundar „secțiune
TERMINOLOGIE/DEFINIȚII”. Motiv: planner-ul a confirmat deja prin scanare
(`^N.N[.N…]. <literă mică>… [-–]`) că exact acest tipar combinat (literă mică +
cratimă/en dash) apare de 90 de ori în P 118/3 și o dată în P 118/2 (33.5) — și
zero ori în celelalte 8 documente. Fereastra de 120 caractere acoperă toate
variantele citate ca dovadă (cratimă lipită, paranteze înainte de cratimă,
cratimă pe rândul următor, en dash), inclusiv exemplele verificate manual în
`extracted.txt` (P 118/3 rândurile 141-409: 2.1-2.65 și subnivelurile 2.19.x,
2.19.18.x; P 118/2 rândurile 13755-13773: 33.1-33.7, unde doar 33.5 începe cu
literă mică). Nicio a doua condiție nu era necesară, deci am ales-o pe cea mai
simplă dintre cele două oferite în task.

### `reimport_approved.py`
- `DOCUMENTE_APROBATE`: adăugat
  `"p118_2_2013": "P118_2_2013_consolidat.txt"` și
  `"p118_3_2015": "P118_3_2015_consolidat.txt"`.
- `PRAGURI_ACOPERIRE`: adăugat `"p118_2_2013": 0.98` și `"p118_3_2015": 0.94`.

## Sincronizare cu teste (nu am atins, doar raportez)
`tests/test_populare_db.py`, `PRAG_ACOPERIRE_MINIM_PER_DOCUMENT` (linia ~489),
conține doar 8 intrări (i5, i7, i9, np004, np010, np057, p118_1, spitale) —
`np091_2003` lipsește deja acolo (probabil pentru că sursa lui e PDF direct,
nu `documente_noi/np091_2003/extracted.txt`). `p118_2_2013` și `p118_3_2015`
**au** `documente_noi/<id>/extracted.txt`, deci ar trebui adăugate în acest
dict de tester, cu aceleași praguri (0.98 / 0.94), dacă se dorește ca testul de
regresie pe acoperire să acopere și aceste două documente noi. Nu le-am
adăugat — e fișier de test, în afara mandatului meu.

## Ce nu am făcut
- Nu am rulat nimic (nici teste, nici preflight).
- Nu am atins `consolidare_normative.py`, `extragere_mo_bis.py`,
  `retrieval_core.py`, `generation_core.py`, `main.py`, `static/`,
  `supabase/`, `.env`, `documente_noi/`, `tests/`.

## Ce ar trebui verificat de planner
- Rulare preflight/teste pe P 118/3 și P 118/2 pentru criteriile de acceptare
  din task (articole proprii 2.1-2.64, inclusiv 2.19.x; 33.5 propriu; celelalte
  8 documente identice cu `main`).
- Contractul importerului (`_valideaza_chunkuri` / `manual_ingestion_import`)
  pe chunk-urile noi din P 118/3 și P 118/2 (≤1000 caractere, articol valid).
- Decizia dacă `tests/test_populare_db.py` trebuie completat de tester cu
  `p118_2_2013`/`p118_3_2015` în `PRAG_ACOPERIRE_MINIM_PER_DOCUMENT`.
- Confirmă că fișierele `P118_2_2013_consolidat.txt` / `P118_3_2015_consolidat.txt`
  chiar există ca `source_key` în DB (`public.documente`) pentru aceste
  document_id — nu am acces/nu am verificat DB-ul.
