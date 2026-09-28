# R18 — Tester

Worktree: `D:\Omnia-MVP-r18-evaluare`, branch `feat/r18-set-evaluare`, commit `73bf5b5`. Citește `R18-coder.md` și `R18-coder-raport.md`. Cod: `retrieval_eval.py`. Setul real: `evaluare/set_aur.json` (30 de cazuri, scris de planner — nu îl modifica).

## Starea verificată de planner
- `python retrieval_eval.py` (fără `--run`) → `set_valid`, exit 0.
- Rulare reală (`--run`): 30 de cazuri, 21 de embedding-uri, acuratețe 26/30, exact 6/6, semantic 18/21, negativ 2/3; raport JSON scris în `evaluare/rapoarte/`.
- `python -m pytest -q`: 1136 passed, 28 skipped.

## Sarcina — fișier nou `tests/test_retrieval_eval.py`, fără rețea și fără DB real
1. **Validarea setului:** set valid minim; respingere pentru: chei lipsă/în plus, `id` duplicat, tip necunoscut, peste 30 de cazuri, `asteptat` gol la non-negativ, `asteptat` nevid la negativ, articol invalid; fără `--run` nu se construiește nicio conexiune și niciun embedder (fake-uri care pică dacă sunt apelate). Include un test că `evaluare/set_aur.json` real trece validarea.
2. **Potrivirea:** articol exact → găsit cu rangul corect; copil (`2.3.2.1.2.(1)`, `4.2.4.3.(4)`, `2.3.2.1.2.1`) al articolului așteptat → găsit; prefix fără separator (`4.4.1` vs așteptat `4.4.11`) → **nu** găsit; alt document cu același articol → nu găsit.
3. **Negative:** `not_found`, `ambiguous_reference`, `out_of_scope` → corect; `found` → greșit.
4. **Poarta anti-calcul** aplicată înainte de căutare (fără embedding pentru „Calculează…”).
5. **Sumar:** acuratețe totală/pe tip/pe document, `recall@1`, `recall@5` calculate corect pe un set mic cu rezultate controlate; plafonul de 30 de embedding-uri; o eroare de provider oprește rularea cu cod stabil; ieșirea stdout e ASCII.
6. **Raportul** nu conține text normativ (dovezile au doar `document_id` și `articol_normalizat`).

## Constrângeri
Scrii doar în `tests/`. Nu rula comenzi. Fără modificări de producție; bug suspectat → raportezi. Fiecare test trebuie să poată pica. Raport în `docs/handoff/R18-tester-raport.md`.
