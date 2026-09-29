# R26 — Tester, runda 2 (după review partea 1 + R26-A)

Worktree `D:\Omnia-MVP-r26`, commit `19c7f0e`. Citește `R26-reviewer-raport.md` (verdict transcris), `R26-A-coder.md`, `R26-A-coder-raport.md`.

## Sarcina — teste noi, sintetice (fără fișierele reale; cele reale doar opțional cu skip)
**A. Goluri semnalate de reviewer**
1. `chunking_core._propaga_marcaj_provenienta` (prin `creeaza_chunkuri` unde e posibil): punct împărțit pe alineate — doar o bucată are marcajul original, celelalte primesc exact `[Articol cu text modificat prin …]` pe rând propriu; articol fără marcaj → text byte-identic; două ordine/tipuri diferite pe același articol → câte un rând, deduplicat, în ordinea primei apariții; bucata care are deja marcajul original nu primește dublura.
2. `_respecta_limita_cu_marcaje`: o bucată de ~990 de caractere care primește un marcaj propagat → se re-împarte, toate părțile ≤ 1000, fiecare cu marcajul, niciun cuvânt pierdut.
3. `PublicCitation.modificari` prin `GenerationService.generate` pentru o dovadă care are doar forma „Articol cu text modificat/introdus/abrogat prin …”; întărește testul regulii 11 să verifice și „Articol cu text”.
4. `consolidare_normative`: `abroga_subunitate` (alineat și literă), inclusiv marcajul `[Abrogat prin …]` și textul vechi dispărut.

**B. R26-A (extragere MO bis)**
5. `extragere_mo_bis.harta_coduri`: semantica `/Differences` (număr → cod curent, fiecare nume incrementează; nume non-`gNNN` consumă un cod fără mapare; GID absent din tabelă → nemapat). Folosește un obiect fals pentru `fitz.open` (monkeypatch), fără PDF real.
6. `extrage_text`: `(cid:N)` rezolvat din hartă; nerezolvat → eliminat și numărat în raport cu cheia `font:cod`; normalizare diacritice aplicată; corectura planner: rândul `2 MONITORUL OFICIAL AL ROMÂNIEI, PARTEA I, Nr. 595 bis/24.IX.2013` devine două rânduri (număr, apoi antet), iar un rând fără antet care începe cu număr rămâne neatins. pdfplumber fals prin monkeypatch.
7. `incarca_tabela`: chei GID convertite la `int`; tabela reală `font_maps/mo_bis_glyph_map.json` se încarcă și conține `TimesNewRomanPSMT` 259 → `ă`, 288 → `ţ` (sedilă — normalizarea o transformă ulterior).
8. `diacritice.normalizeaza_diacritice`: `ǎ`→`ă`, `Ǎ`→`Ă`; restul comportamentului neschimbat (testele existente).
9. `populare_db --document`: filtrează după `metadata["document_id"]`, repetabil; fără argument comportament identic; în `--dry-run` se afișează acoperirea (fără DB/Voyage — verifică prin monkeypatch că nu se construiește niciun client).

Scrii doar în `tests/`. Nu rula comenzi. Fiecare test poate pica (spune ce schimbare l-ar rupe). Raport: `docs/handoff/R26-tester-runda2-raport.md`.
