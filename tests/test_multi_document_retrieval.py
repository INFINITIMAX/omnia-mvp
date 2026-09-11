"""RED D11: context pentru interpretare, nu filtru implicit de documente.

Numai dovezi fictive și API-uri existente. D12/D13 acoperă cele trei expresii
aprobate și codurile absente din catalog. Negațiile, restricțiile multiple,
continuările ambigue și persistența/UI rămân în afara acestui lot.
"""

import pytest

from retrieval_core import (
    ArticleParser,
    ConversationTurn,
    Evidence,
    PostgresApprovedCatalogRepository,
    PostgresRetrievalRepository,
    RetrievalService,
)


CODES = {
    "doc-i7": "I7-2011",
    "doc-np010": "NP 010-2022",
    "doc-p1": "P 118/1-2025",
    "doc-p2-2013": "P 118/2-2013",
    "doc-p2-2026": "P 118/2-2026",
}
VECTOR = (0.1, 0.2)


class CursorFake:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []
        self.closed = False

    def execute(self, sql, parameters):
        self.calls.append((sql, parameters))

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed = True


class ConnectionFake:
    def __init__(self, rows):
        self.cursor_instance = CursorFake(rows)

    def cursor(self):
        return self.cursor_instance


def catalog_parser():
    # Exercită inclusiv aliasurile scurte derivate de catalogul real, nu un parser fals.
    connection = ConnectionFake([(document, code, "1.1") for document, code in CODES.items()])
    catalog = PostgresApprovedCatalogRepository(connection).load()
    sql, parameters = connection.cursor_instance.calls[0]
    assert "document.status = %s" in sql and parameters == ("approved",)
    assert connection.cursor_instance.closed
    return catalog.create_parser()


def evidence(document, *, article="1.1", content=None, score=0.9):
    return Evidence(
        chunk_id=list(CODES).index(document) + 1,
        document_id=document,
        cod_document=CODES[document],
        titlu_document=f"Document fictiv {document}",
        articol=article,
        articol_normalizat=article,
        content=content if content is not None else f"Marcaj fictiv distinct pentru {document}.",
        content_hash=f"hash-fictiv-{document}-{article}",
        score=score,
    )


class RepositoryFake:
    """Înregistrează ruta cerută; rezultatele respectă filtrul primit, fără fallback."""

    def __init__(self, rows):
        self.rows = tuple(rows)
        self.exact_calls = []
        self.global_calls = []
        self.scoped_calls = []

    def find_exact(self, document_id, article_normalized):
        self.exact_calls.append((document_id, article_normalized))
        return [item for item in self.rows
                if item.articol_normalizat == article_normalized
                and (document_id is None or item.document_id == document_id)]

    def find_semantic(self, embedding, top_k):
        self.global_calls.append((tuple(embedding), top_k))
        return self.rows[:top_k]

    def find_semantic_in_documents(self, embedding, top_k, document_ids):
        self.scoped_calls.append((tuple(embedding), top_k, tuple(document_ids)))
        return tuple(item for item in self.rows if item.document_id in document_ids)[:top_k]


class EmbedderFake:
    def __init__(self):
        self.questions = []

    def embed_query(self, question):
        self.questions.append(question)
        return VECTOR


def retrieve(question, rows, context=()):
    repository = RepositoryFake(rows)
    embedder = EmbedderFake()
    result = RetrievalService(catalog_parser(), repository, embedder).retrieve(question, context)
    return result, repository, embedder


def assert_global(repository, embedder, embedding_text):
    assert repository.global_calls == [(VECTOR, 5)]
    assert repository.scoped_calls == []
    assert repository.exact_calls == []
    assert embedder.questions == [embedding_text]


def test_multi_document_intrebarea_generala_cauta_global_si_pastreaza_doua_surse():
    question = "Ce marcaje sunt descrise pentru piesele fictive?"
    rows = (evidence("doc-i7"), evidence("doc-np010"))

    result, repository, embedder = retrieve(question, rows)

    assert_global(repository, embedder, question)
    assert result.status == "found"
    assert result.evidence == rows


@pytest.mark.parametrize("previous_codes", [
    ("I7-2011",),
    ("I7-2011", "NP 010-2022"),
    ("P 118/2-2013",),
])
def test_multi_document_citarile_istorice_nu_filtreaza_dar_intrebarea_ajunge_in_embedding(previous_codes):
    previous = "Ce marcaje au piesele fictive?"
    question = "Dar cele pentru capace?"
    # Ambele dovezi sunt din afara documentului P118; cel puțin una e în afara I7.
    rows = (evidence("doc-i7"), evidence("doc-np010"))
    context = (ConversationTurn(previous, previous_codes),)

    result, repository, embedder = retrieve(question, rows, context)

    assert_global(repository, embedder, previous + "\n" + question)
    assert result.status == "found"
    assert result.evidence == rows


def test_multi_document_nu_cere_mai_intai_scoped_hit_pentru_continuare():
    previous = "Ce marcaje are piesa fictivă?"
    question = "Și capacul?"
    rows = (evidence("doc-np010"),)
    context = (ConversationTurn(previous, ("I7-2011",)),)

    result, repository, embedder = retrieve(question, rows, context)

    assert_global(repository, embedder, previous + "\n" + question)
    assert result.status == "found" and result.evidence == rows


@pytest.mark.parametrize("question", [
    "Ce spune I7-2011 despre marcajele pieselor fictive?",
    "Ce spune P 118/1-2025 despre marcajele pieselor fictive?",
    "Ce spune I7-2011 despre marcajele folosite doar temporar?",
])
def test_multi_document_mentionarea_simpla_nu_impune_exclusivitate(question):
    rows = (evidence("doc-i7"), evidence("doc-np010"))
    previous = "Discutăm marcajele pieselor fictive."
    context = (ConversationTurn(previous, ("NP 010-2022",)),)

    result, repository, embedder = retrieve(question, rows, context)

    assert_global(repository, embedder, previous + "\n" + question)
    assert result.status == "found" and result.evidence == rows


@pytest.mark.parametrize("question", [
    "Compară marcajele pieselor fictive din I7-2011 și NP 010-2022.",
    "Ce informații despre marcaje oferă NP 010-2022 și I7-2011?",
    "Compară P 118/1-2025 și P 118/2-2013 privind piesele fictive.",
])
def test_multi_document_doua_documente_distincte_fara_articol_nu_sunt_ambiguitate(question):
    rows = (evidence("doc-p1"), evidence("doc-p2-2013")) if "P 118" in question else (
        evidence("doc-i7"), evidence("doc-np010"),
    )

    result, repository, embedder = retrieve(question, rows)

    assert result.status == "found"
    assert result.evidence == rows
    assert_global(repository, embedder, question)


def test_multi_document_contextul_pastreaza_ultimele_trei_intrebari_fara_scope():
    context = tuple(ConversationTurn(f"Întrebare fictivă {index}", ("I7-2011",)) for index in range(4))
    question = "Continuarea despre marcaje?"
    rows = (evidence("doc-np010"),)

    result, repository, embedder = retrieve(question, rows, context)

    assert_global(repository, embedder, "\n".join([turn.intrebare for turn in context[-3:]] + [question]))
    assert result.status == "found" and result.evidence == rows


@pytest.mark.parametrize("score,accepted", [(None, False), (0.49, False), (0.5, True)])
def test_multi_document_scorul_minim_ramane_050(score, accepted):
    rows = (evidence("doc-i7", score=0.9), evidence("doc-np010", score=score))
    question = "Descrie marcajele fictive."

    result, repository, embedder = retrieve(question, rows)

    assert_global(repository, embedder, question)
    assert result.status == "found"
    assert result.evidence == (rows if accepted else rows[:1])


def test_multi_document_pragul_si_plafonul_contextului_raman_neschimbate():
    rows = (
        evidence("doc-i7", content="a" * 6000, score=0.9),
        evidence("doc-np010", content="b" * 6000, score=0.8),
        evidence("doc-p1", content="c", score=0.7),
        evidence("doc-p2-2013", content="d", score=0.49),
    )
    question = "Descrie piesele fictive."

    result, repository, embedder = retrieve(question, rows)

    assert_global(repository, embedder, question)
    assert result.status == "found"
    assert result.evidence == rows[:2]
    assert sum(len(item.content) for item in result.evidence) == 12000


@pytest.mark.parametrize("code,document", [
    ("P 118/1-2025", "doc-p1"),
    ("p 118 / 1 - 2025", "doc-p1"),
    ("P11812025", "doc-p1"),
    ("P 118/2-2013", "doc-p2-2013"),
    ("p 118 / 2 - 2013", "doc-p2-2013"),
    ("P11822013", "doc-p2-2013"),
    ("P 118/2-2026", "doc-p2-2026"),
    ("P11822026", "doc-p2-2026"),
])
def test_multi_document_alias_slash_rezolva_identitatea_partea_si_anul(code, document):
    parsed = catalog_parser().parse(f"{code}, art. 1.1")

    assert parsed.document_id == document
    assert parsed.article_normalized == "1.1"
    assert parsed.has_explicit_article
    assert not parsed.requires_clarification


@pytest.mark.parametrize("token", [
    "XP 118/1-2025", "P 118/1-2025X", "P 118/1-20250", "P 118/12-2025",
    "XP11812025", "P11812025X",
])
def test_multi_document_alias_slash_nu_potriveste_interiorul_altui_token(token):
    # Aici izolăm granițele aliasului complet; nu stabilim politica unui cod necunoscut.
    parser = ArticleParser({"doc-p1": ("P 118/1-2025",)})
    parsed = parser.parse(f"{token}, art. 1.1")

    assert parsed.document_id is None
    assert not parsed.requires_clarification
    assert parsed.article_normalized == "1.1"


def test_multi_document_alias_scurt_comun_la_doi_ani_ramane_realmente_ambiguu():
    parsed = catalog_parser().parse("P1182, art. 1.1")

    assert parsed.requires_clarification
    assert parsed.document_id is None


def test_multi_document_acelasi_alias_la_doua_documente_nu_devine_comparatie():
    parser = ArticleParser({"doc-a": ("I7-2011",), "doc-b": ("I7-2011",)})
    parsed = parser.parse("I7-2011, art. 1.1")

    assert parsed.requires_clarification
    assert parsed.document_id is None


@pytest.mark.parametrize("code,document", [
    ("I7-2011", "doc-i7"),
    ("P11812025", "doc-p1"),
    ("P 118/1-2025", "doc-p1"),
    ("P 118/2-2013", "doc-p2-2013"),
    ("P 118/2-2026", "doc-p2-2026"),
])
def test_multi_document_document_si_articol_exact_nu_sunt_inlocuite_de_context(code, document):
    target = evidence(document)
    other = evidence("doc-np010")
    context = (ConversationTurn("Discutăm alte piese fictive.", ("NP 010-2022",)),)

    result, repository, embedder = retrieve(f"{code}, art. 1.1", (other, target), context)

    assert repository.exact_calls == [(document, "1.1")]
    assert repository.global_calls == repository.scoped_calls == []
    assert embedder.questions == []
    assert result.status == "found"
    assert result.evidence == (target,)
    assert result.evidence[0].cod_document == CODES[document]


def test_multi_document_cautarea_sql_globala_pastreaza_approved_si_top_k():
    connection = ConnectionFake([])
    repository = PostgresRetrievalRepository(connection)

    assert repository.find_semantic(VECTOR, 5) == []

    sql, parameters = connection.cursor_instance.calls[0]
    assert "WHERE document.status = 'approved' AND chunk.embedding IS NOT NULL" in sql
    assert "chunk.document_id =" not in sql
    assert "LIMIT %s" in sql
    assert parameters == ("[0.1,0.2]", "[0.1,0.2]", 5)
    assert connection.cursor_instance.closed


# D12: inventar finit, exact cum a fost aprobat; fără sinonime sau regex în teste.
RESTRICTION_PHRASES = ("doar din", "numai din", "exclusiv din")
RESTRICTION_DOCUMENTS = (("I7-2011", "doc-i7"), ("P 118/1-2025", "doc-p1"))


def assert_scoped_once(repository, embedder, question, document):
    assert repository.scoped_calls == [(VECTOR, 5, (document,))]
    assert repository.global_calls == []
    assert repository.exact_calls == []
    assert embedder.questions == [question]


@pytest.mark.parametrize("phrase", RESTRICTION_PHRASES)
@pytest.mark.parametrize("code,document", RESTRICTION_DOCUMENTS)
def test_d12_formele_aprobate_cu_cod_cunoscut_folosesc_numai_scope(phrase, code, document):
    question = f"Răspunde {phrase} {code} despre marcajele pieselor fictive."
    target = evidence(document, score=0.5)
    decoy = evidence("doc-np010", score=0.99)

    result, repository, embedder = retrieve(question, (decoy, target))

    assert_scoped_once(repository, embedder, question, document)
    assert result.status == "found"
    assert result.evidence == (target,)
    assert result.evidence[0].cod_document == code


@pytest.mark.parametrize("phrase", RESTRICTION_PHRASES)
@pytest.mark.parametrize("code,document", RESTRICTION_DOCUMENTS)
@pytest.mark.parametrize("target_state", ["absent", "fara-scor", "sub-prag"])
def test_d12_scope_fara_dovada_acceptata_nu_are_fallback_global(phrase, code, document, target_state):
    question = f"Răspunde {phrase} {code} despre marcajele pieselor fictive."
    rows = [evidence("doc-np010", score=0.99)]
    if target_state != "absent":
        rows.append(evidence(document, score=None if target_state == "fara-scor" else 0.49))

    result, repository, embedder = retrieve(question, rows)

    assert_scoped_once(repository, embedder, question, document)
    assert result.status == "not_found"
    assert result.evidence == ()


@pytest.mark.parametrize("phrase", RESTRICTION_PHRASES)
def test_d12_scope_pastreaza_limita_contextului(phrase):
    question = f"Răspunde {phrase} I7-2011 despre marcajele pieselor fictive."
    targets = (
        evidence("doc-i7", article="1.1", content="a" * 6000, score=0.9),
        evidence("doc-i7", article="1.2", content="b" * 6000, score=0.8),
        evidence("doc-i7", article="1.3", content="c", score=0.7),
    )
    rows = (evidence("doc-np010", score=0.99),) + targets

    result, repository, embedder = retrieve(question, rows)

    assert_scoped_once(repository, embedder, question, "doc-i7")
    assert result.status == "found"
    assert result.evidence == targets[:2]
    assert sum(len(item.content) for item in result.evidence) == 12000


@pytest.mark.parametrize("phrase", RESTRICTION_PHRASES)
@pytest.mark.parametrize("code", [
    pytest.param("XX 999-2099", id="necunoscut"),
    pytest.param("NP 777-2099", id="neaprobat-absent-din-catalog"),
])
@pytest.mark.parametrize("with_history", [False, True], ids=["fara-istoric", "istoric-cu-cod-aprobat"])
def test_d13_restrictia_la_cod_absent_din_catalog_clarifica_fara_dependente(phrase, code, with_history):
    # La acest seam, un cod neaprobat nu este expus de catalog, la fel ca unul necunoscut.
    # Nu simulăm o schimbare de status DB și nu pretindem verificarea quota prin retrieval.
    parser = catalog_parser()
    assert parser.documents_for_official_code(code) == frozenset()
    repository = RepositoryFake((evidence("doc-i7"), evidence("doc-np010")))
    embedder = EmbedderFake()
    context = (ConversationTurn("Ce marcaje au piesele fictive?", ("I7-2011",)),) if with_history else ()
    question = f"Răspunde {phrase} {code} despre marcajele pieselor fictive."

    result = RetrievalService(parser, repository, embedder).retrieve(question, context)

    assert result.status == "ambiguous_reference"
    assert result.evidence == ()
    assert embedder.questions == []
    assert repository.global_calls == []
    assert repository.scoped_calls == []
    assert repository.exact_calls == []
