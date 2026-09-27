# R15 — Reviewer: reimport `approved` cu poartă automată (D24)

Worktree: `D:\Omnia-MVP-r15-reimport`, branch `feat/r15-reimport-approved`; `main` e în `D:\Omnia-MVP`.
Context: `docs/handoff/R15-coder.md` (sarcina, D24, rundele 2–3), `R15-coder-raport.md`, `R15-tester.md`, `R15-tester-raport.md`, `docs/DECISIONS.md` (D24, D23, D18), `AGENTS.md`.

Dovezi planner: `python -m pytest -q` cu `documente_noi` local → **1101 passed**. Dry-run real, read-only, pe cele 9 documente `approved`: toate trec poarta (acoperire 0,882–0,999, peste prag). Discrepanță acceptată de planner: chunk-urile invalide opresc execuția cu `invalid_chunks` înainte de evaluarea porții (fără raport, fără scriere) — echivalent ca siguranță.

## Ce verifici — scriptul va scrie în DB-ul de producție și va chema Voyage
1. **Siguranța datelor:** poate un `--commit` lăsa un document fără chunk-uri, cu chunk-uri amestecate vechi/noi sau cu chunk-urile altui document? Ordinea backup → Voyage → tranzacție e garantată? Backup-ul e complet (toate coloanele, `embedding::text`) și suficient pentru `--restore`? `--restore` poate restaura peste documentul greșit?
2. **Tranzacția:** lock advisory, `FOR UPDATE`, reverificări (`approved`, `source_key`, număr de chunk-uri), `DELETE` limitat la `document_id`, `INSERT` complet; `commit_unknown` fără retry; nicio schimbare de status.
3. **Poarta D24:** implementată exact cum scrie în `docs/DECISIONS.md`; praguri codate, nemodificabile din CLI; poarta nu poate fi ocolită.
4. **Secrete/date:** nimic din `.env` în rapoarte sau loguri; rapoartele conțin doar extrase ≤120 caractere.
5. **Cod:** reutilizarea helper-elor private din `manual_ingestion_import.py` e rezonabilă? cod inutil, duplicare, decoratorul `_un_singur_tip_de_eroare`, fix-ul „număr lipit de majusculă” din `chunking_core.py` (fals-pozitive?), mutarea `acoperire_text_brut` fără schimbare de semantică.
6. **Tester:** teste redundante sau care trec indiferent de cod; ordinea strictă e realmente verificată; testele restore și `concurrent_change`.

## Constrângeri
Read-only. Nu edita, nu rula comenzi. Întoarce verdictul APROBAT / RESPINS, cu finding-uri pe severitate (fișier:linie, dovadă), separat coder/tester, max 700 de cuvinte.
