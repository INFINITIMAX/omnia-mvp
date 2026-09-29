# R29 — Tester: raport

## Fișier creat
`D:\Omnia-MVP-r29\tests\test_chunking_np127.py` — 7 teste noi, doar `creeaza_chunkuri`
și `acoperire_text_brut` din `chunking_core` (același stil ca `test_chunking_core.py`:
texte sintetice mici, un docstring „ar pica dacă...” per test).

Nu am atins `chunking_core.py` și nici `test_chunking_core.py`.

## Ce verifică fiecare test și ce l-ar face să cadă

1. `test_articolul_n_la_inceput_de_rand_devine_articol_cu_punct` — „Articolul 117 ...”
   la început de rând produce chunk unic cu `articol == "117."`, fără cuvântul
   „Articolul” în text. Ar cădea dacă marcajul nu s-ar recunoaște deloc, dacă
   punctul final nu s-ar adăuga, sau dacă „Articolul 117” ar rămâne în corpul textului.

2. `test_articolul_urmat_de_litera_mica_nu_devine_articol_nou` — „Articolul 117
   evacuarea...” (literă mică imediat după număr) nu deschide articol nou; textul
   rămâne un singur chunk „5.”. Ar cădea dacă lookahead-ul ar accepta și litere mici
   (ar apărea un al doilea chunk „117.”).

3. `test_articolul_in_mijlocul_frazei_nu_deschide_articol_nou` — „Articolul 6” în
   mijlocul unui rând (nu la început) rămâne text simplu. Ar cădea dacă regexul nu
   ar cere strict începutul de rând (ar apărea un chunk „6.” separat, rupând un
   singur chunk „5.” în două).

4. `test_titluri_capitol_si_sectiune_np127_elimina_dar_secretiune_fraza_ramane` —
   „Capitolul I ...”, „Secțiunea 1 ...”, „Secțiunea a 2-a ...” dispar complet din
   text și nu devin articole proprii (rămân doar `["1.", "2."]`); fraza obișnuită
   „Secțiunea conductelor se dimensionează...” (fără număr după „Secțiunea”) rămâne
   text, atașată ultimului articol. Ar cădea fie dacă titlurile ar rămâne în text /
   ar deveni chunk-uri separate, fie dacă fraza obișnuită ar fi eliminată din
   greșeală (regresie exact pentru cazul I5 semnalat de coder).

5. `test_plus_eliminat_inaintea_articolului_urmator` — un „+” pe rând propriu urmat
   de „Articolul 2” dispare din text. Ar cădea dacă separatorul ar rămâne în chunk.

6. `test_plus_pastrat_cand_e_parte_dintr_o_formula` — regresie directă pentru
   corectura planner #1: un „+” pe rând propriu într-o formulă (`a` / `+` / `b`,
   NU urmat de Articolul/Capitolul/Secțiunea) trebuie păstrat. Ar cădea dacă
   implementarea ar elimina orbește toate rândurile „+” (varianta inițială a
   coder-ului, respinsă de planner) — exact bug-ul pe care corectura 1 îl repară.

7. `test_acoperire_text_sintetic_format_np127_este_aproape_completa` — regresie
   directă pentru corectura planner #2: text sintetic în format NP 127 (articole +
   separatori „+”) dă acoperire ≥0.99. Ar cădea dacă `_normalizeaza_pentru_acoperire`
   nu ar scoate prefixul „Articolul N” din linia brută — exact mecanismul care
   producea acoperire 11% pe NP 127 înainte de corectură.

## Atenție la scriere — diacritice
Testele pentru „Secțiunea” folosesc explicit `ț` (nu litera simplă `t`), pentru că
`PATTERN_TITLU_SECTIUNE_NP127` cere caracterul cu diacritic (`Sec[țţ]iunea`) — am
verificat regexul din sursă înainte de a scrie testul, ca să nu obțin un test care
trece mereu din greșeală (linie „Sectiunea 1” fără diacritic nu s-ar potrivi
niciodată cu pattern-ul, indiferent de comportamentul real al codului).

## Ce nu am acoperit și de ce
- Nu am testat direct pe `documente_noi/np127_2009/extracted.txt` (interzis să citesc
  integral fișiere mari; task-ul cere teste sintetice, nu pe documentul real —
  verificarea pe documentul real revine preflight-ului planner-ului, deja descrisă
  în `R29-coder-raport.md`).
- Nu am testat separat cazul „+” la sfârșit de document (fără linie următoare
  nevidă) — comportamentul (păstrat, pentru că regexul de eliminare nu găsește
  un „următor” care să înceapă cu Articolul/Capitolul/Secțiunea) e acoperit
  implicit de aceeași ramură de cod ca testul 6, nu am dus-o ca test separat ca
  să nu multiplic teste redundante pe aceeași ramură.
- Nu am adăugat un test explicit pentru „Capitolul XIV Referințe tehnice...”
  lipit de tabelul de standarde (cazul semnalat de coder ca decizie nespecificată)
  — nu ține de cele 4 puncte din sarcina tester-ului; dacă planner-ul vrea o
  decizie fermă pe acel caz, e nevoie întâi de o regulă explicită în handoff,
  altfel orice test pe el ar fixa un comportament nespecificat.

## Suspiciuni de bug
Niciuna găsită prin citirea codului (`PATTERN_ARTICOL_NP127`,
`_elimina_marcaje_capitol_np127`, `_normalizeaza_pentru_acoperire`) — ambele
corecturi din handoff par implementate corect în `chunking_core.py` (liniile
74-86, 319-334, 816-825). Testele de mai sus sunt regresii care ar fi picat pe
varianta *dinaintea* corecturilor; planner-ul trebuie să le ruleze ca să confirme
că picã pe varianta veche și trec pe varianta curentă.

## Comanda pentru planner
```powershell
cd D:\Omnia-MVP-r29
python -m pytest -q tests/test_chunking_np127.py
```
(sau `python -m pytest -q` pentru tot suite-ul, ca să confirm și cele 1355 passed
existente rămân neafectate.)
