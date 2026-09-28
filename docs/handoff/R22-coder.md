# R22 — Coder: diacriticele corupte din I7-2011

Worktree: `D:\Omnia-MVP-r22-i7`, branch `fix/r22-diacritice-i7`, pornit din branch-ul R21 (`fix/r21-anexe-p118`, commit `7905696`, PR #23 nemerge-uit încă) pentru că atinge același fișier. Aprobat de Lucian 28-09-2026.

Notă: `diacritice.normalizeaza_diacritice` (`diacritice.py:34`) face azi doar sedilă→virgulă; extinde-o sau adaugă o funcție alăturată, fără a schimba comportamentul pentru textele fără aceste caractere.

## Dovezi (planner, `documente_noi/i7_2011/extracted.txt`)
Caractere care nu există în română, substituite sistematic la extragerea PDF-ului I7:
- `Ġ` (U+0120) ×11030 → `ț` (ex. „protecĠia”)
- `ú` (U+00FA) ×4683 → `ș` (ex. „úi”, „úocurilor”)
- `ğ` (U+011F) ×58 → `Ț` (în cuvinte cu majuscule: „INSTALAğIILOR”, „PROTECğII”, „SECURITĂğII”)
- `܊` (U+070A) ×31 → `ț` („construc܊ii”, „re܊elele”)
- `܈` (U+0708) ×24 → `ș` („܈i”, „܈antierele”)
- `\x98` ×74 = simbol din formule („Pi Pa \x98 \x98 unde”) — **nu se mapează**.
Aceste caractere apar în citatele date utilizatorilor (ex. „locuinĠe”, „úi”).

## Sarcina
1. Funcție de normalizare a acestor substituții (în `diacritice.py`, lângă normalizarea existentă sedilă→virgulă), aplicată:
   - în `procesare_documente.extrage_text` (extrageri viitoare);
   - la începutul `chunking_core.creeaza_chunkuri` **și** în `chunking_core.acoperire_text_brut` pe textul brut, ca metrica de acoperire să compare texte normalizate identic (altfel poarta D24 ar vedea „pierderi” false).
2. Verifică în I7 dacă există și forma majusculă corectă a lui `ș` coruptă (ex. un alt caracter străin în cuvinte cu majuscule precum „ÎNTREŢINERE”, „SIGURANŢĂ”); raportează ce găsești, mapează doar ce e dovedit în text.
3. Nu atinge alte reguli. Nu atinge `retrieval_core.py`, `main.py`, `generation_core.py`, `supabase/`, `.env`, `documente_noi/`.

## Acceptare (planner)
I7: zero `Ġ`, `ú`, `ğ`, `܊`, `܈` în chunk-uri; acoperire ≥ valoarea curentă; celelalte 8 documente neschimbate (număr de chunk-uri și acoperire identice); pytest verde.
