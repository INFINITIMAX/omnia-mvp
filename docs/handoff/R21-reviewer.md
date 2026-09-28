# R21 — Reviewer

Worktree: `D:\Omnia-MVP-r21-anexe`, branch `fix/r21-anexe-p118`; `main` în `D:\Omnia-MVP`. Citește `R21-coder.md` (rundele 1–5), `R21-coder-raport.md`, `R21-tester.md`, `R21-tester-raport.md`, `docs/DECISIONS.md` (D18, D24, D25).

Dovezi planner (textele reale, local): `python -m pytest -q` cu `documente_noi` → **1234 passed**. P 118/1: 43/43 titluri de anexă din corp cu chunk propriu, 811/811 „Art.” proprii, acoperire 0,996 (metrica corectată pentru marcajele `A.<nr>.`), niciun `27.3`/`48.6`/`29.1`/`2.940` în corp. Celelalte 8 documente: acoperire neschimbată, 0 articole neconsecutive. Tester-ul a găsit două bug-uri reale preexistente (potrivire pe sufix: „stabilit.” ≈ „lit.”, „verticala” ≈ „la”), reparate în runda 5. Rămân 3 titluri de anexă-părinte („ANEXA 3 -”, „ANEXA 4 -”, „ANEXA 5 -”) lipite la finalul ultimului chunk al anexei precedente (acceptat ca minor).

## Ce verifici
1. **Pierdere sau atribuire greșită de conținut:** regulile noi (prag 50 „Art.”, regiuni de anexă, cuprins înainte de primul „Art.”, continuare pe cuvânt întreg) pot atribui conținut greșit în alte documente sau în normative viitoare cu format diferit? Cazuri limită plauzibile.
2. **Metrica `acoperire_text_brut`:** eliminarea `A.<nr>.` poate umfla artificial acoperirea (ascunde pierderi reale)?
3. **Compatibilitate cu căutarea:** identificatorii `ANEXA N…` se normalizează la `anexan…` și funcționează cu `_ANNEX_REFERENCE`, `find_exact` (copii) și `_is_known_article` fără coliziuni cu articolele din corp.
4. **Cod inutil** (ex. resturi din rundele anterioare, plasa din runda 2 scoasă complet?).
5. **Tester:** teste care trec indiferent de cod, redundanțe, testul pe documentul real verifică sursa, nu doar numărul.

Read-only, fără comenzi. Verdict APROBAT/RESPINS, finding-uri pe severitate cu fișier:linie, separat coder/tester, max 600 de cuvinte.
