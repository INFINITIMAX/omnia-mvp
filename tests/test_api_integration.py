"""Teste FastAPI complet mockuite pentru integrarea Retrieval + Generation."""

import importlib
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

import main
from generation_core import GenerationValidationError


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
    main.app.dependency_overrides.clear()
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


def configure(api, connection, embedder=None, generator=None):
    main.app.dependency_overrides[main.get_connection_factory] = lambda: lambda: connection
    main.app.dependency_overrides[main.get_embedder] = lambda: embedder or EmbedderFake()
    main.app.dependency_overrides[main.get_text_generator] = lambda: generator or GeneratorFake()
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
def test_input_invalid_este_422_inainte_de_conexiune(api, question):
    connection_calls = 0

    def factory():
        nonlocal connection_calls
        connection_calls += 1
        return ConnectionFake()

    main.app.dependency_overrides[main.get_connection_factory] = lambda: factory
    response = api.post("/intreaba", json={"intrebare": question})

    assert response.status_code == 422
    assert connection_calls == 0


@pytest.mark.parametrize(
    ("connection", "embedder", "generator", "question"),
    [
        (ConnectionFake(error=RuntimeError("db")), EmbedderFake(), GeneratorFake(), "art. 4.4.7.2"),
        (ConnectionFake(), EmbedderFake(error=RuntimeError("voyage")), GeneratorFake(), "întrebare semantică"),
        (ConnectionFake(), EmbedderFake(), GeneratorFake(error=RuntimeError("claude")), "art. 4.4.7.2"),
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


def test_root_ramane_functional(api):
    response = api.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_import_main_nu_creeaza_clienti_externi(monkeypatch):
    voyage_calls = []
    anthropic_calls = []
    monkeypatch.setattr(main.voyageai, "Client", lambda *args, **kwargs: voyage_calls.append(1))
    monkeypatch.setattr(main, "Anthropic", lambda *args, **kwargs: anthropic_calls.append(1))

    importlib.reload(main)

    assert voyage_calls == []
    assert anthropic_calls == []
