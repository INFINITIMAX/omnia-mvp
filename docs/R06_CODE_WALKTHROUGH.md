# R06 — explicația modificărilor pentru începător

Predare: **11-09-2026**. Explică implementarea locală verificată, nu un deploy. Referințele sunt pentru snapshotul R06 consemnat în `revizii.md`; liniile se pot deplasa ulterior. Liniile care doar închid paranteze și înregistrările repetitive sunt explicate împreună cu instrucțiunea lor.

## 1. Ce schimbă produsul

Înainte, backendul afișa primele 600 de caractere din fragment, indiferent unde era informația relevantă. Acum generatorul trebuie să întoarcă un obiect JSON cu `raspuns` și `pasaje`. Backendul verifică fiecare pasaj în dovada exactă asociată citării și afișează textul validat.

Un pasaj autentic nu face automat afirmația adevărată. Cele zece rezultate neconforme R05 rămân în diagnostic.

## 2. `generation_core.py` — transportul și eroarea

- Liniile 29–39, `GeneratedText`: păstrează textul transportat și indicatorul `truncated`. Documentația precizează că textul trebuie să fie pachetul JSON, nu proză simplă. Valoarea implicită a indicatorului rămâne `False`.
- Liniile 42–49, `Generator`: interfața rămâne `generate(prompt, max_tokens=...)`. Poate transporta JSON ca `str` sau `GeneratedText`; nu apare un client extern nou.
- Liniile 56–57, `InvalidGenerationPayloadError`: definește o eroare nouă care moștenește `GenerationValidationError`. Prin moștenire ajunge la ruta existentă HTTP 503 și rollback, fără schimbarea executabilă a `main.py`.

## 3. `GenerationService.generate` — ordinea operațiilor

- `evidence_by_id = dict(assigned)`: transformă perechile ID–dovadă într-un dicționar; un ID poate fi rezolvat direct la dovada sa.
- `_supported_reference_fragments(...)`: păstrează verificarea existentă a referințelor normative, separată de proveniența pasajelor.
- `_build_prompt(...)`: construiește instrucțiunile și datele pentru generator.
- `generated, used_ids, passages = self._generate_validated(...)`: primește răspunsul decodat, ID-urile efectiv citate și pasajele deja verificate. Nu continuă dacă validarea eșuează.
- `_unsupported_normative_references(generated.text, ...)`: verifică referințele în răspunsul decodat, nu în întregul transport JSON.
- Ramura `if unsupported`: păstrează unica reîncercare existentă pentru referințe normative nesusținute. A doua ieșire trece din nou prin validarea completă; nu se reutilizează pasajele primei ieșiri.
- Constructorul `PublicCitation`: ia codul, titlul și articolul din `evidence_by_id`, nu din declarațiile modelului.
- `citat=passages[citation_id]`: înlocuiește vechea tăiere `content[:600]` cu pasajul verificat. Nu există fallback la prefix.
- `for citation_id in used_ids`: păstrează ordinea primei utilizări din răspuns și deduplicarea citărilor.
- `if generated.truncated`: adaugă avertismentul existent numai după ce întregul pachet a trecut validarea.
- `return GenerationResult(...)`: păstrează rezultatul intern și structura publică utilizate anterior.

## 4. `_generate_validated`, liniile 285–298

| Instrucțiune | Explicație |
|---|---|
| Definiția metodei și tipul rezultatului | Metoda primește promptul și dicționarul dovezilor; întoarce text, ID-uri și pasaje. |
| `self._generator.generate(...)` | Execută un singur apel prin interfața deja existentă, cu același plafon de tokeni. |
| `self._as_generated_text(...)` | Verifică și uniformizează învelișul transportului, fără să repare conținutul. |
| `payload = self._decode_payload(generated.text)` | Parsează JSON-ul strict; orice eșec oprește metoda. |
| `answer = payload["raspuns"]` | Extrage numai câmpul care va deveni răspuns public. |
| Verificarea `isinstance(answer, str)` și `answer.strip()` | Respinge tipul greșit, textul gol și textul compus numai din spații. |
| `raise EmptyGeneratedAnswerError(...)` | Păstrează eroarea tipată existentă pentru răspuns gol. |
| `_validated_used_ids(answer, set(evidence_by_id))` | Validează citările răspunsului față de ID-urile permise, păstrând erorile vechi pentru citare lipsă/necunoscută. |
| `_validated_passages(...)` | Verifică separat pasajele, exact pentru ID-urile folosite. |
| `return GeneratedText(answer, truncated=...), used_ids, passages` | Întoarce textul decodat, păstrează indicatorul original și livrează numai pasajele validate. |

## 5. `_decode_payload`, liniile 301–322

- Definiția metodei: intrarea este textul JSON; rezultatul trebuie să fie un dicționar.
- `unique_object(pairs)`: funcție locală folosită de parser pentru fiecare obiect JSON, inclusiv cele imbricate.
- `result = {}`: pornește un dicționar gol pentru obiectul respectiv.
- `for key, value in pairs`: parcurge perechile în ordinea primită, înainte ca un dicționar obișnuit să ascundă duplicatele.
- `if key in result`: detectează o cheie repetată după decodarea JSON, inclusiv variante scrise prin escape-uri.
- `raise InvalidGenerationPayloadError(...)`: respinge duplicatul în loc să aleagă tăcut prima sau ultima valoare.
- `result[key] = value`: memorează fiecare pereche acceptată.
- `return result`: livrează obiectul construit fără duplicate.
- `reject_constant(...)`: respinge constantele nepermise precum `NaN`, pe care parserul Python le-ar putea accepta implicit.
- `json.loads(..., object_pairs_hook=..., parse_constant=...)`: folosește parserul standard împreună cu cele două controale explicite.
- `except (ValueError, RecursionError)`: transformă erorile de parsare sau de adâncime în eroarea tipată a contractului; nu repară textul.
- Verificarea `isinstance(payload, dict)`: respinge liste, numere sau alte tipuri la rădăcină.
- `set(payload) != {"raspuns", "pasaje"}`: respinge câmpurile lipsă sau suplimentare.
- `return payload`: întoarce numai obiectul cu schema acceptată.

## 6. `_validated_passages`, liniile 325–353

- Definiția metodei: primește lista brută, ID-urile citate și dovezile autorizate.
- `if not isinstance(value, list)`: cere o listă de pasaje; alt tip este eroare.
- `passages = {}`: dicționarul rezultat este inițial gol.
- `for entry in value`: verifică fiecare intrare, nu doar prima.
- Controlul `dict` și al cheilor `{id, citat}`: interzice intrările malformate sau metadata suplimentară furnizată de model.
- `citation_id = entry["id"]`: citește ID-ul declarat pentru pasaj.
- `isinstance(..., str)` și `re.fullmatch(...)`: permit numai ID-uri în forma așteptată, nu numere, spații sau alte tokenuri.
- `citation_id.upper()`: tratează `C1` și `c1` ca același ID, compatibil cu citările existente.
- `citation_id not in used_ids`: respinge un pasaj pentru o citare nefolosită/necunoscută.
- `citation_id in passages`: respinge duplicatele după canonizarea majusculelor.
- `quote = entry["citat"]`: citește textul declarat.
- `not isinstance(quote, str)`: refuză alte tipuri decât textul.
- `not quote.strip()`: detectează textul gol; verificarea nu schimbă textul păstrat.
- `len(quote) > MAX_CITATION_CHARS`: refuză mai mult de 600 caractere; nu taie automat pasajul.
- `quote not in evidence_by_id[citation_id].content`: cere potrivire literală în dovada proprie, nu într-o altă dovadă.
- `raise InvalidGenerationPayloadError(...)`: oricare dintre condițiile invalide oprește întregul răspuns.
- `passages[citation_id] = quote`: memorează textul original, cu spațiile și diacriticele intacte.
- `set(passages) != set(used_ids)`: după parcurgere verifică să nu lipsească pasajul vreunei citări.
- `return passages`: numai dicționarul complet valid poate ajunge la construirea citărilor publice.

## 7. Promptul și trunchierea

Liniile 408–417 adaugă instrucțiuni pentru JSON strict, cheile permise, un pasaj pentru fiecare ID folosit, limita de 600 caractere, copiere literală și închiderea completă a pachetului în bugetul existent. Regulile vechi despre dovezi, calcule, referințe și date neîncrezătoare rămân.

JSON complet valid plus `truncated=True` poate produce răspunsul cu avertisment. JSON tăiat înainte să fie valid produce 503. Nu există parser de recuperare, completare automată sau retry pentru această eroare.

## 8. `tests/generation_fixture_helpers.py`

- Importurile folosesc numai JSON, regex, dataclass și tipul local `GeneratedText`.
- `simulated_provider_payload(...)` este o simulare de provider pentru regresiile vechi, nu cod folosit de aplicație.
- `answer = ...`: extrage textul candidatului și păstrează posibilitatea transportului cu indicator de trunchiere.
- `documents = json.loads(...)`: citește dovezile sintetice deja trimise prin promptul testului.
- `by_id = {...}`: indexează textul acelor dovezi după ID.
- `ids = tuple(dict.fromkeys(...))`: găsește ID-urile din candidat, le canonizează și păstrează ordinea fără repetări.
- `assert ...`: împiedică helperul să fie folosit pentru repararea unei fixture intenționat invalide.
- `json.dumps({raspuns, pasaje}, ensure_ascii=False)`: creează transportul fictiv. Prefixul ales aici aparține simulării din test, nu unui fallback al backendului.
- Ramura `GeneratedText`: păstrează exact indicatorul de trunchiere în noul transport.
- `RawGeneratorFake`: stochează payloadul literal; fiecare apel incrementează contorul, reține promptul/plafonul și întoarce datele fără reparare. Este folosit pentru cazurile invalide și regresiile R06 explicite.

## 9. Evaluatorul 5A adaptat

- `ModelPassage`: o înregistrare cu `id` și `citat`, reprezentând intrarea declarată de generatorul fictiv, nu verdictul așteptat.
- `GroundingCase.model_passages`: adaugă această intrare separat de `required_passages`, care rămâne cerința evaluatorului.
- Fiecare linie nouă `model_passages=(...)` din G01–G19 declară explicit ce ar întoarce generatorul. G14 păstrează pasajul autentic, dar irelevant, din C1; G16 folosește C99; G17 nu are pasaje; G18/G19 aleg pasajul tardiv din C2.
- `FixedGenerator`: primește numai `payload` și numără apelurile; nu primește așteptările sau justificările.
- `json.dumps({"raspuns": case.candidate, "pasaje": [...]})`: construiește transportul din intrările explicite ale cazului, fără copierea cerințelor gold.
- `asdict(passage)`: transformă fiecare înregistrare de intrare într-un obiect JSON.
- Candidații, întrebările, dovezile, așteptările, justificările și cerințele originale sunt neschimbate pentru toate cele 19 cazuri. Testul dedicat demonstrează că schimbarea gold-ului nu modifică payloadul generatorului.

## 10. Testele noi și adaptările, grupate după aceeași regulă verificată

- `test_citation_passages.py`: generatorul RAW și constructorii sintetici pregătesc date, nu le validează în locul serviciului. Matricele testează atât payloaduri pozitive, cât și lipsuri, coliziuni de ID, chei duplicate, tipuri greșite, citate modificate, 600/601 caractere și JSON incomplet. Fiecare rând repetă aceeași verificare pentru o intrare diferită; `pytest.raises` cere refuzul, iar contorul cere un singur apel.
- Testele pasajului tardiv verifică textul exact și dovada corectă, nu numai lungimea citatului.
- Testele trunchierii verifică ambele ramuri aprobate. Cele pentru retry verifică separat că o a doua generare validă nu reutilizează pasajele primei generări.
- Funcția diagnostică R05 necolectată de pytest nu a fost raportată ca test executat.
- Testele API noi verifică 503, rollback și disponibilitatea quota într-o cerere ulterioară, rate/buget deja consumate, rollback eșuat, câmpurile publice și pasajul tardiv. Ele folosesc conexiuni și provideri falși, nu DB sau servicii reale.
- Cele patru adaptări ale aserțiunilor/decoratorilor vechi au fost comparate explicit de QA: plafonul de 600, cerințele promptului, scenariile erorii de dependență și transportul fake-ului evaluatorului. Nu s-au șters scenarii sau slăbit garanții.
- Probele suplimentare ale gazdei verifică aceeași contabilizare pe ruta semantică: un embedding și o generare, o rezervare de buget, rollback quota numai la eroare.

## 11. Rezultat și limitări

402 teste focalizate și 761 în suita completă au trecut. Cele 11 omise cer corpus local absent. QA și Reviewer au aprobat scope-ul local; cele opt fișiere revizuite au fost reconfirmate neschimbate prin hash la predare.

Pe aceiași 19 candidați fictivi, pasajele omise sunt 0 în loc de 2. Cele 10 afirmații nepublicabile acceptate rămân R05. Nu s-a măsurat dacă modelul real respectă noul format, relevanța alegerii sale, latența sau costul. Implementarea este conectată în cod la calea API existentă, dar **nu este publicată în producție**.

**Valoare CV:** contract fail-closed, proveniență literală verificabilă, control al retry-urilor și migrare de teste verificată independent, fără prezentarea falsă a unei verificări structurale drept verificare semantică.
