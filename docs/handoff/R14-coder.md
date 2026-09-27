# R14 — Coder: chunker unificat, titluri ca context, curățare antete MO

Worktree: `D:\Omnia-MVP-r14-chunker`, branch `feat/r14-chunker-unificat` (din `main` `fbf5177`).
Aprobat de Lucian 27-09-2026: titlurile devin context pentru articolele copil; „art. 4.4” întoarce copiii; chunkerele se unifică.

## Problema (dovezi din DB read-only, 27-09)
- ~450 de chunk-uri din documentele `approved` sunt doar titluri de secțiune („4.4. Dimensionarea conductelor de aer”, „3.3. Siguranța la foc”): NP 057 18,5%, I7 13%, NP 010 9,6%, I5 8,8%, NP 015 8,3%. În normativele RO, titlurile și articolele au aceeași numerotare; `PATTERN_ARTICOL` le tratează la fel, iar singurul filtru e `LUNGIME_MINIMA_CHUNK = 15`.
- Antetul de pagină MO și numerele de pagină intră în text: rândul `MONITORUL OFICIAL AL ROMÂNIEI, PARTEA I, Nr. 204 bis/10.III.2025`, cu 1–2 rânduri doar-cifre imediat alăturate (separate eventual de rânduri goale). Exemplu real: „…vizibile. 88 MONITORUL OFICIAL AL ROMÂNIEI, PARTEA I…”, „Etanșeitatea 39”.
- Titluri de capitol cu cifre romane, la început de rând („II. POMPELE DE DISTRIBUȚIE A CARBURANȚILOR”), se lipesc la finalul articolului anterior.
- Două chunkere copiate și divergente: `populare_db.creeaza_chunkuri` (fără limită de 1000, fără sufix) și `manual_ingestion_preflight._creeaza_chunkuri_locale` (cu limită `_MAX_CHUNK_CHARS = 1000` și tratare sufix).

## Sarcina
1. **Modul nou `chunking_core.py`**, cu o singură funcție publică `creeaza_chunkuri(text: str) -> list[dict[str, str]]` (chei `articol`, `text`), deterministă, fără I/O, DB sau rețea. Pornește de la `_creeaza_chunkuri_locale` (varianta mai strictă: tratare sufix, limită 1000, split secundar pe subpuncte) și adaugă, în ordine:
   a. **Curățare antete MO:** elimină rândurile care se potrivesc cu antetul MO (`^\s*MONITORUL OFICIAL AL ROMÂNIEI, PARTEA I, Nr\. .+$`, tolerant la spații) și rândurile doar-cifre (1–4 cifre) aflate la cel mult 3 rânduri de antet, cu doar rânduri goale sau doar-cifre între ele. **Nu** elimina rânduri doar-cifre fără antet în apropiere (sunt celule de tabel). Referințele din text („publicat în Monitorul Oficial al României, Partea I, nr. 34”) nu sunt antete și rămân.
   b. **Cuprins:** păstrează detectarea existentă (`linie ... 12`) și adaug-o pe cea cu numărul de pagină pe rândul următor (NP 010: „1.1. Obiect și domeniul de aplicare\n3\n1.2. …\n4”). Criteriu acceptat: în primele 20% din text, o succesiune de ≥5 intrări consecutive de tip „număr articol + titlu scurt + rând doar-cifre” e cuprins și se sare.
   c. **Titluri de capitol romane** (`^\s*[IVXLC]{1,6}\.\s+` urmat de text majoritar cu majuscule, pe un singur rând) sunt separatoare: închid articolul curent și nu intră în textul lui.
   d. **Titluri de secțiune:** un segment numerotat este titlu dacă textul lui e pe un singur rând, are ≤ 200 de caractere, nu se termină cu `.`, `;` sau `:`, **și** următorul segment numerotat este copil al lui (numărul lui începe cu numărul titlului + cifră, ex. `4.4.` → `4.4.1.`). Titlul nu devine chunk; textul lui (`"{numar} {titlu}"`, ex. `4.4. Dimensionarea conductelor de aer`) se pune ca **primul rând** în textul fiecărui copil direct. Un segment care arată a titlu, dar nu are copii, rămâne chunk normal (nu pierdem conținut).
   e. Deduplicarea „cea mai lungă variantă câștigă” rămâne, dar **numără și întoarce** variantele eliminate, ca să nu mai fie pierdere silențioasă: expune `ultimele_statistici()` sau un rezultat secundar echivalent (`duplicate_eliminate`, `titluri_contopite`, `antete_eliminate`); alege forma cea mai simplă.
2. **`populare_db.py` și `manual_ingestion_preflight.py`** folosesc `chunking_core.creeaza_chunkuri`; șterge implementările vechi și constantele/pattern-urile devenite nefolosite. Nu schimba altceva în fluxurile de import (gate-uri, statusuri, embeddings, DB).
3. **`retrieval_core.py`:**
   - `PostgresRetrievalRepository.find_exact`: dacă nu există niciun chunk cu `articol_normalizat` exact, întoarce copiii secțiunii: `articol_normalizat LIKE articol || '.%'` (parametrizat; escapează `%`/`_` nu e necesar, formatul e `[a-z0-9().-]+`), ordonați după `document_id, chunk_order, id`. Păstrează ambele variante (cu și fără `document_id`).
   - `ArticleParser._is_known_article`: un articol e cunoscut și dacă există un articol cunoscut care începe cu `articol + "."`.
   - Nu modifica `_has_ambiguous_article` și nici ruta semantică.

## Criterii de acceptare (planner-ul le verifică)
- Pe textele reale (`documente_noi/<id>/extracted.txt`) planner-ul rulează o comparație vechi/nou; pentru NP 057, I7, I5, NP 010, NP 015: zero chunk-uri care sunt doar titlu cu copii; zero apariții ale antetului MO în chunk-uri; NP 010 fără intrări de cuprins ca chunk-uri.
- Niciun conținut pierdut: orice text de articol din vechiul rezultat se regăsește (normalizat pentru spații) în noul rezultat, cu excepția antetelor MO, numerelor de pagină și titlurilor contopite.
- `python -m pytest -q` verde (planner-ul rulează).

## Constrângeri dure
- Nu rula comenzi (doar planner-ul rulează). Nu scrie teste noi (le scrie Tester-ul); actualizează doar testele existente care importă funcții șterse sau pe care le rupi direct, și raportează-le.
- Nu atinge: `main.py`, `generation_core.py`, `access_control.py`, `static/`, `supabase/`, `.env`, `documente_noi/`.
- Fără DB, Voyage, Anthropic, rețea. Fără comentarii inutile; în română ca restul codului.
- Nu adăuga abstracții peste ce cere sarcina.

## Predare
Scrie `docs/handoff/R14-coder-raport.md`: fișiere modificate, ce ai decis la fiecare punct 1a–1e (inclusiv euristici și praguri), testele existente atinse și de ce, riscuri deschise.
