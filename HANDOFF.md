# NormativAI — current state and next actionable steps

Updated: **11-09-2026** (EET). This is a handoff, **not a claim that D11 or production readiness is complete**.

## 1. The short version

- **Completed locally:** the synthetic grounding evaluator (5A) and verified citation passages (R06). QA and Reviewer approved both local slices.
- **P1 exact-article remediat local:** articolul nemarcat/marcat după cod complet ajunge din nou la exact lookup, iar anul 2099 rămâne fail-closed. Host: 105 focused și 962 full passed/11 skips. Re-review P1 este încă necesar.
- **Fresh GREEN:** 515 focused passed; full suite 863 passed/11 corpus skips/0 failures. R05 diagnostic remains 19 cases/10 findings/exit 1 intentional.
- **Still wrong:** authentic quotes can accompany unsupported claims. D11 fixes retrieval routing, not semantic claim truth.
- **Last GitHub checkpoint:** `d0f457ee15a51111cfec9d691f84f14e6da6f406` contains RED tests. The GREEN runtime diff is currently uncommitted pending independent review.
- No live DB/provider calls, merge or deployment were made.

## 2. Where the work is

| Item | Location / state |
|---|---|
| Working directory | `D:\Omnia-MVP-stabilizare` |
| Working branch | `fix/stabilizare-coduri-normative` |
| Base | `237e11db81251b8eb316ec02aa01e428089c66bc` |
| Current local HEAD | `d0f457ee15a51111cfec9d691f84f14e6da6f406`; D11–D14 runtime/test migration is uncommitted pending QA/Reviewer. |
| Git checkpoint | `d0f457ee15a51111cfec9d691f84f14e6da6f406`, pushed to `origin/fix/stabilizare-coduri-normative`; this is intentionally RED. |
| Last recorded production SHA | `47a61339037c941e97f136686832142b8e1ac8e6`; production was **not rechecked** for this handoff. |
| Complete issue register | [revizii.md](revizii.md): 28 findings, approved decisions, remediation steps and production gates. |
| Approval source | [docs/DECISIONS.md](docs/DECISIONS.md) |
| Current task / acceptance checks | [TASKS.md](TASKS.md), [GATES.md](GATES.md) |
| Beginner explanation of R06 | [docs/R06_CODE_WALKTHROUGH.md](docs/R06_CODE_WALKTHROUGH.md) |

## 3. What we have

### Existing foundation — retain it

FastAPI/Python, PostgreSQL/pgvector retrieval, approved-document filtering, official citations, calculation refusal, anonymous quota/rate limiting and provider-call budgeting. Keep the architecture; no rewrite or new orchestration framework is approved.

The importer status-reconciliation fix and automatic-worker code are already in the repository base. **The worker stays inactive:** no permanent worker or logon task. The worker SHA migration remains unapplied according to the recorded handoff. A safe single-PDF manual import route is still missing.

### Completed local stabilization

| Deliverable | What improved | Important limit |
|---|---|---|
| 5A evaluator | 19 reproducible, fictitious fixed-output cases distinguish unsupported claims, bad citations and missing passages. | Not live-model accuracy or human-expert validation. |
| R06 citation passages | Model supplies a passage; backend verifies literal occurrence in the corresponding evidence and owns public metadata. | A genuine passage does not prove that it supports every claim. |
| R06 failure handling | Invalid passage/payload returns 503 with checked quota rollback; no retry caused by that failure. Valid complete truncated JSON retains the existing warning. | Already consumed provider cost and rate/budget accounting are not undone. |
| Verification | Historical RED: 133 failures / 18 passes before the fix. Focused GREEN: 402 passes. Independent QA and Reviewer: OK. | Approval is local, not deployment authorization. |

The R06 internal JSON format, 600-character citation limit and existing 1200-token generation ceiling are documented. Passages use some of those output tokens; real-model adherence, cost and truncation effects remain unmeasured.

### Fresh checks run for this handoff

- Focused D11 verification: **515 passed**, zero failures/errors.
- Full suite: **863 passed, 11 skipped, zero failures/errors**. The skips require absent local corpus fixtures.
- Diagnostic: **19 cases, 19 fake calls, 17 publications, 2 structural refusals; 10 unsupported candidates accepted; zero missing passages/valid rejections/execution errors**. Exit 1 is intentional and not a live error rate.
- Host snapshot protection confirms only authorized D11 Python seams changed; R06/5A inputs and runtime files are protected.
- `git diff --check` passed; zero staged files at preflight. QA/Reviewer still pending.

## 4. The latest task: D11 multi-document search

**Lucian's approved intent:** search all approved documentation by default and combine relevant evidence. Conversation history helps interpret the question; previously cited document codes must not silently restrict the next search. A document mention alone is not a request for exclusivity.

Explicit restrictions still matter. We want multi-source answers, not incorrect source attribution or silent substitution when a user requests a particular source/article.

**Current local code implements this policy:** slash aliases; global semantic default; no hard filter from mentions/history; comparisons of distinct documents; finite current-question phrases `doar/numai/exclusiv din [cod]`; known-code scoped retrieval without global fallback; absent code as `ambiguous_reference` before dependencies; exact `nu doar din [cod]` global guard. History remains in embedding even for scope.

RED evidence: 42 failures/35 passes for D11–D13, then 5 failures for D14/history. GREEN: 515 focused and 863 full passes. D11 gates are **7/8 met**; only independent QA/Reviewer and final handoff remain. D02/D03, other negations, multiple restrictions and UI replay remain outside this slice.

## 5. GitHub snapshot — checked 11-09-2026

- Remote: `https://github.com/INFINITIMAX/omnia-mvp.git`.
- `origin/main` este **exact** `237e11db81251b8eb316ec02aa01e428089c66bc`, identic cu baza acestui worktree. Nu există schimbări remote de integrat.
- Branch-ul local `fix/stabilizare-coduri-normative` pornește din acel SHA și are checkpoint-ul RED `d0f457e` împins pe GitHub. Nu am făcut fetch/pull/rebase/merge; push-ul nu schimbă `main` sau producția.
- Există cinci PR-uri Dependabot deschise (#1–#5), independente de D11. Nu le-am actualizat/îmbinat.

## 6. Immediate next steps — in order

1. Run read-only QA and independent review on the exact local runtime diff.
2. Resolve only concrete review findings with the same Coder, rerun affected host checks, then update the handoff/gates.
3. Commit and push the verified GREEN increment; it remains a branch checkpoint, not merge/deploy.
4. Later, decide D02/D03 separately: ambiguous article follow-ups, other negations/multiple restrictions, persistence of scope and UI history replay.

## 7. After D11 — remaining product work

| Priority | Action | Evidence required |
|---|---|---|
| Answer correctness (R05) | Prepare real questions with manually checked answers/citations, approve the evaluation budget, measure the current system, then approve a targeted protection. | Real-corpus/model results; not only green synthetic tests. |
| Conversation/history | Resolve remaining exact follow-ups, unknown references, reopening and clearing history; verify in a browser. | Approved scenario matrix and end-to-end conversation checks. |
| Corpus integrity | Inventory actual approved documents/chunks; inspect missing/duplicate articles, extraction and text-hash idempotency. | Explicitly approved DB/corpus audit; the historical “10 documents” is not a current inventory. |
| Manual ingestion | Deliver one PDF → local validation → separately approved DB/Voyage import → pending status → separate public approval. | Tested safe import/update behavior; no watcher or implicit approval. |
| Operations/privacy/legal | Verify timeouts/TLS, grants/proxy handling, budget accounting, retention/cleanup, privacy wording, PDF-library/corpus rights, backup restore and rollback. | Approved values, working runbooks and demonstrated recovery. |
| Release | Review the actual candidate changes, close applicable production gates, obtain publication approvals and run post-deploy checks. | Exact candidate SHA, CI/reviews, authorized release and smoke evidence. |

The separate review of the initial documentation lot also remains open. **No production gate is closed by this handoff.**

## 8. Commands and evidence

Safe existing local checks, from PowerShell:

```powershell
Set-Location 'D:\Omnia-MVP-stabilizare'
python -m pytest -q
git diff --check
```

Only **after the new test file exists**:

```powershell
python -m pytest -q tests/test_multi_document_retrieval.py
python -m pytest -q tests/test_retrieval_core.py tests/test_multi_document_retrieval.py tests/test_api_integration.py tests/test_citation_passages.py
```

Evidence root: `C:\Users\Lucian-PC\AppData\Local\Temp\normativai-stabilizare-237e11d\`.

- `handoff-11-09-2026/`: fresh full-suite and diagnostic logs, JSON/JUnit, command/exit receipts and `verification.json`.
- `multi-document/`: pre-D11 snapshots, authorization, RED/GREEN receipts/logs, evaluator-after-D11 evidence and host `verify.py`. Do not rerun baseline mode over the saved baseline.
- `r06/`: reviewed snapshots, RED/GREEN evidence and supplemental API/QA checks.

Temporary evidence can expire. This Markdown preserves the conclusions; if artifacts disappear, rerun the applicable checks rather than inventing evidence. Never include `.env`, secrets, PDF contents or extracted normative text in a commit or public handoff.

**CV value:** measurable regression work, source provenance and explicit safety/cost boundaries—not claiming factual accuracy merely because citations and tests are valid.
