# NormativAI — current state and next actionable steps

Updated: **25-09-2026** (EET). Rewritten after a 10-day documentation gap (previous version dated 11-09-2026, but `main` had advanced through 15-09-2026 without a matching handoff). This version is a **read from git history + fresh host verification**, not a new implementation session.

## 1. The short version

- **`main` is at `132f7f4`** (merge commit for NP091 verified symbols), pushed to `origin/main`. Working tree clean on `main` as of this handoff.
- **D11–D22 are all accepted and live**, later than the 11-09 handoff suggested: multi-document search (D11-D14), passage verification (D20/R06), safe generation diagnostics (D21), structured Anthropic tool output (D22), and a real read-only R05 pilot run (15-09-2026, 20 real cases, 16 `answered`/4 `ambiguous_reference`, zero uncited answers).
- **Fresh host verification for this handoff:** `python -m pytest -q` → **1021 passed, 1 warning** (external `httpx`/`starlette.testclient` deprecation, not a project issue). No DB/provider calls made for this check.
- **Production** (`https://normativai.ro`): `/health` → `200 {"status":"ok"}`, verified live for this handoff (25-09-2026). Security headers present (CSP, HSTS, X-Frame-Options, nosniff, Permissions-Policy). Railway deploy is manual (`railway up`, no Git Source connected) — **the exact deployed SHA is unconfirmed**; `main` has moved since the last recorded deploy note (`4bc4973`, 13-09-2026), and nobody has re-verified which commit is actually live.
- **Repo hygiene fixed today:** 31 stale git worktrees (all already merged into `main`) and 51 stale local branches were removed. Only 5 worktrees with genuinely unmerged work remain, plus `main`.

## 2. Where the work is

| Item | Location / state |
|---|---|
| Main working directory | `D:\Omnia-MVP` (worktree for `main`) |
| Open worktrees with real unmerged work | see §3 below — 5 total |
| Untracked, never-run audit briefs | `docs/handoff/R07-operations.md`, `docs/handoff/R07-security.md` — read-only production-readiness audits, prepared but never executed or reported |
| Complete issue register | [revizii.md](revizii.md): R01–R28 findings, approved decisions, remediation steps, production gates — not re-audited for this handoff, treat as historical unless re-verified |
| Approval source | [docs/DECISIONS.md](docs/DECISIONS.md) |
| Task log (chronological, not an index) | [TASKS.md](TASKS.md) — see the new "Stare curentă" section at the top for a quick-read summary; the rest is historical predare-by-predare log, kept for traceability |
| Production gates | [GATES.md](GATES.md) |

## 3. Open worktrees — genuinely unmerged work

| Worktree | Branch | Last commit | Status |
|---|---|---|---|
| `D:\Omnia-MVP-context` | `feat/context-conversatie` | `b480584` — "wip: conserva testele API pentru context conversational" | WIP checkpoint, not confirmed active |
| `D:\Omnia-MVP-mobil-b` | `feat/mobil-varianta-b` | `793d303` — "wip: conserva varianta mobila B inainte de integrare" | WIP checkpoint, paused before integration |
| `D:\Omnia-MVP-no-calculations` | `fix/blocheaza-calcule-proiectare` | `dfead38` + **uncommitted local changes** (`.github/workflows/tests.yml`, `DEPLOYMENT.md`, `GATES.md`, `TASKS.md`, `docs/DECISIONS.md`) | Most "live" of the five, but **Lucian confirmed 25-09-2026: not resuming this branch right now** |
| `D:\Omnia-MVP-i7` | `fix/i7-glife-corupte` | `b239a72` — "wip: conserva maparea tehnica Monotype WGL4" | WIP checkpoint, paused |
| `D:\Omnia-MVP-r08-split-article-retrieval` | `fix/r08-split-article-retrieval` | `8023d1a` — "fix: accept consecutive chunks for split articles" | Real fix commit, not WIP-labeled, never merged — worth checking if still needed |

None of these five have been inspected in depth for this handoff (read-only branch/commit inspection only). Before resuming any of them, re-read their actual diff against current `main` — commits are 10+ days old and `main` has moved.

## 4. Confirmed via git history (not re-verified live) — feature timeline through 15-09-2026

In rough order, most recent first (see `TASKS.md` for full predare text per item):

- **R05 pilot, finalized operational (15-09-2026):** 20-case local manifest (8 exact, 8 semantic, 4 negative), real read-only run: 8 embeddings, 16 generations, 16 `answered` with 20 citations, 4 `ambiguous_reference`, zero uncited `answered`. Semantic content verdict remains human review; local report not in Git.
- **D22 (14-09-2026):** Anthropic returns exclusively the `return_grounded_answer` tool; structured input goes through R06, no free-text fallback/retry. Live in `main` SHA `e895605`, Railway deployment `SUCCESS`.
- **D21 (14-09-2026):** `GenerationValidationError` caught by `POST /intreaba` logs only the internal class name + a stable code — no question, model answer, evidence, provider payload, traceback, DB fields, or secrets. Public response stays generic `503`. Live in `main` SHA `42dcc52`.
- **D20/R06 (14-09-2026):** for a non-empty, ≤600-char `pasaje.citat` on a valid/used ID without literal provenance in its own evidence, the server publishes a deterministic literal excerpt from that same evidence instead. Live in `main` SHA `0261ef5`.
- **D18 (13-09-2026):** operator-confirmed metadata for manual preflight — accepted locally on `fix/manual-metadata-preflight`, not yet independently re-confirmed merged for this handoff.
- **Deploy verified (13-09-2026):** `main` published manually to Railway from SHA `4bc4973`; healthcheck + smoke passed without provider calls. **This is the last recorded live-deploy verification** — 12 days stale as of this handoff.
- **D11–D14 multi-document search:** long saga (started 11-09), finally "ACCEPTAT LOCAL" — exact-article routing fixed, QA/re-review OK, 105 focused / 962 full tests passed. The underlying branch `fix/stabilizare-coduri-normative` is confirmed merged into `main` as of today's worktree cleanup.
- **R06 final handoff + explicit STOP from Lucian (11-09-2026):** citation-passage verification closed locally; Lucian requested a stop before starting the next task.

## 5. What's NOT confirmed / open risk

- **Production SHA is unconfirmed against current `main`.** `/health` responds, but nobody has checked whether Railway is actually serving `132f7f4` or something from mid-September. Not urgent (site works), but a real gap before claiming "production reflects current work."
- **`revizii.md` (R01–R28 findings register) was not re-read for this handoff.** Treat its findings as of their last recorded status, not re-verified today.
- **The two R07 audit briefs (`docs/handoff/R07-operations.md`, `R07-security.md`) were written but never executed.** They look like a natural next step for confirming "Omnia is clean and functional" (Lucian's stated priority, 25-09-2026) before moving to the RAG ingestion check and, later, the planned AutoCAD extension work.
- **Dependabot: 5 open PRs, stale since 06-09-2026 (19 days).** One (`anthropic` 0.116.0 → 1.3.0) is a major version bump — likely has breaking API changes, needs careful review, not a routine merge.
- **The 5 open worktrees (§3) haven't been checked for whether their WIP work is still relevant** given how much has landed on `main` since they were paused.

## 6. Lucian's stated roadmap (25-09-2026)

In order:
1. **Confirm Omnia is clean and functional** — this handoff sync is part of that; the R07 audits (§5) are a natural next step.
2. **Verify the RAG ingestion path** works correctly end-to-end.
3. **Build an AutoCAD extension** so Omnia can be opened/used from inside AutoCAD.

`fix/blocheaza-calcule-proiectare` (§3) is explicitly **not** being resumed right now, despite having live uncommitted changes — Lucian's call, not a technical block.

## 7. Immediate next steps — in order

1. Merge this doc-sync branch (`docs/sync-handoff-tasks-25-09`) into `main`, with Lucian's explicit approval (per `AGENTS.md` rule 8 — no direct push to `main` without approval).
2. Decide whether to run the two prepared R07 audits (operations + security) now, as the concrete next action for "confirm Omnia is clean."
3. After that: RAG ingestion verification (scope not yet defined — needs a spec before implementation).
4. AutoCAD extension: needs its own intent/spec — completely new surface area (desktop plugin, not web), not started.

## 8. Commands and evidence

Safe existing local checks, from PowerShell, on `D:\Omnia-MVP` (or any worktree):

```powershell
Set-Location 'D:\Omnia-MVP'
python -m pytest -q
git diff --check
```

Fresh result for this handoff: `1021 passed, 1 warning` (external deprecation warning only).

Never include `.env`, secrets, PDF contents or extracted normative text in a commit or public handoff.

**CV value:** documentation-debt detection and repair (stale handoff caught against real git history), git hygiene at scale (31 worktrees + 51 branches identified as safe-to-delete via `--merged` checks, not guessed), production-vs-main drift flagged explicitly instead of assumed — the kind of operational discipline that's easy to skip and expensive to skip.
