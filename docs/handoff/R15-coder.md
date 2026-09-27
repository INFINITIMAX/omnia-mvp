# R15 — Coder: reimport sigur al documentelor `approved` cu chunker-ul R14

Worktree: `D:\Omnia-MVP-r15-reimport`, branch `feat/r15-reimport-approved` (din `main` `a4f47af`, care conține R14).
Decizii Lucian (27-09-2026): plan R15 aprobat; **poarta dinaintea commit-ului este automată** (D24, vezi mai jos) — fără aprobare manuală a raportului per document.

## Context
- R14 (`chunking_core.creeaza_chunkuri`) crește mult acoperirea: P 118/1 96,3% → 99,4% (articole „Art.” proprii 33 → 811/811), I7 79,8% → 95,9%. Producția are încă chunk-urile vechi.
- Nu există mecanism de înlocuire pentru documente `approved`: `manual_ingestion_import.py` refuză identitățile existente; `replace_pending_ingestion.py` lucrează doar pe `pending`; `populare_db.py` face DELETE/INSERT fără gate (finding F3, R10). Reutilizează din ele helper-ele sigure (lock, loturi embedding, hash chunk, conexiune, client Voyage cu `timeout=30, max_retries=0`, `commit_unknown`) prin import, fără copiere.
- Documente `approved` (document_id → source_key): `i5_2022` `i5_2022_extras.txt`, `i7_2011` `i7_2011_extras.txt`, `i9_2022` `I9_2022_extras.txt`, `np004_03` `np004_03_extras.txt`, `np010_2022` `NP010_extras.txt`, `np057_02` `NP0572002_extras.txt`, `p118_1_2025` `P118_1_2025_extras.txt`, `spitale_2022` `NP015_2022_extras.txt`, `np091_2003` `pdf_<sha256 al PDF-ului>`.
- Schema chunk: `articol, articol_normalizat, text, content_hash, chunk_order, document_id, embedding, sursa` (`sursa` = `source_key`; FK `(document_id, source_key)`; `unique (document_id, chunk_order)`).

## Sarcina — script nou `reimport_approved.py`
CLI cu un singur document per rulare: `--document <document_id>`, opțional `--pdf <cale>`, și exact unul dintre modurile: implicit **dry-run**, `--commit`, `--restore <fisier_backup>`.

1. **Sursa textului:** pentru `source_key` care nu începe cu `pdf_`: `documente_noi/<document_id>/extracted.txt` (fișierul trebuie să existe, direct în acel folder). Pentru `source_key` `pdf_<sha>`: `--pdf` obligatoriu, fișier direct în `documente_noi/_inbox`, iar SHA-256 al PDF-ului trebuie să fie exact `<sha>`; textul vine din `procesare_documente.extrage_text`. Orice nepotrivire → eroare cu token stabil, fără scriere.
2. **Dry-run (implicit):** conexiune DB `readonly`; verifică documentul (există, `status = 'approved'`, `source_key` așteptat) și citește numărul de chunk-uri actual; calculează chunk-urile noi cu `chunking_core.creeaza_chunkuri`; evaluează **poarta automată** (pct. 4); scrie un raport JSON atomic în `documente_noi/_reports/<document_id>.reimport.json` (număr vechi/nou, acoperire, statistici `ultimele_statistici()`, verdict poartă cu motivele, 3 exemple scurte articol+primele 120 caractere). Fără Voyage, fără scriere DB.
3. **`--commit`:** aceiași pași ca dry-run; dacă poarta pică → oprire fără nicio scriere și fără Voyage. Dacă trece:
   a. **Backup** read-only al chunk-urilor actuale ale documentului (toate coloanele, `embedding::text`) în `backups/reimport-<document_id>-<timestamp UTC>.json`, scris atomic, **înainte** de orice apel Voyage sau scriere;
   b. embeddings pentru chunk-urile noi (loturile și clientul existente);
   c. **o singură tranzacție:** lock advisory pe document; `SELECT … FOR UPDATE` pe rândul din `documente`; reverifică `status = 'approved'`, `source_key` și că numărul de chunk-uri e identic cu cel citit la început (altfel rollback, token `concurrent_change`); `DELETE` chunk-urile documentului; `INSERT` cele noi cu `chunk_order` 1..n, `content_hash` calculat cu aceeași funcție ca importerul, `articol_normalizat` validat; commit. Statusul documentului **nu** se schimbă (documentul nu iese din producție).
   d. Eroare după trimiterea commit-ului cu rezultat necunoscut → `commit_unknown`, fără retry (ca importerul).
4. **Poarta automată (D24)** — toate trebuie să treacă: acoperirea față de textul brut ≥ pragul documentului; zero chunk-uri care conțin antetul de pagină MO; toate chunk-urile validează (`articol_normalizat` în contract, text nevid, ≤1000 caractere); numărul nou > 0; pentru `p118_1_2025`, toate articolele „Art. N.N…” urmate de majusculă din text apar ca articol de bază al unui chunk. Praguri: i5 0,97; i7 0,95; i9 0,96; np004 0,90; np010 0,99; np057 0,87; p118 0,99; spitale 0,97; np091 0,95 (provizoriu, ajustabil doar prin PR). Metrica de acoperire: exact cea din testul `test_acoperirea_continutului_brut_ramane_peste_prag` (`tests/test_populare_db.py`) — mut-o într-o funcție publică în `chunking_core.py` (ex. `acoperire_text_brut(text, chunkuri) -> float`) și fă testul existent să o folosească, fără să-i schimbi pragurile sau semantica.
5. **`--restore <fisier_backup>`:** validează că backup-ul aparține documentului (document_id, source_key) și că documentul e `approved`; într-o singură tranzacție (același lock și `FOR UPDATE`) înlocuiește chunk-urile cu cele din backup (`embedding` din text cu `::vector`). Fără Voyage. Nu are poartă de acoperire (e revenire la starea anterioară).
6. **`docs/DECISIONS.md`:** adaugă D24 (textul de mai jos) deasupra D23.

## D24 (de inserat în `docs/DECISIONS.md`)
> ### D24 — reimport `approved` cu poartă automată, aprobat Lucian (27-09-2026)
> Documentele `approved` pot primi chunk-urile produse de chunker-ul unificat (R14) prin `reimport_approved.py --commit`, fără aprobare manuală a raportului per document, **numai** dacă poarta automată trece: acoperire față de textul brut ≥ pragul documentului, zero antete de pagină MO în chunk-uri, chunk-uri valide, iar pentru P 118/1 toate articolele „Art.” ca articole proprii. Înlocuirea se face într-o singură tranzacție, fără schimbare de status, după un backup local al chunk-urilor vechi (inclusiv embeddings); `--restore` revine din backup fără cost Voyage. Pragurile se schimbă doar prin PR. Execuția în producție (scriere DB + Voyage) rămâne o aprobare separată a lui Lucian.

## Constrângeri dure
- Nu rula comenzi. Nu scrie teste noi (Tester-ul); poți adapta testul de acoperire existent doar ca să folosească funcția publică (pct. 4).
- Nu atinge: `main.py`, `generation_core.py`, `retrieval_core.py`, `access_control.py`, `static/`, `supabase/migrations/`, `.env`, `documente_noi/` (doar citit, la rulare).
- Nu modifica comportamentul `populare_db.py`, `manual_ingestion_import.py`, `replace_pending_ingestion.py`; doar importă din ele. Dacă un helper e privat (`_nume`) și trebuie reutilizat, e acceptabil importul lui; raportează-l.
- Fără secrete în loguri sau rapoarte; rapoartele pot conține doar fragmente scurte de text (≤120 caractere).

## Predare
`docs/handoff/R15-coder-raport.md`: fișiere, fluxul fiecărui mod, token-urile de eroare, ce ai reutilizat, riscuri deschise.
