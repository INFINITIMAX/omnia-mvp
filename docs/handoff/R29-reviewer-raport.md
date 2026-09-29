# R29 — Raport reviewer (transcris integral de planner)

Verdict: ACCEPT (cu un punct semnalat pentru decizie explicită a planner-ului, neblocant pentru criteriile de acceptare curente).

## Ce am verificat
- Diff efectiv față de `D:\Omnia-MVP\chunking_core.py` (main, `8d8f3fc`): am citit ambele fișiere secțiune cu secțiune (header, regexuri L1-130, `creeaza_chunkuri` L160-207, `_elimina_titluri_capitol_roman`/`_elimina_marcaje_capitol_np127` L308-334, `_extrage_segmente` L578-690, `_normalizeaza_pentru_acoperire`/`acoperire_text_brut` L816-850, `_aplica_limita_caractere` L853+). Singurele diferențe sunt exact cele descrise în `R29-coder-raport.md`: 3 regexuri noi (`PATTERN_ARTICOL_NP127`, `PATTERN_TITLU_CAPITOL_NP127`, `PATTERN_TITLU_SECTIUNE_NP127`, `PATTERN_LINIE_SEPARATOR_PLUS`), funcția `_elimina_marcaje_capitol_np127`, o linie de apel în `creeaza_chunkuri`, o linie de înregistrare în uniunea `_extrage_segmente`, o linie în `_normalizeaza_pentru_acoperire`. Niciun fișier în plus, nicio abstracție/opțiune nesolicitată. Restul fișierului (900+ linii) e identic.
- Risc de fals pozitiv pe celelalte documente: am grepuit direct în `D:\Omnia-MVP\documente_noi\*\extracted.txt` (nu am citit fișiere mari integral, doar pattern matching):
  - `^\s*Articolul\s+\d+\s+[A-ZĂÂÎȘȚŞŢ„(]` → apare **doar** în `np127_2009`.
  - `^\s*Capitolul\s+[IVXLC]+\s+\S` și `^\s*Sec[țţ]iunea\s+(?:a\s+\d+-a|\d+)\s+\S` → **doar** în `np127_2009`.
  - `^\+$` (linie doar „+”) → apare și în `p118_3_2015`; am verificat un caz concret (linia 2146, urmat de „[Text modificat prin Ordinul nr. 6.025/2018...]”) — garda condiționată din `_elimina_marcaje_capitol_np127` (elimină „+” doar dacă rândul nevid următor începe cu `Articolul`/`Capitolul`/`Secțiunea`) îl lasă corect neatins. Confirmă exact corectura planner #1.
  - Confirmarea coder-ului/testerului despre riscul zero pentru celelalte 12 documente e verificată independent, nu doar preluată din raport.
- Reutilizarea mecanismului generic (`_este_referinta_rupta`, `_baza_articol`) pentru noul pattern: verificat că `_baza_articol` produce corect „117.” din grupul capturat „117”, că `_este_referinta_rupta` nu respinge fals marcajele reale (lookahead pe majusculă/„/(”, iar liniile „+” dintre articole sunt deja eliminate înainte de `_extrage_segmente`, deci „ultimul cuvânt anterior” e mereu finalul frazei articolului precedent, nu „+” sau „articolul”) — nicio ramură specială adăugată, exact cum pretinde raportul.

## Punctul 2 din task (Capitolul XIV / tabelul de standarde lipit de art. 173)
Am citit direct din `D:\Omnia-MVP\documente_noi\np127_2009\extracted.txt` (liniile 396-450): confirmat — linia 402 „Capitolul XIV Referințe tehnice și legislative 1. Standarde Nr.” e eliminată integral de `PATTERN_TITLU_CAPITOL_NP127.match` (matches pe prefix, dar codul face `continue` pe linia întreagă, deci pierde și „1. Standarde Nr.”), iar tot tabelul de standarde SR/SR EN care urmează (zeci de linii, fără niciun marcaj „Articolul”) rămâne atașat, ca text, la ultimul articol real — „173.” — și va fi tăiat în mai multe chunk-uri, toate etichetate „173.”.

Acesta e un risc real de citare greșită într-un instrument RAG axat pe citare legală (un chunk din tabelul de standarde SR EN ar apărea sub identificatorul „articolul 173”, care în realitate vorbește despre planurile de evacuare, nu despre standarde). Nu e un bug de cod — comportamentul e exact ce descrie task-ul („titluri, eliminate ca `_elimina_titluri_capitol_roman`”) aplicat consecvent — ci un gol de specificație pe care coder-ul l-a semnalat explicit și transparent în raport, fără să ascundă nimic, cerând decizie de la planner. Nu blochează acceptarea codului livrat (task-ul nu a cerut nimic despre acest tabel, criteriile de acceptare sunt îndeplinite), dar recomand ferm ca planner-ul să decidă explicit înainte de deploy: fie un identificator propriu (`CAP. XIV.` sau similar) pentru tabel, fie acceptarea documentată a limitării. Nu e treaba tester-ului să fi acoperit asta — a semnalat corect în raport de ce nu a scris test pe acest caz (comportament nespecificat, ar fixa ceva nedecis).

## Teste (`tests/test_chunking_np127.py`, 7 teste)
Pentru fiecare am verificat concret „ce l-ar face să cadă” comparând cu regex-urile reale din `chunking_core.py`, nu am luat de-a gata descrierile din raport:
1. `Articolul 117` → `117.`, text curat — pică dacă marcajul nu se recunoaște sau punctul lipsește. Real.
2. Literă mică după „Articolul 117” → nu deschide articol — pică dacă lookahead-ul ar accepta litere mici; am verificat regexul (`(?=[A-ZĂÂÎȘȚŞŢ„(])`) chiar exclude litere mici. Real.
3. „Articolul 6” în mijlocul rândului → text simplu — pică dacă regexul n-ar cere `\n` la început. Real (regexul are `\n[ \t]*Articolul` explicit).
4. Titluri Capitol/Secțiune eliminate, dar „Secțiunea conductelor...” (frază, fără număr) păstrată — regresie exact pentru distincția cerută în task. Real, non-redundant cu 1-3.
5/6. „+” eliminat înaintea articolului următor vs. păstrat într-o formulă — regresie directă pentru corectura planner #1, am confirmat pe document real (p118_3) că garda există și funcționează. Real, complementare (nu redundante — testează cele două ramuri ale aceleiași condiții).
7. Acoperire ≥0.99 pe text sintetic — regresie directă pentru corectura planner #2 (`_normalizeaza_pentru_acoperire` scoate prefixul „Articolul N”); am confirmat în cod (linia 822) că fără acest `re.sub` liniile brute cu „Articolul N ...” nu s-ar potrivi cu textul din chunk (care nu mai conține marcajul) — testul chiar ar fi picat pe varianta veche. Real.

Niciun test din cele 7 nu e de tipul „trece întotdeauna” — fiecare are o schimbare de cod identificabilă care l-ar strica, iar eu am localizat explicit acea schimbare în sursă, nu doar am citit afirmația testerului. Nu am găsit teste redundante. Asertorii nu sunt slabe (verifică valori exacte ale `articol`/`text`, nu doar `is not None`).

## Ce nu am putut verifica direct
Nu pot rula `pytest` (fără shell) — planner trebuie să confirme efectiv 1355 passed + cele 7 noi, conform comenzii din `R29-tester-raport.md`. Am citit doar fragmente din `extracted.txt` (liniile 396-450), nu integral, conform constrângerii.

## Concluzie
ACCEPT pentru codul din `chunking_core.py` și pentru testele din `tests/test_chunking_np127.py`. Un singur item de urmărit, neblocant: decizie explicită a planner-ului despre identificatorul tabelului de standarde din Capitolul XIV (în prezent etichetat „173.”), înainte de a considera NP 127 gata pentru citare în producție.

---

## Decizia planner-ului (29-09-2026)
- Accept. Toate testele trec (1362 passed).
- **Capitolul XIV (Referințe tehnice și legislative) se exclude din textul importat** (`documente_noi/np127_2009/extracted.txt`, local; varianta completă păstrată în `D:\_scratch\omnia\np127_extracted_complet.txt`). Motiv: e doar o listă de standarde SR/SR EN și acte citate, fără cerințe normative; atașată art. 173 ar fi citată greșit; standardele sunt oricum excluse de regula de conținut. Rezultat: 191 chunk-uri, articole 1–173, acoperire 0.9351 (≥ pragul 0.93), art. 173 se încheie la textul lui propriu.
