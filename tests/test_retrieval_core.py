"""Teste sintetice pentru Retrieval Core; nu folosesc DB, Voyage sau texte normative."""

from dataclasses import dataclass

import pytest

from retrieval_core import (
    ArticleParser,
    Evidence,
    PostgresApprovedCatalogRepository,
    PostgresRetrievalRepository,
    RetrievalService,
)


ALIASES = {"doc-np010": ("NP010", "NP 010-2022")}
KNOWN = {"doc-np010": ("4.4.7.2", "4.6.(1)", "3.2.(B).l.")}


def evidence(
    chunk_id=1, document_id="doc-np010", article="4.4.7.2", content="fragment sintetic",
    content_hash="hash-a", score=None,
):
    return Evidence(
        chunk_id, document_id, "NP TEST-2026", "Titlu sintetic", article,
        ArticleParser.normalize_article(article), content, content_hash, score,
    )


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


@dataclass
class RepositoryFake:
    exact: list[Evidence]
    semantic: list[Evidence]
    exact_calls: int = 0
    semantic_calls: int = 0
    top_k: int | None = None

    def find_exact(self, _document_id, _article):
        self.exact_calls += 1
        return self.exact

    def find_semantic(self, _embedding, top_k):
        self.semantic_calls += 1
        self.top_k = top_k
        return self.semantic


class EmbedderFake:
    def __init__(self, result=(0.1, 0.2)):
        self.result = result
        self.calls = 0

    def embed_query(self, _question):
        self.calls += 1
        return self.result


def service(repository, embedder=None, **config):
    return RetrievalService(
        ArticleParser(ALIASES, KNOWN), repository, embedder or EmbedderFake(), **config
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" 3.2. (B). L. ", "3.2.(b).l"),
        ("3.2.\u00a0(B).", "3.2.(b)"),
        ("3.2.\u202f(B).", "3.2.(b)"),
    ],
)
def test_normalizarea_articolului_este_identica_contractului_db(raw, expected):
    assert ArticleParser.normalize_article(raw) == expected


@pytest.mark.parametrize("question", ["în 2022", "la 12.5 m", "versiunea 3.12.1"])
def test_parserul_nu_confunda_numere_fara_marker(question):
    parsed = ArticleParser(ALIASES, KNOWN).parse(question)
    assert parsed.article_normalized is None
    assert not parsed.has_explicit_article


def test_parserul_accepta_markerii_si_articol_neambiguu_din_metadata():
    parser = ArticleParser(ALIASES, KNOWN)
    assert parser.parse("Articolul 4.4.7.2.").has_explicit_article
    assert parser.parse("art. 4.6. (1)").article_normalized == "4.6.(1)"
    assert parser.parse("art.\u00a03.2.\u202f(B). L.").article_normalized == "3.2.(b).l"
    annex = parser.parse("ANEXA 1.1.")
    assert annex.article_normalized == "anexa1.1"
    assert annex.has_explicit_article
    assert parser.parse("anexa 3").article_normalized == "anexa3"
    assert parser.parse("consulta 4.4.7.2").article_normalized == "4.4.7.2"


@pytest.mark.parametrize(
    "question",
    ["art. 4.4.7.2 și articolul 4.6.(1)", "consulta 4.4.7.2 și 4.6.(1)"],
)
def test_parserul_cere_clarificare_pentru_doua_articole(question):
    parsed = ArticleParser(ALIASES, KNOWN).parse(question)

    assert parsed.requires_clarification
    assert parsed.article_normalized is None


def test_aliasurile_metadata_recunosc_np010_si_np_010_2022():
    parser = ArticleParser(ALIASES, KNOWN)
    assert parser.parse("NP010, art. 4.4.7.2").document_id == "doc-np010"
    assert parser.parse("NP 010-2022, art. 4.4.7.2").document_id == "doc-np010"


@pytest.mark.parametrize("question", ["XNP010, art. 4.4.7.2", "NP0100, art. 4.4.7.2"])
def test_aliasul_nu_se_potriveste_interiorul_altui_token(question):
    parsed = ArticleParser(ALIASES, KNOWN).parse(question)

    assert parsed.document_id is None


def test_aliasurile_suprapuse_din_documente_diferite_cer_clarificare():
    parser = ArticleParser(
        {"doc-scurt": ("NP010",), "doc-lung": ("NP 010-2022",)},
        {"doc-scurt": ("4.4.7.2",), "doc-lung": ("4.4.7.2",)},
    )

    assert parser.parse("NP 010-2022, art. 4.4.7.2").requires_clarification


def test_parserul_cere_clarificare_pentru_doua_documente():
    parser = ArticleParser(
        {"doc-a": ("NP010",), "doc-b": ("NP057",)},
        {"doc-a": ("4.4.7.2",), "doc-b": ("4.4.7.2",)},
    )

    parsed = parser.parse("NP010 și NP057, art. 4.4.7.2")

    assert parsed.requires_clarification
    assert parsed.document_id is None


def test_articol_nemarcat_cunoscut_in_doua_documente_ramane_exact():
    parser = ArticleParser(
        {"doc-a": ("NP010",), "doc-b": ("NP057",)},
        {"doc-a": ("4.4.7.2",), "doc-b": ("4.4.7.2",)},
    )

    parsed = parser.parse("consulta 4.4.7.2")

    assert parsed.article_normalized == "4.4.7.2"
    assert not parsed.requires_clarification


def test_catalogul_approved_foloseste_numai_metadata_oficiala_si_inchide_cursorul():
    connection = ConnectionFake([
        ("doc-1", "NP 010-2022", "4.4.7.2"),
        ("doc-1", "NP 010-2022", "4.6.(1)"),
    ])

    catalog = PostgresApprovedCatalogRepository(connection).load()
    parser = catalog.create_parser()
    sql, parameters = connection.cursor_instance.calls[0]

    assert "FROM public.documente AS document" in sql
    assert "public.documente_chunks AS chunk" in sql
    assert "document.status = %s" in sql
    assert parameters == ("approved",)
    assert "source_key" not in sql
    assert "chunk.text" not in sql
    assert parser.parse("NP010, art. 4.4.7.2").document_id == "doc-1"
    assert connection.cursor_instance.closed


def test_repository_exact_foloseste_numai_sql_parametrizat_cu_document_optional():
    connection = ConnectionFake([(1, "doc", "COD", "Titlu", "1.1", "1.1", "text", "hash")])
    repository = PostgresRetrievalRepository(connection)

    found = repository.find_exact("doc", "1.1")

    sql, parameters = connection.cursor_instance.calls[0]
    assert "document.status = 'approved' AND chunk.document_id = %s AND chunk.articol_normalizat = %s" in sql
    assert parameters == ("doc", "1.1")
    assert "FROM public.documente_chunks" in sql
    assert "WHERE chunk.document_id = 'doc'" not in sql
    assert found[0].content == "text"
    assert connection.cursor_instance.closed

    repository.find_exact(None, "1.1")
    sql, parameters = connection.cursor_instance.calls[1]
    assert "document.status = 'approved' AND chunk.articol_normalizat = %s" in sql
    assert parameters == ("1.1",)


def test_repository_propaga_eroarea_db_si_inchide_cursorul():
    class CursorDefect(CursorFake):
        def execute(self, sql, parameters):
            super().execute(sql, parameters)
            raise RuntimeError("db indisponibil")

    connection = ConnectionFake([])
    connection.cursor_instance = CursorDefect([])

    with pytest.raises(RuntimeError, match="db indisponibil"):
        PostgresRetrievalRepository(connection).find_exact("doc", "1.1")

    assert connection.cursor_instance.closed


def test_repository_semantic_foloseste_pgvector_parametrizat_scor_si_limita():
    connection = ConnectionFake([(1, "doc", "COD", "Titlu", "1.1", "1.1", "text", "hash", 0.75)])
    found = PostgresRetrievalRepository(connection).find_semantic([0.1, 2], 3)

    sql, parameters = connection.cursor_instance.calls[0]
    assert "1 - (chunk.embedding <=> %s::vector) AS score" in sql
    assert sql.index("AS score") < sql.index("FROM public.documente_chunks")
    assert "WHERE document.status = 'approved' AND chunk.embedding IS NOT NULL" in sql
    assert "ORDER BY chunk.embedding <=> %s::vector" in sql
    assert "ORDER BY chunk.embedding <=> %s::vector," not in sql
    assert "LIMIT %s" in sql
    assert parameters == ("[0.1,2.0]", "[0.1,2.0]", 3)
    assert found[0].score == 0.75


@pytest.mark.parametrize("top_k", [0, -1, True, "5"])
def test_repository_refuza_top_k_nepozitiv_sau_cu_tip_invalid(top_k):
    repository = PostgresRetrievalRepository(ConnectionFake([]))

    with pytest.raises(ValueError, match="top_k"):
        repository.find_semantic([0.1], top_k)


@pytest.mark.parametrize("embedding", [[float("nan")], [float("inf")], []])
def test_repository_refuza_embedding_gol_sau_nefinit(embedding):
    repository = PostgresRetrievalRepository(ConnectionFake([]))

    with pytest.raises(ValueError):
        repository.find_semantic(embedding, 3)


@pytest.mark.parametrize("top_k", [0, -1, True, "5"])
def test_service_refuza_semantic_top_k_invalid(top_k):
    with pytest.raises(ValueError, match="semantic_top_k"):
        service(RepositoryFake([], []), semantic_top_k=top_k)


@pytest.mark.parametrize("max_chars", [0, -1, True, "100"])
def test_service_refuza_limita_context_invalida(max_chars):
    with pytest.raises(ValueError, match="max_context_chars"):
        service(RepositoryFake([], []), max_context_chars=max_chars)


def test_limita_intrebarii_accepta_1000_si_respinge_1001_inainte_de_dependente():
    repository = RepositoryFake([evidence()], [])
    embedder = EmbedderFake()
    retrieval = service(repository, embedder)
    accepted = "x" * (1000 - len(" art. 4.4.7.2")) + " art. 4.4.7.2"

    assert retrieval.retrieve(accepted).status == "found"
    assert repository.exact_calls == 1
    assert embedder.calls == 0

    with pytest.raises(ValueError, match="limita"):
        retrieval.retrieve(accepted + "x")

    assert repository.exact_calls == 1
    assert repository.semantic_calls == 0
    assert embedder.calls == 0


def test_exact_gasit_nu_apeleaza_embedderul():
    repository = RepositoryFake([evidence()], [])
    embedder = EmbedderFake()

    result = service(repository, embedder).retrieve("NP010 art. 4.4.7.2")

    assert result.status == "found"
    assert result.evidence == (evidence(),)
    assert repository.exact_calls == 1
    assert repository.semantic_calls == 0
    assert embedder.calls == 0


def test_articol_nemarcat_validat_in_metadata_face_exact_fara_embedding():
    repository = RepositoryFake([evidence()], [])
    embedder = EmbedderFake()

    result = service(repository, embedder).retrieve("consulta 4.4.7.2")

    assert result.status == "found"
    assert repository.exact_calls == 1
    assert repository.semantic_calls == 0
    assert embedder.calls == 0


def test_referinte_multiple_nu_apeleaza_lookup_sau_embedder():
    repository = RepositoryFake([evidence()], [evidence(score=0.99)])
    embedder = EmbedderFake()

    result = service(repository, embedder).retrieve("art. 4.4.7.2 și art. 4.6.(1)")

    assert result.status == "ambiguous_reference"
    assert repository.exact_calls == 0
    assert repository.semantic_calls == 0
    assert embedder.calls == 0


def test_articol_explicit_lipsa_nu_are_fallback_semantic():
    repository = RepositoryFake([], [evidence(score=0.99)])
    embedder = EmbedderFake()

    result = service(repository, embedder).retrieve("articolul 99.99.99")

    assert result.status == "not_found"
    assert repository.exact_calls == 1
    assert repository.semantic_calls == 0
    assert embedder.calls == 0


def test_exact_deduplica_hashuri_identice_din_acelasi_document():
    duplicate = evidence(chunk_id=2)
    result = service(RepositoryFake([evidence(), duplicate], [])).retrieve("art. 4.4.7.2")

    assert result.status == "found"
    assert result.evidence == (evidence(),)


def test_exact_pastreaza_documentele_diferite_chiar_cu_acelasi_hash():
    din_alt_document = evidence(chunk_id=2, document_id="doc-alternativ")
    result = service(RepositoryFake([evidence(), din_alt_document], [])).retrieve("art. 4.4.7.2")

    assert result.status == "found"
    assert [item.document_id for item in result.evidence] == ["doc-np010", "doc-alternativ"]


def test_hashuri_diferite_pentru_acelasi_document_articol_sunt_ambigue():
    conflicting = evidence(chunk_id=2, content="alt fragment", content_hash="hash-b")
    result = service(RepositoryFake([evidence(), conflicting], [])).retrieve("art. 4.4.7.2")

    assert result.status == "ambiguous_article"
    assert result.evidence == ()


def test_semantic_detecteaza_hashuri_diferite_pentru_acelasi_articol():
    repository = RepositoryFake(
        [],
        [
            evidence(content_hash="hash-a", score=0.90),
            evidence(chunk_id=2, content_hash="hash-b", score=0.80),
        ],
    )

    result = service(repository).retrieve("întrebare semantică")

    assert result.status == "ambiguous_article"
    assert result.evidence == ()


def test_semantic_aplica_top_k_prag_deduplicare_si_context():
    repository = RepositoryFake(
        [],
        [
            evidence(content="aaaa", content_hash="a", score=0.90),
            evidence(chunk_id=2, content="duplicat", content_hash="a", score=0.80),
            evidence(chunk_id=3, article="5.1.1", content="bbbb", content_hash="b", score=0.60),
            evidence(chunk_id=4, article="6.1.1", content="respins", content_hash="c", score=0.49),
        ],
    )
    result = service(repository, semantic_top_k=3, max_context_chars=8).retrieve("întrebare semantică")

    assert result.status == "found"
    assert [item.content_hash for item in result.evidence] == ["a", "b"]
    assert repository.top_k == 3


def test_limita_de_context_exclude_candidatul_care_ar_depasi_limita():
    """Spre deosebire de testul de mai sus, aici un al treilea candidat NU incape."""
    repository = RepositoryFake(
        [],
        [
            evidence(article="4.1.1", content="aaaa", content_hash="a", score=0.90),
            evidence(chunk_id=2, article="4.1.2", content="bbbb", content_hash="b", score=0.80),
            evidence(chunk_id=3, article="4.1.3", content="cccc", content_hash="c", score=0.70),
        ],
    )
    result = service(repository, semantic_top_k=3, max_context_chars=8).retrieve("întrebare semantică")

    assert result.status == "found"
    # 4 + 4 = 8 incape; al treilea ar duce la 12 > 8, deci trebuie exclus, nu doar taiat.
    assert [item.content_hash for item in result.evidence] == ["a", "b"]
    assert len(result.evidence) < len(repository.semantic)


def test_semantic_sub_prag_este_not_found_si_erorile_dependentei_se_propagă():
    repository = RepositoryFake([], [evidence(score=0.49)])
    assert service(repository).retrieve("întrebare semantică").status == "not_found"

    class EmbedderDefect:
        def embed_query(self, _question):
            raise RuntimeError("serviciu indisponibil")

    with pytest.raises(RuntimeError, match="indisponibil"):
        service(RepositoryFake([], []), EmbedderDefect()).retrieve("întrebare semantică")
