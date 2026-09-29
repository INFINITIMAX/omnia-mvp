# R26 — Raport reviewer, partea 1 (transcris integral de planner)

Verdict: RESPINS (motiv: acoperire de teste, nu bug de cod)

Am citit R26-spec.md, DECISIONS.md (D27 + Runda 2), toate brief-urile/rapoartele R26-B-*, R26-C-*, R26-D-*, și codul: consolidare_normative.py, chunking_core.py (funcțiile noi din D27: _propaga_marcaj_provenienta, _respecta_limita_cu_marcaje, _aplica_limita_caractere), generation_core.py (_MODIFICATION_MARKER, regula 11), main.py (CitationResponse/CSP), static/index.html, tests/test_consolidare_normative.py, tests/test_chunking_core.py, tests/test_citation_modificari.py.

## Codul (coder-ii B, C, D) — nu am găsit cod inutil sau bug-uri de logică
Am urmărit manual traiectoria completă pentru cazurile-cheie:
- `consolidare_normative.py`: segmentarea ordinului, cele 8 tipuri de operații (inclusiv `abroga_subunitate`, `inlocuieste_sintagma_in_bloc`, `aparitie`+`justificare`), verificările fail-closed (`_verifica_final`), toate coerente cu cele trei runde de brief-uri și cu corecturile planner-ului. Nimic în plus față de brief.
- `chunking_core.py` — funcția `_propaga_marcaj_provenienta` + `_respecta_limita_cu_marcaje`: am simulat manual pe hârtie scenariul din testul existent (marcaj lângă limita de 1000) inclusiv re-split-ul după propagare — logica e corectă (fiecare bucată rezultată din re-split primește sufixul complet de marcaje „Articol cu text …”, lungimea finală rămâne ≤1000 prin construcție). Nu e cod inutil — e exact ce cerea D27 Runda 2 și „Corectura 4” a planner-ului.
- `generation_core.py`/`main.py`/`static/index.html` — `modificari` derivat strict server-side din `Evidence.content`, niciodată din răspunsul modelului; UI folosește exclusiv `createElement`/`textContent` (fără `innerHTML`); regula 11 din prompt menționează ambele forme de marcaj.

## Motivul respingerii: goluri de test exact pe punctele pe care brief-ul reviewer-ului le cerea explicit verificate

**1. `chunking_core._propaga_marcaj_provenienta` — funcționalitatea centrală a R26-D nu are niciun test.**
Fișier: `D:\Omnia-MVP-r26\tests\test_chunking_core.py`. Am căutat explicit `"Articol cu text"` / `_propaga_marcaj_provenienta` / `_respecta_limita_cu_marcaje` în tot `tests/` — zero potriviri.
Cele două teste existente (`test_marcaj_de_provenienta_nu_este_taiat_la_limita_de_1000_caractere`, linia 467, și `test_text_fara_marcaj_de_provenienta_se_taie_la_limita_ca_inainte`, linia 487) verifică **doar** că tăietura la 1000 caractere nu rupe un marcaj existent — ele testează un articol dintr-o singură bucată logică, nu scenariul propriu-zis din spec: **un punct despărțit pe alineate în mai multe bucăți (`3.3.1.(1)`, `3.3.1.(2)`, `3.3.1.(4)`), unde doar una conține marcajul original și celelalte trebuie să primească `[Articol cu text modificat prin …]`**. Acesta e chiar exemplul din `R26-D-coder.md` (P 118/3, 3.3.1) și din DECISIONS.md D27 Runda 2 — motivul pentru care a existat rundă separată de coder. Fără un test pe acest caz, o regresie în `_propaga_marcaj_provenienta` (de exemplu grupare greșită după articolul de bază, sau lipsa deduplicării pe `(adjectiv, rest)`) ar trece nedetectată prin `pytest`.
Lipsesc și: (a) test cu articole **fără** niciun marcaj care rămân byte-identice (regresie explicit cerută în task-ul D-coder-ului), (b) test cu mai multe ordine/tipuri de marcaj pe același articol (deduplicare + ordinea primei apariții — menționat explicit ca risc în raportul D-coder-ului).

**2. `generation_core._modification_markers` — forma „Articol cu text modificat/introdus/abrogat” nu e testată deloc.**
Fișier: `D:\Omnia-MVP-r26\tests\test_citation_modificari.py`. Am căutat `"Articol cu text"` — zero potriviri. Toate cele 9 teste din fișier (scrise de C-tester, înainte de runda D) verifică doar formele „Text modificat/introdus”/„Abrogat”. D-coder a extins regex-ul `_MODIFICATION_MARKER` să recunoască și forma la nivel de articol (`D:\Omnia-MVP-r26\generation_core.py:97-101`), dar niciun test nu confirmă că `PublicCitation.modificari` conține corect acest text pentru o citare a unei bucăți care are doar marcajul propagat. E exact fluxul complet D27 (chunker → citare → UI) — verigă netestată.
`test_promptul_contine_regula_11_despre_marcajele_de_provenienta` (linia 175) verifică doar substringurile „Text modificat/introdus prin Ordinul” și „Abrogat prin Ordinul”, care existau și înainte de adăugarea mențiunii „Articol cu text …” — testul ar trece identic chiar dacă acea adăugare a D-coder-ului ar fi ștearsă din prompt. Aserțiune slăbită față de ce s-a schimbat efectiv.

**3. `abroga_subunitate` — zero teste, confirmat.**
Am căutat `abroga_subunitate` în `test_consolidare_normative.py` — zero potriviri. Testerul însuși semnalase asta onest în raport („nu are test dedicat”), dar reviewer-ul o cere explicit ca punct de verificare, deci rămâne un gol de acoperire pentru un tip de operație folosit real în manifestul P 118/2/3 și nu doar „ușor de adăugat” cum spune raportul — trebuie adăugat înainte de acceptare.

## Ce nu e o problemă (verificat, nu semnalez)
- Testele existente pentru schema `modificari` (`test_api_integration.py`, `test_citation_passages.py`, `test_ui_static.py`) sunt actualizate corect, cu motive clare de eșec pentru fiecare (nu sunt „mereu verzi”).
- `test_verifica_final_*` (apelate direct pe funcția privată) — decizie transparentă și justificată a testerului (fail-closed practic irealizabil prin API-ul public cu un manifest corect); acceptabil.
- Suspiciunea de bug semnalată de tester (`segmenteaza_ordin` nu detectează singur o numerotare cu gol, fail-closed vine din `aplica_operatii`) e deja documentată clar în ambele rapoarte — nu o tratez ca blocantă, dar planner-ul ar trebui să decidă dacă vrea eroare explicită chiar în `segmenteaza_ordin`.
- Nu am găsit cod inutil în niciunul din B/C/D; toate abaterile de la brief (ex. `inlocuieste_sintagma_in_bloc` rămas neutilizat pe item 24) au fost cerute explicit de planner în rundele 2/3.
- CSP: hash-urile din `main.py` (recalculate de planner) corespund structurii curente din `static/index.html` (script/style neating altfel); UI respectă regula anti-XSS.

## Recomandare pentru planner
Nu retrimite la coder — codul e corect din câte am putut verifica manual. Retrimite la **tester** (rundă suplimentară) cu cerința explicită:
1. Teste sintetice pentru `_propaga_marcaj_provenienta` (scenariul multi-alineat din spec + regresie „fără marcaj → byte-identic” + „mai multe ordine/tipuri pe același articol”).
2. Teste pentru `_modification_markers`/`PublicCitation.modificari` cu forma „Articol cu text modificat/introdus/abrogat” (inclusiv prin `GenerationService.generate`, ca restul testelor din `test_citation_modificari.py`).
3. Întărirea `test_promptul_contine_regula_11...` să verifice explicit și mențiunea „Articol cu text”.
4. Test dedicat pentru `abroga_subunitate`.

Fișiere relevante: `D:\Omnia-MVP-r26\chunking_core.py` (liniile 787-883), `D:\Omnia-MVP-r26\generation_core.py` (liniile 93-107, 402-406), `D:\Omnia-MVP-r26\consolidare_normative.py` (liniile 470-478), `D:\Omnia-MVP-r26\tests\test_chunking_core.py` (467-499), `D:\Omnia-MVP-r26\tests\test_citation_modificari.py` (175-181), `D:\Omnia-MVP-r26\docs\DECISIONS.md` (D27 + Runda 2, linia 11).

---

## Decizia planner-ului (29-09-2026)
- Accept respingerea: codul rămâne, se retrimite la **tester** (runda 2) cu cele 4 cerințe, plus testele pentru R26-A (extragere MO bis, ǎ/Ǎ, `populare_db --document`, antetul MO cu numărul de pagină lipit — corectură planner `19c7f0e`).
- Numerotarea neconsecutivă: rezolvată deja de planner înainte de verdict (`PATTERN_INSTRUCTIUNE_ASCUNSA`, eroare în `segmenteaza_ordin`, test actualizat în `fd48768`).
- După runda de teste: review partea 2 (R26-A + testele noi).
