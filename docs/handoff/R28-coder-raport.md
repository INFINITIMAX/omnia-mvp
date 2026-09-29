# R28 — Coder: raport

## Fișier modificat
`D:\Omnia-MVP-r28\chunking_core.py` — doar `PATTERN_TITLU_ANEXA` (linia ~46-53, plus comentariul de deasupra).

## Ce am schimbat
```python
PATTERN_TITLU_ANEXA = re.compile(
    r"\n[ \t]*ANEXA[ \t]+(?:(?:NR\.|Nr\.)[ \t]*)?"
    r"(\d+(?:\.\d+)?(?:\.?\([A-Za-z]\))?(?:bis|[A-Za-z])?)\.?[ \t]*"
    r"(?=[\-–]|[A-ZĂÂÎȘȚŞŢ]|$)",
    re.MULTILINE,
)
```
Față de varianta din `main`:
- am adăugat, între `ANEXA` și numărul capturat, un grup necapturat opțional `(?:NR\.|Nr\.)[ \t]*` — acceptă `NR.`/`Nr.` cu sau fără spațiu în continuare (`ANEXA NR. 1`, `ANEXA NR.14bis`, `ANEXA Nr. 3`), dar nu și alte capitalizări (`nr.`, `Nr`, fără punct etc.), exact cum cerea task-ul;
- în grupul capturat, sufixul de literă unică `[A-Za-z]?` a devenit `(?:bis|[A-Za-z])?` — încearcă întâi `bis` (P 118/2: `14bis`), apoi cade pe litera unică deja existentă (`3.1.(a)b` etc., dacă mai există undeva). Identificatorul rămâne numărul/sufixul (`33`, `14bis`), fără `NR.`/`Nr.` în el, deci articolele din anexă tot devin `ANEXA 33.33.5.` etc.
- restul tiparului (grupurile `(?:\.\d+)?`, `(?:\.?\([A-Za-z]\))?`, punctul opțional final, lookahead-ul pe `-`/`–`/majusculă/`$`) rămâne neschimbat — nu am atins logica de regiune din R21 (liniile 588-640 nu au fost atinse).

## Verificare manuală pe fragmentele citite din `extracted.txt`
- `ANEXA NR. 1` (rândul 11241): `ANEXA` + spațiu + `NR.` + spațiu + `1`, urmat de rând nou → se potrivește, grupul capturat = `"1"`.
- `ANEXA NR.14bis` (rândul 11932): `NR.` lipit, apoi `14bis` → grupul capturat = `"14bis"` (alternativa `bis` se potrivește complet, nu doar litera `b`).
- `ANEXA NR.32` / `ANEXA NR.33` (rândurile 13749, 13754): analog, grupul capturat = `"32"` / `"33"`; pentru Anexa 33, definițiile `33.1.`… vor primi prefixul `ANEXA 33.` (compus cu `_baza_articol` în logica existentă, neatinsă), deci devin `ANEXA 33.33.1.` etc., conform criteriului de acceptare.
- Am verificat că textul din corp `anexa nr. 8, la…` (literă mică) nu e afectat: `ANEXA` cu majuscule e literal în regex, deci trimiterile scrise cu literă mică rămân excluse ca înainte.

## Contractul importerului
`populare_db.py:64-66`: `articol.lower()` + eliminare spații + `rstrip(".")`, verificat cu `^[a-z0-9().-]+$`. Grupul capturat de `PATTERN_TITLU_ANEXA` nu conține niciodată `NR`/`Nr` (sunt în afara grupului), deci identificatorul rămâne format doar din cifre, punct și eventual litere ASCII din `bis`/sufixul unic — `anexa33.33.5` trece testul, la fel ca înainte de schimbare.

## Ce nu am făcut / nu am putut verifica
- Nu am rulat comenzi (interzis prin task): nu am confirmat compilarea regex-ului, numărul de cuvinte pierdute, valoarea `duplicate_eliminate` sau chunk-urile celorlalte 9 documente. Planner-ul trebuie să ruleze `chunking_core` pe P 118/2 și pe restul documentelor `approved` cu `extracted.txt` și să compare cu `main`.
- Nu am citit integral `extracted.txt`; am verificat doar fragmentele indicate (~11235-11250, ~11925-11940, ~13745-13800). Dacă mai există variante de titlu de anexă în alte zone ale documentului (ex. `ANEXA NR 4` fără punct, sau litere de capitalizare diferite), nu au fost verificate — planner-ul ar trebui să caute `grep -n "ANEXA NR" extracted.txt` complet dacă vrea siguranță totală.
- Nu am atins `_este_titlu_anexa_de_cuprins` / `_linia_anterioara_indica_continuare_anexa` / logica de regiune (R21) — funcțiile existente operează generic pe `PATTERN_TITLU_ANEXA.match(...)`, deci ar trebui să funcționeze neschimbate pentru noile forme, dar nu am putut confirma prin rulare (ex. dacă P 118/2 are un cuprins cu intrări `ANEXA NR. 1 ..... 239`, trebuie verificat că `_este_titlu_anexa_de_cuprins` le exclude corect).
- Nu am scris teste (rolul tester-ului).

## Ce ar trebui verificat de planner
1. Rulare chunking pe P 118/2: articolele Anexei 33 apar ca `ANEXA 33.33.1.` … `ANEXA 33.33.19.`, capitolul 33 din corp rămâne `33.x.` (fără prefix), `duplicate_eliminate` scade față de `main`.
2. Comparație cuvânt-cu-cuvânt (fără marcaje) P 118/2 chunked pe `fix/r28-anexe-nr` vs `main` — niciun cuvânt pierdut.
3. Rulare pe celelalte 9 documente `approved` cu `extracted.txt` (inclusiv P 118/3) — chunk-uri identice cu `main` (regex-ul nou e strict mai permisiv, dar nu ar trebui să prindă nimic nou în ele dacă nu conțin `ANEXA NR`/`bis`; de verificat totuși explicit).
4. Import real/preflight pe un fragment cu `ANEXA 33.33.5.` normalizat → trece `[a-z0-9().-]+` (verificat pe hârtie mai sus, dar merită confirmat prin rulare).
