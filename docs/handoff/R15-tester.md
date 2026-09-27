# R15 — Tester: teste pentru `reimport_approved.py`

Worktree: `D:\Omnia-MVP-r15-reimport`, branch `feat/r15-reimport-approved`, commit coder `1131b42`.
Citește întâi `docs/handoff/R15-coder.md` (sarcina, D24, runda 2) și `docs/handoff/R15-coder-raport.md`. Cod: `reimport_approved.py`, `chunking_core.py` (funcția nouă `acoperire_text_brut` și fix-ul pentru numărul lipit de majusculă).

## Starea verificată de planner
- `python -m pytest -q` cu `documente_noi` local: 1070 passed, 1 failed — `tests/test_populare_db.py::test_chunking_documentelor_deja_validate_ramane_neschimbat[i7_2011-2229]`: numărul I7 e acum **2226** (schimbare intenționată: runda 2 a recuperat articolele cu număr lipit de cuvânt).
- Dry-run real, read-only, pe toate cele 9 documente: toate trec poarta D24 (acoperire: p118 0,993; i7 0,971; i5 0,978; i9 0,969; np004 0,923; np010 0,999; np057 0,882; spitale 0,982; np091 0,989).

## Sarcina
1. Actualizează numărul I7 la **2226** în `NUMAR_CHUNKURI_ASTEPTAT_PER_DOCUMENT`.
2. În `tests/test_chunking_core.py`: test pentru numărul lipit de majusculă (`3.0.1.Condiții generale…` → `articol` `3.0.1.`, textul începe cu „Condiții”), plus un test negativ că `1.1./` și `1.1.,text` rămân invalide.
3. **Fișier nou `tests/test_reimport_approved.py`**, cu DB și Voyage falsificate (fără rețea, fără `.env`), urmând stilul testelor existente pentru `manual_ingestion_import.py` / `replace_pending_ingestion.py`:
   - **dry-run:** conexiune setată `readonly`, zero scrieri, zero apeluri Voyage, raport JSON scris atomic cu câmpurile `poarta_trece`, `motive_poarta`, `acoperire`, `prag_acoperire`, `chunk_count_vechi/nou`, `statistici_chunking`, `exemple` (extrase ≤120 caractere);
   - document inexistent / nu e `approved` / `source_key` diferit → token de eroare, zero scrieri;
   - sursă text: `extracted.txt` lipsă → eroare; pentru `pdf_<sha>`: `--pdf` lipsă, PDF în afara `_inbox`, SHA diferit → eroare, fără extragere/scriere;
   - **poarta:** acoperire sub prag, antet MO într-un chunk, chunk invalid, P 118/1 cu un articol „Art.” lipsă → `poarta_trece` fals cu motivul corect; cu `--commit`, poarta picată → zero Voyage, zero backup, zero scrieri;
   - **commit reușit:** ordinea strictă backup (fișier scris, cu `embedding::text`) → Voyage → o singură tranzacție (lock, `FOR UPDATE`, reverificare status/source_key/număr, `DELETE` numai pentru documentul dat, `INSERT` cu `chunk_order` 1..n și `sursa` = `source_key`) → commit; statusul documentului nu e modificat;
   - `concurrent_change` (numărul de chunk-uri s-a schimbat între citire și tranzacție) → rollback, nicio scriere persistată;
   - eroare Voyage → nicio scriere DB; eroare la commit cu rezultat necunoscut → `commit_unknown`, fără retry;
   - **restore:** backup pentru alt document / alt `source_key` → refuz; restore valid → o tranzacție cu `DELETE` + `INSERT` din backup, `embedding` trimis ca text pentru `::vector`, zero Voyage;
   - modurile se exclud reciproc (`--commit` cu `--restore` → eroare de argumente).

## Constrângeri dure
- Scrii doar în `tests/`. Nu modifici cod de producție; bug suspectat → raportezi.
- Nu rula comenzi. Niciun test nu atinge rețeaua, DB-ul real sau `.env`.
- Fiecare test trebuie să poată pica dacă comportamentul apărat e rupt; fără teste redundante.

## Predare
`docs/handoff/R15-tester-raport.md`: fișiere, lista testelor și ce apără fiecare, bug-uri suspectate.
