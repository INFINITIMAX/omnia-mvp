# R24 — Reviewer

Worktree: `D:\Omnia-MVP-r24`, branch `feat/r24-limita-refuz`. Bază: `main` `45a82db` (copie de referință în `D:\Omnia-MVP`). Commit-uri: `917509d` coder, `464f44c` tester + fix planner (`grounding_eval.py`: `"gasit": True` în payload-ul `FixedGenerator`, plus aserțiunea corespunzătoare din `tests/test_grounding_eval.py`).

Citește: `R24-coder.md` (inclusiv Runda 2), `R24-coder-raport.md`, `R24-tester.md`, `R24-tester-raport.md`, `docs/DECISIONS.md` (D26).

Stare verificată de planner: `python -m pytest -q` → 1242 passed, 30 skipped. Evaluare reală cu codul R24: 0 erori de generare, 23/23 răspunsuri cu citate literale, NEG-04 → `not_found` fără citări.

## Ce verifici
1. **Coder** (`generation_core.py`, `main.py`, `DECISIONS.md`): cod în plus față de brief? `gasit=true` păstrează neschimbat D20/D22 (pasaj literal, ≥1 citare, reîncercare pentru referințe nesusținute)? `gasit=false` → mereu `not_found` + mesaj standard + fără citări, fără reîncercare; erori rămân doar pentru chei lipsă/în plus, `gasit` ne-boolean (atenție: `bool` e subclasă de `int` în Python — `0`/`1` trebuie respinse), JSON invalid? `/intreaba` mapează `not_found` din generare ca `not_found` de la căutare, cu cota consumată? Nu scapă textul modelului când `gasit=false`? Fișiere interzise neatinse?
2. **Tester** (`tests/`): aserțiuni D20/D22 slăbite? Teste noi redundante sau care trec indiferent de cod? Acoperă toate punctele 2.x din `R24-tester.md`?
3. **Fix planner** în `grounding_eval.py`: minim și corect?

## Verdict
APROBAT / RESPINS, cu listă de probleme (fișier:linie, gravitate, motiv). Nu modifici nimic.
