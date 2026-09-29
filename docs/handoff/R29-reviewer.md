# R29 — Reviewer

Worktree `D:\Omnia-MVP-r29`, branch `feat/r29-np127`, bază `main` `8d8f3fc` (`D:\Omnia-MVP`). Citește `R29-coder.md`, `R29-coder-raport.md`, `R29-tester.md` (cu corecturile planner-ului), `R29-tester-raport.md`.

## Starea verificată de planner
- 11 documente cu `extracted.txt`: chunk-uri identice cu `main`, acoperire neschimbată (după corectura planner la separatorul „+”).
- NP 127:2009 (text oficial din Portalul Legislativ, MO 74/2010): 196 chunk-uri, articole 1–173, art. 117 / 129 / 130 cu conținutul cerut de feedback-ul de testare; acoperire 0.9381 (lipsesc antetul Portalului și titlurile de capitol/secțiune); prag 0.93 în `reimport_approved` și în testul paralel.
- Teste: toate trec.

## Ce verifici
1. Cod inutil / risc de fals pozitiv: `PATTERN_ARTICOL_NP127`, eliminarea titlurilor, separatorul „+” condiționat — pot atinge alte documente sau formate viitoare?
2. Decizia coder-ului de a elimina titlurile de capitol/secțiune (fără context propagat) și tabelul din Capitolul XIV lipit de art. 173 — acceptabil sau risc de citare greșită (tabelul de standarde etichetat „art. 173”)?
3. Teste: acoperă, pot pica, nu sunt redundante?

Verdict APROBAT / RESPINS cu listă. Nu modifici nimic.
