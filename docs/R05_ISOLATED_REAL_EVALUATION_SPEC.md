# R05 — evaluator real izolat

**Status:** aprobat de Lucian la 13-09-2026, înainte de rulare.

## Scop

Măsoară pe 20 de întrebări aprobate dacă răspunsurile reale sunt semantic susținute de dovezile citate. Nu modifică ruta publică sau comportamentul aplicației.

## Izolare

- Citește numai documentele `approved` și chunk-urile printr-o conexiune PostgreSQL `readonly`.
- Nu apelează `POST /intreaba`; nu rezervă quota, rate limit sau `paid_call_budget`.
- Poate apela Voyage și Anthropic numai prin comandă explicită a operatorului.
- Nu face retry automat. Orice eroare oprește rularea și este raportată local.

## Input și output

- Primește explicit un manifest local cu exact 20 cazuri aprobate; manifestul și raportul sunt ignorate de Git.
- Cazurile au ID, categorie (`exact`, `semantic`, `negative`) și întrebare. Nu conțin răspunsuri normative gold în Git.
- Raportul local atomic conține status tehnic, citări publice, contoare de apeluri și răspunsul pentru revizuirea umană; nu este comis.
- Evaluatorul impune maximum 20 cazuri, 8 embeddings semantice și 16 generări. Plafonul generatorului rămâne 1.200 tokeni/răspuns.

## Verdict uman

Lucian etichetează fiecare rezultat: `supported`, `unsupported`, `incomplete`, `correct_refusal` sau `execution_error`. Nu pretindem că citarea literală validă rezolvă R05.

## Excluderi

Fără deploy, migrare, import, `approved`, schimbare DB, expunere publică, retry, cache sau ajustare automată a produsului.
