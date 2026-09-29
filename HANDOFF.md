# NormativAI — current state and next actionable steps

## START AICI — pagina de predare pentru orice agent nou (29-09-2026, EET)

Citește în ordine: această secțiune → `docs/DECISIONS.md` (D23–D27 sunt cele recente) → `TASKS.md` (index) → `AGENTS.md` (roluri). Secțiunile de mai jos („Updated: 25-09-2026”, „§0 27-09-2026”) sunt **istoric**.

### Stare live
- Producție: `https://normativai.ro`, Railway, **main `1dc9be0`**, deploy 29-09 pe `ce4ebee` (R28 a schimbat doar importul, nu runtime-ul). Health: `/health`, `/health/db` (SELECT 1, cache 60 s), `/health/provideri`.
- **11 normative `approved`**: P 118/1-2025, P 118/2-2013 și P 118/3-2015 (consolidate cu Ordinele 6.026/2018 și 6.025/2018, D27), I5-2022, I7-2011, I9-2022, NP 004-03, NP 010-2022, NP 015-2022 (`spitale_2022`), NP 057-02, NP 091-2003. `disabled`: `i13_2015_modificari`, `p118_2_2013_modificari` (doar ordine de modificare, D23).
- Evaluare (`evaluare/set_aur.json`, **36** de întrebări, versiune 1): căutare **34/36** (rămân NP015-03 sub prag și NEG-04 — acceptate, D25); generare: 0 erori, toate răspunsurile cu citate literale, refuz corect fără dovezi (D26).
- Citarea are câmpul `modificari` („Text modificat prin Ordinul nr. …”) pentru textele consolidate (D27).

### În lucru / următorul pas
- **Niciun task în lucru.** Ultimul: R28 (PR #33) — `PATTERN_TITLU_ANEXA` acceptă `ANEXA NR. N` / `Nr.` / `14bis`, anexele P 118/2 sunt regiuni proprii (Anexa 33 → `ANEXA 33.33.x.`); P 118/2 reimportat (1840 chunk-uri); evaluare căutare 34/36.
- Idei de backlog (nedecise): numerotarea „(A).2.” din NP 057; PR-urile dependabot (atenție la `anthropic` major); I 13-2015 complet (textul de bază lipsește).

### Regulile globale ale lui Lucian (rezumat — sursa completă e în afara repo-ului)
Sursa: `~/.claude/CLAUDE.md` și `~/.agents/` pe calculatorul lui Lucian; un agent pornit în altă parte nu le vede, deci le respectă de aici:
- Răspunde în română, clar și concis; date `DD-MM-YYYY`, fus orar EET. Nu ghici — întreabă când e ambiguu.
- **Nimic instalat sau lucrat pe `C:\`** — proiecte, venv-uri, fișiere temporare doar pe `D:\` (excepție: configurările cerute de sistem în `%USERPROFILE%`).
- Nu afișa niciodată secrete, chei API sau valori din `.env`.
- Mașina e Windows, se lucrează în PowerShell; la etape mari se aplică disciplina `ai-native-sdlc` (intent → spec → plan → build + verificare → review → deploy gate).
- Predarea între agenți se face **prin fișiere** (`docs/handoff/`), niciodată doar în conversație; nu suprascrie și nu șterge munca altui agent fără instrucțiuni explicite.

### Cum se lucrează aici (reguli + comenzi)
- **Fluxul de 4 agenți** (planner rulează comenzi; coder/tester scriu; reviewer doar citește). Brief-uri și rapoarte în `docs/handoff/<ID>-<rol>.md`; verdictul reviewer-ului îl transcrie planner-ul integral în `<ID>-reviewer-raport.md`.
- **Fără aprobarea explicită a lui Lucian:** merge/push în main, deploy, migrații/scrieri în DB de producție, apeluri plătite (Voyage/Anthropic). Lucian a spus: fără reîncărcare automată Anthropic, fără plafon zilnic de cost, fără unealtă de import self-service (normativele se adaugă prin agent). Doar normative publicate în Monitorul Oficial (niciodată SR/SR EN/STAS, versiuni abrogate, documente doar cu modificări).
- **Deploy:** doar `scripts/deploy.ps1` (refuză main murdar/nesincronizat sau teste roșii). Agentul e blocat de classifier → Lucian rulează: `! powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:/Omnia-MVP/scripts/deploy.ps1`. Apoi test rapid pe site (ex. `D:\_scratch\omnia\smoke_r26.py`).
- **Teste:** `python -m pytest -q`. În worktree-uri, testele pe documentele reale cer joncțiune temporară: `New-Item -ItemType Junction -Path documente_noi -Target D:\Omnia-MVP\documente_noi` … apoi `cmd /c rmdir documente_noi` (întotdeauna șters după).
- **Regresia chunker-ului:** orice schimbare în `chunking_core.py` se compară cu `git show main:chunking_core.py` pe toate `documente_noi/*/extracted.txt`: documentele neatinse trebuie să dea chunk-uri **identice**, cele atinse fără cuvinte pierdute.
- **Evaluare:** cu `.env` încărcat în mediu: `python retrieval_eval.py --run --raport <json>` (căutare, câteva cenți Voyage); `--run --generare` (căutare + generare, ~1 USD Anthropic — cere aprobare).
- **Import document nou:** `documente_noi/<id>/{metadata.json, extracted.txt}` → `python populare_db.py --dry-run --document <id>` → `python populare_db.py --document <id>` (DB + Voyage, status `indexed_pending_validation`) → aprobare prin migrare SQL în `supabase/migrations/` (model: `20260929120000_approve_p118_2_si_p118_3.sql`), aplicată după aprobarea lui Lucian.
- **Reimport document aprobat:** `python reimport_approved.py --document <id>` (dry-run + poarta D24) → `--commit` (backup automat în `backups/`, `--restore <fișier>` pentru revenire).
- **Normative cu ordine de modificare:** `extragere_mo_bis.py` (PDF-uri „MO bis”, glife din `font_maps/mo_bis_glyph_map.json`) → `consolidare_normative.py --baza --ordin --manifest --iesire --raport` (manifestul JSON explicit per ordin, fail-closed; `corectie_tipar` doar cu justificare).
- **Pană a classifier-ului** (comenzile nu primesc verdict): nu insista; programează o reluare (CronCreate) și oprește-te.

### Date și unelte în afara Git (pe disc, nu le șterge)
- `D:\Omnia-MVP\documente_noi\` — PDF-urile oficiale, `extracted.txt`, `metadata.json`, pentru P 118/2 și P 118/3 și `baza.txt`, `ordin_*.txt`, `manifest_*.json`; `_reports/` rapoarte de reimport; `_on_hold_*` / `_rejected` = documente respinse cu motiv.
- `D:\Omnia-MVP\backups\` — backup-uri de reimport (embeddings incluse).
- `D:\Omnia-MVP\posibil_normative\` — arhiva veche a lui Lucian (exclusă local din Git prin `.git/info/exclude`); majoritatea documentelor sunt abrogate sau standarde.
- `D:\_scratch\omnia\` — scripturi ajutătoare: `db_ro.py` (interogare DB **read-only**, SQL pe stdin), `smoke_r24.py`/`smoke_r26.py` (test rapid pe site), `r26/diag.py` (diagnostic consolidare), rezultatele evaluărilor (`r26/eval_*.json`), `R26-status.md`.

---

Updated: **25-09-2026** (EET). Rewritten after a 10-day documentation gap (previous version dated 11-09-2026, but `main` had advanced through 15-09-2026 without a matching handoff). This version is a **read from git history + fresh host verification**, not a new implementation session.

## 0. Update 27-09-2026 — read this first

Sections 1–8 below describe 25-09-2026 and are kept as history.

- **Production = `main` `f5fbbc1`**, Railway deployment `15cbb8b7` (`SUCCESS`, 27-09-2026). Checks: `/health`, `/`, `/termeni`, `/confidentialitate` 200; `/docs`, `/openapi.json` 404; CSP/HSTS/X-Frame-Options present. One approved real `/intreaba` smoke: 200, answer per normative for 7 documents, literal quotes of 43–254 characters.
- **Merged 27-09 (all with green CI):**
  - PR #10, R11: 15-09 citation relaxations reverted, prompt asks for one sentence; see `docs/handoff/R11-pilot-raport.md`.
  - PR #11, R08: consecutive split chunks accepted; 292 split articles existed in `approved` documents.
  - PR #12, R12: prompt rule 8, answer per document and flag conflicts (Lucian's product intent); rule 9, missing formulas/tables/figures are not reconstructed; the R05 runner applies the calculation gate.
  - PR #13, D23: amendment-only `i13_2015_modificari` and `p118_2_2013_modificari` → `disabled`. Applied by Lucian in the Supabase SQL Editor; verified 9 `approved` / 2 `disabled`.
- **Open, in order:** recursive folders in `documente_noi/`; chunker stores section headings as articles; import policy for amended normatives; R08 semantic route (top-k gaps, evidence order); AutoCAD extension.
- **Tests:** `main` suite passes in CI (pytest + pip-audit) for every merged PR.
- **Tooling note:** the auto-mode classifier blocked production DB writes and some production reads from the assistant; Lucian ran those himself (`!` prefix or SQL Editor). `railway up` ran from the assistant on 27-09 after Lucian's explicit approval.

## 1. The short version

> **Correction after the Opus audit (R10, same day):** see `docs/handoff/R10-audit-complet-opus-raport.md`. Most important: the citation contract on `main` was changed on 15-09 (`1091bb8`, `6888902`) without a written decision — the tool schema no longer has `pasaje`, so the public quote is the first ~600 characters of the chunk. That contradicts D20/D22/R06 as written in `docs/DECISIONS.md`. The "D20/D22 live" claims below describe the approved contracts, not current `main` behavior. Also: D18 **is** confirmed merged (`fa82e31`, merge `762fe34`); R09 overstated R08's production impact.

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
- **D18 (13-09-2026):** operator-confirmed metadata for manual preflight — merged into `main` (`fa82e31`, merge `762fe34`), confirmed by the R10 audit.
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
