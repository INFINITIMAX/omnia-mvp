# R26-C — Coder: raport (D27 — proveniența modificărilor în citare)

## Fișiere modificate

### `generation_core.py`
- Adăugat `_MODIFICATION_MARKER` (regexul din spec) și helper-ul `_modification_markers(content)`, care întoarce marcajele distincte (fără paranteze drepte), în ordinea apariției, folosind `dict.fromkeys` pentru deduplicare.
- `PublicCitation` primește câmpul `modificari: tuple[str, ...] = ()`.
- În `GenerationService.generate`, la construirea `citations`, `modificari` se derivă din `evidence_by_id[citation_id].content` (dovada completă citată, nu doar pasajul/citatul), deci server-side, independent de răspunsul modelului.
- Prompt: adăugată regula `11` (după regula 10, înainte de `<intrebare_json>`), care instruiește modelul să menționeze explicit când o dovadă conține marcaj `[Text modificat/introdus prin ...]` sau `[Abrogat prin ...]`. Celelalte reguli nu au fost atinse.

### `main.py`
- `CitationResponse` primește `modificari: list[str] = Field(default_factory=list)`.
- `from_public` schimbat din `cls(**citation.__dict__)` în `cls(**{**citation.__dict__, "modificari": list(citation.modificari)})`, ca tuple-ul din `PublicCitation` să ajungă listă (pydantic ar fi coercizat oricum tuple→list, dar am făcut conversia explicit, conform cerinței din task).

### `static/index.html`
- CSS: adăugată clasa `.art-mod` (font mono, 11px, `--paper-quiet`, `overflow-wrap: anywhere`) — stil discret, coerent cu `.art-doc`/`.art-ref-id`, plasată imediat după `.art-quote`.
- JS (`setMessage`): după randarea `citation.citat`, pentru fiecare `citation.modificari` (array verificat cu `Array.isArray`, fiecare element validat ca string nevid) se creează un `<p class="art-mod">` cu `textContent = modificare`, adăugat în `article`. Exclusiv `createElement`/`textContent`, fără `innerHTML`.

## CSP — atenție pentru planner
Am modificat **atât** blocul `<style>` (adăugarea regulii `.art-mod`), **cât și** blocul `<script>` (adăugarea buclei `citation.modificari.forEach(...)` în `setMessage`) din `static/index.html`. Ambele hash-uri trebuie recalculate în `main.py`:
- `_CSP_SCRIPT_HASHES` (linia ~519, comentariu `static/index.html <script>`)
- prima intrare din `_CSP_STYLE_HASHES` (linia ~521, comentariu `static/index.html <style>`)

Nu am rulat nimic (nu am acces la shell) — hash-urile vechi au rămas neschimbate în cod; planner-ul trebuie să le regenereze, altfel pagina se rupe sub CSP.

## Decizii neincluse explicit în task
- Regula de prompt a fost numerotată `11` (task-ul nu preciza numărul); am ales să o adaug la final, ca să nu perturb numerotarea/referințele existente din regulile 1-10.
- În `from_public` am făcut conversia explicit la `list(...)`, deși pydantic ar fi convertit oricum un `tuple` la `list[str]` — am urmat exact atenționarea din task, nu am lăsat-o pe seama coerciției implicite.

## Ce nu am făcut
- Nu am scris teste (nu e rolul meu).
- Nu am atins `retrieval_core.py`, `chunking_core.py`, `retrieval_eval.py`, `supabase/`, `.env`, `documente_noi/`, sau fișierele coder-ului paralel (`extragere_mo_bis.py`, `diacritice.py`, `populare_db.py`).
- Nu am recalculat hash-urile CSP (nu pot rula comenzi) — vezi secțiunea de mai sus.

## Ce ar trebui verificat de planner
- Recalcularea și actualizarea `_CSP_SCRIPT_HASHES` și primei intrări din `_CSP_STYLE_HASHES` în `main.py`, apoi verificare manuală că pagina se încarcă sub CSP (fără erori în consolă de tip „Refused to execute/apply”).
- Rulare teste existente pentru `generation_core.py` și `main.py` (contractul D20/D22/D26 — pasaj literal, ≥1 citare, `gasit` — nu a fost atins structural, dar merită confirmare).
- Verificare că regexul `_MODIFICATION_MARKER` se potrivește exact cu marcajele efective puse de planner în textul consolidat (format `nr.`, spații, puncte din numărul ordinului).
