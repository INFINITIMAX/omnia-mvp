"""Teste FastAPI complet mockuite pentru integrarea Retrieval + Generation."""

import importlib
from dataclasses import dataclass
from types import SimpleNamespace

import anthropic
import dotenv
import psycopg2
import pytest
from fastapi.testclient import TestClient
import voyageai

import main


CATALOG_ROWS = [("doc-1", "NP 010-2022", "4.4.7.2")]
EXACT_ROW = (1, "doc-1", "NP 010-2022", "Titlu oficial", "4.4.7.2", "4.4.7.2", "fragment public", "hash-a")
SEMANTIC_ROW = EXACT_ROW + (0.9,)


class CursorFake:
    def __init__(self, connection):
        self.connection = connection
        self.closed = False
        self.rows = []

    def execute(self, sql, parameters):
        self.connection.calls.append((sql, parameters))
        if self.connection.error is not None:
            raise self.connection.error
        if "SELECT document.document_id" in sql:
            self.rows = self.connection.catalog_rows
        elif "AS score" in sql:
            self.rows = self.connection.semantic_rows
        else:
            self.rows = self.connection.exact_rows

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed = True


class ConnectionFake:
    def __init__(self, *, catalog_rows=CATALOG_ROWS, exact_rows=(EXACT_ROW,), semantic_rows=(SEMANTIC_ROW,), error=None):
        self.catalog_rows = catalog_rows
        self.exact_rows = exact_rows
        self.semantic_rows = semantic_rows
        self.error = error
        self.calls = []
        self.closed = False
        self.cursors = []

    def cursor(self):
        cursor = CursorFake(self)
        self.cursors.append(cursor)
        return cursor

    def close(self):
        self.closed = True


@dataclass
class EmbedderFake:
    result: tuple[float, ...] = (0.1, 0.2)
    calls: int = 0
    error: Exception | None = None

    def embed_query(self, _question):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result


@dataclass
class GeneratorFake:
    answer: str = "Răspuns [C1]."
    calls: int = 0
    error: Exception | None = None
    prompt: str | None = None

    def generate(self, prompt, *, max_tokens):
        self.calls += 1
        self.prompt = prompt
        if self.error:
            raise self.error
        return self.answer


@pytest.fixture
def api():
    original_dependencies = main.app.state.runtime_dependencies
    yield TestClient(main.app)
    main.app.state.runtime_dependencies = original_dependencies


def configure(api, connection, embedder=None, generator=None):
    main.app.state.runtime_dependencies = main.RuntimeDependencies(
        connection_factory=lambda: connection,
        embedder_factory=lambda: embedder or EmbedderFake(),
        text_generator_factory=lambda: generator or GeneratorFake(),
    )
    return api


def test_exact_answered_are_citare_publica_si_zero_voyage(api):
    connection = ConnectionFake()
    embedder = EmbedderFake()
    generator = GeneratorFake()

    response = configure(api, connection, embedder, generator).post(
        "/intreaba", json={"intrebare": "NP 010-2022, art. 4.4.7.2"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "answered",
        "raspuns": "Răspuns [C1].",
        "citari": [{
            "id": "C1", "cod_document": "NP 010-2022", "titlu_document": "Titlu oficial",
            "articol": "4.4.7.2", "citat": "fragment public",
        }],
    }
    assert embedder.calls == 0
    assert generator.calls == 1
    assert connection.closed
    assert "source_key" not in generator.prompt
    assert "content_hash" not in generator.prompt


def test_semantic_answered_face_exact_un_embedding(api):
    connection = ConnectionFake()
    embedder = EmbedderFake()
    generator = GeneratorFake()

    response = configure(api, connection, embedder, generator).post(
        "/intreaba", json={"intrebare": "Care este regula sintetică?"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "answered"
    assert embedder.calls == 1
    assert generator.calls == 1
    assert connection.closed


@pytest.mark.parametrize(
    ("question", "connection"),
    [
        ("art. 99.99.99", ConnectionFake(exact_rows=())),
        ("art. 4.4.7.2", ConnectionFake(exact_rows=(EXACT_ROW, EXACT_ROW[:-1] + ("hash-b",)))),
        ("art. 4.4.7.2 și art. 4.6.(1)", ConnectionFake()),
    ],
)
def test_statusurile_controlate_nu_apeleaza_claude(api, question, connection):
    generator = GeneratorFake()

    response = configure(api, connection, EmbedderFake(), generator).post(
        "/intreaba", json={"intrebare": question}
    )

    assert response.status_code == 200
    assert response.json()["status"] in {"not_found", "ambiguous_article", "ambiguous_reference"}
    assert response.json()["citari"] == []
    assert generator.calls == 0
    assert connection.closed


@pytest.mark.parametrize("question", ["", "   ", "x" * 1001])
def test_input_invalid_este_422_inainte_de_toti_providerii(api, question):
    calls = {"connection": 0, "embedder": 0, "generator": 0}

    def connection_factory():
        calls["connection"] += 1
        return ConnectionFake()

    def embedder_factory():
        calls["embedder"] += 1
        return EmbedderFake()

    def generator_factory():
        calls["generator"] += 1
        return GeneratorFake()

    main.app.state.runtime_dependencies = main.RuntimeDependencies(
        connection_factory=connection_factory,
        embedder_factory=embedder_factory,
        text_generator_factory=generator_factory,
    )
    response = api.post("/intreaba", json={"intrebare": question})

    assert response.status_code == 422
    assert calls == {"connection": 0, "embedder": 0, "generator": 0}


@pytest.mark.parametrize(
    ("connection", "embedder", "generator", "question"),
    [
        (ConnectionFake(error=psycopg2.OperationalError("db")), EmbedderFake(), GeneratorFake(), "art. 4.4.7.2"),
        (ConnectionFake(), EmbedderFake(error=main.ProviderUnavailableError()), GeneratorFake(), "întrebare semantică"),
        (ConnectionFake(), EmbedderFake(), GeneratorFake(error=main.ProviderUnavailableError()), "art. 4.4.7.2"),
        (ConnectionFake(), EmbedderFake(), GeneratorFake(answer="răspuns fără citare"), "art. 4.4.7.2"),
    ],
)
def test_erorile_dependentei_sunt_503_generic_si_conexiunea_se_inchide(
    api, connection, embedder, generator, question
):
    response = configure(api, connection, embedder, generator).post("/intreaba", json={"intrebare": question})

    assert response.status_code == 503
    assert response.json() == {"detail": "Serviciul este temporar indisponibil."}
    assert connection.closed


@pytest.mark.parametrize("embeddings", [[], [[]], [("nu-este-numar",)], [([float("inf")],)]])
def test_adaptorul_voyage_refuza_raspunsurile_invalide(embeddings):
    class ClientFake:
        def embed(self, *_args, **_kwargs):
            return SimpleNamespace(embeddings=embeddings)

    with pytest.raises(main.ProviderUnavailableError):
        main.VoyageQueryEmbedder(ClientFake()).embed_query("întrebare")


def test_adaptorul_voyage_inveleste_eroarea_sdk():
    class ClientFake:
        def embed(self, *_args, **_kwargs):
            raise voyageai.error.APIConnectionError("indisponibil")

    with pytest.raises(main.ProviderUnavailableError):
        main.VoyageQueryEmbedder(ClientFake()).embed_query("întrebare")


@pytest.mark.parametrize("content", [[], [SimpleNamespace(type="tool_use")], [SimpleNamespace(type="text", text=" ")]])
def test_adaptorul_anthropic_refuza_raspunsurile_invalide(content):
    class MessagesFake:
        def create(self, **_kwargs):
            return SimpleNamespace(content=content)

    class ClientFake:
        messages = MessagesFake()

    with pytest.raises(main.ProviderUnavailableError):
        main.AnthropicTextGenerator(ClientFake()).generate("prompt", max_tokens=800)


def test_adaptorul_anthropic_extrage_doar_blocurile_text_si_inveleste_eroarea_sdk():
    class MessagesFake:
        def create(self, **_kwargs):
            return SimpleNamespace(content=[SimpleNamespace(type="text", text="răspuns")])

    class ClientFake:
        messages = MessagesFake()

    assert main.AnthropicTextGenerator(ClientFake()).generate("prompt", max_tokens=800) == "răspuns"

    class MessagesDefect:
        def create(self, **_kwargs):
            raise anthropic.APIConnectionError(request=None)

    class ClientDefect:
        messages = MessagesDefect()

    with pytest.raises(main.ProviderUnavailableError):
        main.AnthropicTextGenerator(ClientDefect()).generate("prompt", max_tokens=800)


def test_configurarea_lipsa_este_503_generic(api):
    main.app.state.runtime_dependencies = main.RuntimeDependencies(
        connection_factory=lambda: (_ for _ in ()).throw(main.DependencyConfigurationError()),
        embedder_factory=EmbedderFake,
        text_generator_factory=GeneratorFake,
    )

    response = api.post("/intreaba", json={"intrebare": "art. 4.4.7.2"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Serviciul este temporar indisponibil."}


def test_eroarea_psycopg_la_inchiderea_conexiunii_este_503_generic(api):
    class ConnectionCloseDefect(ConnectionFake):
        def close(self):
            self.closed = True
            raise psycopg2.OperationalError("închidere db")

    response = configure(api, ConnectionCloseDefect()).post(
        "/intreaba", json={"intrebare": "art. 4.4.7.2"}
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Serviciul este temporar indisponibil."}


def test_root_ramane_functional(api):
    response = api.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_import_main_nu_creeaza_clienti_externi(monkeypatch):
    voyage_calls = []
    anthropic_calls = []

    dotenv_calls = []

    with monkeypatch.context() as patch:
        patch.setattr(voyageai, "Client", lambda *args, **kwargs: voyage_calls.append(1))
        patch.setattr(anthropic, "Anthropic", lambda *args, **kwargs: anthropic_calls.append(1))
        patch.setattr(dotenv, "load_dotenv", lambda: dotenv_calls.append(1))
        importlib.reload(main)

        assert dotenv_calls == [1]
        assert voyage_calls == []
        assert anthropic_calls == []

    importlib.reload(main)
