# R27 — Raport reviewer (transcris integral de planner)

## Verdict: RESPINS (o singură problemă, minoră dar reală — ușor de reparat, nu necesită retrimitere completă la coder dacă planner-ul o poate corecta direct sau printr-un mini-task de o linie)

### Ce am verificat
- `chunking_core.py`: funcția `_este_referinta_rupta` (liniile 466-512), patternurile noi (359-369).
- `reimport_approved.py`: `DOCUMENTE_APROBATE`/`PRAGURI_ACOPERIRE` (liniile 38-66), comparate cu `D:\Omnia-MVP\documente_noi\p118_2_2013\metadata.json` și `p118_3_2015\metadata.json`.
- `tests/test_r27_definitii_terminologie.py` (nou, 8 teste), `tests/test_reimport_approved.py` (2 teste noi), `tests/test_populare_db.py` (sincronizare `PRAG_ACOPERIRE_MINIM_PER_DOCUMENT`).
- Comparație cu descrierea din `R27-coder-raport.md` și `R27-tester-raport.md`.

### 1. Comentariu de cod inconsecvent cu comportamentul real implementat (BUG DE DOCUMENTAȚIE, nu de logică)

**Fișier**: `D:\Omnia-MVP-r27\chunking_core.py`, liniile 361-366.

Comentariul de lângă definiția patternurilor spune:
```python
# ...fereastra
# de căutare acoperă și variantele cu cratimă lipită de termen, cu paranteze înainte de
# cratimă și cu cratima mutată pe rândul următor (2.16, 2.30, 2.61 etc.).
```

Dar implementarea reală (liniile 506-511) face exact opusul, cu comentariu propriu care o spune clar:
```python
# Cratima trebuie să fie pe același rând: în I7, „4.1.4.2.2.2. sau” e urmat pe rândul
# următor de „-” (enumerare), nu e o definiție.
if _PATTERN_LITERA_MICA_DUPA_NUMAR.match(rest) and _PATTERN_CRATIMA_DEFINITIE.search(
    urmator.split("\n", 1)[0][:_LUNGIME_FEREASTRA_CRATIMA_DEFINITIE]
):
```

`urmator.split("\n", 1)[0]` taie explicit la primul rând — cratima pe rândul următor **nu** mai e acoperită. Acesta e exact corectura pe care planner-ul a cerut-o după coder (testul I7 `test_i7_cratima_doar_pe_randul_urmator_nu_devine_articol` din tester confirmă comportamentul corect, funcțional).

**De ce contează**: codul funcționează corect (verificat: testele tester-ului validează exact comportamentul corect, iar planner-ul a rulat suita reală). Problema e că cine citește comentariul de la liniile 361-366 (viitor coder/reviewer, inclusiv la R28 când se rezolvă coliziunea Anexa 33 din P 118/2) va înțelege greșit regula și poate reintroduce regresia I7 crezând că "cratima pe rândul următor" e un caz acoperit intenționat.

**Ce ar trebui schimbat**: eliminați „și cu cratima mutată pe rândul următor (2.16, 2.30, 2.61 etc.)” din comentariul de la 365-366, sau înlocuiți-l cu ceva de genul „fereastra e limitată la rândul curent (`urmator.split("\n", 1)[0]`) — cratima pe rândul fizic următor NU e recunoscută ca definiție (vezi I7, `_este_referinta_rupta`)”.

Notă conexă: `R27-coder-raport.md` descrie codul **înainte** de corectura planner-ului (nu conține `urmator.split("\n", 1)[0]`, ci `urmator[:120]` fără restricție de rând). Raportul nu a fost actualizat după corectură — cod real e corect, dar raportul de predare e stale. Nu blochează, dar planner-ul ar trebui să știe că raportul coder-ului nu reflectă starea finală a fișierului dacă îl folosește ca referință ulterior.

### Restul — ACCEPT, fără rezerve

- **Nicio schimbare de scop**: coder a atins doar `chunking_core.py` și `reimport_approved.py`, exact cele două fișiere din brief. Tester a atins doar `tests/`. Constrângerile din `R27-coder.md` (nu atinge `consolidare_normative.py`, `retrieval_core.py`, `main.py`, `documente_noi/`, `tests/` etc.) respectate.
- **Risc "cod inutil transformă în articol ceva ce nu e definiție"**: verificat empiric — planner a scanat toate cele 9 documente pentru tiparul exact și a găsit 0 apariții false în afara P 118/3 (90) și P 118/2 (1, cazul 33.5 real). Fereastra de 120 caractere + restricția la același rând (I7) elimină cazul specific de risc numit în brief (trimiteri "conform 2.5. din ..." + cratimă pe rând separat). Nu am găsit alt scenariu realist neacoperit în corpusul actual.
- **`reimport_approved.py`**: `source_key`-urile (`P118_2_2013_consolidat.txt`, `P118_3_2015_consolidat.txt`) și `document_id`-urile (`p118_2_2013`, `p118_3_2015`) sunt identice cu `metadata.json` din `documente_noi/`. Pragurile (0.98/0.94) coerente cu valorile reale citate în brief (0.9858/0.9499). `tests/test_populare_db.py` sincronizat corect, cu comentariu explicit al motivului.
- **Teste**: cele 8 teste sintetice din `test_r27_definitii_terminologie.py` sunt distincte, fiecare acoperă o ramură de cod diferită (spații, cratimă lipită, paranteză, en dash, sub-nivel, fără-cratimă-rămâne-atașat, I7-regresie, majusculă-neschimbată), asertează pe conținut real (`c["articol"]`, text prezent/absent), nu doar `assertTrue`/`isDefined` — fiecare ar pica la o schimbare relevantă de comportament. Niciun test nu e "mereu verde". Cele 2 teste din `test_reimport_approved.py` verifică valori concrete + un dry-run end-to-end pozitiv. Nicio redundanță găsită.
- **Decizia tester-ului de a nu inventa `NUMAR_CHUNKURI_ASTEPTAT_PER_DOCUMENT` pentru P 118/2/3** (fără acces la rulare) e corectă — evită un test fals (fie mereu verde cu valoare greșită, fie fals-roșu la prima rulare reală).

### Recomandare
Nu retrimite tot ciclul la coder — e o corectură de comentariu de o linie, low-risk, planner-ul o poate face direct (nu implică logică sau teste noi) sau o poate da coder-ului ca task de o linie. După corectare, R27 poate fi acceptat integral.

---

## Decizia planner-ului (29-09-2026)
- Comentariul de la `chunking_core.py:361-366` corectat de planner (fereastra limitată la rândul curent, cu trimitere la regresia I7). Fără schimbare de logică; testele trec neschimbat.
- `R27-coder-raport.md` descrie codul dinainte de corectura planner (`urmator[:120]`); starea finală e cea din `R27-tester.md` și din acest raport.
- Cu corectura aplicată, R27 acceptat. Reimport doar P 118/3; P 118/2 rămâne pe varianta curentă până la R28 (coliziunea Anexa 33 / capitolul 33).
