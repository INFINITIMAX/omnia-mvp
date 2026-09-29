# R26-A — Coder: extragerea textului din PDF-urile „MO bis” (P 118/2, P 118/3)

Worktree: `D:\Omnia-MVP-r26`, branch `feat/r26-p118-consolidat` (din `main` `d3bd129`). Context complet: `docs/handoff/R26-spec.md`. Lucru autonom aprobat de Lucian (28-09-2026); fără DB/Voyage.

## Dovezi (planner)
- Sursele oficiale: `documente_noi/p118_2_2013/source.pdf` = MO nr. 595 bis/24-09-2013 (304 p.); `documente_noi/p118_3_2015/source.pdf` = MO nr. 243 bis/09-04-2015 (66 p.).
- PyMuPDF (`procesare_documente.extrage_text`) **pierde** ă/ș/ț/Ă/Ș/Ț (ex. „reelele de alimentare cu ap”). Fonturile sunt Type1 subset, cu `/Encoding /Differences` care numesc glifele `/gNNN` = GID din fontul Windows original, iar `ToUnicode` e inutil pentru ele. pdfplumber le raportează ca text `(cid:N)`, unde N = codul din `/Differences`.
- Planner a generat tabela `font_maps/mo_bis_glyph_map.json`: `fonturi[<nume font fără prefix de subset>][<GID ca text>] = caracter` (19 fonturi, 109 intrări, din fonturile Windows cu fontTools + Adobe Symbol/Wingdings). Prototipul planner (`D:\_scratch\omnia\proto_mo_bis.py`, citește-l) a produs text curat: P 118/2 cu 0 caractere nerezolvate, P 118/3 cu 5 (4 × MicrosoftYaHei cid 648, 1 × Wingdings cid 2 — simboluri decorative).

## Sarcina
1. Modul nou `extragere_mo_bis.py`:
   - `harta_coduri(pdf_path, tabela) -> dict[str, dict[int, str]]`: pentru fiecare font din PDF (nume **complet**, cu prefixul de subset, exact cum îl dă pdfplumber în `char["fontname"]`), cod `/Differences` → caracter, prin `/gNNN` → `tabela`. Parsarea `/Differences` trebuie să respecte semantica PDF: un număr setează codul curent, fiecare nume îl folosește și îl incrementează.
   - `extrage_text(pdf_path, tabela=None) -> tuple[str, dict]`: pdfplumber, pagină cu pagină; înlocuiește fiecare caracter `(cid:N)` cu caracterul din hartă; nerezolvate → eliminate și **numărate** în raport (`{"nerezolvate": {"<font>:<cod>": n}, "pagini": n}`). Textul paginilor e unit cu `\n`; apoi aplică `diacritice.normalizeaza_diacritice` (sedilă → virgulă).
   - `incarca_tabela(cale=font_maps/mo_bis_glyph_map.json)`, ca `glyph_mapping.incarca_tabela`.
   - CLI: `python extragere_mo_bis.py <pdf> <iesire.txt> [--raport <json>]`; scrie atomic; fără rețea/DB.
2. `diacritice.py`: adaugă `ǎ` (U+01CE) → `ă` și `Ǎ` (U+01CD) → `Ă` (apar în MO 595 bis ca glifă greșită pentru ă, ex. „mecanicǎ”, „siguranŃǎ”), în aceeași funcție. Nu schimba altceva.
3. `populare_db.py`: argument `--document <document_id>` (repetabil) care limitează procesarea la acele foldere; fără el, comportament identic cu azi. În `--dry-run`, afișează pe document și acoperirea `chunking_core.acoperire_text_brut(text, chunkuri)`.

## Constrângeri
- Nu atinge `retrieval_core.py`, `generation_core.py`, `main.py`, `static/`, `chunking_core.py`, `reimport_approved.py`, `supabase/`, `.env`. Nu modifica `font_maps/mo_bis_glyph_map.json`.
- Nu rula comenzi. Nu scrie teste (tester-ul). Fără comentarii inutile; stilul fișierelor vecine (română, docstring-uri scurte).
- Raport: `docs/handoff/R26-A-coder-raport.md` (fișiere, decizii, ce ai verificat prin citire).
