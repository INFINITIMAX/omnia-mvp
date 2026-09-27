# R14 — Tester: teste pentru chunker-ul unificat

Worktree: `D:\Omnia-MVP-r14-chunker`, branch `feat/r14-chunker-unificat`, commit coder `ea05e44`.
Citește întâi `docs/handoff/R14-coder.md` (sarcina și rundele 1–7) și `docs/handoff/R14-coder-raport.md` (deciziile coder-ului). Codul e în `chunking_core.py`, `retrieval_core.py` (`find_exact`, `ArticleParser._is_known_article`), `populare_db.py`, `manual_ingestion_preflight.py`.

## Starea verificată de planner
- `python -m pytest -q`: 1009 passed, 13 failed, 11 skipped. Cele 13 care pică verifică intenționat vechea formă SQL a rutei exacte: 12 × `tests/test_api_integration.py::test_api_p1_restrictia_cu_articol_cunoscut_pastreaza_ruta_exacta[*]` și `tests/test_retrieval_core.py::test_repository_exact_foloseste_numai_sql_parametrizat_cu_document_optional`.
- `tests/test_auto_ingestion_worker.py::test_doua_procese_nu_pot_rezerva_ambele_ultimul_slot` pică intermitent pe Windows și pe `main` — **nu e în scope, nu-l atinge**.
- Rezultat pe textele reale (`D:\Omnia-MVP\documente_noi\<id>\extracted.txt`), număr de chunk-uri nou: i5_2022 786, i7_2011 2229, i9_2022 769, np004_03 84, np010_2022 438, np057_02 300, p118_1_2025 3005, spitale_2022 634.
- Acoperire față de textul brut (procent de rânduri ≥50 caractere, fără antet MO, regăsite în chunk-uri după eliminarea marcajelor de articol și a „(N)”): i5 97,9%, i7 95,9%, i9 97,1%, np004 92,3%, np010 99,9%, np057 88,5%, p118 99,4%, spitale 98,3%.

## Sarcina
1. **Actualizează cele 13 teste SQL** la noul contract al rutei exacte: o singură interogare `(chunk.articol_normalizat = %s OR chunk.articol_normalizat LIKE %s)`, parametri cu `articol + ".%"`, cu și fără `document_id`. Păstrează ce verificau în esență (SQL parametrizat, filtrul `approved`, un singur apel, ruta exactă păstrată la restricție). Nu slăbi aserțiunile fără motiv.
2. **Teste noi pentru `find_exact`:** potrivire exactă existentă → numai rândurile exacte, chiar dacă există și copii; fără potrivire exactă → copiii în ordinea `document_id, chunk_order, id`; niciun rând → listă goală.
3. **Teste noi pentru `ArticleParser._is_known_article`** (prin API-ul public al parser-ului): un articol-secțiune fără chunk propriu, dar cu copii cunoscuți, e recunoscut; un prefix fără punct (`4.4` vs `4.41.`) **nu** e recunoscut greșit.
4. **Fișier nou `tests/test_chunking_core.py`**, cu texte sintetice mici care reproduc fiecare regulă (câte un test pozitiv și unul negativ unde are sens):
   - antet MO + numere de pagină alăturate eliminate; număr singur fără antet în apropiere (celulă de tabel) păstrat; referința „publicat în Monitorul Oficial al României, Partea I, nr. 34” păstrată;
   - colofonul MO de final eliminat;
   - cuprins cu puncte de conducere ca bloc (≥5 intrări) eliminat; un „150...500” izolat în corp **nu** taie nimic din text (regresia I7);
   - cuprins cu număr de pagină pe rândul următor eliminat; cuprins fără numere de pagină (titluri cu copii în corp) eliminat;
   - titlu de capitol roman nu intră în textul articolului anterior;
   - titlu de secțiune contopit ca prim rând în copii și absent ca chunk; titlu fără copii rămâne chunk;
   - introducere-titlu la split pe subpuncte nu devine chunk; fără prefix dublat;
   - marcaj `Art. N.N.N.` recunoscut; `Art. N.N.` urmat de literă mică sau punctuație = trimitere;
   - număr simplu urmat de literă mică = trimitere (regresia P 118/1 „2.3.2.1.2. lit. a)”, articolul real nu se pierde);
   - rând anterior terminat în `Art.`/`alin.`/`conform` → marcajul următor e trimitere (regresia P 118/1 3.2.11.20);
   - D18: `1.1.,` la final de rând = articol valid fără virgulă; `1.1.,text` nu e articol;
   - număr fără punct final (`3.1.5.7 Amplasarea`) = articol `3.1.5.7`; zecimal cu literă mică după (`0.4 kV`) nu e articol;
   - dată `15.01.2024` nu e articol;
   - limita de 1000 caractere pe chunk; `ultimele_statistici()` numără corect pe un exemplu mic.
5. **Înlocuiește testul cu numere fixe** `test_chunking_documentelor_deja_validate_ramane_neschimbat` (`tests/test_populare_db.py`, liniile ~449–476): actualizează numerele la valorile de mai sus **și** adaugă, cu același `skipif` pe `documente_noi`, un test de acoperire per document, cu pragurile: i5 ≥97%, i7 ≥95%, i9 ≥96%, np004 ≥90%, np010 ≥99%, np057 ≥87%, p118 ≥99%, spitale ≥97%. Metrica: rândurile brute de ≥50 caractere (după eliminarea marcajelor de articol `(Art. )?N.N.…` și `(N)` și a spațiilor multiple), fără rândurile cu „MONITORUL OFICIAL”, al căror prefix de 45 de caractere apare în textul concatenat al chunk-urilor (normalizat la fel). Adaugă și un test care cere pentru P 118/1 ca toate articolele `Art. N.N…` urmate de majusculă din text să apară ca `articol` propriu (811/811).

## Constrângeri dure
- Scrii doar în `tests/`. Nu modifici cod de producție; dacă un test arată un bug real, raportează-l, nu-l repara.
- Nu rula comenzi (planner-ul rulează și îți întoarce rezultatul).
- Testele nu trebuie să treacă indiferent de cod: fiecare trebuie să poată pica dacă regula respectivă e ruptă.
- Nu atinge `test_doua_procese_nu_pot_rezerva_ambele_ultimul_slot`.

## Predare
Scrie `docs/handoff/R14-tester-raport.md`: fișiere atinse, lista testelor noi, ce regulă apără fiecare, testele modificate și de ce, bug-uri suspectate.
