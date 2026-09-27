# R15 — Raport Coder

## Runda 2 — fix `chunking_core.py`: cuvânt lipit de marcajul de articol (27-09-2026)

**Bug:** în `_extrage_segmente`, când marcajul numeric era urmat direct (fără spațiu) de un cuvânt care începe cu majusculă — caz real în I7 (`3.0.1.CondiĠii`, `4.1.5.3.1.Legătura`, `5.5.1.GeneralităĠi`, `7.23.10.1.InstalaĠiile`) și NP 057 (`3.1.2.3.3.Mentenanța`, `3.1.4.1.5.Acoperișurile,`) — codul vechi lipea întregul cuvânt de `articol` (`sufix = re.match(r"[^\s]+", ...)` capturează orice șir nevid până la următorul spațiu, nu doar un caracter de punctuație). Rezultatul (`3.0.1.CondiĠii`) nu trece `_normalizeaza_articol` → `invalid_chunks` în dry-run.

**Fix (`chunking_core.py`):** adăugat `_PATTERN_MAJUSCULA_LIPITA = re.compile(r"[A-ZĂÂÎȘȚŞŢ]")` lângă `_PATTERN_CARACTER_VALID_DUPA_NUMAR`. În `_extrage_segmente`, înainte de a construi `sufix`/`candidat`, verific primul caracter imediat după marcaj (`sursa[potrivire.end(1):potrivire.end(1)+1]`): dacă e o majusculă (inclusiv diacritice), `articol` rămâne `articol_baza` (numărul curat), fără nicio lipire — cuvântul intră natural în `text_segment`, fiindcă `inceput_text = potrivire.end()` nu s-a schimbat. Dacă primul caracter lipit NU e majusculă (ex. virgula din cazul D18 `"1.1.,"`), ramura veche (gluing + stripping virgulă) rămâne exact neschimbată — verificat pe cod: cazul `"1.1.,"` are primul caracter `","`, nu majusculă, deci intră tot pe calea veche.

Am verificat prin citire (nu am rulat comenzi):
- `1.1./` și `1.1.,text` sunt filtrate mai devreme, la nivel de `_este_referinta_rupta` (nu ajung deloc în acest bloc), deci fix-ul nu le atinge — testele D18 (`test_d18_virgula_la_final_de_rand_e_articol_valid_fara_virgula`, `test_d18_virgula_urmata_de_text_pe_acelasi_rand_nu_e_articol`) rămân neschimbate logic.
- Pe exemplele reale date de planner (`D:\Omnia-MVP\documente_noi\i7_2011\extracted.txt` — „3.0.1.Condi”, și `np057_02\extracted.txt` — „3.1.2.3.3.Mentenan”): primul caracter după marcaj e literă majusculă (`C`, respectiv `M`) în ambele, deci intră pe ramura nouă — `articol` rămâne numărul curat, cuvântul devine începutul textului articolului.
- Nu am găsit alt loc din `_extrage_segmente`/`_este_referinta_rupta` care ar produce un `articol` cu literă glued fără să treacă prin acest bloc — singurul punct de gluire e cel modificat.

**Nu am atins `tests/`** (constrângere explicită Runda 2). Nu am rulat `pytest` — planner-ul trebuie să confirme cu `pytest tests/test_chunking_core.py tests/test_populare_db.py` (în special testele D18, cele de `articol` glued/(N), și dry-run real pe I7/NP057 dacă `documente_noi` e prezent) că nu apare nicio regresie și că `i7_2011`/`np057_02` nu mai produc `invalid_chunks`.

## Fișiere create/modificate

- **`reimport_approved.py`** (nou): CLI `--document <id> [--pdf <cale>]` cu exact un mod: implicit dry-run, `--commit`, `--restore <backup>`. Conține toată logica cerută (vezi „Fluxul fiecărui mod” mai jos).
- **`chunking_core.py`**: adăugat `acoperire_text_brut(text, chunkuri) -> float` (public) + `_normalizeaza_pentru_acoperire` și constantele `_PATTERN_MARCAJ_ARTICOL_ACOPERIRE`, `_PATTERN_SUBPUNCT_PARANTEZA_ACOPERIRE`, `LUNGIME_MINIMA_LINIE_ACOPERIRE`. Logica e mutată **identic** (praguri/semantică neschimbate) din testul existent.
- **`tests/test_populare_db.py`**: `_acoperire_continut_brut` acum deleagă la `chunking_core.acoperire_text_brut`; am șters `_PATTERN_MARCAJ_ARTICOL`, `_PATTERN_SUBPUNCT_PARANTEZA`, `_normalizeaza_pentru_acoperire` (mutate) și importul nefolosit `re`. Restul testului neatins — asta e singura adaptare permisă explicit de task (pct. 4/22 din handoff).
- **`docs/DECISIONS.md`**: adăugat D24 deasupra D23, text exact din handoff.

## Fluxul fiecărui mod

- **Dry-run (implicit)**: `_evalueaza()` — citește textul (fișier local sau PDF+`extrage_text`), construiește chunk-uri noi cu `chunking_core.creeaza_chunkuri` + le validează cu `manual_ingestion_import._valideaza_chunkuri` (contract identic importerului), deschide o conexiune **readonly** (`psycopg2` + `connection.set_session(readonly=True, autocommit=False)`, urmând exact patternul din `real_grounding_eval.run_isolated_evaluation`), verifică `document_id`/`status='approved'`/`source_key` și numără chunk-urile curente, evaluează poarta D24, scrie raportul JSON atomic (`os.replace`) în `documente_noi/_reports/<document_id>.reimport.json`. Fără Voyage, fără scriere DB (rollback+close pe conexiunea readonly).
- **`--commit`**: rulează exact `_evalueaza()` (readonly). Dacă poarta pică → întoarce raportul cu `status: "poarta_respinsa"`, fără Voyage, fără scriere. Dacă trece: backup readonly (`SELECT ... embedding::text ... ORDER BY chunk_order`) scris atomic în `backups/reimport-<document_id>-<timestamp_UTC>.json`, apoi `manual_ingestion_import._cere_embeddings`, apoi o singură tranzacție scriere: `SET LOCAL statement_timeout`, lock advisory (`base._LOCK_SQL` pe `document_id`), `SELECT ... FOR UPDATE`, reverifică `status`/`source_key`/număr de chunk-uri identic cu cel citit la dry-run (altfel `concurrent_change`), `DELETE` + `INSERT` cu `chunk_order` 1..n și `content_hash`/`articol_normalizat` calculate cu helper-ele importerului, `commit()`. Statusul documentului nu se schimbă (nu ating `documente.status`). Eroare la `connection.commit()` → `commit_unknown`, fără rollback, fără retry (identic D17).
- **`--restore <backup>`**: validează calea (`_cale_directa` pe `backups/`), conținutul JSON (document_id/source_key/chunk-uri coerente), apoi o singură tranzacție (același lock + `FOR UPDATE`, reverifică `approved`+`source_key`) `DELETE` + `INSERT ... embedding = %s::vector`. Fără Voyage, fără poartă de acoperire.

## Token-uri de eroare (toate subclase `ReimportError(ValueError)`, fără text normativ)

`unknown_document`, `not_approved`, `source_key_mismatch`, `missing_pdf_argument`, `invalid_pdf_path`, `invalid_extraction`, `unstable_pdf`, `missing_text_source`, `empty_text_source`, `invalid_chunks`, `outside_inbox`, `outside_backups`, `invalid_backup`, `backup_document_mismatch`, `restore_identity_mismatch`, `concurrent_change`, `commit_unknown`, `database_error`, `report_write_failed`, plus token-urile propagate ca atare de la `manual_ingestion_import` (ex. `voyage_error`, `configuration_error`) — vezi decizia de mapare mai jos.

## Ce am reutilizat (import, fără copiere)

Din `manual_ingestion_import.py` (ca `base`): `_conexiune_implicita`, `_client_voyage_implicit`, `_cere_embeddings`, `_hash_chunk`, `_normalizeaza_articol`, `_valideaza_chunkuri`, `_inchide_sigur`, `_cale_directa`, `_hash_sha256`, `_required_environment`, `_LOCK_SQL`, `_INSERT_CHUNK_SQL`, `_TIMEOUT_STATEMENT_MS`, `_TIMEOUT_CONECTARE_SECUNDE`, `FOLDER_INBOX`, `ImportError` (clasa lor, tratată explicit, vezi mai jos). Toate sunt private (`_nume`) în modulul sursă — le-am importat, nu le-am copiat, conform excepției din constrângeri.

Nu am reutilizat nimic direct din `replace_pending_ingestion.py` (target diferit — pending, nu approved) sau `backup_baza_de_date.py` (backup-ul de reimport e per-document, nu per-tabel; am scris propriul writer JSON atomic, mai simplu decât cel din `manual_ingestion_preflight._scrie_raport_atomic`, fără lock-file separat, fiindcă fiecare document are un singur fișier de raport/backup pe rulare, un singur Coder/operator activ conform `AGENTS.md`).

## Decizie netrivială: mapare `manual_ingestion_import.ImportError`

Modulul `manual_ingestion_import.py` definește o clasă proprie numită `ImportError`, care **umbrește** built-in-ul `ImportError` în acel fișier — un pattern deja existent în proiect, dar confuz dacă îl reproduci. Nu am redenumit nimic din `manual_ingestion_import.py` (constrângere: nu-i modific comportamentul). În `reimport_approved.py` am ales să NU umbresc built-in-ul: excepția mea se numește `ReimportError`, iar oriunde apelez direct helper-e din `base` care pot ridica `base.ImportError` (conexiuni, `_cere_embeddings`), prind explicit `(ReimportError, base.ImportError)` și re-ridic `ReimportError(str(error))`, păstrând token-ul original (ex. `voyage_error`, `configuration_error`) fără să-l „tocesc" la `database_error`. Raportez asta explicit — e o decizie de stil, nu de comportament.

## Ce NU am făcut

- Nu am rulat nimic (nici pytest, nici scriptul) — conform regulii de rol.
- Nu am scris teste noi.
- Nu am atins `main.py`, `generation_core.py`, `retrieval_core.py`, `access_control.py`, `static/`, `supabase/migrations/`, `.env`, `populare_db.py`, `manual_ingestion_import.py`, `replace_pending_ingestion.py`.
- Nu am validat local pe corpus real (`documente_noi/` nu există în acest worktree — e gitignored, confirmat cu Glob înainte de a scrie codul).
- Nu am adăugat validare care să refuze explicit `--pdf` dat pentru documente non-`pdf_` (ex. `i5_2022 --pdf ceva.pdf`) — argumentul e pur și simplu ignorat în acel caz. Dacă vrei fail-closed acolo, e un one-line addition, dar handoff-ul nu o cere explicit.

## Ce ar trebui verificat de planner

1. `pytest tests/test_populare_db.py` — în special testele de acoperire/P118 (ar trebui neschimbate ca rezultat, doar rutate prin funcția nouă) și că nu există erori de import/sintaxă în `chunking_core.py`.
2. Un `import reimport_approved` / `python reimport_approved.py --help` pentru verificare sintactică rapidă (nu am cum să confirm că fișierul parsează fără erori — nu am rulat nimic).
3. Verificare manuală a query-urilor SQL (nume coloane/tabel `public.documente`, `public.documente_chunks`) față de schema reală — le-am derivat din `manual_ingestion_import.py`/`backup_baza_de_date.py`, dar nu am acces la schema live.
4. Risc: lock advisory în `commit_document`/`restore_from_backup` se ia doar pe `document_id` (nu și pe `source_key`/`cod_oficial` ca în importerul de documente noi) — suficient cât timp `reimport_approved.py` e singurul script care scrie pe un `document_id` deja `approved` în afara migrărilor SQL manuale; dacă rulează concurent cu `populare_db.py` pe același document, verificarea „număr de chunk-uri identic" + `FOR UPDATE` tot prinde schimbarea (`concurrent_change`), dar merită confirmat explicit că nu e nevoie de lock suplimentar pe `source_key`.
5. Risc minor: dacă `chunking_core.creeaza_chunkuri` produce o listă goală, `base._valideaza_chunkuri` ridică `ValueError` generic (din `manual_ingestion_preflight._valideaza_chunkuri_locale`), pe care îl prind și-l transform în `ReimportError("invalid_chunks")` **înainte** de evaluarea explicită a porții — deci raportul JSON nu se mai scrie în acel caz (nu apuc să notez motivul „zero chunk-uri noi" în `documente_noi/_reports/...`). Practic echivalent ca siguranță (se oprește tot înainte de Voyage/scriere), dar diferă de la litera spec-ului („evaluează poarta... scrie raport") — semnalez, nu am schimbat fără aprobare.
