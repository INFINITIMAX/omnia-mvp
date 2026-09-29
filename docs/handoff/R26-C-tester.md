# R26-C — Tester: proveniența modificărilor în citare

Worktree `D:\Omnia-MVP-r26`, branch `feat/r26-p118-consolidat`, commit coder `f7e209e` (+ planner: hash-uri CSP recalculate, comentariu corectat — marcajul e pe **rând propriu după** textul modificat, nu la început). Citește `R26-C-coder.md`, `R26-C-coder-raport.md`, `R26-spec.md`.

## Starea verificată de planner
`python -m pytest -q` → **18 failed**, 1251 passed, 30 skipped. Eșecurile: teste care verifică schema exactă a citării (`test_api_integration.py` 15, `test_citation_passages.py` 2) și `test_ui_static.py::test_raspuns_si_citari_randate_prin_textcontent`. Cauza așteptată: câmpul nou `modificari`.

## Sarcina
1. Actualizează testele existente la schema nouă (`modificari` = `[]` când dovada nu are marcaj). Nu slăbi nicio altă aserțiune (D20/D22/D26). Dacă un test pică din alt motiv, raportează bug suspectat.
2. Teste noi:
   - marcaj în dovada citată → `PublicCitation.modificari` conține textul fără paranteze; mai multe marcaje identice → o singură intrare; marcaje diferite → ordinea apariției; toate cele trei variante (Text modificat / Text introdus / Abrogat);
   - marcaj doar în **altă** dovadă (necitată) → nu apare la citarea curentă;
   - text asemănător dar invalid (alt format, lipsă „publicat în”, fără paranteze) → ignorat;
   - marcaj pus de model în `raspuns`/`pasaje` dar absent din dovadă → nu apare (derivat server-side);
   - `/intreaba` expune `modificari` ca listă JSON;
   - UI static: randarea lui `modificari` folosește doar `createElement`/`textContent`; hash-urile CSP din `main.py` corespund blocurilor `<script>`/`<style>` curente din `index.html` (dacă există deja un test pentru asta, verifică doar că trece);
   - promptul conține regula 11.
3. Scrii doar în `tests/`. Nu rula comenzi. Fiecare test nou poate pica (spune ce schimbare de cod l-ar rupe). Raport: `docs/handoff/R26-C-tester-raport.md`.
