# R29 — Coder: raport

## Fișier modificat
`D:\Omnia-MVP-r29\chunking_core.py` — singurul fișier atins, conform constrângerii.

## Ce am adăugat

1. **`PATTERN_ARTICOL_NP127`** (lângă celelalte regexuri de articol, ~L68-76): recunoaște
   `Articolul N` (N întreg, la început de rând, urmat de spațiu apoi majusculă/„/() — format
   unic acestui normativ, confirmat prin grep pe toate `documente_noi/*/extracted.txt`.
   Grupul capturat e doar cifra, fără punct; `_baza_articol` (deja existent) îi adaugă punctul
   final, deci identificatorul rezultat e „117.”, „129.” etc. — exact contractul cerut la
   punctul 1 din task. Am înregistrat-o în uniunea de marcaje din `_extrage_segmente` (lângă
   `PATTERN_ARTICOL_FARA_PUNCT`); restul mecanismului (construcția `articol_baza`, verificarea
   generică `_este_referinta_rupta`/`_este_data_zi_luna_an`, limita de 1000, split secundar) e
   reutilizat neschimbat — nu am adăugat nicio ramură specială pentru acest pattern în bucla de
   asamblare a segmentelor.

2. **`PATTERN_TITLU_CAPITOL_NP127`** și **`PATTERN_TITLU_SECTIUNE_NP127`** + funcția nouă
   **`_elimina_marcaje_capitol_np127`** (lângă `_elimina_titluri_capitol_roman`, aceeași
   tehnică: filtrare linie-cu-linie, rândul întreg e eliminat înainte de segmentare, nu devine
   niciodată articol sau chunk propriu). Acoperă atât „Capitolul I Dispoziții generale” /
   „Capitolul XIV Referințe tehnice și legislative …”, cât și „Secţiunea 1 …” / „Secţiunea a
   2-a …” (ambele forme de diacritice ț/ţ, ambele forme de numerotare secțiune). Aceeași funcție
   elimină și rândurile formate doar din „+” (`PATTERN_LINIE_SEPARATOR_PLUS`), cerute la punctul 3.
   Apelată în `creeaza_chunkuri` imediat după `_elimina_titluri_capitol_roman`.

## Verificări de siguranță făcute (fără să rulez cod, doar `grep`/citire)
- `^Articolul \d+ ` și `^Capitolul\s+[IVXLC]+\s` apar **doar** în `np127_2009/extracted.txt`
  printre toate documentele — zero risc pentru celelalte 12.
- `^Sec[țţ]iunea` apare și în `i5_2022/extracted.txt`, dar acolo e „Secțiunea conductelor se...”
  (frază obișnuită, nu urmată de un număr) — regexul meu cere explicit un număr sau „a N-a” după
  „Secţiunea”, deci nu se potrivește acolo; I5 rămâne neatins.
- Am citit integral toate liniile `Articolul`/`Capitolul`/`Secţiunea` din NP 127 (via grep) ca
  să confirm formatul e uniform (mereu la început de rând, mereu urmat de majusculă sau „(”),
  fără excepții care ar cere logică suplimentară de „referință ruptă”.

## Decizie luată, nespecificată explicit în task
„Capitolul XIV Referințe tehnice și legislative 1. Standarde Nr.” e o singură linie „murdară”
din extragere (titlul de capitol lipit de începutul tabelului de standarde, fără „+” separator).
Am eliminat-o integral ca rând de titlu (ca pe celelalte capitole), ceea ce înseamnă că tot
tabelul de referințe care urmează (fără niciun marcaj „Articolul” în el) rămâne atașat, ca
text, la articolul „173.” (ultimul articol real dinaintea lui) și va fi tăiat în bucăți ≤1000
de `_aplica_limita_caractere`, toate cu identificatorul „173.”. Nu pierde conținut (bun pentru
acoperire), dar înseamnă că „173.” devine, în date, un articol cu mai multe chunk-uri, ultimele
fiind de fapt tabelul de standarde. Nu există altă informație în task despre cum ar trebui
tratat acest tabel, iar criteriile de acceptare nu cer nimic specific despre el — semnalez
totuși, ca planner-ul să decidă dacă e acceptabil sau dacă preferă un identificator propriu de
tip „Capitolul XIV.” pentru acest tabel (ar necesita cod suplimentar, nu l-am scris).

## Ce nu am făcut
- Nu am scris teste (rolul tester-ului).
- Nu am rulat nimic (nu am acces la shell) — nu pot confirma efectiv acoperirea 0.95, numărul
  exact de articole 1–173, sau conținutul literal al chunk-urilor 117/129/130.
- Nu am propagat textul titlurilor de „Capitolul”/„Secţiunea” ca context în corpul articolelor
  copil — am ales eliminarea completă a rândului (ca `_elimina_titluri_capitol_roman`), nu
  propagare de context, considerând-o interpretarea mai simplă și mai sigură a cerinței „sunt
  titluri, context pentru articolele-copil, nu articole” (vezi motivația de mai sus: articolele
  1–173 sunt numerotate plat, fără nicio relație de prefix numeric cu „Capitolul I”/„Secţiunea
  1”, deci mecanismul existent de propagare — bazat pe prefixe numerice comune — nu se poate
  reutiliza fără logică paralelă nouă; eliminarea simplă e exact tehnica deja folosită de
  `_elimina_titluri_capitol_roman` pentru alt format de titlu de capitol). Dacă planner-ul
  consideră că propagarea de context e obligatorie, retrimiteți task-ul — implementarea ei ar
  necesita o funcție nouă de urmărire pozițională (nu bazată pe prefix), aproximativ 20-30 de
  linii.

## Ce ar trebui verificat de planner
- Rulare preflight/import pe `documente_noi/np127_2009/extracted.txt`: 173 articole distincte
  „1.” … „173.”, fără „+” în text, acoperire ≥ 0.95.
- Am citit direct în sursă (linia 268, 292, 294 din `extracted.txt`) conținutul cerut de
  criteriile de acceptare: „Articolul 117” conține „600 mc/h”, „sprinkler” și „900 mc/h” (sursa
  scrie unitatea „mc/h”, nu „m3/h” cum apare în textul task-ului, dar sensul e identic — de
  verificat totuși explicit la testare, ca nu cumva importerul/testul să caute literal „m3/h”);
  „Articolul 129” conține „8,00 m față de orice construcție supraterană”; „Articolul 130” conține
  „8,00 m” (prizele de aer proaspăt). Segmentarea pe aceste trei articole nu are nimic special
  fizic în sursă (fiecare pe un rând propriu, urmat de „+”), deci regexul nou ar trebui să le
  separe corect ca „117.”, „129.”, „130.” — planner-ul trebuie să confirme cu preflight-ul.
- Reimport pe celelalte 12 documente: chunk-uri identice cu `main` (regex-urile noi sunt
  restrânse strict la formatul unic NP 127, dar merită confirmarea automată).
