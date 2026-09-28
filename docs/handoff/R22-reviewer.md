# R22 — Reviewer

Worktree: `D:\Omnia-MVP-r22-i7`, branch `fix/r22-diacritice-i7` (pornit din R21, PR #23). Revizuiește doar diferența față de R21: `git diff origin/fix/r21-anexe-p118...HEAD` (citește fișierele direct). Citește `R22-coder.md`, `R22-coder-raport.md`, `R22-tester.md`, `R22-tester-raport.md`.

Dovezi planner: `python -m pytest -q` cu `documente_noi` → **1247 passed**. I7: 15826 caractere corupte în sursă → 0 în chunk-uri; acoperire 0,971 neschimbată; 2215 chunk-uri. Celelalte 8 documente: 0 astfel de caractere în sursă, număr de chunk-uri și acoperire identice.

## Ce verifici
1. **Mapările:** fiecare substituire e dovedită în textul real (`documente_noi/i7_2011/extracted.txt`)? `ú` e o literă legitimă în texte străine (nume, citate) — riscul pentru normative viitoare e acceptabil sau ar trebui limitată corectura la documentele în care apare sistematic?
2. **Integrarea:** aplicată consecvent în `extrage_text`, `creeaza_chunkuri` și `acoperire_text_brut` (simetrie pentru poarta D24); nicio altă modificare de comportament.
3. **Cod inutil**; teste care trec indiferent de cod.

Read-only, fără comenzi. Verdict APROBAT/RESPINS, finding-uri pe severitate cu fișier:linie, separat coder/tester, max 400 de cuvinte.
