# R21 — Coder: anexele și identificatorii falși din P 118/1

Worktree: `D:\Omnia-MVP-r21-anexe`, branch `fix/r21-anexe-p118` (din `main` `9118a12`). Aprobat de Lucian 28-09-2026.

## Dovezi (planner, chunker-ul curent pe `documente_noi/p118_1_2025/extracted.txt`)
- **916 din 2862 chunk-uri (32%)** au `articol` care nu e un articol real „Art. N.N…”: `27.3.` ×140, `6.1.38.(317)` ×111, `6.1.38.` ×104, `3.2.11.` ×101, `7.8.` ×86, `1.25.` ×70, `3.9.1.` ×65, `48.6.` ×44, `29.1.` ×27, `8.7.` ×15, `2.940.` ×4.
- **Anexele ocupă 42% din P 118/1**: corpul lor începe la rândul 26220 (`ANEXA 1  - AMPLASARE CONSTRUCȚII`), până la finalul fișierului (45541). Cuprinsul anexelor e la rândurile ~408–600 (aceleași titluri + `A.10. 1.1. SCOP…`).
- Surse de identificatori falși (toate prin marcajul „număr fără punct final” din runda 6 R14, gândit pentru I7):
  - rândul 2742 `48.6 Substrat - material…` (definiție numerotată dintr-o listă);
  - rândul 29752 `7.8 Prevenirea descărcărilor electrostatice…` (numerotare internă de anexă);
  - rândul 33887 `27.3 Mj/kg, în orice fel de` (valoare + unitate, ruptă pe rând nou).
- Anexele interne folosesc și marcajul `A.10. 2.7.7. Pentru intervenția…` (anexa 10, articolul 2.7.7), rândul 37875.
- Alte documente au anexe cu formate diferite: I9 (`ANEXA 1  ` la 5162, `ANEXA 1.1  `, `ANEXA 5.3. `; dar rândul 1513 `ANEXA 2.1, au caracter de recomandare…` e **trimitere în text**, nu titlu), NP 057 (`ANEXA 1. `, `ANEXA 3.1. `, `ANEXA 3.4.(A).`). Pattern-ul curent `PATTERN_ARTICOL` acceptă deja `ANEXA\s+\d+\.\d+\.` ca marcaj (`chunking_core.py:21`). Parser-ul normalizează „anexa 2.1” din întrebări prin `_ANNEX_REFERENCE` (`retrieval_core.py:36`).

## Sarcina (în `chunking_core.py`)
1. **În documentele care folosesc marcaje „Art. N.N…” pentru articole** (prag: ≥ 50 de marcaje „Art.” recunoscute), marcajul „număr fără punct final” (`PATTERN_ARTICOL_FARA_PUNCT`) nu mai produce începuturi de articol. În celelalte documente (ex. I7) rămâne ca acum.
2. **Regiuni de anexă.** Un titlu de anexă e un rând care începe cu `ANEXA N` (N = număr cu opțional `.M`, sufix literă sau `(X)`), urmat de sfârșit de rând, `-`, `–`, `.` sau un titlu cu majuscule; **nu** e titlu dacă după număr urmează virgulă sau text cu literă mică (trimitere). Titlurile din cuprinsul detectat (runda 1b/7 R14) nu contează. Din primul titlu de anexă din corp până la următorul titlu de anexă, conținutul aparține acelei anexe:
   - textul dintre titlu și primul marcaj intern devine un chunk cu `articol` = `ANEXA N` (normalizare → `anexan`, compatibil cu `_ANNEX_REFERENCE`);
   - marcajele interne (`A.10. 2.7.7.`, numere simple) produc articole cu prefixul anexei: `ANEXA 10.2.7.7` sau echivalent care se normalizează la `anexa10.2.7.7` — astfel sunt copii ai anexei (regula copiilor din `find_exact` și `_is_known_article`) și nu mai pot coincide cu articolele din corp;
   - titlul anexei devine context (prim rând) al chunk-urilor ei, ca titlurile de secțiune din R14.
3. Nu atinge restul regulilor (antete MO, cuprins, trimiteri rupte, D18, dedup normalizat, subpuncte). Nu atinge `retrieval_core.py`, `main.py`, `generation_core.py`, `supabase/`, `.env`, `documente_noi/`, `evaluare/`.

## Criterii de acceptare (planner-ul verifică pe textele reale)
- P 118/1: niciun `articol` din corp de forma `27.3`, `48.6`, `7.8`, `29.1`, `2.940`; conținutul anexelor are identificatori `anexa…`; 811/811 articole „Art.” rămân articole proprii.
- Toate cele 9 documente: acoperirea față de textul brut nu scade sub valorile curente; 0 articole normalizate neconsecutive; testele existente trec (numerele fixe de chunk-uri le actualizează Tester-ul).
- Evaluarea pe setul de aur rămâne ≥ 27/30 după reimport (o rulează planner-ul).

## Runda 2 — regiunea de anexă începe prea devreme (28-09-2026)

Dovezi planner după runda 1 (textele reale):
- **P 118/1: 0/811 articole „Art.” proprii** (înainte 811/811); 3528 din 3694 chunk-uri au `articol` „ANEXA …” (ex. `ANEXA 1.(1)`, `ANEXA 10.1.1.1.`); acoperire 0,993 → **0,941** (sub pragul D24 de 0,99). Cauza: **cuprinsul anexelor** de la rândurile 408–435 (`ANEXA 1  - AMPLASARE CONSTRUCȚII`, `ANEXA 2  - …`, `ANEXA 2.1 - …`, câte un titlu pe rând, fără conținut între ele) e luat drept titlu real; tot corpul (rândurile 435–26219) devine „anexă”.
- **I9:** apar `ANEXA 2.1.11.1.` … `ANEXA 2.1.11.17.` — articole din corp înghițite de o anexă începută prea devreme (inclusiv cazul semnalat de tine, rândul 3036–3037 `…și` ↵ `ANEXA 5.3.`). Anexele reale ale I9 încep la rândul 5162.
- Celelalte documente: neconsecutive 0 peste tot; NP 057 290 chunk-uri (era 298), acoperire 0,882 neschimbată.

Reguli suplimentare pentru titlul de anexă (toate trebuie să fie adevărate):
1. **Nu e intrare de cuprins:** următorul rând nevid **nu** e tot un titlu `ANEXA …` și nu e doar un număr de pagină; un bloc de ≥2 titluri de anexă consecutive (doar rânduri goale între ele) e cuprins, nu corp.
2. **Nu e continuarea unei fraze:** rândul nevid anterior nu se termină cu literă mică, virgulă, `și`, `sau`, `din`, `la`, `în`, `conform`, `prevederile` (sau orice cuvânt din lista existentă de trimiteri rupte).
3. Rămân valabile excluderile din runda 1 (virgulă sau literă mică după număr).

Acceptare: P 118/1 811/811 „Art.” proprii și acoperire ≥ 0,993; I9 fără identificatori `ANEXA` pentru conținutul de dinainte de rândul 5162; celelalte documente cu acoperire ≥ valorile de dinainte de R21 (i5 0,979; i7 0,971; i9 0,969; np004 0,923; np010 0,999; np057 0,882; spitale 0,982; np091 0,989) și 0 neconsecutive. Actualizează raportul cu „Runda 2”.

## Runda 3 — metrica de acoperire și cuprinsul anexelor P 118/1 (28-09-2026)

Dovezi planner după runda 2: P 118/1 **811/811** „Art.” proprii ✓ (plasa ta pe `PATTERN_ARTICOL_ART` e acceptată); I9 anexe corecte, acoperire 0,969 ✓; 0 neconsecutive peste tot ✓. Rămân două probleme:

1. **Metrica `acoperire_text_brut` raportează fals 0,942 pentru P 118/1.** Toate cele 1050 de rânduri „lipsă” încep cu marcajul intern `A.10. x.y.z.` (rândurile 36000–43000); conținutul e prezent și corect etichetat (verificat: „Pentru limitarea propagării fumului…” → `ANEXA 10.2.2.9.`). Metrica elimină doar marcajele `(Art. )N.N.` și `(N)`, nu și `A.N.`. Cu `A.N.` eliminat din textul brut, acoperirea e **0,995**. Cerință: `acoperire_text_brut` elimină, la normalizarea textului brut, și marcajele interne de anexă `A.<nr>.` (aceleași pe care chunker-ul le mută în identificator). Nu schimba pragurile D24.
2. **Intrările din cuprinsul anexelor câștigă dedup-ul:** chunk-ul `ANEXA 2.3.` (309 caractere) conține textul cuprinsului („- PEREȚI DE SECTORIZARE … ANEXA 2.4 - PEREȚI ANTIFOC … ANEXA 3 - LIMITAREA…”); la fel `ANEXA 3.2.`, `ANEXA 7.6.`. Titlurile din cuprinsul P 118/1 sunt pe două rânduri (rândul 414 → continuare 415), deci regula „următorul rând e alt titlu ANEXA” nu le prinde. Cerință: **în documentele cu ≥ 50 de marcaje „Art.”**, un titlu de anexă aflat **înaintea ultimului marcaj „Art.”** din document este intrare de cuprins și se ignoră complet (nu produce chunk, nu deschide regiune). În celelalte documente, regulile din runda 2 rămân cum sunt.

Acceptare: P 118/1 — 811/811 „Art.”, `acoperire_text_brut` ≥ 0,993, niciun chunk `ANEXA …` al cărui text conține un alt titlu `ANEXA N -`; celelalte documente neschimbate față de runda 2. Actualizează raportul cu „Runda 3”.

## Runda 4 — „ultimul Art.” e greșit; anexele conțin trimiteri „Art.” (28-09-2026)

Dovezi planner după runda 3: P 118/1 acoperire 0,996 și 811/811 „Art.” ✓; dar **18 din 43 de titluri de anexă din corp nu produc niciun chunk** (ANEXA 1, 2, 2.1–2.4, 3, 3.1–3.3 …; conținutul lor ajunge sub alte identificatori). Cauza: în regiunea anexelor există 3 rânduri „Art.” care sunt **trimiteri**: rândul 26351 `Art. 7.1.3.);`, 29484 `Art. 2.4.9.4. (2).`, 35900 `Art. 2.1.3..`. Ultimul „Art.” brut e la 35900, deci regula din runda 3 ignoră toate titlurile de anexă de dinainte. În plus, `ANEXA 4.5 - ÎNCĂPERI DE DEPOZITARE` e respins pentru că rândul anterior e o legendă de figură terminată cu literă mică („Figura 173 - Stație de pompare - Acces pe scara verticală”).

Cerințe:
1. Înlocuiește „înainte de ultimul marcaj Art.” cu **„înainte de primul marcaj Art. acceptat”** (primul articol real al corpului; în P 118/1 rândul 776; cuprinsul anexelor e la 408–600).
2. **Scoate plasa din runda 2** (resetarea regiunii de anexă la un marcaj `PATTERN_ARTICOL_ART`): cu punctul 1 nu mai e necesară și poate închide o anexă la o trimitere „Art.” din interiorul ei.
3. Regula „continuare de frază” pentru titlul de anexă (runda 2, punctul 2): respinge doar dacă rândul anterior se termină cu **virgulă** sau cu unul dintre cuvintele de trimitere (`și`, `sau`, `din`, `la`, `în`, `conform`, `prevederile`, lista existentă) — **nu** simplu cu literă mică (legendele de figuri se termină cu literă mică). Cazul I9 rândul 3036–3037 („…și” ↵ `ANEXA 5.3.`) trebuie să rămână respins.

Acceptare: P 118/1 — toate cele 43 de titluri de anexă din corp (după rândul 26220) produc cel puțin un chunk cu prefixul lor; 811/811 „Art.”; acoperire ≥ 0,993; niciun chunk `ANEXA …` al cărui text conține titlul altei anexe; I9 neschimbat față de runda 3 (anexe de la 5162, acoperire 0,969); restul documentelor neschimbate. Actualizează raportul cu „Runda 4”.

## Runda 5 — cuvinte comparate ca sufix, nu ca întreg (28-09-2026)

Dovezi planner: după runda 4, P 118/1 are 43/43 anexe, 811/811 „Art.”, acoperire 0,996 ✓. Testele noi ale Tester-ului au găsit un **bug real, preexistent din R14 runda 5**: `_linia_anterioara_se_termina_cu_trimitere` (`chunking_core.py:364–376`) folosește `cuvant.endswith(sufix)` pe tot rândul, deci „…corect stabi**lit.**” e tratat ca trimitere („lit.”) și marcajul „Art. N.N.” următor e înghițit de articolul anterior (reprodus: 7 articole „Art. i.1.” sintetice → 1 singur segment). Aceeași eroare în `_linia_anterioara_indica_continuare_anexa`: „Figura 173 - Acces pe scara vertica**la**” se termină cu „la” → titlul `ANEXA 4.5` e respins. În corpusul actual efectul e 0 (verificat), dar e latent pentru documente viitoare.

Cerință: în ambele funcții, potrivirea se face pe **ultimul cuvânt întreg** al rândului (precedat de început de rând sau de un caracter care nu e literă), nu pe sufixul șirului; `art.`, `lit.`, `pct.`, `alin.` rămân cuvinte cu punct. Nu schimba listele de cuvinte și nimic altceva. Actualizează raportul cu „Runda 5”.

## Constrângeri dure
Nu rula comenzi. Nu scrie teste noi. Fără comentarii inutile. Raport: `docs/handoff/R21-coder-raport.md` (reguli, praguri, cazuri limită observate în I9 și NP 057).
