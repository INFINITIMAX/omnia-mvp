# R21 — Coder: anexele și identificatorii falși din P 118/1

Worktree: `D:\Omnia-MVP-r21-anexe`, branch `fix/r21-anexe-p118` (din `main` `9118a12`). Aprobat de Lucian 28-09-2026.

## Dovezi (planner, chunker-ul curent pe `documente_noi/p118_1_2025/extracted.txt`)
- **916 din 2862 chunk-uri (32%)** au `articol` care nu e un articol real „Art. N.N…”: `27.3.` ×140, `6.1.38.(317)` ×111, `6.1.38.` ×104, `3.2.11.` ×101, `7.8.` ×86, `1.25.` ×70, `3.9.1.` ×65, `48.6.` ×44, `29.1.` ×27, `8.7.` ×15, `2.940.` ×4.
- **Anexele ocupă 42% din P 118/1**: corpul lor începe la rândul 26220 (`ANEXA 1  - AMPLASARE CONSTRUCȚII`), până la finalul fișierului (45541). Cuprinsul anexelor e la rândurile ~408–600 (aceleași titluri + `A.10. 1.1. SCOP…`).
- Surse de identificatori falși (toate prin marcajul „număr fără punct final” din runda 6 R14, gândit pentru I7):
  - rândul 2742 `48.6 Substrat - material…` (definiție numerotată dintr-o listă);
  - rândul 29752 `7.8 Prevenirea descărcărilor electrostatice…` (numerotare internă de anexă);
  - rândul 33887 `27.3 Mj/kg, în orice fel de` (valoare + unitate, ruptă pe rând nou).
- Anexele interne folosesc și marcajul `A.10. 2.7.7. Pentru intervenția…` (anexa 10, articolul 2.7.7), rândul 37875.
- Alte documente au anexe cu formate diferite: I9 (`ANEXA 1  ` la 5162, `ANEXA 1.1  `, `ANEXA 5.3. `; dar rândul 1513 `ANEXA 2.1, au caracter de recomandare…` e **trimitere în text**, nu titlu), NP 057 (`ANEXA 1. `, `ANEXA 3.1. `, `ANEXA 3.4.(A).`). Pattern-ul curent `PATTERN_ARTICOL` acceptă deja `ANEXA\s+\d+\.\d+\.` ca marcaj (`chunking_core.py:21`). Parser-ul normalizează „anexa 2.1” din întrebări prin `_ANNEX_REFERENCE` (`retrieval_core.py:36`).

## Sarcina (în `chunking_core.py`)
1. **În documentele care folosesc marcaje „Art. N.N…” pentru articole** (prag: ≥ 50 de marcaje „Art.” recunoscute), marcajul „număr fără punct final” (`PATTERN_ARTICOL_FARA_PUNCT`) nu mai produce începuturi de articol. În celelalte documente (ex. I7) rămâne ca acum.
2. **Regiuni de anexă.** Un titlu de anexă e un rând care începe cu `ANEXA N` (N = număr cu opțional `.M`, sufix literă sau `(X)`), urmat de sfârșit de rând, `-`, `–`, `.` sau un titlu cu majuscule; **nu** e titlu dacă după număr urmează virgulă sau text cu literă mică (trimitere). Titlurile din cuprinsul detectat (runda 1b/7 R14) nu contează. Din primul titlu de anexă din corp până la următorul titlu de anexă, conținutul aparține acelei anexe:
   - textul dintre titlu și primul marcaj intern devine un chunk cu `articol` = `ANEXA N` (normalizare → `anexan`, compatibil cu `_ANNEX_REFERENCE`);
   - marcajele interne (`A.10. 2.7.7.`, numere simple) produc articole cu prefixul anexei: `ANEXA 10.2.7.7` sau echivalent care se normalizează la `anexa10.2.7.7` — astfel sunt copii ai anexei (regula copiilor din `find_exact` și `_is_known_article`) și nu mai pot coincide cu articolele din corp;
   - titlul anexei devine context (prim rând) al chunk-urilor ei, ca titlurile de secțiune din R14.
3. Nu atinge restul regulilor (antete MO, cuprins, trimiteri rupte, D18, dedup normalizat, subpuncte). Nu atinge `retrieval_core.py`, `main.py`, `generation_core.py`, `supabase/`, `.env`, `documente_noi/`, `evaluare/`.

## Criterii de acceptare (planner-ul verifică pe textele reale)
- P 118/1: niciun `articol` din corp de forma `27.3`, `48.6`, `7.8`, `29.1`, `2.940`; conținutul anexelor are identificatori `anexa…`; 811/811 articole „Art.” rămân articole proprii.
- Toate cele 9 documente: acoperirea față de textul brut nu scade sub valorile curente; 0 articole normalizate neconsecutive; testele existente trec (numerele fixe de chunk-uri le actualizează Tester-ul).
- Evaluarea pe setul de aur rămâne ≥ 27/30 după reimport (o rulează planner-ul).

## Constrângeri dure
Nu rula comenzi. Nu scrie teste noi. Fără comentarii inutile. Raport: `docs/handoff/R21-coder-raport.md` (reguli, praguri, cazuri limită observate în I9 și NP 057).
