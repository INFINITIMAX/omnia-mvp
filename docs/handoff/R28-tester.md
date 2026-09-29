# R28 — Tester

Worktree `D:\Omnia-MVP-r28`, commit după `ce4ebee`. Citește `R28-coder.md`, `R28-coder-raport.md`.

## Starea verificată de planner (pe documentele reale)
- 9 documente (i5, i7, i9, np004, np010, np057, p118_1, spitale, p118_3): chunk-uri identice cu `main`.
- P 118/2: 34 de anexe recunoscute (`ANEXA 1`…`ANEXA 33`, `ANEXA 14bis`); definițiile Anexei 33 → `ANEXA 33.33.1.`…`ANEXA 33.33.7.`; capitolul 33 din corp rămâne `33.x.`; fragmentele `1.0.` au dispărut; `duplicate_eliminate` 23 → 16; acoperire 0.9902. Cuvinte „pierdute” = doar titlurile `ANEXA NR. N` (mutate în identificator) și subtitlul „TERMINOLOGIE”; +200 de cuvinte recuperate.

## Sarcina — teste sintetice în `tests/test_chunking_core.py` (sau fișier nou)
1. `PATTERN_TITLU_ANEXA` prinde `ANEXA NR. 1`, `ANEXA NR.2`, `ANEXA Nr. 3`, `ANEXA NR.14bis` (identificator `14bis`), cu identificatorul fără `NR`/`Nr`.
2. Nu prinde `anexa nr. 8, la clădirile…` (literă mică, trimitere din corp) și nici forme deja excluse de R21 (virgulă/literă mică după număr).
3. Un text sintetic cu capitol `33.` în corp și o anexă `ANEXA NR.33` cu `33.1.`…`33.3.` → articolele anexei devin `ANEXA 33.33.x.`, cele din corp rămân `33.x.`, niciun text al anexei pierdut (regresia reală din P 118/2).
4. Formele vechi (`ANEXA 3`, `ANEXA 3.1.`) se comportă exact ca înainte.

Scrii doar în `tests/`. Nu rula comenzi. Raport: `docs/handoff/R28-tester-raport.md`.
