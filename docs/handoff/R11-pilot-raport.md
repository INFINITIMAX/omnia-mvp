# R11 — revenire la pasajul verificat (D20) + pilot R05 nou (25–27-09-2026)

## Decizie
Lucian a ales (25-09-2026) revenirea la contractul aprobat D20/D22/R06, după ce auditul R10 (F1) a arătat că pe 15-09 contractul fusese relaxat fără decizie scrisă. Revert: `1091bb8`, `6888902`, `0bfab8d`. Păstrat: `9f7c5bf` (limita 600 în schemă).

## Schimbări pe branch
- 3 revert-uri: `pasaje` obligatoriu în schemă; lipsă/gol/peste 600 caractere → refuz (503); pasaj valid dar neliteral → excerpt literal din aceeași dovadă (excepția D20).
- `c3646e7`: prompt + descrierea câmpului `citat` cer o singură frază, ideal sub 300 caractere, niciodată articolul întreg. Validarea D20 neschimbată.
- Host: 1016 passed, 11 skipped (skip = `documente_noi/` local absent din worktree).

## Pilot
Manifestul din 15-09 nu mai exista pe disc; manifest nou de 20 cazuri aprobat de Lucian (local, `D:\_scratch\omnia\`, în afara Git). Întrebările exacte alese din documente fără/cu puține articole împărțite, ca să nu măsoare bug-ul R08.

| Rulare | Rezultat |
|---|---|
| 1 (înainte de `c3646e7`) | oprit la E06: `generation_passage_value` (pasaj gol/peste 600) — contractul strict pica pe articole lungi |
| 2 (după `c3646e7`) | E01–E08, S01–S08, N01 trecute fără eroare de pasaj; oprit la N02 pe `r05_cost_limit` (greșeală de manifest: negativ care cerea al 9-lea embedding) |
| 3 | oprit la S07: `execution_error` — credit Anthropic epuizat (confirmat de Lucian) |
| subset 27-09 (S07, N02, N03, N04) | toate rulate fără eroare |

**Concluzie:** după `c3646e7`, toate generările (19) au trecut validarea strictă D20. Raport complet agregat nu există (runner-ul scrie doar la 20/20); dovezile sunt rulările de mai sus.

## Finding-uri noi din pilot
1. **N04 — formulă inventată (serios).** În NP 091-2003 art. 4.1.5 formula e imagine; textul extras are „se va calcula cu formula: [gol]". Modelul a scris `C = Q × D / 1000`, care nu există în dovadă — încalcă regula 2 din prompt. În plus, `scope_core` nu a blocat „Calculează".
2. **N03 — referință ambiguă ajunge la generare.** „art. 4.4 din normativ" a primit răspuns (I 13-2015) în loc de refuz ambiguu.
3. **P 118/2-2013 (modificat 2018) este document doar de modificare** — titlu în DB: „modificări și completări (Ordinul nr. 966/2018)". Încalcă regula de conținut; e `approved` și servit public.
4. Date (din citiri read-only 25-09): 292 articole împărțite în documentele `approved` (P 118/1-2025: 197) → R08 afectează producția; NP 091-2003 art. 4.4.6 are chunk-uri fără legătură (bibliografie lipită de ultimul articol); I7-2011 are glife corupte în DB.

## Planner — decizie
R11 e gata de review și merge, cu aprobarea lui Lucian. Finding-urile 1–3 sunt task-uri separate. Credit Anthropic epuizat în timpul pilotului ⇒ și producția a dat 503 în acel interval; propus: alertă de credit.
