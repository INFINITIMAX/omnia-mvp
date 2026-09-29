# R29 — Coder: articole „Articolul N” (NP 127:2009, parcaje subterane)

Worktree `D:\Omnia-MVP-r29`, branch `feat/r29-np127` (din `main` `8d8f3fc`). Aprobat de Lucian 29-09-2026 (feedback de la testare: debitul de desfumare 600/900 m³/h pe autoturism și distanța de 8 m a gurilor de evacuare a fumului sunt în NP 127, lipsă din aplicație).

## Date (planner, local, în afara Git)
- `documente_noi/np127_2009/extracted.txt` — textul oficial al anexei din Portalul Legislativ (MO nr. 74/02.02.2010), 593 de rânduri, cu diacritice. Structura: `Capitolul I Dispoziții generale`, `Secţiunea 1 Obiect și domeniu de aplicare` (uneori `Secţiunea a 2-a …`), `Articolul 117 (1) Evacuarea fumului … (2) …` (alineatele pe același rând cu articolul), rânduri `+` ca separatoare, la final `Capitolul XIV Referințe tehnice și legislative` (tabele cu standarde) și note de subsol. 173 de articole, 14 capitole.
- Scanare planner pe toate `documente_noi/*/extracted.txt`: tiparul `^Articolul N` / `^Capitolul <roman>` apare **doar** în NP 127.
- `retrieval_core._ARTICLE_MARKER` recunoaște deja „articolul 117” / „art. 117” → articolul normalizat `117`.

## Sarcina (`chunking_core.py`)
1. Rândurile `Articolul N` (N întreg, la început de rând) deschid un articol cu identificatorul `N.` (ca celelalte articole, cu punct final); textul articolului începe după `Articolul N`.
2. `Capitolul <roman> <titlu>` și `Secţiunea/Secțiunea <n|a n-a> <titlu>` sunt titluri — context pentru articolele-copil (ca titlurile de secțiune existente), nu articole.
3. Rândurile formate doar din `+` nu apar în chunk-uri.
4. Alineatele inline `(1) … (2) …` pot rămâne în același chunk (split-ul existent pe lungime rămâne valabil); nu e obligatoriu split pe alineat.
5. Reutilizează mecanismele existente (regiuni, titluri, limita de 1000) — fără logică paralelă.

## Criterii de acceptare (planner)
- NP 127: articole `1.` … `173.` fiecare propriu; `117.` conține „600 m3/h … sprinkler” și „900 m3/h”; `129.` conține „8,00 m față de orice construcție supraterană”; `130.` conține „8,00 m” (prize de aer proaspăt); fără `+` în text; contractul importerului trece (≤1000, articol valid); acoperire ≥ 0.95.
- Celelalte 12 documente cu `extracted.txt`: chunk-uri **identice** cu `main`.

## Constrângeri
Doar `chunking_core.py`. Nu rula comenzi, nu scrie teste. Raport: `docs/handoff/R29-coder-raport.md`. Poți citi fragmente mici din `D:\Omnia-MVP\documente_noi\np127_2009\extracted.txt` (ex. rândurile 1–60, ~430–470, ultimele 80).
