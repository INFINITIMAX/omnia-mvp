# NormativAI (internal project name: Omnia)

**NormativAI** is a public question-answering application for Romanian technical regulations in construction and building services. **Omnia** is the internal repository/project name.

It uses retrieval-augmented generation (RAG) with a strict evidence rule: every generated answer must be grounded in at least one fragment from explicitly approved documents and must include its official source citation. The public application never exposes raw documents, chunks, embeddings, internal IDs, or direct database access.

Live application: https://normativai.ro

## How it works

1. `POST /intreaba` receives a question and first applies anonymous access controls: a signed cookie, per-browser quota, and per-IP rate limiting. These controls run before any paid provider call.
2. A deterministic regex parser, not an LLM, detects explicit document or article references. An explicit article uses an exact PostgreSQL lookup and does not call Voyage.
3. Otherwise, the question receives one Voyage embedding (`voyage-3.5`) and is compared through pgvector with approved document fragments (top 5, similarity threshold 0.50).
4. Retrieved evidence is deduplicated and limited to approximately 12,000 characters. Claude (`claude-sonnet-4-6`, maximum 1,200 tokens) is called only when at least one evidence item is available.
5. The generated response is validated: every citation must map to evidence actually provided to the model. Internal identifiers and source filenames never reach the client.

## Architecture

| Component | Responsibility |
|---|---|
| `main.py` | FastAPI public routes, orchestration, anonymous access control, lazy Voyage/Anthropic adapters |
| `retrieval_core.py` | Document/article parser, PostgreSQL repository, exact and semantic retrieval logic |
| `generation_core.py` | Prompt construction and citation validation; testable without Claude |
| `access_control.py` | Signed cookie, 10-question browser quota, 5/minute and 30/hour IP limits, daily paid-call budget |
| `procesare_documente.py` | PDF text extraction with PyMuPDF |
| `glyph_mapping.py` | Formula reconstruction from PDFs using CambriaMath fonts without `/ToUnicode` |
| `diacritice.py` | Symmetric Romanian diacritic normalization during ingestion and querying |
| `populare_db.py` | Idempotent ingestion using content hashes and batched embeddings |
| `supabase/migrations/` | Versioned schema and database access controls |

## Security and cost controls

- Row Level Security is enabled for every database table, with public roles denied access. FastAPI is the only database client.
- Missing or malformed security configuration fails closed with a generic `503`; there is no insecure fallback.
- Retrieval considers only documents explicitly marked `approved`.
- A strict CSP, HSTS, `X-Frame-Options`, and `Permissions-Policy` are applied to public responses.
- The frontend renders server and user data only through DOM APIs and `textContent`; static regression tests forbid `innerHTML` and related unsafe APIs.
- The paid-call budget covers Voyage and Anthropic calls independently of browser quota and IP limits.
- `/docs`, `/redoc`, `/openapi.json`, and the document catalog endpoint are unavailable publicly.
- Secrets and source documents are excluded from Git; `documente_noi/` remains ignored.

## Local setup

Requires Python 3.12 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Tests

```powershell
python -m pytest -q
```

At commit `74ccec6`, the local/mock-first suite passed with **533 passed, 11 skipped**. Default tests do not read `.env` and do not call Anthropic, Voyage, or Supabase. Tests requiring local, gitignored source documents skip automatically when those files are absent.

## CI

For every push and pull request targeting `main`, GitHub Actions runs (`.github/workflows/tests.yml`):

- the full pytest suite;
- `pip-audit` against `requirements.txt` for known dependency vulnerabilities.

Dependabot checks Python dependency updates weekly. These checks run without application secrets or paid provider calls.

## Cost-free ingestion validation

```powershell
python populare_db.py --dry-run
```

This validates metadata and chunking, including embedding batch construction, without calling Voyage or modifying Supabase.

## Local API startup

Local API execution requires locally configured environment variables. See `main.py` for `DB_*`, `VOYAGE_API_KEY`, `ANTHROPIC_API_KEY`, and `ANONYMOUS_*`; no secret belongs in Git.

```powershell
python -m uvicorn main:app --reload
```

## Current status

- The public application is live. The verified production deployment is merge commit `47a6133` from `main`.
- The current catalog contains 10 explicitly approved documents; the repository does not claim a current indexed-fragment total.
- Explicit document references and approved document codes resolved from conversation context restrict semantic retrieval. A scoped miss becomes `not_found`; it never falls back to global retrieval.
- Requests to perform engineering calculations or project sizing are rejected server-side before retrieval, Voyage, or Anthropic.
- Known deferred work includes controlled external testing, physical cleanup scheduling for expired rate-limit records, an independent security review, and the future import of the complete P 118/2-2013 base text. Until then, only its approved amendment content is available.
- Browser quota is cookie-based. Deleting the cookie resets the quota; this is an accepted MVP limitation.

## Additional documentation

- `PLAN.md` — product objective and phases.
- `TASKS.md` — task handoffs and delivery history.
- `docs/HYBRID_SEARCH_SPEC.md` — detailed retrieval and API contract.
- `docs/DECISIONS.md` — approved product and technical decisions.
- `DEPLOYMENT.md` — production runtime configuration and deployment safeguards.
