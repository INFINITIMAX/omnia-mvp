# R26-A — Coder: raport

## Fișiere

### `extragere_mo_bis.py` (nou)
- `incarca_tabela(cale=font_maps/mo_bis_glyph_map.json)`: citește `date["fonturi"]`, cheile GID convertite la `int`. Returnează direct `dict[str, dict[int, str]]` (nu structura brută JSON), la fel cum `glyph_mapping.incarca_tabela` transformă tabela sa înainte de a o întoarce.
- `harta_coduri(pdf_path, tabela)`: pentru fiecare font din PDF (nume complet, cu prefix de subset, din `page.get_fonts(full=True)[..][3]` via PyMuPDF — verificat că e aceeași convenție de nume ca `pdfplumber` `char["fontname"]`, dovedit funcțional în `proto_mo_bis.py`), citește `/Encoding`→`/Differences` din xref, respectă semantica PDF (număr = cod curent, fiecare `/gNNN` următor folosește codul și îl incrementează), și mapează GID (extras din `/gNNN`) prin `tabela[nume_bază]` la caracter. Rezultat: `cod -> caracter` per font.
- `extrage_text(pdf_path, tabela=None)`: pdfplumber pagină cu pagină, înlocuiește fiecare `(cid:N)` din `char["text"]` cu caracterul din hartă; nerezolvate → eliminate din output și numărate în `raport["nerezolvate"]["<font>:<cod>"]`. Pagini unite cu `\n`, apoi `diacritice.normalizeaza_diacritice`. Întoarce `(text, raport)`, `raport = {"nerezolvate": {...}, "pagini": n}`.
- CLI: `python extragere_mo_bis.py <pdf> <iesire.txt> [--raport <json>]`, scriere atomică (`.tmp` + `replace`), fără rețea/DB.
- Nu am folosit `fontTools`/`TTFont` (spre deosebire de prototip): tabela precomputată din JSON conține deja GID→caracter, deci nu mai e nevoie să citim fonturile Windows la runtime.

### `diacritice.py` (modificat)
- Adăugat `ǎ`(U+01CE)→`ă` și `Ǎ`(U+01CD)→`Ă` în `_SEDILA_LA_VIRGULA`, folosit de `normalizeaza_diacritice` (aceeași funcție, cum a cerut brief-ul).
- Am actualizat docstring-ul modulului și al funcției ca să reflecte cele 6 perechi (nu mai spune „strict patru perechi” / nu mai listează `ă` printre caracterele netratate, ca să nu contrazică codul). Nu am atins `_SUBSTITUIRI_PDF_LA_DIACRITICE` / `corecteaza_substituiri_pdf`.

### `populare_db.py` (modificat)
- Import: `from chunking_core import acoperire_text_brut, creeaza_chunkuri`.
- Argument nou `--document` (`action="append"`, dest `documente`), repetabil. Fără el, `args.documente` e `None` → comportament identic cu azi (niciun filtru).
- Filtrare: în bucla din `main()`, dacă `args.documente` e setat și `metadata["document_id"]` nu e în listă, se sare documentul (înainte de citirea/chunking-ul textului, ca să nu irosească timp pe documente excluse).
- În `--dry-run`: pentru fiecare document procesat, print suplimentar cu acoperirea (`chunking_core.acoperire_text_brut(continut, chunkuri)`, format procentual `.1%`).

## Decizii neincluse explicit în brief
- `incarca_tabela` întoarce `tabela["fonturi"]` transformat (nu tot obiectul JSON cu `_descriere`), pentru simetrie cu `harta_coduri(pdf_path, tabela)` care se așteaptă la `tabela[nume_font][gid]`.
- Filtrarea `--document` se face pe `metadata["document_id"]`, nu pe numele folderului (brief spune „limitează procesarea la acele foldere”, dar identificatorul e explicit `document_id`; foldere și `document_id` corespund 1:1 în `documente_noi/`, verificat prin `gaseste_documente()`/`metadata.json`).
- Am pus verificarea `--document` înaintea citirii `extracted.txt`, ca să nu facă I/O inutil pe documentele excluse — comportamentul „identic cu azi” fără flag e neschimbat.

## Ce nu am făcut
- N-am rulat nimic (Python, teste) — conform regulilor. N-am scris teste.
- N-am atins `chunking_core.py`, `retrieval_core.py`, `generation_core.py`, `main.py`, `static/`, `reimport_approved.py`, `supabase/`, `.env`, `font_maps/mo_bis_glyph_map.json`.

## Ce ar trebui verificat de planner
- Rulare reală: `python extragere_mo_bis.py documente_noi/p118_2_2013/source.pdf /tmp/out.txt --raport /tmp/raport.json` și compararea cu `proto_mo_bis.py` (0 nerezolvate pt. P118/2, 5 pt. P118/3).
- Confirmă că `char["fontname"]` din pdfplumber e identic ca string cu `page.get_fonts(full=True)[..][3]` din PyMuPDF pe ambele PDF-uri (am preluat convenția din prototip, dar n-am putut rula cod ca s-o reverific eu însumi).
- `populare_db.py --dry-run --document <id>` pe un document existent, ca să confirme filtrarea și noul print de acoperire.
- Import circular/lipsă: `extragere_mo_bis.py` importă `diacritice` (fără probleme, modul independent, fără dependențe către `extragere_mo_bis`).
