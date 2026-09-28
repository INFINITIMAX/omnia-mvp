# R23 — Raport reviewer (transcris integral de planner)

VERDICT: APROBAT

Am comparat D:\Omnia-MVP-r23-gen\retrieval_eval.py cu D:\Omnia-MVP\retrieval_eval.py (main, 45a82db), citit R23-coder.md (rundele 1-3), R23-coder-raport.md, R23-tester.md, R23-tester-raport.md, tests/test_retrieval_eval.py (secțiunea nouă „7. Generare (R23)”), generation_core.py, main.py (mapările API din /intreaba) și evaluare/set_aur.json.

## 1. Cod coder (retrieval_eval.py)

Diff față de main: singurul fișier atins, exact ce spune raportul. Fără --generare, `run_evaluation` nu introduce nicio cheie nouă în `evaluated`/`public_case`/`sumar` (blocul de generare e complet condiționat de `generation_service is not None`) — am verificat linie cu linie, comportamentul vechi (load_gold_set, _CountingEmbedder, _score, _is_correct, _build_summary, main()) e identic byte-cu-byte cu versiunea din main, cu excepția adăugărilor aditive (MAX_GENERATION_CALLS, argumentul --generare, parametrii noi cu default-uri care nu schimbă apelul existent).

Verificări specifice:
- `--generare` fără `--run` → exit 2, `generare_requires_run`, verificat înaintea oricărei conexiuni DB/embedder/generator — corect, nu se poate ajunge la cost.
- Clasificarea `rezultat_final`: `refuz_cautare` (status în `_REFUSAL_STATUSES`, inclusiv `out_of_scope`), `raspuns`, `refuz_generare_unsupported` (UngroundedReferenceError), `refuz_generare_not_found` (GenerationResult.status == "not_found", ramură adăugată de planner în commit 0c0e994, nu de coder), `eroare_generare:<Clasa>`. Toate coerente cu ce descrie R23-coder.md rundele 1-3.
- Distincția critică din Runda 2 — `ProviderUnavailableError` cu `__cause__ is None` (răspuns Anthropic invalid/trunchiat la max_tokens, din `main.AnthropicTextGenerator._validated_tool_response`, care nu face `raise ... from`) vs. cu `__cause__` setat (eșec real de rețea/credit, `raise ... from error`) — am verificat în main.py că exact asta se întâmplă (liniile ~327-341): primul caz nu oprește rularea (devine `eroare_generare:ProviderUnavailableError`, 503), al doilea se repropagă și oprește rularea. Logica din `_run_generation` (liniile 264-273 din retrieval_eval.py) reflectă corect acest contract.
- `_vizibil_utilizator`: mapează `refuz_generare_unsupported`→200/`unsupported_answer`, `refuz_generare_not_found`→200/`not_found`, `eroare_generare:*`→503/None, altfel None. Am verificat maparea `unsupported_answer` și `not_found` în main.py (liniile 910-946): sunt statusurile publice reale ale API-ului `/intreaba`. Notă (nu blocantă, doar informativă pentru planner): în main.py actual, ramura `else` care apelează `GenerationService.generate` (liniile 922-946) nu verifică deloc `generated.status` — presupune mereu "answered". Deci `refuz_generare_not_found` modelează un comportament care nu există încă live în main.py (branch D26, cum notează corect handoff-ul reviewer-ului); textul `_NOT_FOUND` coincide cu cel din `generation_core.GenerationResult` ("Nu am găsit această informație..."), deci maparea e coerentă ca design anticipat, nu ca stare curentă verificabilă în producție. Nu e un motiv de respingere — brief-ul cere explicit doar coerență, nu conformitate cu main.py curent.
- Eroare de provider/DB la căutare oprește rularea (neschimbat); eroare de generare invalidă nu oprește rularea — confirmat în cod și în dovezile planner-ului din raport (Runda 2/3: rulare reală cu 3× `eroare_generare:ProviderUnavailableError` care nu a oprit rularea).
- Fără chei/secrete în raport: `citat` tăiat la 300 caractere înainte de a intra în `public_case["citari"]`; textul intern `content` al `Evidence` nu ajunge niciodată în raportul serializat (confirmat și de testul tester-ului, vezi mai jos).
- Nu am găsit cod nenecesar față de task: import-urile sunt toate folosite (`AnthropicTextGenerator`, `ProviderUnavailableError` din main; `GenerationService`, `GenerationValidationError`, `PublicCitation`, `UngroundedReferenceError` din generation_core); `_CountingGenerator` local e justificat (plafon 30 diferit de cel hardcodat la 16 din real_grounding_eval); nu s-a atins niciun fișier interzis (generation_core.py, retrieval_core.py, main.py, chunking_core.py, real_grounding_eval.py, evaluare/set_aur.json — cu excepția I5-01 discutată separat, supabase/, .env, documente_noi/).

## 2. Teste tester (tests/test_retrieval_eval.py, secțiunea R23)

Am citit toate cele ~25 teste noi. Fiecare are o schimbare de cod concretă care l-ar pica (confirmat prin citire directă, nu doar prin descrierea din raport):
- Testele de izolare (`--generare` fără `--run`, fără generare = fără construcție de generator) folosesc fake-uri care ridică `AssertionError` dacă sunt apelate — nu pot trece "oricum".
- Testele de clasificare (`_run_generation` izolat cu `_GenerationServiceStub`) acoperă toate cele 5 ramuri (raspuns, refuz_generare_unsupported, refuz_generare_not_found, eroare_generare cu/fără cauză pentru ProviderUnavailableError, MissingCitationError) — asertează valori concrete (`==`), nu `assertIsNotNone`.
- Testele de metrici (`_citeaza_asteptat`, `_citate_literale`, `_declara_lipsa`) testează atât cazul pozitiv cât și cel negativ pentru fiecare funcție — nu sunt redundante, fiecare pereche verifică o graniță diferită (document greșit vs. articol-copil; whitespace normalizat vs. text inventat; diacritice vs. fără diacritice).
- Testele de pipeline (`run_evaluation` cu `GenerationServiceFake`) verifică non-scurgerea textului intern, tăierea la 300 caractere, distribuția sumarului pe 3 cazuri eterogene, și plafonul de 30 aplicat la nivelul apelurilor brute (inclusiv reîncercarea) — acesta din urmă e testul cel mai valoros: dovedește explicit că un singur caz cu 2 apeluri brute lovește un plafon setat la 1, deci reîncercarea internă a GenerationService nu poate ocoli plafonul.
- Nu am găsit teste redundante (fiecare test are un scop distinct) și nu am găsit teste slabe (`toBeDefined`/`assertIsNotNone` fără valoare) — toate folosesc asserții de egalitate exactă.

Gol minor (nu blocant): nu există un test de pipeline dedicat pentru `sumar["generare"]["declara_lipsa"]` (agregarea la nivel de sumar, peste mai multe cazuri) — doar funcția `_declara_lipsa` e testată izolat. Codul de agregare e trivial (`sum(1 for item in raspunsuri if item["declara_lipsa"])`), risc scăzut, dar tehnic task-ul tester (R23-tester.md, punctul 5) cerea acoperire pentru "sumarul generare (distribuție, erori pe clasă, contoare)" — `declara_lipsa` la nivel de sumar rămâne neverificat direct. Nu consider asta motiv de respingere, dar planner-ul poate cere un test suplimentar dacă vrea acoperire completă.

## 3. Set de aur (evaluare/set_aur.json, I5-01)

`versiune` a rămas 1 — corect. I5-01 acceptă acum atât `5.4` cât și `5.7` pentru "Cum se alege filtrarea aerului exterior în funcție de gradul de poluare?". Nu am acces la textul sursă al documentului I5-2022 în acest worktree (nu există fișiere sursă locale, conținutul e doar în DB), deci nu pot verifica direct din text dacă ambele articole tratează filtrarea aerului. Contextual: schimbarea a fost făcută de planner (commit 0c0e994) după o rulare reală (Runda 3, 30 de cazuri reale), nu de coder pe baze speculative, ceea ce reduce riscul unei relaxări nejustificate. Recomand ca planner-ul să confirme explicit (din propria verificare a textului normativ, dacă are acces) că art. 5.7 tratează efectiv filtrarea aerului alături de 5.4, nu doar că modelul a răspuns cu el.

## Concluzie
ACCEPT. Nu am găsit cod nenecesar, bug-uri de logică, abateri de la constrângeri, sau teste fără valoare. Cele două observații (mapare `refuz_generare_not_found` anticipată față de main.py curent, lipsă test de agregare pentru `declara_lipsa` în sumar) sunt informative, nu motive de respingere.

---

## Decizia planner-ului (28-09-2026)
- **Accept.** R23 e gata de PR.
- Maparea `not_found` anticipată: intenționată; devine reală când R24 (D26) intră în main. R23 și R24 se integrează împreună.
- I5-01: art. 5.7 era ținta inițială a setului de aur; art. 5.4 („Filtre de aer”) a fost adăugat de planner după citirea textului din DB, care leagă direct alegerea filtrării de poluarea aerului exterior. Deci nu e o relaxare pe baza răspunsului modelului.
- Test de agregare `declara_lipsa` în sumar: nu îl adaug; codul e o singură sumă, iar metrica nu decide nimic în producție. Risc acceptat.
