# Preflight manual pentru un PDF — specificație aprobată

**Status:** aprobat de Lucian la 11-09-2026 pentru implementare locală.

## Intenție

NormativAI are nevoie de o cale manuală, repetabilă și fără cost pentru a examina un singur PDF înainte de orice import. Aceasta înlocuiește folosirea improprie a workerului automat sau a `populare_db.py` pentru prima etapă.

## Scope livrabil

Se adaugă un CLI local care primește explicit un singur PDF din `documente_noi/_inbox` și scrie un raport JSON local în `documente_noi/_reports`.

Preflight-ul:

1. acceptă numai un fișier `.pdf` direct din `_inbox`;
2. calculează SHA-256 înainte și după extracție și refuză PDF-ul modificat în timpul procesării;
3. extrage local textul cu calea existentă PyMuPDF/glife/diacritice;
4. măsoară numărul de pagini și caractere, creează și validează chunk-uri local;
5. identifică doar candidați unici pentru cod, titlu și an; nu inventează metadata;
6. produce un raport fără text normativ, chunk-uri, embedding-uri, secrete sau conținutul PDF-ului.

Un raport `ready_for_human_metadata` arată numai că verificările locale au trecut și candidatul de identitate este unic. Lucian verifică manual identitatea și metadata înainte de orice pas următor. Orice candidat lipsă sau ambiguu este `blocked`, nu o permisiune de import.

## Interfață propusă

```powershell
python manual_ingestion_preflight.py --pdf documente_noi/_inbox/un-document.pdf --report documente_noi/_reports/un-document.preflight.json
```

Ambele căi sunt validate. Raportul nu se suprascrie; un nume nou este necesar pentru o rulare nouă.

## Neincluse explicit

- Nu se scanează automat inbox-ul și nu există watcher, scheduler sau pornire la logon.
- Nu se modifică Supabase, nu se citește DB și nu se aplică migrare.
- Nu se apelează Voyage, Anthropic sau orice API plătit.
- Nu se creează documente, chunk-uri sau embeddings persistente.
- Nu se acordă status `indexed_pending_validation` sau `approved`.
- Nu se modifică sau activează `auto_ingestion_worker.py`, `populare_db.py` ori workerul istoric.

## Gate-uri de continuare

1. **Preflight local:** raport valid, testat mock-first, fără servicii externe.
2. **Aprobarea Lucian DB + Voyage:** decizie ulterioară, explicită; va necesita un importer nou, insert-only, numai `indexed_pending_validation`.
3. **Aprobarea Lucian pentru publicare:** operație separată pentru `approved`.

## Valoare CV

Separarea verificabilă dintre validare locală, cost/persistență și publicare demonstrează controlul unui pipeline RAG cu documente sensibile.
