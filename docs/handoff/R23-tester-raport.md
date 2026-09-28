# R23 — Raport Tester

Am citit `R23-tester.md`, `retrieval_eval.py` complet și `tests/test_retrieval_eval.py` existent. Am adăugat teste
exclusiv în `tests/test_retrieval_eval.py` (secțiunea nouă `# --- 7. Generare (R23) ---`), fără să modific cod de
producție și fără să rulez comenzi.

## Fișiere atinse
- `D:\Omnia-MVP-r23-gen\tests\test_retrieval_eval.py` — adăugat import `MissingCitationError, PublicCitation,
  UngroundedReferenceError` din `generation_core`, plus ~25 teste noi.

## Ce verifică fiecare test nou (și ce l-ar face să pice)

**Fără `--generare` / `--generare` fără `--run`**
- `test_generare_fara_run_respinge_cu_exit_2_fara_niciun_apel` — pică dacă `--generare` fără `--run` nu mai dă exit 2,
  nu mai scrie `generare_requires_run` pe stderr, sau dacă ajunge să apeleze DB/embedder/generator (fake-urile ridică
  `AssertionError`).
- `test_fara_generare_nu_construieste_generator_si_raportul_ramane_neschimbat` — pică dacă `run_evaluation` cu
  `generation=False` totuși apelează `generator_factory` (fake ridică `AssertionError`) sau dacă raportul capătă chei
  noi (`generare`, `generation_calls`, sau chei pe caz în plus față de cele 6 vechi).

**Clasificarea `rezultat_final` (`_run_generation` izolat, cu un stub la nivel `GenerationService`)**
- `test_run_generation_raspuns_normal_devine_raspuns_cu_metrici_corecte` — pică dacă `rezultat_final` nu e `raspuns`
  sau dacă `citeaza_asteptat`/`citate_literale` nu ies `True` pentru un citat literal către articolul așteptat.
- `test_run_generation_ungrounded_reference_devine_refuz_generare_unsupported` — pică dacă maparea
  `UngroundedReferenceError → refuz_generare_unsupported` sau `vizibil_utilizator` (200/`unsupported_answer`) se rupe.
- `test_run_generation_missing_citation_devine_eroare_generare_cu_clasa_si_continua` — pică dacă
  `MissingCitationError` nu devine `eroare_generare:MissingCitationError` sau dacă `vizibil_utilizator` nu e 503.
- `test_run_generation_provider_unavailable_fara_cauza_devine_eroare_generare_si_continua` — pică dacă
  `ProviderUnavailableError` **fără** `__cause__` nu e tratată identic cu erorile de validare (503, rulare continuă).
- `test_run_generation_provider_unavailable_cu_cauza_se_propaga_si_opreste_rularea` — pică dacă
  `ProviderUnavailableError` **cu** `__cause__` (simulează `AnthropicError` de rețea) e înghițită în loc să se
  propage (adică dacă rularea NU se oprește la o indisponibilitate reală de provider).
- `test_vizibil_utilizator_mapeaza_fiecare_clasa_de_rezultat_final` — pică la orice schimbare a maparei celor 5 clase.

**Metrici de conținut**
- `test_citeaza_asteptat_fals_daca_documentul_citat_e_gresit` / `..._adevarat_pentru_articol_copil_citat` — pică dacă
  `_citeaza_asteptat` nu mai distinge documentul corect sau nu mai acceptă articolul-copil.
- `test_citate_literale_fals_daca_citatul_nu_apare_in_dovada` / `..._adevarat_cu_whitespace_normalizat` — pică dacă
  verificarea literală devine prea permisivă sau prea strictă la whitespace.
- `test_declara_lipsa_functioneaza_indiferent_de_diacritice` (parametrizat cu/fără diacritice) și
  `..._fals_pentru_un_raspuns_obisnuit` — pică dacă euristica nu mai normalizează diacriticele sau devine prea largă.

**Pipeline complet (`run_evaluation` cu `GenerationService` înlocuit printr-un fake care numără apelurile brute)**
- `test_refuz_de_cautare_nu_declanseaza_nicio_generare` — pică dacă un status de refuz căutare (`not_found` etc.)
  ajunge totuși să apeleze generarea (fake-ul generator ridică o eroare la orice apel real).
- `test_gasit_cu_generare_reusita_devine_raspuns_si_numara_apelul` — pică dacă `generation_calls`/sumarul `generare`
  nu reflectă corect un răspuns reușit.
- `test_citatul_publicat_in_raport_este_taiat_la_300_de_caractere` — pică dacă tăierea la 300 de caractere din
  `citation.citat[:300]` e eliminată sau modificată (citatul de 400 de caractere ar ieși netăiat).
- `test_raportul_de_generare_nu_publica_textul_intern_al_dovezii` — pică dacă textul intern al dovezii ajunge în
  raportul serializat (verifică non-scurgerea, similar cu testul existent pentru căutare, dar pe ruta de generare).
- `test_sumarul_generare_distribuie_si_numara_erorile_pe_clasa` — pică dacă distribuția `rezultat_final` sau
  `erori_generare` nu mai numără corect pe 3 cazuri eterogene (răspuns/eroare/refuz căutare).
- `test_plafonul_de_generari_include_reincercarea_si_opreste_rularea_fara_raport` — pică dacă plafonul de generări nu
  se aplică per-apel-brut (adică dacă o reîncercare internă a `GenerationService` NU e numărată de
  `_CountingGenerator`, plafonul ar putea fi ocolit).

## Ce nu am acoperit și de ce
- Nu am testat direct logica de retry din `generation_core.GenerationService` (referințe normative nesusținute →
  o singură reîncercare) — e deja acoperită în `tests/test_generation_core.py` și `tests/test_citation_passages.py`;
  aici am testat doar că plafonul de generări din `retrieval_eval` numără corect apelurile brute, indiferent câte
  face `GenerationService` intern, prin fake-uri, nu prin `GenerationService` real.
- Nu am scris un test separat pentru „pasaj invalid” (`InvalidGenerationPayloadError`) ca rezultat_final distinct —
  e aceeași ramură `except GenerationValidationError` ca `MissingCitationError` în `_run_generation`, deci testul cu
  `MissingCitationError` acoperă comportamentul ramurii; nu am dublat cu fiecare subclasă concretă.
- Nu am rulat testele (nu am acces la shell) — planner-ul trebuie să le ruleze.

## Suspiciuni de bug
Niciuna găsită în codul coder-ului la citire; toate testele scrise reflectă comportamentul descris explicit în
`R23-tester.md`/`R23-coder.md`, nu presupuneri.

## Comanda pentru planner
```
python -m pytest tests/test_retrieval_eval.py -q
```
sau, pentru toată suita:
```
python -m pytest -q
```
