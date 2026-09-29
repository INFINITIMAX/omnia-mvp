# R27 — Coder: definițiile cu literă mică devin articole proprii

Worktree `D:\Omnia-MVP-r27`, branch `fix/r27-definitii` (din `main` `916f40f`). Aprobat de Lucian 29-09-2026.

## Dovezi (planner)
- Evaluarea pe 36 de întrebări: P1183-03 („Ce este semnalul de confirmare alarmă…”, așteptat P 118/3 art. 2.56) — căutarea găsește textul corect, dar în chunk-ul etichetat **`1.7.`**. Cauza: `_PATTERN_CARACTER_VALID_DUPA_NUMAR` (`chunking_core.py`) cere majusculă/„/(/cifră după numărul articolului, iar definițiile încep cu literă mică: `2.56. semnal de confirmare alarmă - semnal de la…`. Toate definițiile 2.1–2.64 din P 118/3 („CAPITOLUL 2 - TERMINOLOGIE SPECIFICĂ”) sunt lipite de 1.7 → citarea ar arăta „Art. 1.7”.
- Același tipar în P 118/2, Anexa 33 „TERMINOLOGIE”: `33.1.`–`33.4.` (majusculă) sunt articole, dar `33.5. instalație cu preacționare – una sau mai multe…` e lipit de 33.4.
- Scanare planner pe toate `documente_noi/*/extracted.txt` după tiparul `^N.N[.N…]. <literă mică>… [-–]`: **0** apariții în i5, i7, i9, np004, np010, np057, p118_1, spitale; 90 în P 118/3; 1 în P 118/2 (33.5 de mai sus).
- Variante reale în P 118/3: cratimă lipită (`2.8. cale de transmisie -conexiune fizică…`, `2.47. program -software…`), paranteze înainte de cratimă (`2.50. punere în funcțiune(PIF) -proces…`), cratimă doar pe rândul următor (`2.16. declanșator manual de alarmare (buton de semnalizare manuală) (fig. 3.1 -`), en dash (`– `), sub-niveluri (`2.19.1.`, `2.19.18.1.`).

## Sarcina
1. `chunking_core.py`: un rând care începe cu număr de articol **cu punct final** urmat de literă mică devine început de articol **doar** dacă e o definiție: cratimă/en dash (`-`/`–`, cu sau fără spații) în primele ~120 de caractere ale rândului **sau** rândul se află într-o secțiune de terminologie (titlu anterior care conține „TERMINOLOGIE” sau „DEFINIȚII”, indiferent de majuscule, până la următorul titlu de capitol/anexă). Alege cea mai simplă variantă care acoperă toate exemplele de mai sus și nu atinge celelalte documente; explică alegerea în raport.
2. `reimport_approved.py`: adaugă `p118_2_2013` (`P118_2_2013_consolidat.txt`) și `p118_3_2015` (`P118_3_2015_consolidat.txt`) în `DOCUMENTE_APROBATE`, cu `PRAGURI_ACOPERIRE` 0.98 și 0.94 (acoperirea actuală: 0.9858 / 0.9499; liniile lipsă sunt sumarul MO și preambulul ordinului). Verifică dacă alte liste/teste paralele (ex. `tests/test_populare_db.py` `PRAG_ACOPERIRE_MINIM_PER_DOCUMENT`) trebuie sincronizate și raportează — nu le modifica dacă sunt teste (tester-ul).

## Criterii de acceptare (verificate de planner)
- P 118/3: articole proprii `2.1`…`2.64` (inclusiv `2.19.x`), `2.56` conține „semnal de confirmare alarmă”; `1.7` nu mai conține definițiile.
- P 118/2: `33.5` (Anexa 33) articol propriu; altfel neschimbat.
- Celelalte 8 documente cu `extracted.txt`: chunk-uri **identice** cu `main`.
- Contractul importerului (≤1000, articol valid) trece.

## Constrângeri
Nu atinge `consolidare_normative.py`, `extragere_mo_bis.py`, `retrieval_core.py`, `generation_core.py`, `main.py`, `static/`, `supabase/`, `.env`, `documente_noi/`, `tests/`. Nu rula comenzi. Raport: `docs/handoff/R27-coder-raport.md`.
