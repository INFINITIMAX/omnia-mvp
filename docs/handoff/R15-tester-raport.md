# R15 — Raport Tester

## Fișiere modificate/create

1. **`tests/test_populare_db.py`** — `NUMAR_CHUNKURI_ASTEPTAT_PER_DOCUMENT["i7_2011"]` actualizat de la `2229` la `2226`, conform stării verificate de planner (runda 2, recuperarea articolelor cu număr lipit de cuvânt).
2. **`tests/test_chunking_core.py`** — două teste noi, adăugate la finalul fișierului:
   - `test_numar_lipit_de_majuscula_nu_se_lipeste_de_articol`: text `"3.0.1.Condiții generale..."` → verifică `articol == "3.0.1."` și `text` care începe cu `"Condiții"`. Ar pica dacă fix-ul din Runda 2 (`_PATTERN_MAJUSCULA_LIPITA`) ar fi eliminat sau ar reveni la lipirea cuvântului de identificator.
   - `test_numar_lipit_de_caracter_ne_majuscul_ramane_referinta_rupta`: text cu `"1.1./ceva..."` (bară, nu majusculă) — verifică că rămâne trimitere ruptă (nu devine articol propriu), ca să confirme că fix-ul Runda 2 e strict limitat la majuscule și nu a lărgit accidental domeniul de excepție. Ar pica dacă `_este_referinta_rupta`/`_PATTERN_MAJUSCULA_LIPITA` ar deveni prea permisive. (Cazul `"1.1.,text"` era deja acoperit de `test_d18_virgula_urmata_de_text_pe_acelasi_rand_nu_e_articol`, existent — nu l-am duplicat.)
3. **`tests/test_reimport_approved.py`** (nou, 34 teste) — DB și Voyage complet falsificate (clase `ReadCursor`/`ReadConn`/`WriteCursor`/`WriteConn`/`VoyageFake`), fără rețea, fără `.env`, `FOLDER_DOCUMENTE`/`FOLDER_RAPOARTE`/`FOLDER_BACKUPS`/`base.FOLDER_INBOX` monkeypatch-uite pe `tmp_path`.

## Ce apără fiecare test (grupat)

**Dry-run (1 test)** — `test_dry_run_este_readonly_fara_voyage_si_scrie_raportul_complet`: verifică zero scrieri SQL (INSERT/UPDATE/DELETE), rollback pe conexiune, toate câmpurile cerute în raportul JSON de pe disc, și trunchierea exemplelor la 120 caractere (folosesc deliberat o linie >120 caractere). Ar pica dacă orice câmp ar lipsi din raport sau dacă s-ar strecura o scriere.

**Identitate document (4 teste)** — document necunoscut în `DOCUMENTE_APROBATE` (zero I/O), document absent din DB, `status != approved`, `source_key` diferit. Fiecare verifică tokenul exact și, unde relevant, că dependențele interzise nu sunt atinse.

**Sursa textului (7 teste)** — `extracted.txt` lipsă/gol (fără conexiune deschisă), și pentru `np091_2003`: `--pdf` lipsă, extensie greșită, PDF în afara `_inbox`, PDF instabil (hash schimbat de „extragere”, fără conexiune), plus un test pozitiv că `source_key` e calculat corect din SHA-ul real al PDF-ului (nu unul declarat).

**Chunk-uri invalide (1 test, cu observație de discrepanță — vezi mai jos)**.

**Poarta D24 (6 teste)** — acoperire sub prag, chunk cu antet MO, P118 cu „Art.” lipsă (+ control pozitiv că același gate nu respinge cazul valid), și `--commit` cu poarta picată → zero Voyage/backup/scriere.

**Commit reușit (1 test cuprinzător)** — `test_commit_reusit_respecta_ordinea_backup_voyage_tranzactie`: ordine strictă prin listă `events` partajată (`["backup","embed","delete"]`), ordinea `lock < FOR UPDATE < DELETE < INSERT` prin indici în `calls`, `DELETE` doar cu `(document_id,)`, `INSERT` cu `chunk_order=1` și `sursa=source_key`, zero `UPDATE` (statusul documentului neschimbat), conținutul backup-ului de pe disc cu `embedding` ca text.

**Eșecuri commit (3 teste)** — `concurrent_change` (rollback, zero DELETE/INSERT), eroare Voyage (backup rămâne pe disc, dar zero scriere DB), `commit_unknown` (commit apelat o singură dată, zero rollback, resurse închise).

**Restore (5 teste)** — refuz pentru document greșit, refuz pentru `source_key` diferit de cel din DB, restore valid (o tranzacție, embedding trimis ca text pentru `::vector`), refuz pentru cale în afara `backups/`, refuz pentru backup invalid (`chunkuri` gol).

**CLI (1 test)** — `--commit` + `--restore` → `SystemExit(2)` la parsare, înainte de orice apel funcțional (verificat prin monkeypatch cu `forbidden` pe toate cele trei funcții).

## Discrepanță suspectată (nu bug de comportament, ci de conformitate cu litera handoff-ului)

Handoff-ul (R15-coder.md pct. 4) cere ca poarta D24 să evalueze printre criterii „toate chunk-urile validează (`articol_normalizat` în contract, text nevid, ≤1000 caractere)” — implicând `poarta_trece=False` cu motiv explicit. În implementare, `_construieste_chunkuri_noi` apelează `base._valideaza_chunkuri` **înainte** de `_evalueaza_poarta`, deci un chunk invalid ridică direct `ReimportError("invalid_chunks")` și oprește execuția fără să mai scrie raportul JSON și fără să treacă vreodată prin `_evalueaza_poarta` (care, de altfel, nici nu conține vreo verificare de validitate a chunk-urilor — doar acoperire, antet MO, `len>0`, P118). Practic echivalent ca siguranță (nimic nu se scrie), dar diferă de litera spec-ului. Coder-ul a semnalat deja acest risc explicit în raportul lui (punctul 5). Am scris testul `test_chunkuri_invalide_opresc_inainte_de_poarta_fara_scriere` ca să **documenteze comportamentul real** (nu ca bug ascuns) — dacă planner-ul decide că handoff-ul trebuie respectat literal, acest test trebuie rescris când coder-ul mută verificarea de validitate în `_evalueaza_poarta`.

## Ce nu am acoperit și de ce

- **`--pdf` dat pentru documente non-`pdf_`** (ex. `i5_2022 --pdf ceva.pdf`): coder-ul a raportat explicit că argumentul e ignorat, nu validat — comportament confirmat, dar handoff-ul tester-ului nu-l cere explicit ca test; l-am lăsat neacoperit ca să nu inventez o cerință în afara scope-ului.
- **Conținutul exact al `statistici_chunking`** din raport: verific doar că e un `dict` prezent, nu valorile — fiindcă `chunking_core.ultimele_statistici()` e stare globală mutabilă, populată doar de apeluri reale la `chunking_core.creeaza_chunkuri` (nu de `create_chunks` injectat), deci valorile depind de ordinea altor teste din sesiune, nu de acest test. Testat corect ca atare (nu ca fals pozitiv).
- **`main()` cu `--commit`/dry-run reale** (fără mock la nivel de `argparse`→funcție): am testat direct funcțiile (`dry_run`/`commit_document`/`restore_from_backup`), nu am dublat cu teste `main()` pentru fiecare mod — ar fi fost redundant, logica de dispatch e trivială și acoperită de testul de exclusivitate CLI.
- **Rularea reală pe `documente_noi`** (corpus real): în afara scope-ului tester-ului; planner-ul are deja dovezi de dry-run real menționate în handoff.

## Comanda exactă pentru planner

```powershell
python -m pytest -q tests/test_reimport_approved.py tests/test_chunking_core.py tests/test_populare_db.py
```

(sau `python -m pytest -q` pentru toată suita, ca să reconfirme cele 1070/1071 anterioare + noile teste).
