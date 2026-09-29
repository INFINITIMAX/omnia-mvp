# R26-C — Coder: proveniența modificărilor în citare (D27)

Worktree: `D:\Omnia-MVP-r26`, branch `feat/r26-p118-consolidat`. Context: `docs/handoff/R26-spec.md`. Un alt coder lucrează în paralel pe `extragere_mo_bis.py`, `diacritice.py`, `populare_db.py` — nu le atinge.

## Contextul deciziei (aprobat de Lucian 28-09-2026, devine D27)
P 118/2 și P 118/3 vor intra în bază **consolidate**: textul articolelor modificate prin Ordinele 6026/2018 și 6025/2018 înlocuiește textul vechi. Ca citarea să rămână onestă, fiecare text modificat/introdus/abrogat conține în dovadă (chunk) un **marcaj fix**, pus de planner la începutul textului afectat, de forma exactă:

```
[Text modificat prin Ordinul nr. 6.025/2018, publicat în Monitorul Oficial nr. 977 din 19.11.2018]
[Text introdus prin Ordinul nr. 6.026/2018, publicat în Monitorul Oficial nr. 966 din 15.11.2018]
[Abrogat prin Ordinul nr. 6.026/2018, publicat în Monitorul Oficial nr. 966 din 15.11.2018]
```
Regex de referință: `\[(Text modificat|Text introdus|Abrogat) prin Ordinul nr\. [0-9.]+/\d{4}, publicat în Monitorul Oficial nr\. \d+ din \d{2}\.\d{2}\.\d{4}\]`

## Sarcina
1. `generation_core.py`: `PublicCitation` primește câmpul `modificari: tuple[str, ...] = ()` — marcajele distincte (textul dintre paranteze drepte, fără paranteze), în ordinea apariției, găsite în `Evidence.content` al dovezii citate. Derivat **server-side** din dovadă, nu din răspunsul modelului. Fără marcaj → `()`.
2. Promptul: o regulă scurtă — dacă o dovadă conține un astfel de marcaj, răspunsul menționează că prevederea are textul modificat/introdus/abrogat prin ordinul respectiv. Nu schimba celelalte reguli.
3. `main.py`: `CitationResponse` expune `modificari: list[str]` (gol implicit). Atenție: `from_public` face `cls(**citation.__dict__)` — asigură tipul listă.
4. `static/index.html`: în lista „Surse citate”, pentru fiecare citare cu `modificari` nevid, afișează sub citat câte un rând mic cu textul marcajului (ex. „Text modificat prin Ordinul nr. 6.025/2018, publicat în Monitorul Oficial nr. 977 din 19.11.2018”). **Numai** `createElement`/`textContent` (regula anti-XSS din proiect; testele statice interzic `innerHTML` etc.). Stil discret, coerent cu restul listei.
5. CSP: modificarea `<script>`/`<style>` din `index.html` schimbă hash-urile din `main.py` (`_CSP_SCRIPT_HASHES`, `_CSP_STYLE_HASHES`, ~linia 519). Nu poți rula comenzi: lasă hash-urile vechi și scrie în raport exact ce blocuri ai modificat — planner-ul recalculează și actualizează hash-urile.

## Constrângeri
- Nu atinge `retrieval_core.py`, `chunking_core.py`, `retrieval_eval.py`, `supabase/`, `.env`, `documente_noi/`, fișierele coder-ului paralel.
- Contractul D20/D22/D26 rămâne neschimbat (pasaj literal verificat, ≥1 citare, `gasit`).
- Nu rula comenzi, nu scrie teste. Raport: `docs/handoff/R26-C-coder-raport.md`.
