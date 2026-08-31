# Omnia — Plan MVP

## Obiectiv

Omnia devine o aplicație publică pentru normative tehnice românești: răspunsuri bazate exclusiv pe dovezi, cu citare oficială, căutare exactă de articol, costuri API controlate și teste automate.

## Faza 0 — Stabilizare

- Review și commit pentru ingestion-ul structurat deja implementat.
- Adăugare `requirements.txt`, `AGENTS.md`, `TASKS.md` și `tests/`.
- Verificare că Git nu conține secrete sau documente normative.

**Gata când:** proiectul este reproductibil, Git este curat și testele au o comandă unică de rulare.

## Faza 1 — Schema Supabase

- Tabel `documents` cu identificator tehnic, cod/titlu oficial, an și status.
- Legătură între chunk-uri și documente.
- Identificator unic pentru fiecare chunk; `articol` nu este singur unic.
- Migrare SQL versionată, verificare RLS/privilegii și indexuri.
- Index pgvector după stabilizarea formei de retrieval.

**Gata când:** schema poate fi recreată din Git, iar API-ul nu mai expune nume interne de fișiere.

## Faza 2 — Ingestion sigur

- Validare `metadata.json` pentru fiecare document.
- Import per document, fără golirea întregului tabel.
- Tranzacții, hash de conținut și raport de validare.
- `--dry-run` fără apeluri Voyage sau modificări Supabase.
- Agentic chunking este upgrade ulterior, nu blocaj MVP.

**Gata când:** importul repetat nu creează duplicate și nu afectează alte documente.

## Faza 3 — Hybrid search

- Extracție/normalizare număr articol din întrebare.
- Exact lookup înainte de semantic search.
- Semantic top-K pentru întrebări generale sau fallback.
- Deduplicare, context limitat și citări structurate.

**Gata când:** un articol real este găsit exact, unul inventat este refuzat, iar răspunsul conține citări oficiale.

## Faza 4 — API și cost control

- Separare retrieval de generare Anthropic.
- Fără apel Claude când lipsesc dovezile.
- Limite pentru întrebare, chunk-uri, context și output.
- Endpoint-uri `/health`, `/documents`, `/intreaba`.
- Erori/timeouts clare, logging fără secrete sau text normativ integral.
- Testele plătite sunt opt-in.

**Gata când:** testele standard nu consumă Anthropic sau Voyage.

## Faza 5 — Testare agresivă

- Unit tests: parser articole, chunking, metadata.
- API tests mockuite: exact match, semantic, document/ articol inexistent, duplicate, conflict, lipsă dovezi, context limitat, erori servicii și prompt injection.
- Set de evaluare cu rezultate așteptate.
- Smoke tests reale puține și deliberate.

**Gata când:** `python -m pytest -q` trece, iar apelurile plătite sunt dezactivate implicit.

## Faza 6 — UI real

- Lista documentelor și contorul vin din `/documents`.
- Coduri/titluri oficiale și citări clare.
- Eliminarea datelor demonstrative false.
- Loading, erori și refuz explicit.
- Decizie de brand: Omnia sau NormativAI.

## Faza 7 — Review și deployment

- Review independent pentru cod, securitate și cost.
- Hosting, secrete, pooling Supabase, health check și budget alerts.
- Smoke tests pe URL public.

**Gata când:** aplicația este publică și trece criteriile de acceptare.

## Faza 8 — Business și CV

- README, diagramă arhitectură, demo/capturi, metrici de test și limitări.
- Rezultate tehnice transformate în bullets CV.

## Criterii obligatorii

- Niciun răspuns fără dovadă/citare.
- Fără secrete sau documente normative în Git.
- Fără push, deploy sau migrare Supabase fără aprobarea lui Lucian.
- Orice cod este explicat pentru nivel începător și orice decizie cu valoare de CV este marcată explicit.
