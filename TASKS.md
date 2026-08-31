# TASKS — Omnia

## Acum

### Faza 0 — Stabilizare

- [x] Eliminare normative-demo din Supabase.
- [x] Structurare locală `documente_noi/` pentru NP 010-2022 și NP 057-02.
- [x] Adaptare `procesare_documente.py`, `populare_db.py`, `chunkingv2.py`.
- [x] Dry-run: 694 chunk-uri validate fără cost API.
- [x] Import real: 694 chunk-uri în Supabase.
- [ ] Review explicat și commit pentru schimbările de ingestion.
- [x] Adăugare `requirements.txt`, structură `tests/` mockuită și documentație locală minimă.
- [x] Verificare Git: fără secrete; documentul-demo eliminat; fișierele locale sunt ignorate.

## Următorul task aprobat pentru Coder

**Titlu:** Fundația reproductibilă pentru Faza 0.

**Scope:** creează `requirements.txt`, configurația minimă de test, un smoke test fără servicii externe și documentația minimă pentru rulare locală. Nu modifica Supabase, API-ul de producție sau UI-ul.

**Criterii de acceptare:**
- instalarea dependențelor este documentată;
- un test local mockuit rulează cu `python -m pytest -q`;
- niciun test implicit nu apelează Anthropic/Voyage/Supabase;
- diff-ul este mic și explicat;
- fără commit/push fără aprobarea lui Lucian.

## Backlog ordonat

1. Faza 1: migrare Supabase pentru metadata documente și chunk identity.
2. Faza 3: hybrid search + citări oficiale.
3. Faza 4: cost control și endpoint-uri.
4. Faza 5: testare agresivă.
5. Faza 6: UI real.
6. Faza 7: review și deployment.
7. Faza 8: business/CV material.

## Observații

- `np057_02` nu are PDF original local; are doar `extracted.txt` și metadata notează acest lucru.
- Supabase are 694 chunk-uri: NP010 = 408, NP057 = 286.
- `claude_herdr.md` este handoff istoric neversionat; `PLAN.md` și acest fișier sunt sursele active de coordonare.
