# R24 — Raport reviewer (transcris integral de planner)

VERDICT: APROBAT

Am verificat R24 comparând D:\Omnia-MVP-r24 (branch feat/r24-limita-refuz) cu D:\Omnia-MVP (main, 45a82db), punct cu punct conform R24-reviewer.md.

## 1. Coder (generation_core.py, main.py, docs/DECISIONS.md)

Diff generation_core.py vs main confirmă exact ce cere brief-ul + Runda 2:
- `MAX_ANSWER_TOKENS`: 1200 → 2000 (linia 13), nicio altă limită atinsă.
- `_decode_payload` (linia 271-274): schema acceptată e exact `{"raspuns","pasaje","gasit"}`; `type(payload["gasit"]) is not bool` — verificare strictă pe tip, `0`/`1`/`1.0` corect respinse (nu doar `isinstance`, care ar lăsa boolii subclasă-de-int să treacă).
- `_generate_validated` (linia 240-243): verificarea `gasit` e mutată înaintea oricărei citiri din `raspuns`/`pasaje` — cu `gasit=False` întoarce direct fără să valideze conținutul, exact soluția Runda 2 (elimină 503 pe refuz onest).
- `generate()` (linia 200-211): `gasit=false` pe prima încercare → `not_found` direct, fără retry; `gasit=true` neschimbat (D20/D22 intacte: pasaj literal verificat linia 297-298, ≥1 citare obligatorie linia 400-401); retry care revine cu `gasit=false` → tot `not_found`, nu excepție.
- Prompt: schema JSON (regula 6) și regula nouă 10 explică semantica gasit=false/true, coerent cu codul.

main.py: `_TOOL["input_schema"]` are `"gasit"` în `required` și `properties` (tip boolean, linia 290, 304-307) — diferența față de main e minimă și corectă. Ruta `/intreaba` (linia 945-951): `generated.status == "not_found"` → mapează la `status="not_found", raspuns=_NOT_FOUND, citari=[]`, identic cu ramura not_found de la căutare; `connection.commit()` rămâne după toate ramurile (linia 959) — cota se consumă normal, apelul plătit deja a avut loc. Nicio scurgere a textului modelului pe ramura gasit=false (conținutul nu mai e citit deloc, cf. mai sus).

docs/DECISIONS.md: D26 conține atât textul original cât și paragraful „Runda 2” cu motivul, decizia și ce rămâne eroare de validare — complet și coerent cu codul.

Fișiere interzise (retrieval_core.py, chunking_core.py, retrieval_eval.py, static/, supabase/, .env, documente_noi/) — verificate, neatinse (singurele apariții ale „gasit” în chunking_core.py/retrieval_eval.py sunt cod preexistent identic cu main, nelegat de D26).

Bug de producție semnalat de tester (`grounding_eval.py::evaluate_case` fără cheia `gasit` în payload-ul `FixedGenerator`) — verificat: planner l-a corectat deja (linia 234, `"gasit": True`), minim și corect, nu atinge altceva din fișier.

## 2. Tester (tests/)

Nicio aserțiune D20/D22 slăbită — verificate direct: `test_gasit_true_fara_citare_ramane_eroare_ca_inainte` (MissingCitationError intact), pasajul literal rămâne verificat neschimbat pe ramura gasit=true.

Teste noi verificate individual, toate cu condiție de eșec clară și specifică (niciunul „trece mereu”):
- `test_gasit_lipsa_este_eroare_de_validare_fail_closed`, `test_gasit_cheie_in_plus_este_eroare_de_validare` — pică dacă schema devine permisivă.
- `test_gasit_neboolean_este_eroare_de_validare_fail_closed` parametrizat cu `0`, `1`, `1.0`, `"true"`, `"false"`, `None` — acoperă exact riscul „bool e subclasă de int” semnalat în brief.
- `test_gasit_false_devine_not_found_fara_citari_chiar_daca_pasaje_sau_raspuns_incalca_regulile` + echivalentul din test_citation_passages.py (`..._gasit_false_ignora_pasaje_malformate...`) + din test_api_integration.py (`..._200_cu_cota_consumata_nu_503`) — acoperă exact scenariul NEG-04/Runda 2, la trei niveluri (unit, citation-schema, integrare HTTP completă cu verificare cotă și un singur apel).
- `test_reincercarea_care_revine_cu_gasit_false_este_refuz_not_found_nu_eroare` — folosește un fake secvențial (`RawSequenceFake`) care aruncă `AssertionError` la al treilea apel, deci verifică explicit absența buclei; pică corect dacă retry-ul nu se oprește la refuz.
- `test_schema_toolului_anthropic_cere_gasit_boolean_obligatoriu` — verifică `required` + tip, pică dacă schema Anthropic redevine opțională pe `gasit`.
- `test_max_answer_tokens_implicit_este_2000` — pică dacă limita revine la 1200.

Nu am găsit teste redundante sau aserțiuni de tip `toBeDefined`-echivalent (`assertTrue`/`is not None` fără verificare de valoare) pe cazurile noi. Acoperă toate punctele 2.x din R24-tester.md, inclusiv bordercase-urile din enumerare.

Punctele nedecise de tester (interacțiune truncated+gasit=false, gasit lipsă nested — nu se aplică, gasit e doar top-level) sunt raționate corect ca fiind acoperite indirect sau nerelevante; nu constituie o gaură de acoperire, sunt de acord cu raționamentul.

## 3. Fix planner grounding_eval.py
Minim (o singură linie adăugată, `"gasit": True`), corect, nu atinge restul fișierului.

## Concluzie
Nu am găsit cod în plus față de brief, bug-uri de logică, abateri de convenții, fișiere interzise atinse sau teste inutile/slabe. Runda 2 e implementată corect: verificarea `gasit` mutată înaintea validării conținutului, deci un refuz onest nu mai poate produce 503, exact scopul declarat.

APROBAT — fără condiții.

---

## Decizia planner-ului (28-09-2026)
Accept. R24 gata de PR, împreună cu R23. Merge în main și deploy doar după aprobarea explicită a lui Lucian.
