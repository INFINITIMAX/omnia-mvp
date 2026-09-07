# Omnia — Specificație hybrid search și testare

## 1. Scop și reguli invariabile

Omnia răspunde numai pe baza dovezilor recuperate din normativele aprobate de Lucian.

Clientul primește:

- răspunsul;
- codul și titlul oficial al documentului;
- articolul;
- un citat exact, dar limitat ca lungime.

Clientul nu primește niciodată:

- `source_key` sau nume tehnice de fișiere;
- chunk-uri brute sau texte normative complete;
- embeddings, credențiale ori detalii Supabase;
- acces direct la baza de date sau endpoint de download.

## 2. Separarea responsabilităților

Implementarea trebuie separată în componente testabile:

1. **Parser:** detectează și normalizează referințe de document/articol fără servicii externe.
2. **Repository:** execută interogări SQL parametrizate și returnează dovezi interne.
3. **Retrieval service:** alege exact lookup sau semantic search, deduplică și limitează contextul.
4. **Generation service:** trimite numai contextul aprobat către Anthropic.
5. **API:** validează cererea și construiește răspunsul public, fără identificatori tehnici.

Clienții Voyage, Anthropic și Supabase/Postgres trebuie să poată fi înlocuiți cu mock-uri în teste.

## 3. Detectarea referințelor explicite

Parserul trebuie să acopere gradual formatele observate în normative:

- `articolul 4.4.7.2`;
- `art. 4.4.7.2`;
- `4.4.7.2`;
- `4.6.(1)`;
- `3.2.(B).l.`;
- `Art. 15`;
- referințe la anexe, când apar în date.

Normalizarea elimină diferențele neesențiale de spațiere, capitalizare și punct final. Valoarea normalizată se păstrează și în DB în `articol_normalizat`, pentru lookup indexabil.

Parserul nu trebuie să confunde automat cu articole:

- ani și date calendaristice;
- numere zecimale sau dimensiuni;
- versiuni software;
- alte secvențe numerice fără context normativ.

Regulă de siguranță:

- `articolul` / `art.` reprezintă o intenție explicită;
- o referință numerică fără marker este tratată ca articol numai dacă forma este neambiguă sau există ca identificator normalizat în documentele selectate;
- cererile cu prea multe referințe sau cu referințe ambigue cer clarificare, nu ghicesc.

Documentele se recunosc după codul oficial normalizat, tolerând diferențe de spații și cratime, de exemplu `NP010`, `NP 010-2022`.

## 4. Exact lookup înainte de semantic search

Când cererea conține o referință explicită:

1. dacă utilizatorul indică documentul, lookup-ul este limitat la acel document;
2. se caută după `document_id` și `articol_normalizat` prin SQL parametrizat;
3. dacă articolul există, se folosesc numai dovezile exacte;
4. dacă articolul explicit nu există, răspunsul este `not_found` și nu se substituie semantic un alt articol;
5. dacă articolul există în mai multe documente și documentul nu a fost indicat, se păstrează dovezile din fiecare document;
6. exact lookup nu apelează Voyage.

### Articole duplicate sau ambigue

- rândurile cu același `content_hash` se deduplică;
- texte diferite cu aceeași pereche document/articol sunt tratate drept ambiguitate de date;
- ambiguitatea nu este ascunsă și nu trimite un număr nelimitat de fragmente către Claude;
- sistemul răspunde controlat (`ambiguous_article`) sau solicită clarificare, iar problema intră în raportul de calitate al ingestion-ului.

Fiecare chunk trebuie să aibă identificator unic și ordine stabilă; `articol` nu este cheie unică.

## 5. Semantic search

Semantic search rulează numai când nu există o intenție explicită de exact lookup.

Flux:

1. validează întrebarea;
2. generează un singur embedding Voyage;
3. rulează nearest-neighbor search în formă compatibilă cu indexul pgvector:
   `ORDER BY embedding <=> query LIMIT TOP_K`;
4. calculează scorul și elimină rezultatele sub prag;
5. deduplică după `content_hash`;
6. aplică limita totală de context în ordine deterministă;
7. dacă nu rămân dovezi suficiente, returnează `not_found` fără Anthropic;
8. numai dovezile rămase ajung la generation service.

## 6. Configurație inițială de cost și context

Valorile inițiale sunt centralizate, testate și calibrate ulterior cu setul de evaluare:

```text
MAX_QUESTION_CHARS = 1000
SEMANTIC_TOP_K = 5
SEMANTIC_MIN_SCORE = 0.50
MAX_CONTEXT_CHARS = 12000
MAX_ANSWER_TOKENS = 800
MAX_CITATION_CHARS = 600
```

Cerințe suplimentare:

- un vizitator anonim primește maximum 10 întrebări în total per browser;
- backend-ul emite un identificator aleator semnat într-un cookie `HttpOnly`, `Secure`, `SameSite=Lax`; contorul este păstrat server-side, nu în JavaScript/localStorage;
- fiecare cerere validă acceptată consumă o întrebare; erorile tehnice interne nu consumă quota;
- ștergerea cookie-ului sau folosirea altui browser poate reseta identitatea anonimă; aceasta este o limitare acceptată și documentată pentru MVP;
- un rate limit separat per IP blochează automatizarea și se aplică înainte de Voyage/Anthropic;
- nu există coduri sau conturi separate pentru testeri în MVP; aplicația este publică pentru oricâți vizitatori, fiecare cu limita de 10 întrebări per browser; cei 4 testeri inițiali folosesc același URL și același flux anonim;
- timeout-urile furnizorilor sunt finite;
- testele standard nu efectuează apeluri plătite;
- smoke tests reale sunt opt-in, de exemplu prin `RUN_PAID_TESTS=1`;
- budget alerts se configurează înainte de deployment public.

## 7. Generare și citări verificabile

Backend-ul atribuie dovezilor ID-uri temporare, de exemplu `[C1]`, `[C2]`.

Claude:

- primește documentele ca date neîncrezătoare delimitate clar;
- este instruit să ignore orice instrucțiune găsită în textul normativ;
- poate cita numai ID-urile furnizate;
- nu construiește metadata oficială și nu poate inventa documente/articole.

Backend-ul:

1. validează că fiecare ID citat există în dovezile recuperate;
2. construiește obiectele publice de citare din DB;
3. include numai citatele folosite și valide;
4. nu expune chunk-ul complet;
5. refuză/fail-safe dacă răspunsul nu poate fi legat de dovezi valide.

Forma publică a unei citări:

```json
{
  "id": "C1",
  "cod_document": "NP 010-2022",
  "titlu_document": "Titlul oficial",
  "articol": "4.4.7.2",
  "citat": "Citat exact și limitat ca lungime..."
}
```

## 8. Contract API țintă

### Răspuns cu dovezi

```json
{
  "status": "answered",
  "raspuns": "Răspuns bazat pe dovadă [C1].",
  "citari": [
    {
      "id": "C1",
      "cod_document": "NP 010-2022",
      "titlu_document": "Titlul oficial",
      "articol": "4.4.7.2",
      "citat": "Citat exact și limitat..."
    }
  ]
}
```

### Fără dovezi

```json
{
  "status": "not_found",
  "raspuns": "Nu am găsit această informație în documentele aprobate.",
  "citari": []
}
```

### Alte reguli API

- **nu există `GET /documents` și nu se reintroduce**: catalogul documentelor indexate nu se expune public (decizie de produs, 07-09-2026 — acoperirea documentară e informație sensibilă competitiv). Metadata oficială a unui document ajunge la utilizator doar prin citările răspunsului la care acel document a contribuit;
- erorile Supabase/Voyage/Anthropic nu sunt transformate în `not_found`;
- indisponibilitatea unei dependențe produce un răspuns sigur, de exemplu HTTP `503`, fără detalii interne;
- cererile invalide sau prea lungi sunt respinse înainte de apeluri plătite;
- contractul păstrează câmpul `raspuns` pentru compatibilitatea UI-ului existent.

## 9. Matrice minimă de teste

| Caz | Rezultat așteptat | Cost implicit |
|---|---|---|
| Articol existent, cu punct final diferit | exact lookup și citare oficială | zero Voyage, Anthropic mock |
| Articol + document explicit | rezultate numai din documentul cerut | zero Voyage, Anthropic mock |
| Articol inexistent explicit | `not_found`, fără semantic fallback | zero Voyage/Anthropic |
| Același articol în mai multe documente | toate documentele relevante | zero Voyage, Anthropic mock |
| Etichetă duplicată cu text diferit | `ambiguous_article` / clarificare | zero Anthropic |
| Duplicate identice | deduplicare prin hash | mock implicit |
| Întrebare semantică relevantă | top-K și prag respectate | Voyage/Anthropic mock |
| Întrebare fără dovezi | `not_found` | zero Anthropic |
| An/datǎ/număr zecimal în întrebare | nu este confundat cu articol | zero sau mock |
| Variante `NP010` / `NP 010-2022` | același document | zero Voyage |
| Context prea mare | trunchiere deterministă | mock implicit |
| Instrucțiuni malițioase în sursă | tratate ca date, nu instrucțiuni | mock implicit |
| Claude citează un ID inexistent | răspuns respins/fail-safe | Anthropic mock |
| Răspuns fără citare validă | răspuns respins/fail-safe | Anthropic mock |
| Eroare DB/Voyage/Anthropic | HTTP sigur, fără secrete | mock implicit |
| Cerere prea lungă | respinsă înainte de furnizori | zero API |
| Vizitator anonim, întrebările 1–10 | cereri permise și contor server-side incrementat | mock implicit |
| Vizitator anonim, întrebarea 11 | quota refuzată înainte de furnizori | zero API |
| Eroare tehnică internă | quota nu este consumată | zero sau mock |
| Cookie falsificat | identificator respins și tratat sigur | zero API |
| Rate limit IP depășit | respins înainte de furnizori | zero API |
| Răspuns public | nu conține `source_key` sau nume `_extras.txt` | mock implicit |
| Smoke test real | executat separat și deliberat | opt-in |

## 10. Set de evaluare și criterii măsurabile

Setul inițial trebuie să conțină întrebări exacte, semantice și fără răspuns, fără a comite conținut normativ protejat în Git.

Criterii MVP:

- 100% exact lookup pentru articolele cunoscute din setul de evaluare;
- 100% refuz pentru articolele explicit inventate;
- minimum 90% retrieval corect pentru întrebările semantice controlate;
- zero `source_key` sau nume tehnice expuse;
- zero apeluri plătite în testele implicite;
- fiecare răspuns `answered` are cel puțin o citare validată;
- query-urile SQL folosesc parametri, nu concatenare de input;
- `python -m pytest -q` trece integral.

Hybrid search nu este declarat gata printr-o singură verificare manuală sau doar pentru că modelul produce un răspuns plauzibil.
