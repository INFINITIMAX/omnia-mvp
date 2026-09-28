# R21 — Tester

Worktree: `D:\Omnia-MVP-r21-anexe`, branch `fix/r21-anexe-p118`. Citește `R21-coder.md` (rundele 1–4) și `R21-coder-raport.md`. Cod: `chunking_core.py`.

## Starea verificată de planner (textele reale)
- P 118/1: **3554** chunk-uri; 811/811 „Art.” proprii; **43/43** titluri de anexă din corp (după rândul 26220) produc chunk-uri cu prefixul lor; acoperire 0,996; niciun `27.3`, `48.6`, `7.8`, `29.1`, `2.940` ca articol din corp.
- Număr de chunk-uri nou: i5_2022 768, i7_2011 2214, i9_2022 **800**, np004_03 85, np010_2022 356, np057_02 **290**, p118_1_2025 **3554**, spitale_2022 616. Acoperire: i5 0,979; i7 0,971; i9 0,969; np004 0,923; np010 0,999; np057 0,882; p118 0,996; spitale 0,982; np091 0,989. 0 articole normalizate neconsecutive.
- `python -m pytest -q`: 1196 passed (testele pe documente reale sunt sărite în worktree fără `documente_noi`; planner-ul le rulează cu link temporar).

## Sarcina
1. Actualizează `NUMAR_CHUNKURI_ASTEPTAT_PER_DOCUMENT` (`tests/test_populare_db.py`) la valorile de mai sus.
2. Test pe document real (același `skipif`): pentru P 118/1, toate titlurile `ANEXA N[.M] -` din corp (după primul articol „Art.”) produc cel puțin un chunk cu identificatorul lor sau un copil al lui; niciun chunk din corp cu identificator care nu e articol „Art.”, titlu de secțiune numerotat sau anexă (în special `27.3`, `48.6`, `7.8`).
3. Teste sintetice în `tests/test_chunking_core.py`:
   - document cu ≥50 marcaje „Art.”: numărul fără punct final (`48.6 Substrat`, `27.3 Mj/kg`) nu începe articol; document fără „Art.”: `3.1.5.7 Amplasarea` rămâne articol (regresia I7);
   - regiune de anexă: titlu `ANEXA 2.1 - TITLU` urmat de conținut → chunk `ANEXA 2.1`; marcaj intern `A.10. 2.7.7. Text` în `ANEXA 10` → identificator copil al anexei; conținutul anexei nu coincide cu un articol din corp cu același număr;
   - cuprins: bloc de titluri `ANEXA …` consecutive înainte de primul „Art.” → ignorat (nu produce chunk);
   - trimiteri: `ANEXA 2.1, au caracter…` și „…și” ↵ `ANEXA 5.3.` nu deschid regiune; titlu precedat de o legendă terminată cu literă mică („Figura 173 - Acces pe scara verticală”) **deschide** regiune;
   - un rând `Art. 2.4.9.4. (2).` în interiorul unei anexe nu închide regiunea;
   - `acoperire_text_brut` elimină marcajele `A.<nr>.`: un text cu `A.10. 2.2.9. Pentru…` și chunk-ul cu „Pentru…” → acoperire 1,0.

## Constrângeri
Scrii doar în `tests/`. Nu rula comenzi. Fără modificări de producție; bug suspectat → raportezi. Fiecare test trebuie să poată pica. Raport în `docs/handoff/R21-tester-raport.md`.
