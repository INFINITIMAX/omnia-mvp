# R26-B — Runda 3 (planner, 29-09-2026)

Diagnostic planner (`D:\_scratch\omnia\r26\diag.py` — rulează fiecare operație separat): **P 118/2: 60/64 OK, P 118/3: 17/18 OK.** Cele 5 eșecuri, cu cauza verificată în texte:

1. **P 118/2 item 19** (`insereaza_dupa`, 6.40, după alineatul (1), nou (2)): în bază 6.40 e un singur paragraf **fără** etichete `(n)` — e implicit alineatul (1).
   → Regulă: dacă punctul nu are nicio etichetă `(n)` și `dupa_alineat == "1"`, noul alineat se inserează la finalul punctului. Dacă punctul are etichete, regula actuală (exact o potrivire). Raportează în intrare `"alineat_implicit": true`.
2. **P 118/3 item 16** (`5.3.5` alin. (2) lit. c)): în bază (rândurile ~1916–1930) există `(2) Aceste cabluri sunt cele care asigură:` urmat de `a)`, `b)`, `c)`, `d)` la început de rând. Căutarea eșuează → probabil întinderea alineatului (2) se termină la prima **literă** (`a)`), nu la următorul **alineat** `(n)`/finalul punctului.
   → Întinderea unui alineat = până la următorul `(n)` sau finalul punctului; literele sunt în interiorul lui. Verifică aceeași logică și la imbricarea din P 118/2 (item 46: 13.31 lit. a) și f); item 10: 4.47 lit. c)).
3. **P 118/2 item 48** (`abroga_punct` 23.51) și **item 49** (`renumeroteaza_inlocuieste` 24.32 → 24.31): sursa MO are numere duplicate:
   - `23.51. Generatoarele de aerosoli cu acționare prin fitil termic…` (rândul ~7434) și `23.51. Documentația trebuie să cuprindă…` (rândul ~7439). Ordinul mută conținutul primului în noul 23.50 alin. (2) (item 47: „(2) Generatoarele de aerosoli cu acționare prin fitil termic…”), deci **prima apariție** se abrogă.
   - `24.32 (1) Etanșările de vapori trebuie prevăzute…` + `(2) …` (rândul ~8107) și `24.32 Etanșările de vapori trebuie să fie conforme cu cerințele EN 13565-1` (rândul ~8111). Noul text din ordin („24.31. (1) Etanșările de vapori trebuie prevăzute… (2) …”) corespunde **primei apariții**.
   → Câmp opțional în țintă: `"aparitie": <n>` (1-based, printre potrivirile din afara cuprinsului) + `"justificare": "<text>"` obligatoriu când e prezent. Folosit **numai** când există >1 potrivire; dacă există exact 1 și `aparitie` e dat → eroare (nu ascundem schimbări de sursă). Raportul include apariția și justificarea. Setează `aparitie: 1` cu justificările de mai sus la itemii 48 și 49.
4. **P 118/2 item 24** (sintagma din tabelele 7.10–7.12): ordinul scrie „calcul **al** densității”, baza are „calcul **ale** densității” — nu coincid literal. Decizie planner: **nu interpretăm**. Pune înapoi `"manual": true` cu `"nota"` care explică discrepanța; planner-ul o raportează lui Lucian. Codul pentru `inlocuieste_sintagma_in_bloc` rămâne (e corect și testabil).

Nu schimba alte operații. Adaugă „Runda 3” în raport. Nu rula comenzi.
