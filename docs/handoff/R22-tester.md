# R22 — Tester

Worktree: `D:\Omnia-MVP-r22-i7`, branch `fix/r22-diacritice-i7` (pornit din R21). Citește `R22-coder.md` și `R22-coder-raport.md`. Cod: `diacritice.py` (`corecteaza_substituiri_pdf`), `procesare_documente.py` (`extrage_text`), `chunking_core.py` (`creeaza_chunkuri`, `acoperire_text_brut`).

## Starea verificată de planner (textele reale)
- I7: 15826 caractere corupte în sursă → **0** în chunk-uri; **2215** chunk-uri (era 2214); acoperire 0,971 neschimbată.
- Celelalte 8 documente: 0 astfel de caractere în sursă; număr de chunk-uri și acoperire identice cu R21 (i5 768, i9 800, np004 85, np010 356, np057 290, p118 3554, spitale 616, np091 213).

## Sarcina
1. Actualizează `NUMAR_CHUNKURI_ASTEPTAT_PER_DOCUMENT["i7_2011"]` la **2215**.
2. `tests/test_diacritice.py`: fiecare substituire (`Ġ`→`ț`, `ú`→`ș`, `ğ`→`Ț`, U+070A→`ț`, U+0708→`ș`) pe cuvinte reale din I7 („protecĠia”, „úi”, „INSTALAğIILOR”, „construc܊ii”, „܈i”); `\x98` rămâne neschimbat; text fără aceste caractere rămâne identic (inclusiv diacritice corecte și sedile, care rămân treaba lui `normalizeaza_diacritice`).
3. `tests/test_chunking_core.py`: `creeaza_chunkuri` pe un text cu caractere corupte produce chunk-uri fără ele; `acoperire_text_brut` pe același text brut corupt și chunk-urile lui dă 1,0 (simetrie — altfel poarta D24 ar vedea pierderi false).
4. `tests/test_procesare_documente.py` (sau fișierul existent de extragere): `extrage_text` aplică corectura (cu PDF/pagini falsificate, ca testele existente), în ordinea corectă față de `normalizeaza_diacritice`.
5. Test pe document real (același `skipif` pe `documente_noi`): niciun chunk I7 nu conține `Ġ`, `ú`, `ğ`, U+070A, U+0708.

## Constrângeri
Scrii doar în `tests/`. Nu rula comenzi. Fără modificări de producție. Fiecare test trebuie să poată pica. Raport în `docs/handoff/R22-tester-raport.md`.
