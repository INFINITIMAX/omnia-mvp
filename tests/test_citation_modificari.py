"""D27: proveniența modificărilor în citare (`PublicCitation.modificari`).

Verifică exclusiv contractul public al `GenerationService.generate` (nu funcția
internă `_modification_markers`): marcajele sunt derivate server-side din
`Evidence.content` al dovezii citate, niciodată din răspunsul/pasajele modelului.
"""

import json

import pytest

from generation_core import GenerationService
from retrieval_core import Evidence


QUESTION = "Ce prevede articolul consolidat?"

MARKER_MODIFICAT = (
    "Text modificat prin Ordinul nr. 6.025/2018, publicat în Monitorul Oficial "
    "nr. 977 din 19.11.2018"
)
MARKER_INTRODUS = (
    "Text introdus prin Ordinul nr. 6.026/2018, publicat în Monitorul Oficial "
    "nr. 966 din 15.11.2018"
)
MARKER_ABROGAT = (
    "Abrogat prin Ordinul nr. 6.026/2018, publicat în Monitorul Oficial "
    "nr. 966 din 15.11.2018"
)
# D27 Runda 2: forma propagată de `chunking_core._propaga_marcaj_provenienta` la
# nivel de articol (nu direct pe textul afectat).
MARKER_ARTICOL_MODIFICAT = (
    "Articol cu text modificat prin Ordinul nr. 6.025/2018, publicat în "
    "Monitorul Oficial nr. 977 din 19.11.2018"
)
MARKER_ARTICOL_INTRODUS = (
    "Articol cu text introdus prin Ordinul nr. 6.026/2018, publicat în "
    "Monitorul Oficial nr. 966 din 15.11.2018"
)
MARKER_ARTICOL_ABROGAT = (
    "Articol cu text abrogat prin Ordinul nr. 6.026/2018, publicat în "
    "Monitorul Oficial nr. 966 din 15.11.2018"
)


class RawGenerator:
    """Transport literal: întoarce exact payloadul dat, fără reparare/selecție."""

    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def generate(self, prompt, *, max_tokens):
        self.calls += 1
        return self.payload


def make_evidence(index, content):
    return Evidence(
        chunk_id=index,
        document_id=f"document-fictiv-{index}",
        cod_document=f"P118-{index}",
        titlu_document=f"Document fictiv {index}",
        articol=f"{index}.1",
        articol_normalizat=f"{index}.1",
        content=content,
        content_hash=f"hash-fictiv-{index}",
    )


def encode_payload(answer, passages, gasit=True):
    return json.dumps({"raspuns": answer, "pasaje": passages, "gasit": gasit}, ensure_ascii=False)


def _generate(evidence, answer, passages):
    generator = RawGenerator(encode_payload(answer, passages))
    result = GenerationService(generator).generate(QUESTION, evidence)
    assert generator.calls == 1
    return result


def test_marcaj_unic_in_dovada_citata_ajunge_in_modificari_fara_paranteze():
    quote = "Condiția tehnică rămasă neschimbată din articol."
    content = f"[{MARKER_MODIFICAT}]\n{quote}"
    evidence = (make_evidence(1, content),)

    result = _generate(evidence, f"{quote} [C1]", [{"id": "C1", "citat": quote}])

    assert result.citari[0].modificari == (MARKER_MODIFICAT,)


def test_marcaje_identice_repetate_devin_o_singura_intrare():
    quote = "Textul final citat de model."
    content = f"[{MARKER_MODIFICAT}]\nText intermediar.\n[{MARKER_MODIFICAT}]\n{quote}"
    evidence = (make_evidence(1, content),)

    result = _generate(evidence, f"{quote} [C1]", [{"id": "C1", "citat": quote}])

    assert result.citari[0].modificari == (MARKER_MODIFICAT,)


def test_marcaje_diferite_pastreaza_ordinea_aparitiei_nu_alfabetica():
    quote = "Fragment citat pentru test."
    # Abrogat apare textual înaintea lui Text introdus în conținut, deci ordinea
    # așteptată e (Abrogat, Text introdus), nu ordinea alfabetică sau cea din regex.
    content = f"[{MARKER_ABROGAT}]\n[{MARKER_INTRODUS}]\n{quote}"
    evidence = (make_evidence(1, content),)

    result = _generate(evidence, f"{quote} [C1]", [{"id": "C1", "citat": quote}])

    assert result.citari[0].modificari == (MARKER_ABROGAT, MARKER_INTRODUS)


def test_toate_cele_trei_variante_de_marcaj_sunt_recunoscute():
    quote = "Fragment citat final."
    content = f"[{MARKER_MODIFICAT}]\n[{MARKER_INTRODUS}]\n[{MARKER_ABROGAT}]\n{quote}"
    evidence = (make_evidence(1, content),)

    result = _generate(evidence, f"{quote} [C1]", [{"id": "C1", "citat": quote}])

    assert result.citari[0].modificari == (MARKER_MODIFICAT, MARKER_INTRODUS, MARKER_ABROGAT)


def test_marcaj_doar_in_alta_dovada_necitata_nu_apare_la_citarea_curenta():
    quote_c1 = "Text simplu, fără nicio modificare."
    evidence = (
        make_evidence(1, quote_c1),
        make_evidence(2, f"[{MARKER_MODIFICAT}]\nAlt fragment, necitat."),
    )

    result = _generate(evidence, f"{quote_c1} [C1]", [{"id": "C1", "citat": quote_c1}])

    assert len(result.citari) == 1
    assert result.citari[0].id == "C1"
    assert result.citari[0].modificari == ()


@pytest.mark.parametrize(
    "invalid_text",
    [
        # Ordinul înlocuit cu Legea: alternanta regexului cere "Ordinul".
        "[Text modificat prin Legea nr. 6.025/2018, publicat în Monitorul Oficial nr. 977 din 19.11.2018]",
        # Lipsește "publicat în".
        "[Text modificat prin Ordinul nr. 6.025/2018 din Monitorul Oficial nr. 977 din 19.11.2018]",
        # Fără paranteze drepte deloc.
        "Text modificat prin Ordinul nr. 6.025/2018, publicat în Monitorul Oficial nr. 977 din 19.11.2018",
        # Paranteză de deschidere lipsă.
        "Text modificat prin Ordinul nr. 6.025/2018, publicat în Monitorul Oficial nr. 977 din 19.11.2018]",
    ],
)
def test_text_asemanator_dar_invalid_este_ignorat(invalid_text):
    quote = "Fragment citat, indiferent de textul invalid alăturat."
    content = f"{invalid_text}\n{quote}"
    evidence = (make_evidence(1, content),)

    result = _generate(evidence, f"{quote} [C1]", [{"id": "C1", "citat": quote}])

    assert result.citari[0].modificari == ()


def test_marcaj_scris_de_model_in_raspuns_dar_absent_din_dovada_nu_apare():
    # Modelul "inventează" (halucinează) un marcaj în textul răspunsului, dar
    # dovada propriu-zisă nu-l conține deloc: server-side, modificari rămâne ().
    quote = "Fragment literal prezent în dovadă, fără niciun marcaj."
    evidence = (make_evidence(1, quote),)
    answer = f"{quote} [{MARKER_MODIFICAT}] [C1]"

    result = _generate(evidence, answer, [{"id": "C1", "citat": quote}])

    assert result.citari[0].modificari == ()
    assert f"[{MARKER_MODIFICAT}]" in result.raspuns


def test_marcaj_scris_de_model_in_pasaj_dar_absent_din_dovada_nu_apare():
    # De data asta marcajul apare în `citat`-ul propus de model (nu literal în
    # dovadă, deci serverul îl înlocuiește cu un extras literal) — indiferent,
    # `modificari` se calculează exclusiv din `Evidence.content`, nu din pasaj.
    real_quote = "Fragment literal prezent în dovadă, fără niciun marcaj."
    evidence = (make_evidence(1, real_quote),)
    fabricated_quote = f"[{MARKER_MODIFICAT}] {real_quote}"

    result = _generate(
        evidence, f"{real_quote} [C1]", [{"id": "C1", "citat": fabricated_quote}]
    )

    assert result.citari[0].modificari == ()


def test_promptul_contine_regula_11_despre_marcajele_de_provenienta():
    evidence = (make_evidence(1, "Conținut oarecare."),)
    prompt = GenerationService._build_prompt(QUESTION, tuple(("C1", item) for item in evidence))

    assert "11." in prompt
    assert "Text modificat/introdus prin Ordinul" in prompt
    assert "Abrogat prin Ordinul" in prompt
    # D27 Runda 2: întărire cerută de reviewer — mențiunea propagată la nivel de
    # articol trebuie să apară explicit, nu doar formele originale de mai sus
    # (care existau și înainte de adăugarea D-coder-ului). Ar pica dacă textul
    # "Articol cu text" ar fi șters din prompt.
    assert "Articol cu text" in prompt


# --- D27 Runda 2: forma "Articol cu text ..." (propagată la nivel de articol) -


def test_marcaj_articol_forma_modificat_ajunge_in_modificari():
    """O dovadă care are DOAR forma propagată la nivel de articol (nu marcajul
    original pe textul afectat) trebuie să producă `modificari` cu acel text.
    Ar pica dacă `_MODIFICATION_MARKER` nu ar mai recunoaște prefixul „Articol
    cu text”, sau dacă `_adjectiv_provenienta`/regex-ul ar altera textul."""
    quote = "Alineat fără marcaj propriu, dintr-un articol modificat în altă parte."
    content = f"[{MARKER_ARTICOL_MODIFICAT}]\n{quote}"
    evidence = (make_evidence(1, content),)

    result = _generate(evidence, f"{quote} [C1]", [{"id": "C1", "citat": quote}])

    assert result.citari[0].modificari == (MARKER_ARTICOL_MODIFICAT,)


def test_marcaj_articol_toate_cele_trei_forme_sunt_recunoscute():
    quote = "Fragment citat final, dintr-un articol cu mai multe modificari."
    content = (
        f"[{MARKER_ARTICOL_MODIFICAT}]\n[{MARKER_ARTICOL_INTRODUS}]\n"
        f"[{MARKER_ARTICOL_ABROGAT}]\n{quote}"
    )
    evidence = (make_evidence(1, content),)

    result = _generate(evidence, f"{quote} [C1]", [{"id": "C1", "citat": quote}])

    assert result.citari[0].modificari == (
        MARKER_ARTICOL_MODIFICAT, MARKER_ARTICOL_INTRODUS, MARKER_ARTICOL_ABROGAT,
    )
