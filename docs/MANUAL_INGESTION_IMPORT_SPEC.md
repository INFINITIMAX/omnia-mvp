# Import manual persistent pentru un PDF — specificație aprobată

**Status:** aprobat de Lucian la 11-09-2026. Implementarea inițială este mock-first; nu autorizează rularea `--commit` pe Supabase sau Voyage.

## Intenție

După preflight-ul local acceptat, operatorul trebuie să poată importa controlat un document nou. Importerul este manual, punctual și insert-only: nu actualizează sau șterge documente, nu aprobă documentul pentru retrieval și nu pornește automat.

## Intrări explicite

```powershell
python manual_ingestion_import.py --pdf documente_noi/_inbox/un-document.pdf --report documente_noi/_reports/un-document.preflight.json --metadata documente_noi/_reports/un-document.metadata.json
```

Metadata locală conține exact `document_id`, `cod_oficial`, `titlu_oficial`, `an`. Importerul compară codul/titlul/anul cu raportul de preflight. `source_key` este derivat intern, deterministic, ca `pdf_<SHA256>`; nu este primit de la operator.

`--commit` este necesar suplimentar pentru a permite DB + Voyage. Fără el, comanda este dry-run și nu deschide DB, nu creează client Voyage și nu face apel de rețea/plătit.

## Contract `--commit`

1. Recalculează SHA-256 și refuză PDF-ul dacă nu coincide cu raportul sau se schimbă în procesare.
2. Reextrage și validează local textul/chunking-ul; metadata trebuie să coincidă cu candidații unici din raport.
3. Deschide PostgreSQL numai cu TLS și timeout; serializarea DB folosește advisory locks pentru SHA, `document_id` și cod.
4. Refuză înainte de Voyage orice identitate existentă: SHA/source, `document_id`, `source_key` sau cod oficial.
5. Păstrează lock-urile în tranzacție pe durata embedding-urilor pentru a evita importuri/costuri duplicate concurente.
6. Cere embeddings Voyage fără retry automat, verifică fiecare lot și revalidează SHA înainte de inserare.
7. Face numai `INSERT` pentru `documente` și `documente_chunks`, cu status exact `indexed_pending_validation`; apoi commit.
8. O eroare DB înainte de commit sau o eroare de validare face rollback; o eroare Voyage face zero scrieri DB. Un apel Voyage deja acceptat poate rămâne facturabil chiar dacă importul nu este persistat.
9. Dacă apelul `connection.commit()` însuși eșuează, statusul este `commit_unknown`: nu declarăm rollback și nu reîncercăm. Se face obligatoriu reconciliere DB read-only după SHA/document/cod înainte de orice decizie ulterioară.

## Excluderi explicite

- Fără update, delete, reimport sau reconciliere a unui document existent.
- Fără migrare nouă și fără aplicarea migrării `document_ingestion_sources`.
- Fără `approved`, endpoint web, browser/Supabase direct, worker, scheduler sau retry automat.
- Fără PDF/text/chunk-uri/chei în Git ori în raportul de rezultat.

## Gate-uri ulterioare

1. Implementare/testare mock-first.
2. QA și review locale.
3. Aprobarea explicită a lui Lucian pentru o comandă `--commit` concretă, cu PDF identificat, estimare de chunk-uri/cost și verificare DB prealabilă read-only.
4. Dacă apare `commit_unknown`, reconciliere DB read-only obligatorie; nu se rerulează `--commit` fără decizie explicită ulterioară.
5. Aprobarea separată pentru trecerea documentului la `approved`.
