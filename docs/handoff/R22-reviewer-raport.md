# R22 — raport Reviewer (transcris integral de planner, 28-09-2026)

VERDICT: APROBAT

## Coder (diacritice.py, procesare_documente.py, chunking_core.py)

Verificat direct în `documente_noi/i7_2011/extracted.txt`: toate cele 5 mapări (Ġ→ț, ú→ș, ğ→Ț, U+070A→ț, U+0708→ș) apar cu forme reale (`protecĠia`, `úi`, `INSTALAğIILOR`, `construc܊ii`, `܈i` — 3326 ocurențe combinate confirmate prin grep). `\x98` corect exclus (nu e diacritică).

Integrare simetrică confirmată prin citire directă:
- `procesare_documente.py:75` — `normalizeaza_diacritice(corecteaza_substituiri_pdf(text))`, aplicat pe tot textul extras.
- `chunking_core.py:128` — `corecteaza_substituiri_pdf(text)` la începutul `creeaza_chunkuri`.
- `chunking_core.py:760` — aceeași funcție aplicată în `acoperire_text_brut` pe textul brut, exact simetria cerută pentru poarta D24.

Nicio abatere de la scope: grep pe `corecteaza_substituiri_pdf` arată doar `diacritice.py`, `procesare_documente.py`, `chunking_core.py` + teste — `retrieval_core.py`, `main.py`, `generation_core.py`, `supabase/`, `.env`, `documente_noi/` neatinse, cum cerea constrângerea.

Cod: fără funcții/opțiuni în plus — o singură funcție nouă + o tabelă, exact ce cerea task-ul. Docstring-ul documentează dovada fiecărei mapări (linie cu exemplu), inclusiv verificarea explicită că nu există formă majusculă coruptă separată pentru Ș (punctul 2 din task, tratat corect ca "nicio dovadă → nicio mapare").

**Notă (nu blocantă):** riscul semnalat în brief privind `ú` ca literă legitimă (nume/citate străine) rămâne acceptat ca atare de planner — funcția se aplică global, nu doar la I7. Pentru un normativ tehnic românesc riscul e mic, dar dacă un document viitor citează nume proprii cu `ú`, ar fi corupt silențios. Nu recomand blocare pe asta (task-ul a cerut aplicare globală explicit), doar semnalez pentru vigilență la R23+ dacă apare un document cu citate străine.

## Tester

Testele sunt concrete, fiecare cu condiție de eșec verificabilă (nu `toBeDefined`-echivalent):
- `test_creeaza_chunkuri_corecteaza_substituirile_pdf_din_text` și `test_acoperire_text_brut_pe_text_corupt_ramane_simetrica` (confirmate prin citire directă) — folosesc text sintetic cu caractere corupte reale din I7, verifică absența lor în chunk-uri și acoperire exact 1.0. Ar pica dacă integrarea ar lipsi.
- Testul de non-regresie pe `\x98` și cel de neatingere a sedilei previn suprapunerea greșită a celor două funcții de normalizare.
- Testul pe document real (`skipif` pe `documente_noi`) acoperă cazul cerut explicit de planner.
- Actualizarea `NUMAR_CHUNKURI_ASTEPTAT_PER_DOCUMENT["i7_2011"]` la 2215 corectă (confirmată de dovezile planner).

Nu am găsit teste redundante sau teste care ar trece indiferent de cod. Limitarea asumată de tester (nu se poate testa ordinea relativă a celor două funcții, seturile de caractere fiind disjuncte) e corect explicată și acceptabilă.

## Concluzie
Ambele livrări corespund task-ului, fără cod sau teste inutile. APROBAT.

---

## Decizia planner-ului
- R22 acceptat. Riscul `ú` notat: la importul unui normativ nou, raportul de dry-run arată câte substituiri s-au aplicat; dacă un document are `ú` legitim, corectura se restrânge atunci printr-o decizie separată.
- PR către `main`, după merge-ul R21 (PR #23). Merge și reimport P 118/1 + I7 cu aprobarea lui Lucian.
