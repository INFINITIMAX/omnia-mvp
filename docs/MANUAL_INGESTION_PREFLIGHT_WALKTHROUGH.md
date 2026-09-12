# Preflight manual PDF — explicație pentru începător

Fișierul `manual_ingestion_preflight.py` este doar etapa locală de verificare. El nu importă documente și nu poate cheltui credite API.

1. Importurile folosesc biblioteca standard și `extrage_text` din `procesare_documente.py`; nu sunt importate biblioteci DB sau AI.
2. `FOLDER_INBOX` și `FOLDER_RAPOARTE` definesc singurele directoare acceptate.
3. `PreflightError` transmite un motiv scurt, controlat, fără conținutul PDF-ului.
4. `_hash_sha256()` calculează amprenta PDF-ului în blocuri, pentru a detecta dacă fișierul s-a schimbat în timpul procesării.
5. `_cale_directa()`, `_valideaza_pdf()` și `_valideaza_raport()` refuză căi din afara directoarelor aprobate, subdirectoare, extensii greșite și rapoarte existente.
6. `find_metadata_candidates()` găsește numai candidați de cod, titlu și an. Nu construiește un `document_id` și nu ghicește metadata finală.
7. `_metadata_unica()` acceptă exact un candidat pentru fiecare câmp; lipsa sau ambiguitatea oprește fluxul.
8. `_creeaza_chunkuri_locale()` și `_valideaza_chunkuri_locale()` verifică local că textul se poate separa în fragmente utile. Validatorul aplică aceeași normalizare a identificatorului de articol ca importerul existent: scoate spațiile, transformă în litere mici, ignoră punctul final și refuză orice alt caracter. Fragmentele rămân numai în memorie.
9. `preflight_pdf()` leagă pașii: validează căile, compară hash-ul înainte/după extracție, verifică textul și chunking-ul, apoi creează raportul minim.
10. `_scrie_raport_atomic()` rezervă numele raportului și publică numai JSON complet. Raportul conține hash, număr de pagini/caractere/chunk-uri și metadata candidat; nu conține text, chunk-uri, embeddings sau secrete.
11. `main()` cere obligatoriu `--pdf` și `--report`; nu scanează inbox-ul și nu pornește importul.

## Limită importantă

Un raport `ready_for_human_metadata` nu înseamnă că documentul a intrat în Supabase sau este disponibil clientului. Lucian verifică identitatea și aprobă separat un viitor import DB + Voyage, apoi separat eventuala publicare `approved`.
