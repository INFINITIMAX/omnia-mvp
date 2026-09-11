# NormativAI — current state and next actionable steps

Updated: **11-09-2026** (EET). This is a handoff, **not a claim that D11 or production readiness is complete**.

## 1. The short version

- **Completed locally:** the synthetic grounding evaluator (5A) and verified citation passages (R06). QA and Reviewer approved both local slices.
- **Approved, not implemented:** multi-document search by default (D11), with restrictions only when explicitly requested.
- **Latest interruption:** the Coder hit its usage limit before saving the D11 test file. No D11 runtime changes, RED results, implementation review or QA results exist.
- **Fresh verification for this handoff:** 761 tests passed, 11 skipped; all Python files still match the pre-D11 snapshot. Nothing was lost or staged.
- **Still wrong:** authentic quotes can accompany unsupported claims. The fixed synthetic diagnostic still exposes 10 such answers. R05 remains open.
- **Checkpoint GitHub:** `8ca650ec21d01142c1936712097b86ec81733188` on `origin/fix/stabilizare-coduri-normative`, `test: checkpoint R06 and multi-document RED`. It preserves a deliberately failing RED lot; it is not merged or deployed. No live DB/provider calls were made.

## 2. Where the work is

| Item | Location / state |
|---|---|
| Working directory | `D:\Omnia-MVP-stabilizare` |
| Working branch | `fix/stabilizare-coduri-normative` |
| Local HEAD / base | `237e11db81251b8eb316ec02aa01e428089c66bc` |
| Git checkpoint | `8ca650ec21d01142c1936712097b86ec81733188`, pushed to `origin/fix/stabilizare-coduri-normative`. D11–D13 is intentionally RED at this checkpoint; do not merge it. |
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

- Full suite: **761 passed, 11 skipped, zero failures/errors**. The skipped tests require absent local corpus fixtures.
- Diagnostic: **19 cases, 19 fake calls, 17 publications, 2 structural refusals**.
- **10 unsupported candidates accepted; zero missing required passages; zero valid-candidate rejections or execution errors.** Diagnostic exit 1 is intentional, not a broken evaluator. This is not a live error rate.
- All Python files match the pre-D11 snapshot; `tests/test_multi_document_retrieval.py` does not exist.
- `git diff --check` passed; zero staged files; no active subagents.

## 4. The latest task: D11 multi-document search

**Lucian's approved intent:** search all approved documentation by default and combine relevant evidence. Conversation history helps interpret the question; previously cited document codes must not silently restrict the next search. A document mention alone is not a request for exclusivity.

Explicit restrictions still matter. We want multi-source answers, not incorrect source attribution or silent substitution when a user requests a particular source/article.

**Current code does not yet implement that policy:**

1. `_ALIAS_SEPARATOR` misses `/` in official codes such as `P 118/1-2025` (R01).
2. Mentioned/cited documents can become mandatory semantic filters.
3. Mentioning two documents is automatically treated as ambiguous, even for a broad comparison.
4. Exact-article follow-ups and history replay still have separately tracked gaps (R02–R04).

The baseline, proposed scope and acceptance gates are saved. **D11 gates: 1/8 met (baseline only).** The Coder's proposed detailed diff and new RED tests were not saved. Implementation, QA and Reviewer stages were not launched.

RED a fost ulterior salvat și demonstrat pentru D11–D13: **42 failures/35 passed/0 errors**, exclusiv comportamental; runtime-ul nu a fost schimbat. D12 aprobă formele finite „doar/numai/exclusiv din [cod]”, numai pentru întrebarea curentă. D13 decide codul necunoscut: HTTP 200 `ambiguous_reference`, fără embedding/generare/global fallback/apel plătit, dar cu quota/rate limit consumate. D14 decide guard-ul exact „nu doar din [cod]”: global implicit, nu scope; alte negații rămân excluse. Codul cunoscut rămâne scoped. Capacitatea Coderului nu se presupune; nu relansăm automat.

## 5. GitHub snapshot — checked 11-09-2026

- Remote: `https://github.com/INFINITIMAX/omnia-mvp.git`.
- `origin/main` este **exact** `237e11db81251b8eb316ec02aa01e428089c66bc`, identic cu baza acestui worktree. Nu există schimbări remote de integrat.
- Branch-ul local `fix/stabilizare-coduri-normative` pornește din acel SHA și are checkpoint-ul `8ca650e` împins pe GitHub. Nu am făcut fetch/pull/rebase/merge; push-ul creează doar branch-ul de lucru, nu schimbă `main` sau producția.
- Există cinci PR-uri Dependabot deschise (#1–#5), independente de D11. Nu le-am actualizat/îmbinat.

## 6. Immediate next steps — in order

### A. Preserve the work and settle the remaining contract

1. Recheck this exact branch, HEAD, dirty files and agent state. Keep the R06 work intact. Obtain separate approval before creating a Git commit/push checkpoint.
2. Planner asks Lucian for the unresolved D01/D02 outcomes; do not let the Coder choose them:
   - An explicit restriction names an unknown/unavailable document: what message/status and quota treatment should apply?
   - A follow-up says “and article 1.1?” after several sources: when must the app clarify which document is intended?
   - A user says “only document X”: how long does that restriction persist, and how is it lifted?
3. Record the answers and the supported restriction phrases/examples in `docs/DECISIONS.md` and the D11 scenario table in `revizii.md`. Do not quietly restore the superseded automatic-scoping policy.

### B. Resume test-first implementation

4. Once Coder capacity is available, reuse the role/worktree and create `tests/test_multi_document_retrieval.py`. First cover:
   - broad questions with evidence from multiple approved documents;
   - follow-ups that retain topic context without a citation-based hard filter;
   - one document mention versus an explicit restriction;
   - broad two-document comparisons versus genuinely ambiguous aliases;
   - slash/space/part/year recognition and negative token-boundary cases;
   - exact document/article identity and explicitly restricted searches without hidden global fallback.
5. Run the new tests **before** runtime edits. Save behavioral RED failures, not import/collection failures. Planner reviews the proposed diff against the approved scenario table before authorizing runtime changes.
6. Implement the smallest change in `retrieval_core.py`. Adapt existing retrieval/API tests only where their expectations encode the superseded policy; retain the scenarios and safety checks, with a clear old/new mapping.
7. Preserve R06, evaluator inputs/gold, approved-only access, public schema, quota/rate/budget, provider-call counts and current retrieval/context/generation limits. Do not add query fan-out or force one result from every document. Eligibility across the corpus is not a promise of exhaustive coverage.

### C. Verify and hand off

8. Run the new/retrieval/API/citation tests, then the full suite. Compare against the saved pre-D11 snapshot; explain every changed test and skip. Do not close a D11 gate merely because the old suite still passes.
9. Have read-only QA check branches/test preservation and an independent Reviewer check intent, security, hidden filters and costs. Host PowerShell/Python runs the checks because the native agent bash environment has no working WSL distribution.
10. Update this handoff, `TASKS.md`, `revizii.md`, overview and gates. Report what remains of R02–R04. Deployment is a separate decision.

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
- `multi-document/`: pre-D11 code snapshots, baseline receipts and host `verify.py`. RED/GREEN receipts and runtime authorization are absent; do not assume they exist. Do not rerun its baseline mode over the saved baseline.
- `r06/`: reviewed snapshots, RED/GREEN evidence and supplemental API/QA checks.

Temporary evidence can expire. This Markdown preserves the conclusions; if artifacts disappear, rerun the applicable checks rather than inventing evidence. Never include `.env`, secrets, PDF contents or extracted normative text in a commit or public handoff.

**CV value:** measurable regression work, source provenance and explicit safety/cost boundaries—not claiming factual accuracy merely because citations and tests are valid.
