# R18 — Reviewer

Worktree: `D:\Omnia-MVP-r18-evaluare`, branch `feat/r18-set-evaluare`; `main` în `D:\Omnia-MVP`. Citește `R18-coder.md`, `R18-coder-raport.md` (inclusiv Runda 2), `R18-tester.md`, `R18-tester-raport.md`, `AGENTS.md`.

Dovezi planner: `python -m pytest -q` → **1169 passed**, 28 skipped. Setul `evaluare/set_aur.json` (30 cazuri, scris de planner; articolele așteptate verificate în textul sursă) validează. Rulare reală: 21 embedding-uri, 26/30 corecte (exact 6/6, semantic 18/21, negativ 2/3).

## Ce verifici
1. **Corectitudinea măsurării:** compunerea căutării e identică cu producția (`main.py` ~890–915)? potrivirea „copil” (`.` și `(`) poate număra greșit un articol diferit ca găsit? rangul și recall@k corecte? negativele: toate statusurile de refuz acceptate, `found` greșit.
2. **Siguranță/cost:** fără generare Anthropic; plafon 30 embedding-uri; conexiune `readonly`; fără `--run` zero apeluri; nicio cheie sau text normativ în raport; raportul în `evaluare/rapoarte/` (gitignored).
3. **Cod:** reutilizarea din `real_grounding_eval.py`/`main.py` rezonabilă; cod inutil.
4. **Setul de aur:** întrebări formulate fără a copia textul articolului (măsoară căutarea reală, nu potrivirea literală)? ambiguități evidente?
5. **Tester:** teste redundante sau care trec indiferent de cod.

Read-only, fără comenzi. Verdict APROBAT/RESPINS, finding-uri pe severitate cu fișier:linie, separat coder/tester, max 500 de cuvinte.
