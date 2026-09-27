# R08 — articol împărțit în chunk-uri

## Sarcină
Remediază regresia: `RetrievalService._has_ambiguous_article` tratează ca ambiguitate mai multe chunk-uri cu hash-uri diferite ale aceluiași `(document_id, articol_normalizat)`. După limita D25 de 1.000 caractere, acesta este comportamentul normal pentru un articol lung și blochează întrebările valide cu `ambiguous_article`.

## Rezultat așteptat
Un articol din același document împărțit în chunk-uri ordonate trebuie returnat ca evidence, nu refuzat. Protecția pentru ambiguități reale trebuie păstrată. Adaugă teste de regresie atât pentru exact lookup, cât și pentru semantic retrieval relevant.

## Decizie aprobată
Extinde minimal contractul intern `Evidence`/repository cu `chunk_order`. Un set de chunk-uri pentru același articol este acceptat numai dacă este secvențial și neambiguu; conflictele reale rămân refuzate.

## Constrângeri
Nu atinge DB, deploy, providers, limitele de 1.000, schema DB, statusurile documentelor sau UI. Nu slăbi testele existente. Coderul editează numai `retrieval_core.py`, testele țintite și raportul. Nu rula comenzi. Scrie raport în `docs/handoff/R08-coder-raport.md`.
