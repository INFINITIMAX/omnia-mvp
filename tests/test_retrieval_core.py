"""Teste sintetice pentru Retrieval Core; nu folosesc DB, Voyage sau texte normative."""

from dataclasses import dataclass, field

import pytest

from retrieval_core import (
    MAX_QUESTION_CHARS,
    ArticleParser,
    ConversationTurn,
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
    # Doar pentru testele de context: rezultatele căutării restrânse la documentele preferate
    # și urma apelurilor (embedding + document_id-uri primite), ca să verificăm ce a cerut serviciul.
    semantic_in_documents: list[Evidence] = field(default_factory=list)
    scoped_calls: list[tuple[tuple[float, ...], tuple[str, ...], int]] = field(default_factory=list)

    def find_exact(self, _document_id, _article):
        self.exact_calls += 1
        return self.exact

    def find_semantic(self, _embedding, top_k):
        self.semantic_calls += 1
        self.top_k = top_k
        return self.semantic

    def find_semantic_in_documents(self, embedding, top_k, document_ids):
        self.scoped_calls.append((tuple(embedding), tuple(document_ids), top_k))
        return self.semantic_in_documents


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


# --- normalizare simetrică a diacriticelor (sedila -> virgulă) în întrebare ---


class EmbedderCareRetineIntrebarea:
    """Reține exact șirul primit, ca să verificăm ce a ajuns la embedder."""

    def __init__(self, result=(0.1, 0.2)):
        self.result = result
        self.intrebari_primite = []

    def embed_query(self, question):
        self.intrebari_primite.append(question)
        return self.result


def test_intrebarea_cu_sedila_ajunge_normalizata_la_embedder():
    repository = RepositoryFake([], [evidence(score=0.99)])
    embedder = EmbedderCareRetineIntrebarea()

    service(repository, embedder).retrieve("ce ştie normativul despre reţea şi acţiune")

    assert embedder.intrebari_primite == ["ce știe normativul despre rețea și acțiune"]


def test_intrebarea_cu_sedila_gaseste_articolul_exact_ca_varianta_cu_virgula():
    """Un articol marcat explicit (numeric) nu e afectat de diacritice, dar
    verificăm că normalizarea nu strică deloc calea exactă: aceeași
    întrebare, scrisă cu sedilă sau cu virgulă, produce exact același
    rezultat (aceeași cerere către find_exact)."""
    repository_sedila = RepositoryFake([evidence()], [])
    repository_virgula = RepositoryFake([evidence()], [])

    intrebare_sedila = "ce spune articolul 4.4.7.2 despre reţea şi Ţara"
    intrebare_virgula = "ce spune articolul 4.4.7.2 despre rețea și Țara"

    rezultat_sedila = service(repository_sedila).retrieve(intrebare_sedila)
    rezultat_virgula = service(repository_virgula).retrieve(intrebare_virgula)

    assert rezultat_sedila.status == rezultat_virgula.status == "found"
    assert repository_sedila.exact_calls == repository_virgula.exact_calls == 1


# --- D11: contextul îmbogățește embedding-ul, fără scope implicit după citări ---


# Două documente distincte, ca în bug-ul real din producție: continuarea unei întrebări
# despre sprinklere (P 118/2-2013) ajungea în instalații electrice (I7-2011).
CONTEXT_ALIASES = {
    "doc-p118": ("P 118/2-2013", "p11822013", "p1182"),
    "doc-i7": ("I7-2011", "i72011", "i7"),
}
CONTEXT_KNOWN = {"doc-p118": ("7.183",), "doc-i7": ("6.3.1",)}


def context_service(repository, embedder=None, **config):
    return RetrievalService(
        ArticleParser(CONTEXT_ALIASES, CONTEXT_KNOWN), repository, embedder or EmbedderFake(), **config
    )


def sprinklere_context():
    return (ConversationTurn("Ce obstacole sunt permise sub sprinklere?", ("P 118/2-2013",)),)


def test_fara_context_cautarea_semantica_ramane_globala_si_neschimbata():
    """Compatibilitate înapoi: o cerere fără context nu atinge deloc restricția semantică."""
    repository = RepositoryFake([], [evidence(score=0.90)])
    embedder = EmbedderCareRetineIntrebarea()

    result = context_service(repository, embedder).retrieve("când am un obstacol?")

    assert result.status == "found"
    assert repository.semantic_calls == 1
    assert repository.scoped_calls == []
    assert embedder.intrebari_primite == ["când am un obstacol?"]


def test_continuarea_fara_referinta_cauta_global_cu_context():
    repository = RepositoryFake([], [evidence(document_id="doc-i7", score=0.99)])
    repository.semantic_in_documents = [evidence(document_id="doc-p118", score=0.80)]
    embedder = EmbedderFake()

    result = context_service(repository, embedder).retrieve(
        "Ok dar spune-mi exact când am un obstacol?", sprinklere_context()
    )

    assert result.status == "found"
    # D11 înlocuiește preferința obligatorie; scenariul și cele două surse sunt păstrate.
    assert [item.document_id for item in result.evidence] == ["doc-i7"]
    assert repository.scoped_calls == []
    assert repository.semantic_calls == 1
    assert repository.top_k == 5
    assert embedder.calls == 1


@pytest.mark.parametrize("scoped", [[], [evidence(document_id="doc-p118", score=0.49)]])
def test_context_scoped_miss_nu_impiedica_dovezile_globale(scoped):
    """D11: lipsa/scorul mic în documentul istoric nu blochează căutarea globală."""
    repository = RepositoryFake([], [evidence(document_id="doc-i7", score=0.90)])
    repository.semantic_in_documents = scoped
    embedder = EmbedderFake()

    result = context_service(repository, embedder).retrieve(
        "Ok dar spune-mi exact când am un obstacol?", sprinklere_context()
    )

    assert result.status == "found"
    assert result.evidence == tuple(repository.semantic)
    assert repository.scoped_calls == []
    assert repository.semantic_calls == 1
    assert repository.top_k == 5
    assert embedder.calls == 1


def test_referinta_explicita_de_document_invinge_contextul():
    """Utilizatorul trebuie să poată schimba deliberat subiectul: dacă numește el documentul,
    contextul nu mai are niciun cuvânt de spus."""
    repository = RepositoryFake([evidence(document_id="doc-i7")], [])
    embedder = EmbedderFake()
    context = (ConversationTurn("Ce spune despre sprinklere?", ("P 118/2-2013",)),)

    result = context_service(repository, embedder).retrieve("I7-2011, art. 6.3.1", context)

    assert result.status == "found"
    assert repository.exact_calls == 1
    assert repository.scoped_calls == []
    assert repository.semantic_calls == 0
    assert embedder.calls == 0


def test_documentul_numit_fara_articol_cauta_global_si_pastreaza_contextul():
    repository = RepositoryFake([], [evidence(document_id="doc-p118", score=0.90)])
    repository.semantic_in_documents = [evidence(document_id="doc-i7", score=0.90)]
    embedder = EmbedderCareRetineIntrebarea()
    context = (ConversationTurn("Ce spune despre sprinklere?", ("P 118/2-2013",)),)

    result = context_service(repository, embedder).retrieve("Ce spune I7-2011 despre obstacole?", context)

    assert result.status == "found"
    # D11: simpla menționare nu este directivă D12 și nu elimină întrebările istorice.
    assert [item.document_id for item in result.evidence] == ["doc-p118"]
    assert repository.scoped_calls == []
    assert repository.semantic_calls == 1
    assert repository.top_k == 5
    assert embedder.intrebari_primite == [
        "Ce spune despre sprinklere?\nCe spune I7-2011 despre obstacole?"
    ]


@pytest.mark.parametrize("scoped", [[], [evidence(document_id="doc-i7", score=0.49)]])
def test_documentul_mentionat_cu_scoped_miss_nu_impiedica_cautarea_globala(scoped):
    """D11: codul menționat fără exclusivitate nu autorizează scoped, nici la miss."""
    repository = RepositoryFake([], [evidence(document_id="doc-p118", score=0.90)])
    repository.semantic_in_documents = scoped
    embedder = EmbedderFake()

    result = context_service(repository, embedder).retrieve("Ce spune I7-2011 despre obstacole?")

    assert result.status == "found"
    assert result.evidence == tuple(repository.semantic)
    assert repository.semantic_calls == 1
    assert repository.scoped_calls == []
    assert repository.top_k == 5
    assert embedder.calls == 1


def test_articolul_explicit_ramane_pe_calea_exacta_chiar_cu_context():
    repository = RepositoryFake([evidence()], [])
    embedder = EmbedderFake()

    result = context_service(repository, embedder).retrieve("art. 7.183", sprinklere_context())

    assert result.status == "found"
    assert repository.exact_calls == 1
    assert repository.scoped_calls == []
    assert embedder.calls == 0


def test_intrebarile_anterioare_imbogatesc_textul_trimis_la_embedding():
    """Miezul problemei: „când am un obstacol?” trebuie să moștenească subiectul „sprinklere”."""
    repository = RepositoryFake([], [evidence(score=0.90)])
    embedder = EmbedderCareRetineIntrebarea()

    context_service(repository, embedder).retrieve(
        "Ok dar spune-mi exact când am un obstacol?", sprinklere_context()
    )

    assert embedder.intrebari_primite == [
        "Ce obstacole sunt permise sub sprinklere?\nOk dar spune-mi exact când am un obstacol?"
    ]


def test_textul_de_embedding_pastreaza_ordinea_cronologica_cu_intrebarea_curenta_ultima():
    repository = RepositoryFake([], [evidence(score=0.90)])
    embedder = EmbedderCareRetineIntrebarea()
    context = (ConversationTurn("prima", ()), ConversationTurn("a doua", ()))

    context_service(repository, embedder).retrieve("curenta", context)

    assert embedder.intrebari_primite == ["prima\na doua\ncurenta"]


def test_intrebarile_din_context_ajung_normalizate_la_embedder():
    repository = RepositoryFake([], [evidence(score=0.90)])
    embedder = EmbedderCareRetineIntrebarea()
    context = (ConversationTurn("ce ştie despre reţea?", ()),)

    context_service(repository, embedder).retrieve("şi acţiunea?", context)

    assert embedder.intrebari_primite == ["ce știe despre rețea?\nși acțiunea?"]


def test_contextul_pastreaza_doar_ultimele_trei_tururi():
    repository = RepositoryFake([], [evidence(score=0.90)])
    embedder = EmbedderCareRetineIntrebarea()
    context = tuple(ConversationTurn(f"tur{index}", ()) for index in range(5))

    context_service(repository, embedder).retrieve("curenta", context)

    assert embedder.intrebari_primite == ["tur2\ntur3\ntur4\ncurenta"]


def test_codurile_necunoscute_din_context_nu_produc_preferinta():
    """Un cod care nu există în catalogul aprobat nu poate lărgi accesul: pur și simplu
    nu se rezolvă, iar căutarea rămâne cea globală."""
    repository = RepositoryFake([], [evidence(score=0.90)])
    context = (ConversationTurn("întrebare anterioară", ("XX 999-1999", "SR EN inexistent")),)

    result = context_service(repository).retrieve("continuare", context)

    assert result.status == "found"
    assert repository.scoped_calls == []
    assert repository.semantic_calls == 1


@pytest.mark.parametrize(
    "coduri",
    [("",), ("x" * 65,), (123,), (None,), ({"cod": "P 118/2-2013"},)],
)
def test_codurile_invalide_din_context_sunt_ignorate_in_siguranta(coduri):
    repository = RepositoryFake([], [evidence(score=0.90)])
    context = (ConversationTurn("întrebare anterioară", coduri),)

    result = context_service(repository).retrieve("continuare", context)

    assert result.status == "found"
    assert repository.scoped_calls == []
    assert repository.semantic_calls == 1


def test_doar_primele_patru_coduri_dintr_un_tur_sunt_luate_in_seama():
    repository = RepositoryFake([], [evidence(score=0.90)])
    repository.semantic_in_documents = [evidence(document_id="doc-p118", score=0.90)]
    context = (
        ConversationTurn(
            "întrebare anterioară",
            ("XX 1", "XX 2", "XX 3", "XX 4", "P 118/2-2013"),
        ),
    )

    context_service(repository).retrieve("continuare", context)

    # D11: niciun cod istoric nu filtrează; plafonul de validare rămâne verificat separat.
    assert repository.scoped_calls == []
    assert repository.semantic_calls == 1
    validated = context_service(repository)._validated_context(context)
    assert validated[0].coduri_documente == ("XX 1", "XX 2", "XX 3", "XX 4")


def test_codurile_repetate_din_istoric_nu_restrang_documentele():
    repository = RepositoryFake([], [evidence(score=0.90)])
    repository.semantic_in_documents = [evidence(document_id="doc-p118", score=0.90)]
    context = (
        ConversationTurn("prima", ("P 118/2-2013", "I7-2011")),
        ConversationTurn("a doua", ("P 118/2-2013",)),
    )

    embedder = EmbedderCareRetineIntrebarea()
    result = context_service(repository, embedder).retrieve("continuare", context)

    # D11: aceleași coduri repetate nu produc nici măcar un filtru deduplicat.
    assert repository.scoped_calls == []
    assert repository.semantic_calls == 1
    assert result.evidence == tuple(repository.semantic)
    assert embedder.intrebari_primite == ["prima\na doua\ncontinuare"]


@pytest.mark.parametrize(
    "context",
    [
        "nu e o listă de tururi",
        ["nu e un tur tipat"],
        [ConversationTurn(123, ())],
        [ConversationTurn("   ", ())],
        [ConversationTurn("x" * (MAX_QUESTION_CHARS + 1), ())],
        [ConversationTurn("întrebare", "nu e o listă de coduri")],
        [ConversationTurn("întrebare", 7)],
    ],
)
def test_contextul_invalid_este_respins_inainte_de_orice_dependenta(context):
    repository = RepositoryFake([evidence()], [evidence(score=0.90)])
    embedder = EmbedderFake()

    with pytest.raises(ValueError):
        context_service(repository, embedder).retrieve("continuare", context)

    assert embedder.calls == 0
    assert repository.semantic_calls == 0
    assert repository.exact_calls == 0
    assert repository.scoped_calls == []


def test_codul_oficial_citat_se_rezolva_prin_catalogul_documentelor_aprobate():
    """Codul întors clientului în citări (`cod_document`) trebuie să se întoarcă la
    `document_id` folosind exact aliasurile catalogului, inclusiv pentru coduri cu „/”."""
    catalog = PostgresApprovedCatalogRepository(
        ConnectionFake([("doc-p118", "P 118/2-2013", "7.183"), ("doc-i7", "I7-2011", "6.3.1")])
    ).load()
    parser = catalog.create_parser()

    assert parser.documents_for_official_code("P 118/2-2013") == frozenset({"doc-p118"})
    assert parser.documents_for_official_code("p 118 / 2 - 2013") == frozenset({"doc-p118"})
    assert parser.documents_for_official_code("I7-2011") == frozenset({"doc-i7"})
    assert parser.documents_for_official_code("NP 010-2022") == frozenset()


@pytest.mark.parametrize("code", ["", "   ", None, 7, ("P 118/2-2013",)])
def test_codul_invalid_nu_rezolva_niciun_document(code):
    assert ArticleParser(CONTEXT_ALIASES, CONTEXT_KNOWN).documents_for_official_code(code) == frozenset()


def test_repository_semantic_restrans_foloseste_any_parametrizat_si_pastreaza_approved():
    connection = ConnectionFake([(1, "doc-p118", "COD", "Titlu", "7.183", "7.183", "text", "hash", 0.75)])

    found = PostgresRetrievalRepository(connection).find_semantic_in_documents(
        [0.1, 2], 3, ("doc-p118", "doc-i7")
    )

    sql, parameters = connection.cursor_instance.calls[0]
    assert "WHERE document.status = 'approved' AND chunk.embedding IS NOT NULL" in sql
    assert "AND chunk.document_id = ANY(%s)" in sql
    assert "doc-p118" not in sql, "identificatorii nu au voie sa fie interpolati in SQL"
    assert parameters == ("[0.1,2.0]", ["doc-p118", "doc-i7"], "[0.1,2.0]", 3)
    assert found[0].score == 0.75
    assert connection.cursor_instance.closed


@pytest.mark.parametrize("document_ids", [(), [], "doc-p118", ("",), (None,), (7,), 5])
def test_repository_semantic_restrans_refuza_lista_de_documente_invalida(document_ids):
    repository = PostgresRetrievalRepository(ConnectionFake([]))

    with pytest.raises(ValueError, match="document_ids"):
        repository.find_semantic_in_documents([0.1], 3, document_ids)


def test_scenariul_real_sprinklere_apoi_obstacol_cauta_global_cu_context():
    """Scenariul istoric este păstrat; D11 nu mai exclude I7 prin citarea anterioară.

    Acest test de rutare nu dovedește relevanța semantică a rezultatului global.
    """
    din_i7 = evidence(document_id="doc-i7", content="ocolirea corniselor", content_hash="i7", score=0.88)
    din_p118 = evidence(document_id="doc-p118", content="obstacole sub sprinklere", content_hash="p118", score=0.72)
    repository = RepositoryFake([], [din_i7])
    repository.semantic_in_documents = [din_p118]

    result = context_service(repository).retrieve(
        "Ok dar spune-mi exact când am un obstacol?", sprinklere_context()
    )

    assert result.status == "found"
    assert [item.content for item in result.evidence] == ["ocolirea corniselor"]
    assert [item.document_id for item in result.evidence] == ["doc-i7"]
    assert repository.semantic_calls == 1
    assert repository.scoped_calls == []
