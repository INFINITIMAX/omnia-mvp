# R29 — Tester

Worktree `D:\Omnia-MVP-r29`, commit `5bf0f26`. Citește `R29-coder.md`, `R29-coder-raport.md`.

## Corecturi planner după coder (verifică-le)
1. Rândurile „+” se elimină **doar** când următorul rând nevid începe cu `Articolul N` / `Capitolul <roman>` / `Secțiunea` (separatorul Portalului Legislativ). Varianta coder-ului le elimina pe toate și schimba chunk-urile I7, P 118/3 și NP 015 (acolo „+” pe rând propriu e semn dintr-o formulă).
2. `_normalizeaza_pentru_acoperire` scoate și `Articolul N` de la început de rând (altfel acoperirea NP 127 era 11%).
- Prag NP 127: 0.93 (acoperire reală 0.9381; lipsesc doar antetul Portalului și titlurile de capitol/secțiune, eliminate intenționat).

## Starea verificată de planner
- 11 documente: chunk-uri identice cu `main`, acoperire neschimbată.
- NP 127: 196 chunk-uri, articole `1.`…`173.` toate prezente, art. 117 (600/900 mc/h), 129 și 130 (8,00 m), fără „+”, contract importer OK.
- `python -m pytest -q` → 1355 passed, 34 skipped.

## Sarcina — teste sintetice
1. `Articolul N` la început de rând → articol `N.`; `Articolul` în mijlocul unei fraze sau urmat de literă mică → nu.
2. Titlurile `Capitolul <roman> …`, `Secţiunea 1 …`, `Secţiunea a 2-a …` nu devin articole și nu apar în text; `Secțiunea conductelor se…` (frază, fără număr) rămâne text.
3. Separatorul „+”: eliminat înaintea `Articolul`/`Capitolul`/`Secțiunea`; **păstrat** când e într-o formulă (ex. rânduri `a`, `+`, `b`) — regresie pentru corectura 1.
4. Acoperirea: un text sintetic în format NP 127 dă acoperire ≈1 pentru articole (corectura 2).

Scrii doar în `tests/`. Nu rula comenzi. Raport: `docs/handoff/R29-tester-raport.md`.
