# NormativAI — registrul deciziilor aprobate

Acest fișier separă deciziile explicite ale lui Lucian de propunerile agenților. O propunere nu devine comportament de produs până când Lucian nu o aprobă.

## Decizii active

### Identitate și acces

- Brand public: **NormativAI**; Omnia rămâne numele intern al repository-ului.
- FastAPI este singurul client al Supabase.
- Browserul nu primește acces Supabase, fișiere normative, embeddings, chunk-uri brute sau endpoint de download.
- Ingestion-ul este controlat exclusiv de Lucian.

### Documente

- Documentele au statusurile `indexed_pending_validation`, `approved` și `disabled`.
- Retrieval-ul folosește numai documente cu status `approved`.
- Lucian a aprobat explicit documentele `np010_2022` și `np057_02`; statusurile au fost actualizate în Supabase, iar cele 694 chunk-uri au fost reconfirmate.
- Decizia este reproductibilă prin migrarea `20260831220000_approve_initial_documents.sql`, care verifică identitatea și nu aprobă alte documente.
- Orice document nou intră implicit în `indexed_pending_validation` și necesită aprobare explicită înainte să poată genera răspunsuri.

### Retrieval și răspunsuri

- Referința explicită la articol folosește exact lookup înainte de semantic search.
- Un articol explicit inexistent returnează `not_found`; nu există fallback semantic ascuns.
- Duplicatele identice se deduplică după `content_hash`; texte diferite pentru aceeași pereche document/articol produc `ambiguous_article`.
- Căutarea semantică rulează numai fără intenție explicită și folosește top-K, prag și limită de context.
- Citările publice vor conține numai metadata oficială și citat limitat; niciodată `source_key`.

### Cost și utilizare

- Testele implicite mockuiesc Supabase, Voyage și Anthropic; apelurile reale sunt opt-in.
- Utilizator anonim: maximum 10 întrebări totale per browser, cu cookie semnat și contor server-side.
- Tester: cod unic, revocabil și stocat ca hash; maximum 50 de întrebări per cod.
- Rate limiting-ul per IP se aplică înainte de servicii plătite.
- Erorile tehnice interne nu consumă quota.

## Regula de schimbare

Înainte de implementarea unei schimbări care afectează comportamentul public, datele eligibile, accesul, costul sau fallback-ul, Planner-ul trebuie să explice:

1. ce vede utilizatorul înainte și după;
2. ce date sau servicii sunt afectate;
3. riscurile și alternativele;
4. dacă există cost sau modificare persistentă;
5. ce rămâne neimplementat.

Schimbarea se implementează numai după aprobarea explicită a lui Lucian.
