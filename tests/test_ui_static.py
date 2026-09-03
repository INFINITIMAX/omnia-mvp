"""Teste statice pentru static/index.html: contract UI, fără server sau browser real."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

INDEX_PATH = Path(__file__).resolve().parents[1] / "static" / "index.html"
HTML = INDEX_PATH.read_text(encoding="utf-8")


def _script_body() -> str:
    match = re.search(r"<script>(.*)</script>", HTML, re.S)
    assert match is not None, "index.html trebuie să conțină un bloc <script> inline"
    return match.group(1)


SCRIPT = _script_body()


# ---------- Contract text și quota ----------

def test_text_initial_limita_exact():
    assert 'Limită: 10 întrebări/browser' in HTML


def test_quota_ulterior_foloseste_intrebari_ramase():
    assert "data.intrebari_ramase" in SCRIPT
    assert "Number.isInteger(data.intrebari_ramase)" in SCRIPT


def test_fara_localstorage_sau_ghicit_quota():
    assert "localStorage" not in SCRIPT
    assert "sessionStorage" not in SCRIPT


# ---------- 403 / 429 / 422 / 503 / rețea ----------

def test_403_blocheaza_permanent_si_seteaza_quota_din_payload():
    assert "response.status === 403" in SCRIPT
    match = re.search(r"if \(response\.status === 403\) \{(.*?)\n        \}", SCRIPT, re.S)
    assert match is not None, "handlerul 403 trebuie identificat pentru verificări stricte"
    block = match.group(1)
    assert "permanentlyLocked = true;" in block
    # quota trebuie citită și validată din body, nu hardcodată ca literal sursă a lock-ului
    assert "Number.isInteger(data.intrebari_ramase)" in block
    assert "data.intrebari_ramase === 0" in block
    assert "`Întrebări rămase: ${data.intrebari_ramase}/browser`" in block


def test_403_cu_payload_invalid_nu_blocheaza_permanent():
    match = re.search(r"if \(response\.status === 403\) \{(.*?)\n        \}", SCRIPT, re.S)
    assert match is not None
    block = match.group(1)
    # dacă JSON e invalid/lipsă sau intrebari_ramase nu e exact 0, nu se blochează și nu se tratează payload-ul ca valid
    assert "readSafeJson(response)" in block
    assert "data !== null" in block
    assert re.search(r"if \(!quotaValid\) \{\s*setMessage\(pendingBody, GENERIC_ERROR\);\s*return;\s*\}", block)
    # linia care blochează permanent apare numai după verificarea quotaValid
    lock_index = block.index("permanentlyLocked = true;")
    guard_index = block.index("if (!quotaValid)")
    assert guard_index < lock_index


def test_429_foloseste_retry_after_numeric_pozitiv_si_lock_temporar():
    assert "response.status === 429" in SCRIPT
    assert "retryAfterSeconds" in SCRIPT
    assert "lockTemporarily" in SCRIPT
    # numai secunde întregi pozitive; nicio interpretare de tip dată calendaristică
    assert re.search(r"\^\[1-9\]\\d\*\$", SCRIPT), "Retry-After trebuie validat strict ca întreg pozitiv"
    assert "Date.parse" not in SCRIPT


def test_422_are_mesaj_clar_dedicat():
    assert "response.status === 422" in SCRIPT
    assert "nu este validă" in SCRIPT


def test_503_si_retea_si_json_invalid_au_mesaj_generic_fara_status_sau_exceptii():
    generic_occurrences = SCRIPT.count("GENERIC_ERROR")
    # folosit atât pentru !response.ok (503/alte erori HTTP), cât și în catch (rețea/JSON invalid)
    assert generic_occurrences >= 3
    assert "String(eroare)" not in SCRIPT
    assert "String(error)" not in SCRIPT
    assert re.search(r"catch\s*\(_\)\s*\{\s*setMessage\(pendingBody,\s*GENERIC_ERROR\);", SCRIPT)


# ---------- Guard click / Enter / chips ----------

def test_form_submit_previne_default_si_are_guard_comun():
    assert "questionForm.addEventListener('submit'" in SCRIPT
    assert "event.preventDefault();" in SCRIPT
    assert "requestActive || permanentlyLocked || temporarilyLocked" in SCRIPT


def test_chips_sunt_ghidate_prin_aceeasi_functie_sendquestion():
    assert "chips.forEach((chip) => {" in SCRIPT
    assert "chip.addEventListener('click', () => sendQuestion(chip.textContent));" in SCRIPT
    assert "chip.addEventListener('keydown'" in SCRIPT


def test_input_si_buton_se_dezactiveaza_in_timpul_cererii():
    assert "inputEl.disabled = disabled;" in SCRIPT
    assert "sendBtn.disabled = disabled;" in SCRIPT


# ---------- maxlength ----------

def test_input_are_maxlength_1000():
    assert re.search(r'id="questionInput"[^>]*maxlength="1000"', HTML)


# ---------- Randare sigură (fără innerHTML pentru date server/user) ----------

def test_fara_innerhtml_in_tot_scriptul():
    assert "innerHTML" not in SCRIPT


@pytest.mark.parametrize(
    "unsafe",
    ["innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "createContextualFragment"],
)
def test_fara_html_brut_in_tot_fisierul(unsafe):
    # Plasă de siguranță împotriva unei regresii viitoare: verifică tot fișierul
    # (nu doar blocul <script>), pentru cazul în care s-ar adăuga un alt <script>
    # sau un atribut inline care ar reintroduce un vector de injectare de marcaj.
    assert unsafe not in HTML


def test_raspuns_si_citari_randate_prin_textcontent():
    # Răspunsul e randat printr-un parser Markdown propriu (renderMarkdown), care
    # construiește exclusiv noduri DOM cu createElement și pune text doar prin
    # textContent/createTextNode — niciodată prin marcaj brut.
    assert "function renderMarkdown(container, text)" in SCRIPT
    assert "parent.appendChild(document.createTextNode(" in SCRIPT
    assert "strong.textContent = match[1];" in SCRIPT
    # Citarea nu mai este o singură linie de text: redesign-ul o culege ca într-un
    # standard tipărit (referință agățată în margine + corp), deci fiecare câmp public
    # are propriul element. Aserțiunea rămâne aceeași ca fond și este întărită:
    # fiecare câmp trebuie să ajungă în DOM printr-o atribuire `.textContent`.
    for field, assignment in (
        ("articol", "articleNo.textContent = `Art. ${citation.articol}`;"),
        ("cod_document", "documentCode.textContent = citation.cod_document || 'Document oficial';"),
        ("titlu_document", "title.textContent = citation.titlu_document || '';"),
        ("citat", "quote.textContent = citation.citat;"),
    ):
        assert f"citation.{field}" in SCRIPT
        assert assignment in SCRIPT
    # Nicio cale alternativă de injectare de marcaj pentru date de la server.
    for unsafe in (
        "innerHTML",
        "outerHTML",
        "insertAdjacentHTML",
        "document.write",
        "createContextualFragment",
        "srcdoc",
    ):
        assert unsafe not in SCRIPT
    # Niciun `citation.<câmp>` nu este folosit în altă parte decât într-o atribuire
    # `.textContent` sau într-un simplu guard de prezență.
    for match in re.finditer(r"citation\.\w+", SCRIPT):
        start = SCRIPT.rfind("\n", 0, match.start()) + 1
        end = SCRIPT.find("\n", match.end())
        line = SCRIPT[start:end].strip()
        assert ".textContent =" in line or line.startswith("if (citation."), line


def test_js_nu_citeste_cookie_httponly():
    assert "document.cookie" not in SCRIPT


# ---------- Fonturi self-hostate (fără procesator terț nedeclarat în GDPR) ----------

FONTS_DIR = INDEX_PATH.parent / "assets" / "fonts"


def test_pagina_nu_incarca_niciun_font_de_pe_cdn_tert():
    for host in ("fonts.googleapis.com", "fonts.gstatic.com", "cdnjs", "jsdelivr", "unpkg"):
        assert host not in HTML
    # nicio referință absolută către alt origin, indiferent de schemă
    assert not re.search(r'(?:src|href)\s*[:=]\s*["\']?(?:https?:)?//', HTML)


def test_fiecare_font_face_indica_un_fisier_local_existent():
    sources = re.findall(r'src:\s*url\("([^"]+)"\)', HTML)
    assert len(sources) >= 6, "cele trei familii trebuie declarate self-hostat"
    for source in sources:
        assert source.startswith("/assets/fonts/"), source
        assert (FONTS_DIR / Path(source).name).is_file(), source


def test_fonturile_au_licenta_versionata():
    assert (FONTS_DIR / "LICENSE.txt").is_file()


# ---------- Linkuri către paginile juridice ----------

def test_footerul_are_linkuri_catre_paginile_juridice():
    assert re.search(r'<a href="/termeni">[^<]+</a>', HTML)
    assert re.search(r'<a href="/confidentialitate">[^<]+</a>', HTML)


# ---------- Elemente demo/false eliminate ----------

@pytest.mark.parametrize(
    "forbidden",
    [
        "247",
        "demoIndexed",
        "doc-popover",
        "docPopover",
        "docSearch",
        "Contul meu",
        "new-convo",
        "convo-item",
        "convo-list",
        "Stări limită</div>",
        "CR 0-2012",
    ],
)
def test_elemente_demo_eliminate(forbidden):
    assert forbidden not in HTML


def test_vizitator_anonim_si_badge_neutru():
    assert "Vizitator anonim" in HTML
    assert "Documente aprobate" in HTML
    assert "documente indexate" not in HTML


# ---------- Fără conturi/istoric/endpointuri suplimentare/persistență ----------

def test_fara_endpointuri_sau_persistenta_neautorizate():
    for forbidden in ("/documents", "/health", "Access-Control", "fetch('/documents')", "fetch('/health')"):
        assert forbidden not in HTML
        assert forbidden not in SCRIPT
    assert "fetch('/intreaba'" in SCRIPT


# ---------- Accesibilitate ----------

def test_aria_live_si_disabled_coerente():
    assert 'role="log"' in HTML
    assert 'aria-live="polite"' in HTML
    assert "chip.setAttribute('aria-disabled'" in SCRIPT


def test_questioninput_are_label_accesibil_asociat():
    match = re.search(r'<label[^>]*\bfor="questionInput"[^>]*>(.*?)</label>', HTML, re.S)
    assert match is not None, "questionInput trebuie să aibă un <label for=\"questionInput\"> asociat"
    assert match.group(1).strip() != ""


# ---------- Randare Markdown (renderMarkdown) ----------

_MARKDOWN_HARNESS = r"""
class Node {
  constructor() { this.children = []; this.className = ''; this._text = ''; }
  appendChild(n) { this.children.push(n); return n; }
  append(...ns) { ns.forEach(n => this.children.push(n)); }
  replaceChildren() { this.children = []; }
  set textContent(v) { this._text = v; this.children = []; }
  get textContent() {
    if (this.children.length) return this.children.map(c => c.textContent !== undefined ? c.textContent : c.data).join('');
    return this._text;
  }
}
class TextNode { constructor(d) { this.data = d; } get textContent() { return this.data; } }

function stubEl() {
  const n = new Node();
  n.addEventListener = () => {};
  n.setAttribute = () => {};
  n.classList = { toggle() {} };
  n.style = {};
  return n;
}

global.document = {
  createElement(tag) { const n = new Node(); n.tag = tag; return n; },
  createTextNode(d) { return new TextNode(d); },
  getElementById() { return stubEl(); },
  querySelectorAll() { return []; },
};
global.window = { setTimeout: () => {} };

const fs = require('fs');
const html = fs.readFileSync(process.argv[2], 'utf-8');
const m = html.match(/<script>([\s\S]*)<\/script>/);
eval(m[1]);

function describe(node) {
  if (node instanceof TextNode) return { text: node.data };
  const children = node.children.map(describe);
  const result = { tag: node.tag, className: node.className, children };
  if (children.length === 0) result.text = node._text;
  return result;
}

const cases = JSON.parse(fs.readFileSync(process.argv[3], 'utf-8'));
const results = cases.map((markdown) => {
  const container = document.createElement('div');
  let threw = null;
  try {
    renderMarkdown(container, markdown);
  } catch (e) {
    threw = String(e && e.message || e);
  }
  return { threw, tree: describe(container) };
});
process.stdout.write(JSON.stringify(results));
"""


def _run_markdown_cases(cases):
    node = shutil.which("node")
    if node is None:
        pytest.skip("node nu este disponibil în acest mediu")
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        harness_path = Path(tmp) / "harness.js"
        cases_path = Path(tmp) / "cases.json"
        harness_path.write_text(_MARKDOWN_HARNESS, encoding="utf-8")
        cases_path.write_text(json.dumps(cases), encoding="utf-8")
        result = subprocess.run(
            [node, str(harness_path), str(INDEX_PATH), str(cases_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _flatten_tags(node):
    tags = [node.get("tag")] if "tag" in node else []
    for child in node.get("children", []):
        tags.extend(_flatten_tags(child))
    return tags


def _flatten_text(node):
    if not node.get("children"):
        return node.get("text") or ""
    return "".join(_flatten_text(child) for child in node["children"])


def test_markdown_titluri_folosesc_h3_h4_nu_h1_h2():
    results = _run_markdown_cases(["## Titlu principal", "### Subtitlu secundar"])
    assert results[0]["threw"] is None
    assert "h3" in _flatten_tags(results[0]["tree"])
    assert "h1" not in _flatten_tags(results[0]["tree"])
    assert "h2" not in _flatten_tags(results[0]["tree"])
    assert results[1]["threw"] is None
    assert "h4" in _flatten_tags(results[1]["tree"])


def test_markdown_bold_produce_strong():
    [result] = _run_markdown_cases(["Text cu **cuvânt important** în mijloc."])
    assert result["threw"] is None
    assert "strong" in _flatten_tags(result["tree"])
    assert _flatten_text(result["tree"]) == "Text cu cuvânt important în mijloc."


def test_markdown_liste_neordonate_si_ordonate():
    results = _run_markdown_cases(["- unu\n- doi\n- trei", "1. primul\n2. al doilea"])
    assert results[0]["threw"] is None
    assert "ul" in _flatten_tags(results[0]["tree"])
    assert _flatten_tags(results[0]["tree"]).count("li") == 3
    assert results[1]["threw"] is None
    assert "ol" in _flatten_tags(results[1]["tree"])
    assert _flatten_tags(results[1]["tree"]).count("li") == 2


def test_markdown_tabel_randat_cu_wrapper_scrollabil():
    markdown = "| Coloană A | Coloană B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"
    [result] = _run_markdown_cases([markdown])
    assert result["threw"] is None
    tags = _flatten_tags(result["tree"])
    assert "table" in tags
    assert tags.count("tr") == 3  # 1 header + 2 rânduri
    assert "thead" in tags and "tbody" in tags
    # containerul de scroll orizontal e clasa dedicată, nu tabelul direct
    assert result["tree"]["children"][0]["className"] == "msg-table-wrap"


@pytest.mark.parametrize(
    "markdown",
    [
        "| a | b | c |\n|---|---|---|\n| 1 | 2 |\n| x | y | z | w |",  # coloane inegale
        "**bold neînchis, fără asterisc final",
        "###",
        "###fără spațiu",
        "",
        "   \n\n   ",
        "* item fără spațiu dublu\n* al doilea",
        "1.fara spatiu dupa punct",
    ],
)
def test_markdown_cazuri_malformate_nu_arunca_si_nu_pierd_tot_continutul(markdown):
    [result] = _run_markdown_cases([markdown])
    assert result["threw"] is None, f"randarea a aruncat pentru: {markdown!r}"


def test_markdown_text_gol_produce_container_gol_fara_eroare():
    [result] = _run_markdown_cases([""])
    assert result["threw"] is None
    assert result["tree"]["children"] == []


# ---------- Sintaxă JS ----------

def test_javascript_extras_este_sintactic_valid():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node nu este disponibil în acest mediu")
    result = subprocess.run(
        [node, "--check", "-"],
        input=SCRIPT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr
