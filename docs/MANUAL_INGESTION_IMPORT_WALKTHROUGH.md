# Importer manual persistent — explicație pentru începător

`manual_ingestion_import.py` este pasul administrativ după preflight. Fără `--commit` nu poate contacta DB sau Voyage.

1. Importurile locale reutilizează numai extracția și chunking-ul preflight; nu reutilizează workerul automat sau importerul legacy.
2. `ImportError` expune numai tokenuri locale controlate, nu textul PDF, SQL sau secrete.
3. Validarea de cale acceptă PDF-ul doar direct din `_inbox`, iar reportul și metadata doar direct din `_reports`.
4. Metadata cere `document_id`, cod, titlu și an. `source_key` nu vine de la operator: este derivat din SHA ca `pdf_<hash>`.
5. Reportul trebuie să fie `ready_for_human_metadata`, să aibă același SHA și aceiași candidați cod/titlu/an.
6. Importerul reextrage textul și compară paginile, caracterele și numărul de chunk-uri cu reportul. Un PDF schimbat este refuzat.
7. În dry-run rezultatul conține numai status, SHA, document ID și număr de chunk-uri; nu conține text, chunk-uri, embedding-uri sau chei.
8. Numai `--commit` încarcă configurarea, deschide PostgreSQL TLS cu timeout și aplică lock-uri pe SHA/document/cod.
9. Identitățile existente sunt refuzate înainte de construirea clientului Voyage. Embedding-urile sunt cerute fără retry automat și sunt verificate ca număr.
10. Inserările sunt doar `INSERT`: un document nou primește exact `indexed_pending_validation`, apoi chunk-urile lui. Nu există update, delete sau `approved`.
11. O eroare înainte de `connection.commit()` face rollback. Dacă Voyage a acceptat deja un apel iar DB eșuează ulterior, costul acelui apel poate exista fără document persistent. **Excepție D17:** dacă `connection.commit()` însuși dă eroare, statusul este `commit_unknown`; nu se face rollback și nu se reia importul.

## Limită operațională

Codul și testele locale nu autorizează o comandă reală `--commit`. Pentru prima rulare este necesară aprobarea explicită a lui Lucian, cu PDF identificat, report/metadata, estimare de chunk-uri/cost și verificare DB read-only. La `commit_unknown`, păstrezi PDF-ul, reportul și metadata neschimbate; faci obligatoriu reconciliere DB **read-only** după SHA/document/cod și nu rerulezi `--commit` fără o nouă aprobare explicită. `approved` cere o aprobare distinctă.
