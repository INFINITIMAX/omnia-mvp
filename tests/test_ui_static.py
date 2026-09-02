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


def test_raspuns_si_citari_randate_prin_textcontent():
    assert "answer.textContent = text;" in SCRIPT
    assert "item.textContent" in SCRIPT
    assert "citation.cod_document" in SCRIPT
    assert "citation.titlu_document" in SCRIPT
    assert "citation.articol" in SCRIPT
    assert "citation.citat" in SCRIPT


def test_js_nu_citeste_cookie_httponly():
    assert "document.cookie" not in SCRIPT


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
