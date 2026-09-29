# R28 — Tester: raport

## Fișier creat
`tests/test_r28_anexa_nr.py` (fișier nou, nu am atins `test_chunking_core.py` existent).

Import: `from chunking_core import PATTERN_TITLU_ANEXA, creeaza_chunkuri` (convenție deja
folosită în `test_chunking_core.py`, care importă și el simboluri "private" din modul).

## Teste și ce le-ar face să pice

1. `test_pattern_titlu_anexa_prinde_variantele_nr_si_bis`
   Verifică direct pe regex (`PATTERN_TITLU_ANEXA.search`) că `ANEXA NR. 1`,
   `ANEXA NR.2` (fără spațiu), `ANEXA Nr. 3` și `ANEXA NR.14bis` se potrivesc, cu
   grupul capturat egal cu `"1"`, `"2"`, `"3"`, respectiv `"14bis"` (fără `NR`/`Nr`
   în identificator).
   **Ar pica dacă**: regex-ul nu ar accepta `NR.`/`Nr.` deloc, ar cere obligatoriu
   spațiu după punct, ar include `NR`/`Nr` în grupul capturat, sau dacă `bis` nu
   s-ar potrivi complet (ex. ar rămâne doar litera `b`).

2. `test_pattern_titlu_anexa_nu_prinde_trimiteri_din_corp_sau_forme_excluse`
   Trei cazuri negative: `anexa nr. 8, la...` (literă mică, deloc `ANEXA`
   majuscul), `ANEXA NR. 2, la...` (virgulă după număr) și `ANEXA NR. 2 au
   caracter...` (literă mică imediat după număr, fără virgulă). Toate trei
   trebuie să dea `search(...) is None`.
   **Ar pica dacă**: adăugarea suportului `NR.`/`Nr.` ar slăbi accidental
   lookahead-ul din R21 și ar accepta virgula sau litera mică drept titlu real,
   sau dacă regex-ul ar deveni case-insensitive din greșeală.

3. `test_anexa_nr_cu_capitol_omonim_in_corp_nu_se_confunda_regresie_p118_2`
   Regresia reală din P 118/2, reprodusă sintetic: capitol `33.1.` în corp
   (înainte de orice anexă) + `ANEXA NR.33` + articole interne `33.1.`, `33.2.`,
   `33.3.`. Verifică prin `creeaza_chunkuri` (end-to-end, nu doar regex) că:
   - `33.1.` din corp rămâne neschimbat și conține textul lui;
   - anexa produce `ANEXA 33.`, `ANEXA 33.33.1.`, `ANEXA 33.33.2.`,
     `ANEXA 33.33.3.`, fiecare cu textul corect (niciun fragment pierdut/contopit).
   **Ar pica dacă**: `ANEXA NR.33` nu ar fi recunoscută ca titlu de anexă (caz în
   care articolele ei ar rămâne `33.1.`/`33.2.`/`33.3.` neprefixate și s-ar
   contopi cu capitolul din corp prin `articol_baza` identic — exact bug-ul din
   regresia reală), sau dacă vreun text ar lipsi din chunk-urile rezultate.

4. `test_forme_vechi_de_anexa_fara_nr_raman_neschimbate`
   `ANEXA 3 - TITLU TREI` urmat de `ANEXA 3.1. - SUBSECTIUNE`, fără `NR.`/`Nr.`,
   end-to-end prin `creeaza_chunkuri`. Verifică `ANEXA 3.` și `ANEXA 3.1.` ca
   identificatori distincți, fiecare cu conținutul corect.
   **Ar pica dacă**: modificarea regex-ului ar altera în vreun fel formele vechi
   (ex. ar cere acum `NR.` obligatoriu, sau ar rupe compunerea identificatorului
   pentru variantele cu subnivel zecimal).

## Ce nu am acoperit și de ce

- **Documentele reale (cele 9 + P 118/2 integral)**: task-ul cere teste
  *sintetice*; comparația cu documentele reale (`extracted.txt`, `duplicate_eliminate`,
  acoperirea 0.9902) e responsabilitatea planner-ului, care rulează comenzi — eu
  nu am acces la shell și nu citesc integral fișiere mari.
- **`_este_titlu_anexa_de_cuprins` cu forma `ANEXA NR.`** (cuprins de anexe scrise
  cu `NR.`, ex. `ANEXA NR. 1 ..... 239`): task-ul nu a cerut explicit acest caz,
  iar coder-ul a semnalat în raportul lui că nu l-a verificat prin rulare. Nu am
  adăugat test pentru el ca să nu depășesc scopul primit — dacă planner-ul vrea
  acoperire aici, e un test suplimentar de adăugat separat.
- **Contractul importerului** (`populare_db.py:64-66`, regex `^[a-z0-9().-]+$` pe
  identificatorul normalizat): coder-ul a verificat manual pe hârtie că
  `anexa33.33.5` trece; nu am adăugat un test dedicat fiindcă nu era în lista
  celor 4 puncte cerute și ar testa `populare_db`, nu `chunking_core`.

## Suspiciuni de bug
Niciuna găsită în timpul scrierii testelor — comportamentul descris de coder în
raportul lui (compunerea `ANEXA {anexa_curenta}.{articol_baza}`) corespunde cu
codul citit din `chunking_core.py` (liniile ~592-657, funcția care produce
segmentele) și cu testele scrise mai sus, construite să verifice exact acel
mecanism pe cazul nou (`NR.`).

## Comanda pentru planner
```
pytest D:\Omnia-MVP-r28\tests\test_r28_anexa_nr.py -v
```
(și, pentru siguranță, întreaga suită `chunking_core`: `pytest D:\Omnia-MVP-r28\tests\test_chunking_core.py D:\Omnia-MVP-r28\tests\test_r28_anexa_nr.py -v`)
