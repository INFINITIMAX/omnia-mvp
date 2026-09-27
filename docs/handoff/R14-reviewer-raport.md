# R14 — raport Reviewer (transcris integral de planner, 27-09-2026)

## Verdict: APROBAT

Am citit integral `docs/handoff/R14-coder.md` (rundele 1–7), `R14-coder-raport.md`, `R14-tester.md`, `R14-tester-raport.md`, codul (`chunking_core.py` complet, `retrieval_core.py` — `find_exact`, `_is_known_article`/`_is_known_in`, integrarea din `populare_db.py`/`manual_ingestion_preflight.py`) și testele noi/modificate (`tests/test_chunking_core.py` integral, testele noi din `tests/test_retrieval_core.py`, diff-ul din `tests/test_populare_db.py`).

### Coder — verificat

- **Domeniul de aplicare respectat:** `populare_db.py` și `manual_ingestion_preflight.py` doar importă din `chunking_core` (`populare_db.py:20`, `manual_ingestion_preflight.py:19-20`), fără logică duplicată rămasă; constantele/pattern-urile vechi nefolosite au fost șterse conform raportului. Nu am găsit atingeri la `main.py`, `generation_core.py`, `access_control.py`, `static/`, `supabase/`, `.env`, `documente_noi/`.
- **`find_exact` (retrieval_core.py:326-356):** o singură interogare SQL parametrizată (`%s` pentru toate valorile variabile, inclusiv `LIKE`), filtrul `document.status = 'approved'` păstrat intact, ambele variante cu/fără `document_id`, ordonare `document_id, chunk_order, id` conform cerinței. Python filtrează corect potrivirile exacte înaintea copiilor. Fără concatenare de identificatori în SQL — sigur.
- **`_is_known_in` (retrieval_core.py:253-258):** verificarea `article in articles or any(known.startswith(article + "."))` evită exact bug-ul de „substring fără separator de punct” (`4.4.1` vs `4.4.11.2`) — corect implementat.
- **`chunking_core.py` (505 linii):** complexitatea e justificată de numărul mare de reguli cerute explicit prin cele 7 runde (antete MO, colofon, cuprins pe bloc, titluri romane, titluri-context, split secundar, marcaje „Art.”/fără punct, trimiteri rupte, dată ZZ.LL.AAAA, D18). Nu am găsit abstracții sau opțiuni în plus față de task — o singură funcție publică, semnătură exact cea cerută, statisticile expuse minimal (`ultimele_statistici()`), fără parametri suplimentari neceruți.
- **Regulile de filtrare (trimitere ruptă, referință Art., dedup) verificate prin citirea codului:** logica allow-list din `_este_referinta_rupta` (linia 316) și verificarea de linie anterioară (linia 301) sunt coerente cu rundele 3-5 din handoff; `_baza_articol` normalizează uniform indiferent de regex-ul sursă (bună decizie, evită duplicare de cod).
- Toate rundele de corectură (D18, pierdere conținut P118/1, prefix dublat, cuprins fără pagini) sunt reflectate corect în cod, coerent cu explicațiile din raport.

Nu am identificat cod nenecesar, bug-uri de logică nedovedite prin dovezile planner-ului (1071 passed, acoperiri crescute pe toate documentele), sau reguli care pierd conținut în tăcere dincolo de riscurile deja semnalate explicit de coder (regula titlu-cu-descendent-oriunde, runda 4) — risc onest raportat, nu ascuns, și fără evidență concretă că s-ar fi manifestat pe corpus.

### Tester — verificat

- Testele SQL actualizate (`test_repository_exact_foloseste_numai_sql_parametrizat_cu_document_optional`, `test_api_p1_...`) verifică substring SQL relevant + tuplul de parametri exact — ar pica real dacă interogarea ar reveni la forma veche sau ar pierde `LIKE`/`approved`.
- Testele noi pentru `find_exact` (potrivire exactă ignoră copiii, fallback pe copii cu ordinea dată de DB, listă goală) sunt distincte, fiecare cu un scenariu adversarial clar, nu redundante.
- `test_prefix_fara_punct_nu_e_confundat_cu_articol_cunoscut` e adversarial bine ales (`4.4.1` vs `4.4.11.2`) — prinde exact bug-ul de lipsă separator; testerul a documentat onest de ce nu a putut folosi exemplul literal din task (constrângere reală a regex-ului `_UNMARKED_ARTICLE`).
- `tests/test_chunking_core.py` (32 teste): am citit tot fișierul — fiecare test construiește text sintetic minim și verifică un rezultat concret (liste de articole, conținut de text, statistici), nu `assertTrue`/`toBeDefined` slabe. Testele pozitiv/negativ (antet vs. celulă de tabel, referință MO în text vs. antet real, interval numeric izolat vs. bloc de cuprins, virgulă D18 la final de rând vs. urmată de text) acoperă exact cazurile de regresie identificate în rundele coderului. Niciun test nu ar trece indiferent de cod — fiecare are o asserție de conținut/structură care ar pica dacă regula corespunzătoare s-ar rupe.
- Numerele fixe din `test_populare_db.py` (`NUMAR_CHUNKURI_ASTEPTAT_PER_DOCUMENT`) și pragurile de acoperire corespund exact cifrelor verificate de planner (786/2229/769/84/438/300/3005/634 și pragurile de acoperire) — nu inventate.
- `test_p118_toate_articolele_art_devin_chunk_propriu`: corectura ulterioară (comparație pe `articol.split("(")[0]`) e justificată corect — articolele lungi împărțite pe subpuncte au sufix legitim, nu bug.
- Nu am găsit teste redundante sau praguri de lungime nejustificate; riscul de fragilitate pe cele 4 teste cu praguri (documentat explicit de tester) e rezonabil și onest raportat, nu ascuns.

### Contracte

- D18 (virgula delimitatoare) respectat explicit în cod și acoperit de 2 teste dedicate.
- Nimic nu atinge generarea, pasajele D20 sau statusurile documentelor — verificat prin grep, singurele fișiere de producție atinse sunt `chunking_core.py` (nou), `retrieval_core.py`, `populare_db.py`, `manual_ingestion_preflight.py`.

Concluzie: munca ambilor agenți e solidă, bine documentată, testată cu scenarii adversariale reale, iar dovezile planner-ului (1071 passed, acoperiri crescute pe toate cele 8 documente) susțin corectitudinea. Nu am motive să resping.

---

## Decizia planner-ului

- R14 acceptat local; PR către `main` deschis pentru aprobarea lui Lucian (regula 8 din `AGENTS.md`).
- Merge-ul schimbă doar ruta exactă (fallback pe copiii secțiunii) și codul de ingestie; **nu modifică datele din producție**. Chunk-urile din DB rămân cele vechi până la reimport.
- Reimportul celor 9 documente cere aprobare separată (scriere DB + Voyage). Blocaj de design de rezolvat întâi: `populare_db.py` face DELETE/INSERT direct peste documente `approved` fără gate (finding F3 din R10). Propunere: reimport ca document nou `pending` sau prin `replace_pending_ingestion`, validare, apoi promovare.
- Rămân pentru R15: numere de articol repetate în anexe (dedup aruncă variante; I7 `duplicate_eliminate` 181), numerotarea „(A).2.” din NP 057, riscul regulii „titlu cu descendent oriunde” semnalat de coder.
