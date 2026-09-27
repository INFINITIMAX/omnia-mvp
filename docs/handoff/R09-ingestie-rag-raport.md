# R09 — audit ingestie RAG (read-only)

**Verdict: sănătoasă, cu un gap real de corectitudine deja identificat și remediat pe branch neintegrat (R08), plus câteva gap-uri operaționale minore.**

## 1. Fluxul complet, de la PDF la chunk căutabil

1. **Extracție** (`procesare_documente.py`): PyMuPDF + corecție glife (fonturi CID fără `/ToUnicode`) + normalizare diacritice. Are un fix punctual, verificat pe hash SHA-256 exact, pentru simbolurile NP 091 corupte (`_repara_np091_verificat`) — protejat, nu se aplică orbește la alte PDF-uri.
2. **Chunking** (`populare_db.py:creeaza_chunkuri`, linia 122): regex pe structura de articole (`PATTERN_ARTICOL`), elimină cuprinsul, deduplichează pe cheie „articol" păstrând varianta mai lungă (linia 137 — **verificat intenționat**, test dedicat `test_creeaza_chunkuri_pastreaza_doar_varianta_mai_lunga_a_articolului`, nu e un bug), apoi split secundar pe subpuncte pentru articole peste 2000 caractere.
3. **Import legacy** (`populare_db.py:importa_document`): validare metadata, hash content, advisory locks, apeluri Voyage fără retry, `INSERT`/`UPDATE` pe sursă — documentat explicit în `AUTO_INGESTION_WORKER.md` ca **NU insert-only** și „nu trebuie prezentat drept substitut sigur" al fluxului manual nou. E calea prin care cele 11 documente `approved` curente au ajuns în producție, înainte ca fluxul manual controlat (D16/D18) să existe.
4. **Fluxul manual nou, controlat** (D16/D18, aprobat 11-09-2026):
   - `manual_ingestion_preflight.py` — validare locală, fără DB/Voyage, identifică metadata sau cere confirmare operator (`operator_confirmed`).
   - `manual_ingestion_import.py` — insert-only, `--commit` opțional pentru DB+Voyage reale, altfel dry-run. Fail-closed pe identitate duplicată (SHA/`document_id`/`source_key`/cod), lock-uri per tranzacție, `commit_unknown` gestionat explicit (fără retry automat).
   - `replace_pending_ingestion.py` — înlocuiește punctual chunk-urile unei surse `indexed_pending_validation`, nu atinge `approved`.
5. **Worker automat** (`auto_ingestion_worker.py`): cod complet, testat, dar **confirmat inactiv** — Task Scheduler neinstalat, migrarea `document_ingestion_sources` neaplicată. Documentat explicit ca „referință istorică", nu operațiune curentă (`AUTO_INGESTION_WORKER.md`, avertisment din 09-09-2026, încă valabil).
6. **Gate-ul `approved`**: separat de orice script — aprobare manuală explicită a lui Lucian, nu există cod care face automat trecerea `indexed_pending_validation` → `approved`.

**Stare confirmată azi (nu doar din TASKS.md):** D18 (`fix/manual-metadata-preflight`) e chiar merge-uit în `main` — `git log main` arată direct commit-urile lui (`fa82e31`, `762fe34`, etc.), deci HANDOFF.md-ul de azi dimineață care spunea "nu reconfirmat" poate fi actualizat la "confirmat merge-uit". `manual_ingestion_import.py` (D16) e de asemenea pe `main`, mock-first, 991 teste treceau la momentul acceptării — dar **nu există dovadă că a fost rulat vreodată cu `--commit` real** pe un document adevărat; gate-ul 3 din spec (aprobare explicită pentru o comandă `--commit` concretă) nu pare declanșat încă.

## 2. Acoperirea reală a testelor

Raport per fișier (linii cod / linii test — indicator de proporție, nu de calitate în sine):

| Fișier | Cod | Test |
|---|---|---|
| `populare_db.py` | 449 | 715 |
| `manual_ingestion_import.py` | 434 | 395 |
| `manual_ingestion_preflight.py` | 411 | 419 |
| `auto_ingestion_worker.py` | 629 | 488 |
| `procesare_documente.py` | 114 | 83 |
| `replace_pending_ingestion.py` | 94 | 77 |

Testele nu sunt mock-uri superficiale — verifică logică reală: dedup pe articol (linia 395 din `test_populare_db.py`), citare din act modificator (403, 483), refuzuri fail-closed pentru identitate duplicată, `commit_unknown` fără rollback/retry. Skip-urile găsite (`test_auto_ingestion_worker.py:302` etc.) sunt condiționate de platformă (`os.name != "nt"`), deci pe acest host Windows chiar rulează, nu sunt gap real.

## 3. GAP DE CORECTITUDINE identificat — retrieval-side, deja remediat dar NEINTEGRAT în main

**R08** (`fix/r08-split-article-retrieval`, commit `8023d1a`, branch deschis, nemerge-uit): `RetrievalService._has_ambiguous_article` din `retrieval_core.py` (nu `populare_db.py`) tratează în prezent **mai multe chunk-uri ordonate ale aceluiași articol lung (după split-ul secundar peste limita de caractere) ca ambiguitate reală** și refuză să răspundă (`ambiguous_article`), în loc să le folosească drept evidence secvențial. Fix-ul extinde contractul intern cu `chunk_order` ca să distingă split legitim de conflict real, cu teste de regresie pentru exact lookup și semantic retrieval.

**Impact pe producție azi:** orice articol suficient de lung încât să fi fost împărțit în subpuncte la ingestie (comun pentru norme tehnice detaliate) poate primi în prezent un refuz fals-pozitiv `ambiguous_article` din partea aplicației live, deși conținutul există corect și complet în DB. Acesta e exact genul de gap pe care principiul "no answer without proof" ar trebui să-l evite prin refuz corect, nu prin refuz în plus față de cazuri valide — o întrebare legitimă e blocată inutil.

**Nu pot verifica dacă acest scenariu s-a materializat deja real** (ar necesita interogare DB live pentru articole cu `chunk_order > 1` și testare live a `/intreaba` pe ele) — marchez explicit ca necesită verificare externă.

## 4. Alte observații

- Deduplicare pe reimport: `chunkurile_sunt_neschimbate` (linia 255) compară hash-uri înainte de a rescrie — evită costuri Voyage duplicate la re-rulare pe aceeași sursă neschimbată. Corect.
- Metadata (cod normativ, articol, an) e validată strict înainte de orice cost extern (`valideaza_metadata`, `valideaza_chunkuri`) — fail-closed, consistent cu restul contractelor D16-D22.
- `docs/MANUAL_INGESTION_IMPORT_WALKTHROUGH.md` și `PREFLIGHT_WALKTHROUGH.md` **nu au fost verificate linie-cu-linie față de codul curent** în acest audit (timp limitat) — dacă urmează să fie folosite curând pentru NP 015-2022 (următorul gate din TASKS.md), merită o trecere rapidă înainte de folosire, nu presupune că sunt sincronizate.
- Nu există migrare `document_ingestion_sources` aplicată — confirmat din documentație, nu verificat live pe Supabase.

## 5. Recomandare concretă

Înainte de a considera "ingestia RAG verificată" complet: **merge R08 în `main`** (fix de corectitudine reală, deja testat, izolat la `retrieval_core.py`, fără atingere DB/deploy) — e blocajul cel mai concret găsit în acest audit. Restul (worker inactiv, walkthrough-uri neverificate) sunt corecte ca stare curentă sau riscuri minore, nu blocaje.
