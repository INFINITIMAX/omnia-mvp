# R26 — Tester, runda 2: raport

Nu am rulat comenzi. Am scris exclusiv în `tests/`. Mai jos, fișier cu fișier, ce
verifică fiecare test nou și ce schimbare de cod l-ar face să pice.

## `tests/test_chunking_core.py` (adăugat import + 5 teste noi, la final)

Import nou: `_propaga_marcaj_provenienta`, `_respecta_limita_cu_marcaje` (funcții
private din `chunking_core`).

**Decizie de testare:** am testat direct funcțiile private, nu prin
`creeaza_chunkuri` de la un capăt la altul. Motiv: scenariul din spec (un punct
despărțit pe alineate de `_aplica_split_secundar`) cere un chunk de bază de
minimum 2000 de caractere ca să declanșeze split-ul secundar — construirea unui
astfel de text real prin tot pipeline-ul (antete, titluri, split) ar face
testul fragil și greu de citit, fără nicio garanție suplimentară față de a
apela direct funcția care conține exact logica cerută de reviewer, cu aceleași
chei de articol (`"3.3.1.(1)"`/`"(2)"`/`"(4)"`) pe care le-ar produce
`_aplica_split_secundar`.

1. `test_propaga_marcaj_pe_punct_despartit_in_mai_multe_alineate` — 3 bucăți ale
   aceluiași articol de bază, doar una are marcajul original „Text modificat”.
   Verifică: celelalte două primesc exact `[Articol cu text modificat prin
   Ordinul nr. ...]` pe rând propriu; bucata cu marcajul original NU primește
   dublura (`text_2.count("[") == 1`).
   **Ar pica dacă:** gruparea după articolul de bază ar rata (ex. regex-ul
   `_PATTERN_SUFIX_ALINEAT_PROVENIENTA` ar înceta să strippeze `(N)`), sau dacă
   bucata cu marcajul original ar primi și ea propagarea.

2. `test_propaga_marcaj_articol_fara_niciun_marcaj_ramane_byte_identic` — un
   articol fără niciun marcaj de proveniență rămâne complet neatins
   (`rezultat == chunkuri`, comparație exactă de listă).
   **Ar pica dacă:** funcția ar adăuga vreun rând în absența oricărui marcaj.

3. `test_propaga_doua_marcaje_diferite_deduplicat_in_ordinea_primei_aparitii` —
   3 bucăți, una cu „Abrogat”, una cu „Text modificat”, una fără nimic.
   Verifică: fiecare bucată primește doar dublurile pe care nu le are deja;
   bucata fără niciun marcaj propriu primește ambele, în ordinea primei
   apariții în listă (abrogat înaintea lui modificat, nu ordine alfabetică).
   **Ar pica dacă:** deduplicarea pe `(adjectiv, rest)` nu ar funcționa, sau
   dacă ordinea ar deveni alfabetică/inversă.

4. `test_respecta_limita_cu_marcaje_reimparte_bucata_care_depaseste_1000` — un
   text de ~993 caractere (sub 1000) primește marcajul propagat (+110 caractere)
   și depășește limita; verifică: re-împărțire în ≥2 bucăți, toate ≤1000,
   fiecare cu marcajul, niciun cuvânt din textul original pierdut (verificare
   cuvânt-cu-cuvânt pe reconstrucție).
   **Ar pica dacă:** re-splitul nu ar respecta limita, ar pierde conținut, sau
   nu ar propaga marcajul pe fiecare bucată rezultată.

## `tests/test_citation_modificari.py` (3 constante noi + 3 teste noi, întărire pe unul existent)

1. `test_promptul_contine_regula_11_despre_marcajele_de_provenienta` — adăugat
   `assert "Articol cu text" in prompt`.
   **Ar pica dacă:** mențiunea „Articol cu text” ar fi ștearsă din regula 11
   (exact golul semnalat de reviewer: testul vechi trecea și fără ea).

2. `test_marcaj_articol_forma_modificat_ajunge_in_modificari` — o dovadă cu
   DOAR forma propagată `[Articol cu text modificat prin Ordinul ...]` (nicio
   formă originală) → `PublicCitation.modificari == (marcajul_articol,)`.
   **Ar pica dacă:** `_MODIFICATION_MARKER` n-ar mai recunoaște prefixul
   „Articol cu text”.

3. `test_marcaj_articol_toate_cele_trei_forme_sunt_recunoscute` — toate cele
   trei variante „Articol cu text modificat/introdus/abrogat” în aceeași
   dovadă → toate trei apar în `modificari`, în ordinea apariției.
   **Ar pica dacă:** oricare dintre cele trei alternative ar lipsi din regex,
   sau ordinea nu ar fi păstrată.

## `tests/test_consolidare_normative.py` (2 teste noi, `abroga_subunitate`)

1. `test_abroga_subunitate_alineat` — abrogă alineatul (1) al punctului 1.2 din
   `baza_simpla`. Verifică: `(1) Abrogat.` prezent, textul vechi dispărut,
   marcajul `[Abrogat prin Ordinul nr. ...]` prezent, restul punctului (alineat
   (2) cu literele a/b/c) rămâne intact.
   **Ar pica dacă:** localizarea alineatului ar rata, textul vechi ar
   supraviețui, sau marcajul ar lipsi.

2. `test_abroga_subunitate_litera` — abrogă litera b) a alineatului (2).
   Verifică: `b) Abrogat.` + marcaj prezente, textul vechi al lui b) dispărut,
   a) și c) neatinse.
   **Ar pica dacă:** localizarea literei ar confunda b) cu a)/c), sau marcajul
   ar lipsi.

## `tests/test_extragere_mo_bis.py` (fișier nou, 9 teste)

Fără PDF real: `fitz.open` și `pdfplumber.open` monkeypatch-uite cu obiecte
false care expun exact suprafața de API folosită (`page.get_fonts(full=True)`,
`document.xref_object`, `document.close`; `pdf.pages`, `page.chars`).
`extract_text` (importat din `pdfplumber.utils` în `extragere_mo_bis`) e
înlocuit cu o concatenare simplă — algoritmul de layout geometric real al
pdfplumber nu e obiectul acestor teste; obiectul e rezolvarea `(cid:N)` și
raportul.

1. `test_harta_coduri_respecta_semantica_differences` — `/Differences [1 /g10
   /space /g12 5 /g20]`, tabelă cu GID 10→ă, 12→ț, 20 absent. Verifică pas cu
   pas semantica cerută: număr→cod curent (1→cod 1, 5→cod 5), fiecare nume
   (inclusiv `/space`, non-`gNNN`) incrementează codul chiar dacă nu are
   mapare, GID absent (20) rămâne nemapat. Verifică și `document.close()`
   apelat.
   **Ar pica dacă:** parsarea `/Differences` n-ar incrementa codul la un nume
   non-`gNNN`, sau ar mapa un GID absent din tabelă.

2. `test_harta_coduri_font_fara_differences_produce_harta_goala` — font
   standard fără `/Encoding`+`/Differences` → hartă goală, fără eroare.
   **Ar pica dacă:** codul ar arunca excepție pe un font fără `/Differences`.

3. `test_incarca_tabela_converteste_cheile_gid_la_int` — JSON temporar cu chei
   string → verifică conversia la `int`.
   **Ar pica dacă:** conversia la `int` ar fi eliminată sau greșit aplicată.

4. `test_incarca_tabela_reala_contine_timesnewromanpsmt_259_si_288` — pe
   `font_maps/mo_bis_glyph_map.json` real: `TimesNewRomanPSMT[259] == "ă"`,
   `[288] == "ţ"` (sedilă, normalizată ulterior).
   **Ar pica dacă:** tabela reală ar fi regenerată greșit sau `incarca_tabela`
   ar altera valorile citite.

5. `test_extrage_text_rezolva_cid_din_harta` — `(cid:5)` cu hartă `{"FontA":
   {5:"ă"}}` → rezolvat corect, `raport["nerezolvate"] == {}`.

6. `test_extrage_text_cid_nerezolvat_e_eliminat_si_numarat` — două `(cid:7)`
   nerezolvate → eliminate din text, `raport["nerezolvate"] == {"FontB:7": 2}`.
   **Ar pica dacă:** caracterele nerezolvate n-ar fi eliminate sau numărătoarea
   cheii `font:cod` ar fi greșită.

7. `test_extrage_text_aplica_normalizarea_diacriticelor` — text cu sedilă
   (`ş`, `ţ`) → normalizat la virgulă (`ș`, `ț`) în textul final.
   **Ar pica dacă:** `normalizeaza_diacritice` n-ar mai fi apelată în
   `extrage_text`.

8. `test_extrage_text_rand_cu_numar_lipit_de_antet_devine_doua_randuri` —
   `"2 MONITORUL OFICIAL AL ROMÂNIEI, PARTEA I, Nr. 595 bis/24.IX.2013"` →
   despărțit în două rânduri (număr, apoi antet).
   **Ar pica dacă:** corectura `_PATTERN_PAGINA_LIPITA_DE_ANTET` ar fi ștearsă
   sau modificată.

9. `test_extrage_text_rand_cu_numar_fara_antet_ramane_neatins` — un rând care
   începe cu număr dar nu e urmat de antetul MO rămâne neschimbat.
   **Ar pica dacă:** regex-ul ar deveni prea agresiv și ar despărți orice rând
   numeric.

## `tests/test_populare_db.py` (3 teste noi + helper `_scrie_document`)

1. `test_document_filtreaza_procesarea_la_documentele_date` — 3 documente pe
   disc, `--document documentA --document documentC` (repetabil) → doar A și C
   apar în output, B absent, `"DRY RUN: 2 chunk-uri validate din 2 documente"`.
   **Ar pica dacă:** filtrul `--document` n-ar exclude documentB, sau n-ar
   include ambele documente cerute.

2. `test_fara_argument_document_proceseaza_toate_documentele` — regresie: fără
   `--document`, ambele documente apar (comportament identic cu azi).
   **Ar pica dacă:** absența flagului ar filtra totuși ceva.

3. `test_dry_run_afiseaza_acoperirea_fara_client_db_sau_voyage` — `--dry-run
   --document documentA` cu `voyageai.Client` și `conecteaza_baza_de_date`
   monkeypatch-uite să arunce `AssertionError` dacă sunt apelate. Verifică:
   `"acoperire text brut:"` apare în output, cu `"100.0%"` (linia din
   `extracted.txt` are peste 50 de caractere, deci trece prin comparația reală
   din `acoperire_text_brut`, nu prin cazul trivial `total == 0`).
   **Ar pica dacă:** `--dry-run` n-ar mai afișa acoperirea, sau ar ajunge să
   construiască efectiv un client Voyage/DB.

## Ce nu am acoperit și de ce

- Nu am adăugat teste end-to-end prin `creeaza_chunkuri` pentru scenariul
  multi-alineat (motivat mai sus — necesită chunk de bază ≥2000 caractere;
  testele directe pe `_propaga_marcaj_provenienta`/`_respecta_limita_cu_marcaje`
  acoperă exact logica cerută, fără fragilitatea unui text sintetic uriaș).
- Nu am rulat `python extragere_mo_bis.py` pe PDF-urile reale (P 118/2, P
  118/3) — task-ul cere explicit „fără PDF real”; verificarea cu sursele reale
  rămâne, cum spune și raportul coder-ului, în sarcina planner-ului.
- Nu am adăugat test pentru cazul în care `page.get_fonts(full=True)` conține
  același font pe mai multe pagini (linia `if nume_complet in harta: continue`
  din `harta_coduri`) — comportament de optimizare, nu de corectitudine; nu are
  impact observabil asupra rezultatului final.
- N-am atins testele cu skip pe `documente_noi` (fișiere reale) — task-ul cere
  explicit sintetic, cu fișierele reale doar opțional.

## Suspiciuni de bug — niciuna nouă

N-am găsit cod nou suspect de bug în această rundă. Singura observație (nu e
bug): în `_respecta_limita_cu_marcaje`, când o bucată depășește limita chiar și
fără niciun marcaj propagat propriu (caz care nu apare în fluxul normal, dar
teoretic posibil dacă cineva ar apela funcția direct cu un chunk >1000 fără
niciun marcaj în el), `adaugate` ar fi listă goală și funcția s-ar comporta ca
`_aplica_limita_caractere` obișnuit — comportament corect, nu l-am semnalat ca
problemă.

## Comanda pentru planner

```powershell
cd D:\Omnia-MVP-r26
pytest tests/test_chunking_core.py tests/test_citation_modificari.py tests/test_consolidare_normative.py tests/test_extragere_mo_bis.py tests/test_populare_db.py -v
```

(sau `pytest` fără argumente pentru toată suita, ca să confirme și că n-am stricat nimic existent).
