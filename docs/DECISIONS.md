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
- Nu există tier de tester, coduri sau conturi în MVP. Aplicația este publică și poate avea oricâți vizitatori; fiecare browser primește maximum 10 întrebări.
- Cei 4 testeri inițiali primesc direct același URL public și folosesc exact fluxul anonim, fără privilegii. Numărul lor nu este o limită tehnică sau de produs.
- Consecințe acceptate: identitatea anonimă nu poate fi revocată individual, ștergerea cookie-ului/alt browser poate reseta limita, iar utilizatorii de pe același IP împart rate limit-ul.
- Consumă quota: `answered`, `not_found`, `ambiguous_article` și `ambiguous_reference`.
- Nu consumă quota: input invalid, HTTP 503, eroare DB/Voyage/Claude sau cerere blocată de rate limit.
- Quota se rezervă atomic înainte de serviciile plătite și se restituie la eroare tehnică, pentru a controla cererile simultane.
- Decizie aprobată la 01-09-2026 (România): pentru MVP cu trafic redus, tranzacția quota rămâne deschisă pe durata apelului provider pentru a garanta rollback la eroare tehnică. Numai cererile simultane din același browser pot aștepta durata primei cereri; lock-ul rate limit per IP este scurt. Decizia se reevaluează înainte de scalare.
- Rate limiting per IP: maximum 5 cereri/minut și 30 cereri/oră, verificat înainte de Voyage/Claude.
- Cookie-ul anonim expiră după 1 an; quota de 10 rămâne asociată lui pe această durată.
- IP-ul nu este stocat brut; identificatorul pentru rate limiting este derivat prin HMAC-SHA-256 server-side, cu o cheie separată de cheia cookie-ului.
- Contoarele/bucket-urile IP se păstrează maximum 24 de ore.

## Regula de schimbare

Înainte de implementarea unei schimbări care afectează comportamentul public, datele eligibile, accesul, costul sau fallback-ul, Planner-ul trebuie să explice:

1. ce vede utilizatorul înainte și după;
2. ce date sau servicii sunt afectate;
3. riscurile și alternativele;
4. dacă există cost sau modificare persistentă;
5. ce rămâne neimplementat.

Schimbarea se implementează numai după aprobarea explicită a lui Lucian.
