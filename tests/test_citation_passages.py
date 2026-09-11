"""Contract RED R06, exclusiv sintetic; diagnosticul R05 nu impune publicarea în CI."""

import json

import pytest

from generation_core import GeneratedText, GenerationService, GenerationValidationError
from retrieval_core import Evidence


QUESTION = "Ce culoare are carcasa fictivă?"
PASSAGE_C1 = "Carcasa fictivă este turcoaz."
PASSAGE_C2 = "Capacul fictiv este violet."
EXACT_WHITESPACE = "  Șurubul\t fictiv\neste îngust.  "
INVENTED_REFERENCE = " Conform STAS 987654321."
EXPECTED_TRUNCATION_NOTICE = (
    "**Răspuns scurtat; reformulează întrebarea mai punctual pentru un răspuns complet.**"
)


class RawGenerator:
    """Returnează payloadul ales literal, fără selecție/reparare pe baza promptului."""

    def __init__(self, payload):
        self.payload = payload
        self.calls = 0
        self.token_limits = []

    def generate(self, prompt, *, max_tokens):
        self.calls += 1
        self.token_limits.append(max_tokens)
        return self.payload


def make_evidence(index, content):
    """Metadata fictivă distinctă permite verificarea mapării făcute de backend."""
    return Evidence(
        chunk_id=index,
        document_id=f"document-fictiv-intern-{index}",
        cod_document=f"DEMO-{index}",
        titlu_document=f"Document fictiv {index}",
        articol=f"{index}.1",
        articol_normalizat=f"{index}.1",
        content=content,
        content_hash=f"hash-fictiv-{index}",
    )


@pytest.fixture
def evidence_pair():
    # Pasajul C1 nu există în prefix; C2 nu există deloc în dovada C1.
    return (
        make_evidence(
            1,
            "Introducere fictivă. " * 40
            + PASSAGE_C1
            + "\n"
            + EXACT_WHITESPACE
            + "\n"
            + "x" * 601,
        ),
        make_evidence(2, "Introducere separată. " + PASSAGE_C2),
    )


def encode_payload(answer, passages):
    # Serializarea este doar transport: citatele sunt alese explicit de fiecare caz.
    return json.dumps({"raspuns": answer, "pasaje": passages}, ensure_ascii=False)


def assert_rejected_once(payload, evidence, expected_type=None):
    generator = RawGenerator(payload)
    with pytest.raises(GenerationValidationError) as caught:
        GenerationService(generator).generate(QUESTION, evidence)
    assert generator.calls == 1
    assert generator.token_limits == [1200]
    if expected_type is not None:
        # Numele sunt clase tipate deja existente; nu importăm excepții R06 inexistente.
        assert type(caught.value).__name__ == expected_type


def test_citation_passages_selecteaza_literal_dincolo_de_600_fara_prefix(evidence_pair):
    answer = f"{PASSAGE_C1} [C1]"
    generator = RawGenerator(encode_payload(answer, [{"id": "C1", "citat": PASSAGE_C1}]))
    assert evidence_pair[0].content.index(PASSAGE_C1) > 600

    result = GenerationService(generator).generate(QUESTION, evidence_pair)

    assert result.status == "answered"
    assert result.raspuns == answer
    assert len(result.citari) == 1
    citation = result.citari[0]
    assert citation.citat == PASSAGE_C1
    assert citation.citat in evidence_pair[0].content
    assert citation.citat != evidence_pair[0].content[:600]
    assert vars(citation) == {
        "id": "C1",
        "cod_document": evidence_pair[0].cod_document,
        "titlu_document": evidence_pair[0].titlu_document,
        "articol": evidence_pair[0].articol,
        "citat": PASSAGE_C1,
    }
    assert generator.calls == 1
    assert generator.token_limits == [1200]


def test_citation_passages_c2_foloseste_numai_dovada_corespunzatoare(evidence_pair):
    answer = f"{PASSAGE_C2} [C2]"
    generator = RawGenerator(encode_payload(answer, [{"id": "C2", "citat": PASSAGE_C2}]))
    assert PASSAGE_C2 not in evidence_pair[0].content

    result = GenerationService(generator).generate(QUESTION, evidence_pair)

    assert result.raspuns == answer
    assert len(result.citari) == 1
    assert vars(result.citari[0]) == {
        "id": "C2",
        "cod_document": evidence_pair[1].cod_document,
        "titlu_document": evidence_pair[1].titlu_document,
        "articol": evidence_pair[1].articol,
        "citat": PASSAGE_C2,
    }
    assert result.citari[0].citat in evidence_pair[1].content
    assert generator.calls == 1


@pytest.mark.parametrize("answer_id,passage_id", [("c1", "C1"), ("C1", "c1"), ("c1", "c1")])
def test_citation_passages_id_case_insensitive(evidence_pair, answer_id, passage_id):
    answer = f"{PASSAGE_C1} [{answer_id}]"
    generator = RawGenerator(
        encode_payload(answer, [{"id": passage_id, "citat": PASSAGE_C1}])
    )

    result = GenerationService(generator).generate(QUESTION, evidence_pair)

    assert result.raspuns == answer
    assert [(c.id, c.citat) for c in result.citari] == [("C1", PASSAGE_C1)]
    assert result.citari[0].citat in evidence_pair[0].content
    assert generator.calls == 1


def test_citation_passages_ordinea_primei_utilizari_nu_ordinea_listei(evidence_pair):
    answer = f"{PASSAGE_C2} [c2] {PASSAGE_C1} [C1] Repetare [C2] [c1]."
    generator = RawGenerator(encode_payload(answer, [
        {"id": "C1", "citat": PASSAGE_C1},
        {"id": "C2", "citat": PASSAGE_C2},
    ]))

    result = GenerationService(generator).generate(QUESTION, evidence_pair)

    assert result.raspuns == answer
    assert [(c.id, c.citat, c.cod_document) for c in result.citari] == [
        ("C2", PASSAGE_C2, evidence_pair[1].cod_document),
        ("C1", PASSAGE_C1, evidence_pair[0].cod_document),
    ]
    assert generator.calls == 1


def test_citation_passages_accepta_exact_600_caractere(evidence_pair):
    quote = "x" * 600
    generator = RawGenerator(encode_payload("Marcaj fictiv [C1]", [{"id": "C1", "citat": quote}]))
    assert quote in evidence_pair[0].content

    result = GenerationService(generator).generate(QUESTION, evidence_pair)

    assert len(result.citari) == 1
    assert result.citari[0].citat == quote
    assert len(result.citari[0].citat) == 600
    assert result.raspuns == "Marcaj fictiv [C1]"
    assert generator.calls == 1


def test_citation_passages_pastreaza_spatii_tab_newline_si_diacritice(evidence_pair):
    answer = "Șurubul fictiv este îngust. [C1]"
    payload = encode_payload(answer, [{"id": "C1", "citat": EXACT_WHITESPACE}])
    generator = RawGenerator(" \t\r\n" + payload + "\n\t ")
    assert EXACT_WHITESPACE in evidence_pair[0].content

    result = GenerationService(generator).generate(QUESTION, evidence_pair)

    assert result.raspuns == answer
    assert result.citari[0].citat == EXACT_WHITESPACE
    assert generator.calls == 1


# Fiecare caz rulează și cu o referință inventată în răspuns: pasajul invalid
# trebuie oprit înainte ca validatorul vechi de referințe să poată face retry.
@pytest.mark.parametrize("reference_suffix", ["", INVENTED_REFERENCE], ids=["fara-referinta", "inainte-de-retry"])
@pytest.mark.parametrize("passages", [
    pytest.param([], id="id-lipsa"),
    pytest.param(None, id="lista-null"),
    pytest.param("C1", id="lista-string"),
    pytest.param({}, id="lista-obiect"),
    pytest.param(1, id="lista-numar"),
    pytest.param(True, id="lista-bool"),
    pytest.param([None], id="intrare-null"),
    pytest.param(["C1"], id="intrare-string"),
    pytest.param([[]], id="intrare-lista"),
    pytest.param([{}], id="intrare-goala"),
    pytest.param([{"id": "C1"}], id="citat-lipsa"),
    pytest.param([{"citat": PASSAGE_C1}], id="id-camp-lipsa"),
    pytest.param([{"id": "C9", "citat": PASSAGE_C1}], id="id-necunoscut"),
    pytest.param([{"id": "C2", "citat": PASSAGE_C2}], id="c1-lipsa-c2-nefolosit"),
    pytest.param([
        {"id": "C1", "citat": PASSAGE_C1},
        {"id": "C2", "citat": PASSAGE_C2},
    ], id="id-cunoscut-nefolosit-extra"),
    pytest.param([
        {"id": "C1", "citat": PASSAGE_C1},
        {"id": "C9", "citat": PASSAGE_C1},
    ], id="id-necunoscut-extra"),
    pytest.param([
        {"id": "C1", "citat": PASSAGE_C1},
        {"id": "C1", "citat": PASSAGE_C1},
    ], id="id-duplicat"),
    pytest.param([
        {"id": "C1", "citat": PASSAGE_C1},
        {"id": "c1", "citat": PASSAGE_C1},
    ], id="id-duplicat-dupa-normalizare"),
    pytest.param([{"id": 1, "citat": PASSAGE_C1}], id="id-numar"),
    pytest.param([{"id": None, "citat": PASSAGE_C1}], id="id-null"),
    pytest.param([{"id": True, "citat": PASSAGE_C1}], id="id-bool"),
    pytest.param([{"id": ["C1"], "citat": PASSAGE_C1}], id="id-lista"),
    pytest.param([{"id": " C1 ", "citat": PASSAGE_C1}], id="id-cu-spatii"),
    pytest.param([{"id": "C01", "citat": PASSAGE_C1}], id="id-zero-initial"),
    pytest.param([{"id": "C1", "citat": PASSAGE_C1, "articol": "inventat"}], id="metadata-extra"),
])
def test_citation_passages_respinge_mapare_invalida_fara_retry(evidence_pair, passages, reference_suffix):
    payload = encode_payload(f"{PASSAGE_C1} [C1]{reference_suffix}", passages)
    assert_rejected_once(payload, evidence_pair)


@pytest.mark.parametrize("reference_suffix", ["", INVENTED_REFERENCE])
def test_citation_passages_respinge_mapare_partiala_pentru_doua_citari(evidence_pair, reference_suffix):
    payload = encode_payload(
        f"{PASSAGE_C1} [C1] {PASSAGE_C2} [C2]{reference_suffix}",
        [{"id": "C1", "citat": PASSAGE_C1}],
    )
    assert_rejected_once(payload, evidence_pair)


@pytest.mark.parametrize("reference_suffix", ["", INVENTED_REFERENCE])
def test_citation_passages_text_simplu_vechi_nu_devine_fallback(evidence_pair, reference_suffix):
    assert_rejected_once(f"{PASSAGE_C1} [C1]{reference_suffix}", evidence_pair)


@pytest.mark.parametrize("reference_suffix", ["", INVENTED_REFERENCE], ids=["fara-referinta", "inainte-de-retry"])
@pytest.mark.parametrize("quote", [
    pytest.param(None, id="null"),
    pytest.param(123, id="numar"),
    pytest.param(True, id="bool"),
    pytest.param([PASSAGE_C1], id="lista"),
    pytest.param({"text": PASSAGE_C1}, id="obiect"),
    pytest.param("", id="gol"),
    pytest.param(" \t\n ", id="numai-whitespace"),
    pytest.param("x" * 601, id="601-caractere-literale"),
    pytest.param(PASSAGE_C2, id="literal-numai-in-alta-dovada"),
    pytest.param("Carcasa fictiva este turcoaz.", id="diacritice-eliminate"),
    pytest.param("Carcasa  fictivă este turcoaz.", id="spatiu-adaugat"),
    pytest.param("Șurubul fictiv este îngust.", id="whitespace-normalizat"),
    pytest.param(PASSAGE_C1 + EXACT_WHITESPACE, id="concatenare-pasaje-neadiacente"),
    pytest.param(" " + PASSAGE_C1 + " ", id="necesita-trim-pentru-potrivire"),
    pytest.param("Carcasa fictivă este roz.", id="text-fabricat"),
])
def test_citation_passages_respinge_citat_invalid_fara_retry(evidence_pair, quote, reference_suffix):
    payload = encode_payload(
        f"{PASSAGE_C1} [C1]{reference_suffix}", [{"id": "C1", "citat": quote}]
    )
    assert_rejected_once(payload, evidence_pair)


@pytest.mark.parametrize("reference_suffix", ["", INVENTED_REFERENCE], ids=["fara-referinta", "inainte-de-retry"])
@pytest.mark.parametrize("raw_template", [
    pytest.param('{"raspuns":ANSWER}', id="pasaje-absente"),
    pytest.param('{"pasaje":PASSAGES}', id="raspuns-absent"),
    pytest.param('{"raspuns":ANSWER,"pasaje":PASSAGES,"extra":true}', id="top-level-extra"),
    pytest.param('{"raspuns":ANSWER,"raspuns":ANSWER,"pasaje":PASSAGES}', id="raspuns-duplicat"),
    pytest.param('{"raspuns":ANSWER,"pasaje":PASSAGES,"pasaje":PASSAGES}', id="pasaje-duplicate"),
    pytest.param('{"raspuns":ANSWER,"pasaje":[{"id":"C1","id":"C1","citat":QUOTE}]}', id="cheie-id-duplicata"),
    pytest.param('{"raspuns":ANSWER,"pasaje":[{"id":"C1","citat":QUOTE,"citat":QUOTE}]}', id="cheie-citat-duplicata"),
    pytest.param('{"raspuns":ANSWER,"pasaje":[{"id":"C1","citat":"fabricat","citat":QUOTE}]}', id="duplicat-nu-last-wins"),
    pytest.param('{"raspuns":ANSWER,"pasaje":[{"id":"C1","citat":QUOTE,"citat":"fabricat"}]}', id="duplicat-nu-first-wins"),
    pytest.param('{"raspuns":ANSWER,"pasaje":PASSAGES,}', id="virgula-finala"),
    pytest.param('{"raspuns":ANSWER,"pasaje":', id="json-incomplet"),
    pytest.param('```json\n{"raspuns":ANSWER,"pasaje":PASSAGES}\n```', id="markdown-fence"),
    pytest.param('Iată: {"raspuns":ANSWER,"pasaje":PASSAGES}', id="proza-inainte"),
    pytest.param('{"raspuns":ANSWER,"pasaje":PASSAGES} Gata.', id="proza-dupa"),
    pytest.param('{"raspuns":ANSWER,"pasaje":PASSAGES} {}', id="doua-obiecte-json"),
    pytest.param('[{"raspuns":ANSWER,"pasaje":PASSAGES}]', id="top-level-lista"),
    pytest.param('ANSWER', id="top-level-string"),
    pytest.param('null', id="top-level-null"),
    pytest.param('{"raspuns":null,"pasaje":PASSAGES}', id="raspuns-null"),
    pytest.param('{"raspuns":123,"pasaje":PASSAGES}', id="raspuns-numar"),
    pytest.param('{"raspuns":true,"pasaje":PASSAGES}', id="raspuns-bool"),
    pytest.param('{"raspuns":[ANSWER],"pasaje":PASSAGES}', id="raspuns-lista"),
    pytest.param('{"raspuns":{"text":ANSWER},"pasaje":PASSAGES}', id="raspuns-obiect"),
    pytest.param('{"raspuns":"","pasaje":PASSAGES}', id="raspuns-gol"),
    pytest.param('{"raspuns":"  ","pasaje":PASSAGES}', id="raspuns-spatii"),
])
def test_citation_passages_respinge_json_nestrict_fara_retry(evidence_pair, raw_template, reference_suffix):
    answer = f"{PASSAGE_C1} [C1]{reference_suffix}"
    # Templatele RAW păstrează inclusiv cheile duplicate; json.dumps(dict) le-ar pierde.
    payload = raw_template.replace("ANSWER", json.dumps(answer, ensure_ascii=False))
    payload = payload.replace("PASSAGES", json.dumps([{"id": "C1", "citat": PASSAGE_C1}], ensure_ascii=False))
    payload = payload.replace("QUOTE", json.dumps(PASSAGE_C1, ensure_ascii=False))
    assert_rejected_once(payload, evidence_pair)


@pytest.mark.parametrize("answer,passages,expected_type", [
    pytest.param("Fără citare.", [], "MissingCitationError", id="citare-absenta"),
    pytest.param("Fără citare.", [{"id": "C1", "citat": "Marcaj [C1] literal."}], "MissingCitationError", id="citare-numai-in-pasaj"),
    pytest.param("Afirmație [C9]", [{"id": "C9", "citat": PASSAGE_C1}], "UnknownCitationError", id="citare-necunoscuta"),
    pytest.param("Afirmație [C0]", [], "MissingCitationError", id="c0-nu-este-id"),
    pytest.param("Afirmație [C01]", [], "MissingCitationError", id="c01-nu-este-id"),
])
def test_citation_passages_id_din_raspuns_pastreaza_eroarea_tipata(answer, passages, expected_type):
    evidence = (make_evidence(1, PASSAGE_C1 + " Marcaj [C1] literal."),)
    assert_rejected_once(encode_payload(answer, passages), evidence, expected_type)


def test_citation_passages_json_complet_trunchiat_pastreaza_notice(evidence_pair):
    answer = f"{PASSAGE_C1} [C1]"
    payload = encode_payload(answer, [{"id": "C1", "citat": PASSAGE_C1}])
    generator = RawGenerator(GeneratedText(payload, truncated=True))

    result = GenerationService(generator).generate(QUESTION, evidence_pair)

    assert result.status == "answered"
    assert result.raspuns == f"{answer}\n\n{EXPECTED_TRUNCATION_NOTICE}"
    assert [(c.id, c.citat) for c in result.citari] == [("C1", PASSAGE_C1)]
    assert result.citari[0].citat in evidence_pair[0].content
    assert generator.calls == 1
    assert generator.token_limits == [1200]


@pytest.mark.parametrize("reference_suffix", ["", INVENTED_REFERENCE])
def test_citation_passages_json_incomplet_trunchiat_nu_se_repara(evidence_pair, reference_suffix):
    payload = encode_payload(
        f"{PASSAGE_C1} [C1]{reference_suffix}", [{"id": "C1", "citat": PASSAGE_C1}]
    )[:-1]
    assert_rejected_once(GeneratedText(payload, truncated=True), evidence_pair)


def test_citation_passages_json_complet_citat_invalid_trunchiat_este_eroare(evidence_pair):
    payload = encode_payload("Carcasa este turcoaz. [C1]", [{"id": "C1", "citat": PASSAGE_C2}])
    assert_rejected_once(GeneratedText(payload, truncated=True), evidence_pair)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_citation_passages_constante_non_json_sunt_respinse(evidence_pair, constant):
    payload = '{"raspuns":"Afirmație [C1]","pasaje":[{"id":"C1","citat":' + constant + '}]}'
    assert_rejected_once(payload, evidence_pair)


def test_citation_passages_chei_duplicate_cu_escape_json_sunt_respinse(evidence_pair):
    payload = (
        '{"raspuns":"Afirmație [C1]","rasp\\u0075ns":"Afirmație [C1]",'
        '"pasaje":[{"id":"C1","citat":"Carcasa fictivă este turcoaz."}]}'
    )
    assert_rejected_once(payload, evidence_pair)


def test_citation_passages_id_literal_din_citat_nu_este_id_folosit_in_raspuns():
    quote = "Marcajul fictiv [C9] este imprimat."
    evidence = (make_evidence(1, quote),)
    answer = "Marcajul este imprimat. [C1]"
    generator = RawGenerator(encode_payload(answer, [{"id": "C1", "citat": quote}]))

    result = GenerationService(generator).generate(QUESTION, evidence)

    assert result.raspuns == answer
    assert [(citation.id, citation.citat) for citation in result.citari] == [("C1", quote)]
    assert generator.calls == 1


class RawSequenceGenerator(RawGenerator):
    """Secvență RAW finită: verifică retry-ul existent fără împachetare din prompt."""

    def __init__(self, payloads):
        super().__init__(None)
        self.payloads = payloads

    def generate(self, prompt, *, max_tokens):
        assert self.calls < len(self.payloads), "apel generator suplimentar"
        self.payload = self.payloads[self.calls]
        return super().generate(prompt, max_tokens=max_tokens)


def test_citation_passages_retry_verifica_referinta_decodata_si_foloseste_noile_pasaje(evidence_pair):
    first = encode_payload(
        "Conform STAS 987654321 [C1].", [{"id": "C1", "citat": PASSAGE_C1}]
    ).replace("STAS ", "STAS\\u0020")
    answer = f"{PASSAGE_C2} [C2]"
    second = encode_payload(answer, [{"id": "C2", "citat": PASSAGE_C2}])
    generator = RawSequenceGenerator((first, second))

    result = GenerationService(generator).generate(QUESTION, evidence_pair)

    assert generator.calls == 2 and generator.token_limits == [1200, 1200]
    assert result.raspuns == answer
    assert [(citation.id, citation.citat) for citation in result.citari] == [("C2", PASSAGE_C2)]
    assert result.citari[0].cod_document == evidence_pair[1].cod_document


def test_citation_passages_invalid_la_retry_nu_reutilizeaza_primul_citat_valid(evidence_pair):
    first = encode_payload(
        "Conform STAS 987654321 [C1].", [{"id": "C1", "citat": PASSAGE_C1}]
    )
    second = encode_payload(
        "Conform STAS 987654321 [C1].", [{"id": "C1", "citat": PASSAGE_C2}]
    )
    generator = RawSequenceGenerator((first, second))

    with pytest.raises(GenerationValidationError) as caught:
        GenerationService(generator).generate(QUESTION, evidence_pair)

    assert type(caught.value).__name__ != "UngroundedReferenceError"
    assert generator.calls == 2 and generator.token_limits == [1200, 1200]


def diagnostic_r05_numar_gresit_cu_citat_literal_valid():
    """Control manual, necolectat de pytest: R06 nu dovedește susținerea afirmației.

    Raportează ce întoarce serviciul, fără assert că numărul greșit trebuie publicat.
    O protecție R05 aprobată ulterior poate refuza/corecta fără a încălca un test CI.
    """
    evidence = (make_evidence(1, "Cutia fictivă conține 7 discuri."),)
    answer = "Cutia fictivă conține 9 discuri. [C1]"
    quote = "Cutia fictivă conține 7 discuri."
    generator = RawGenerator(encode_payload(answer, [{"id": "C1", "citat": quote}]))
    report = {
        "limita": "R05: proveniența literală nu validează numărul din afirmație",
        "dovada": evidence[0].content,
        "raspuns_candidat": answer,
        "citat_candidat": quote,
        "citat_literal_valid": quote in evidence[0].content,
    }
    try:
        result = GenerationService(generator).generate(QUESTION, evidence)
    except GenerationValidationError as error:
        report.update(status="refuzat", eroare=type(error).__name__)
    else:
        report.update(
            status=result.status,
            raspuns_observat=result.raspuns,
            citate_observate=[citation.citat for citation in result.citari],
        )
    report["generator_calls"] = generator.calls
    return report
