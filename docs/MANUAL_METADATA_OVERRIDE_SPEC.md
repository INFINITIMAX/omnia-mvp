# Preflight cu metadata confirmată de operator — specificație aprobată

**Status:** aprobat de Lucian la 13-09-2026 pentru documente unde PDF-ul nu permite extragerea sigură a codului.

## Problemă

PDF-ul de bază NP 015-2022 are text extras și chunking aproape complet, dar codul nu poate fi extras sigur din copertă, iar documentul complet introduce referințe normative multiple. Preflight-ul actual blochează corect ambiguitatea; nu trebuie să ghicească identitatea.

## Contract

`manual_ingestion_preflight.py` acceptă opțional o metadata locală explicită, din `_reports`, cu `document_id`, `cod_oficial`, `titlu_oficial` și `an`.

- Fără metadata explicită, comportamentul automat actual rămâne neschimbat: candidații lipsă/ambigui blochează preflight-ul.
- Cu metadata explicită validă, raportul marchează `metadata_source: "operator_confirmed"` și păstrează metadata în `metadata_confirmation`; nu o declară extrasă din PDF.
- SHA, paginile, caracterele și chunking-ul rămân obligatorii. Raportul nu conține text normativ, chunk-uri, embeddings sau secrete.
- Importerul persistent acceptă acest raport numai dacă metadata de import coincide exact cu `metadata_confirmation`. Nu schimbă `--commit`, insert-only, pending, costurile, D17 sau aprobarea separată pentru `approved`.

## Virgula după articol

Pentru compatibilitate cu formatul PDF observat, numai o virgulă urmată imediat de whitespace sau sfârșit după un articol deja recunoscut este tratată ca punctuație de separare și nu intră în identificator.

- Slash-ul și orice alt caracter neacceptat rămân fail-closed.
- Virgula nu devine parte acceptată a identificatorului de articol.
- Testele sintetice demonstrează atât cazul acceptat cu virgulă, cât și refuzul slash-ului și al virgulei ne-delimitatoare.

## Excluderi

Fără DB, Voyage, import persistent real, `approved`, worker, scheduler, deploy, PDF/text în Git sau acceptarea altor metadata ambigue automat.
