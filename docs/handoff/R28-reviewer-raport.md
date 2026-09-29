# R28 — Raport reviewer (transcris integral de planner)

VERDICT: ACCEPT

## Ce am verificat

### 1. Cod (`chunking_core.py`, coder)
Am comparat linie cu linie `D:\Omnia-MVP-r28\chunking_core.py` (liniile ~18-57) cu `D:\Omnia-MVP\chunking_core.py` (main, `ce4ebee`). Singura diferență e `PATTERN_TITLU_ANEXA` (plus comentariul explicativ deasupra) — exact scopul din `R28-coder.md`, nimic altceva atins:

```python
PATTERN_TITLU_ANEXA = re.compile(
    r"\n[ \t]*ANEXA[ \t]+(?:(?:NR\.|Nr\.)[ \t]*)?"
    r"(\d+(?:\.\d+)?(?:\.?\([A-Za-z]\))?(?:bis|[A-Za-z])?)\.?[ \t]*"
    r"(?=[\-–]|[A-ZĂÂÎȘȚŞŢ]|$)",
    re.MULTILINE,
)
```

Am urmărit regex-ul manual pe cazurile relevante din task:
- `ANEXA NR. 1`, `ANEXA NR.2`, `ANEXA Nr. 3`, `ANEXA NR.14bis` → se potrivesc, grup capturat fără `NR`/`Nr` (`"1"`, `"2"`, `"3"`, `"14bis"`).
- `anexa nr. 8, la clădirile...` (literă mică) → nu se potrivește (`ANEXA` majuscul e literal).
- `ANEXA Nr. 1/2` (format din `i13_2015_modificari`, disabled) → nu se potrivește: după „Nr. ” regexul cere o cifră, `\d+` prinde doar „1”, apoi lookahead-ul eșuează la „/” (nu e `-`, `–`, majusculă sau sfârșit de rând), iar varianta fără grupul opțional `NR.` eșuează imediat pe „N” (nu e cifră) — deci niciun fals pozitiv pe acest document, chiar dacă e disabled.
- Formele vechi (`ANEXA 3`, `ANEXA 3.1.`, litera unică `3a`) rămân neschimbate — grupul `NR.`/`Nr.` e opțional, iar `(?:bis|[A-Za-z])?` încearcă întâi „bis”, apoi cade pe litera unică, exact ca înainte pentru cazurile fără „bis”.

Nu am găsit cod inutil, abstracții în plus, sau atingeri ale logicii de regiune din R21 (liniile 588-640 neschimbate, verificat). Contractul importerului (`populare_db.py:64-66`, `^[a-z0-9().-]+$`) rămâne respectat — grupul capturat nu conține niciodată `NR`/`Nr`.

Rezultatele reale raportate de planner (P 118/2: 34 de anexe, Anexa 33 → `ANEXA 33.33.x.`, `duplicate_eliminate` 23→16, acoperire 0.9902, 0 cuvinte pierdute în afară de titluri mutate/subtitlul „TERMINOLOGIE”, celelalte 9 documente identice cu main) nu le pot re-rula (fără shell), dar sunt plauzibile și consistente cu comportamentul regexului verificat manual.

### 2. Teste (`tests/test_r28_anexa_nr.py`, tester)
4 teste, fiecare cu o condiție de eșec reală și distinctă:
1. `test_pattern_titlu_anexa_prinde_variantele_nr_si_bis` — regex direct, verifică grupul capturat exact (nu doar `is not None`). Ar pica dacă suportul NR/bis lipsește sau dacă identificatorul ar include „NR”.
2. `test_pattern_titlu_anexa_nu_prinde_trimiteri_din_corp_sau_forme_excluse` — 3 cazuri negative (literă mică, virgulă, literă mică fără virgulă), toate corect excluse de lookahead — am verificat manual că regexul chiar le respinge.
3. `test_anexa_nr_cu_capitol_omonim_in_corp_nu_se_confunda_regresie_p118_2` — end-to-end prin `creeaza_chunkuri`, reproduce exact regresia reală (capitol `33.x.` în corp + `ANEXA NR.33` cu articole `33.x.`); verifică atât identificatorii cât și conținutul text per chunk. Ar pica real dacă regexul nu recunoaște `ANEXA NR.33`.
4. `test_forme_vechi_de_anexa_fara_nr_raman_neschimbate` — regresie pentru formele fără `NR.`, tot end-to-end.

Nu sunt redundante — fiecare acoperă un unghi diferit (regex izolat / excludere / regresie reală / neregresie forme vechi). Convenția de import și apelare (`creeaza_chunkuri(text)`, chei `"articol"`/`"text"`) e identică cu `tests/test_chunking_core.py` existent — verificat. Niciun `toBeDefined()`/assert slab; toate verifică valori concrete.

Acoperire: cele 4 puncte cerute explicit în `R28-tester.md` sunt toate acoperite. Testerul a documentat explicit ce a lăsat afară (documentele reale — responsabilitatea planner-ului; `_este_titlu_anexa_de_cuprins` cu `ANEXA NR.` — nu era cerut; contractul importerului — nu era în listă) — decizii motivate, nu scăpări ascunse.

### 3. `HANDOFF.md` „START AICI” + `TASKS.md`
Verificat împotriva `docs/DECISIONS.md` (D23–D27) și `TASKS.md`:
- „36 de întrebări, versiune 1” — confirmat: `evaluare/set_aur.json` are 36 de intrări `"id":` (D25 menționa 30, deci setul a crescut între timp — nu e o contradicție, e o evoluție consistentă cu `TASKS.md` care spune tot „34/36”).
- Scripturile menționate există: `reimport_approved.py`, `supabase/migrations/20260929120000_approve_p118_2_si_p118_3.sql`.
- Fișierele din `D:\_scratch\omnia\` menționate în HANDOFF (`db_ro.py`, `smoke_r24.py`, `smoke_r26.py`, `r26/diag.py`, `r26/eval_*.json`, `R26-status.md`) există toate.
- `TASKS.md` „Stare curentă” e coerent cu `HANDOFF.md` (aceleași cifre: main `ce4ebee`, 34/36, R28 în lucru).
- `AGENTS.md` rolurile citate corespund descrierii fluxului din HANDOFF.

Nu am găsit afirmații inexacte sau lipsuri esențiale pentru un agent nou.

## Concluzie
Cod minimal și exact pe scopul cerut, fără cod inutil. Teste solide, fiecare cu o cauză de eșec reală, fără redundanță, acoperă tot ce a cerut task-ul. Documentația de predare (`HANDOFF.md`/`TASKS.md`) e corectă față de starea reală verificabilă.

**ACCEPT — poate merge la reimport P 118/2, fără remedieri necesare.**

---

## Decizia planner-ului (29-09-2026)
Accept. Merge în main, apoi reimport P 118/2 prin `reimport_approved.py` (poarta D24) și evaluare de căutare. Runtime-ul nu se schimbă (chunker-ul e folosit doar la import), deci nu e nevoie de deploy.
