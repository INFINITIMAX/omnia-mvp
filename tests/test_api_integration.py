"""Teste FastAPI complet mockuite pentru integrarea Retrieval + Generation."""

import importlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import anthropic
import dotenv
import psycopg2
import pytest
from fastapi.testclient import TestClient
import voyageai

import main
from access_control import RateLimitResult


CATALOG_ROWS = [("doc-1", "NP 010-2022", "4.4.7.2")]
EXACT_ROW = (1, "doc-1", "NP 010-2022", "Titlu oficial", "4.4.7.2", "4.4.7.2", "fragment public", "hash-a")
SEMANTIC_ROW = EXACT_ROW + (0.9,)
NOW = datetime(2026, 9, 1, 12, 34, 56, tzinfo=UTC)
ACCESS_RUNTIME_CONFIG = main.AnonymousAccessControlRuntimeConfig(
    main.AccessControlConfig(bytes(range(32)), bytes(range(32, 64))), cookie_secure=False
)


class CursorFake:
    def __init__(self, connection):
        self.connection = connection
        self.closed = False
        self.rows = []
        self.row = None

    def execute(self, sql, parameters):
        self.connection.calls.append((sql, parameters))
        if self.connection.error is not None:
            raise self.connection.error
        if "INSERT INTO public.anonymous_usage" in sql:
            self.row = next(self.connection.quota_results)
        elif "SET request_count = request_count + 1" in sql:
            self.rows = [("minute", self.connection.minute_count), ("hour", self.connection.hour_count)]
        elif "SELECT document.document_id" in sql:
            self.rows = self.connection.catalog_rows
        elif "AS score" in sql:
            self.rows = self.connection.semantic_rows
        elif "pg_advisory_xact_lock" not in sql and "rate_limit_buckets" not in sql:
            self.rows = self.connection.exact_rows

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed = True


class ConnectionFake:
    def __init__(
        self, *, catalog_rows=CATALOG_ROWS, exact_rows=(EXACT_ROW,), semantic_rows=(SEMANTIC_ROW,),
        minute_count=1, hour_count=1, quota_results=((1,),), error=None, rollback_error=None,
    ):
        self.catalog_rows = catalog_rows
        self.exact_rows = exact_rows
        self.semantic_rows = semantic_rows
        self.minute_count = minute_count
        self.hour_count = hour_count
        self.quota_results = iter(quota_results)
        self.error = error
        self.rollback_error = rollback_error
        self.calls = []
        self.closed = False
        self.cursors = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        cursor = CursorFake(self)
        self.cursors.append(cursor)
        return cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1
        if self.rollback_error is not None:
            raise self.rollback_error

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
    yield TestClient(main.app, client=("127.0.0.1", 50000))
    main.app.state.runtime_dependencies = original_dependencies


def configure(api, connection, embedder=None, generator=None, runtime_config=ACCESS_RUNTIME_CONFIG):
    main.app.state.runtime_dependencies = main.RuntimeDependencies(
        connection_factory=lambda: connection,
        embedder_factory=lambda: embedder or EmbedderFake(),
        text_generator_factory=lambda: generator or GeneratorFake(),
        access_control_config_factory=lambda: runtime_config,
        now_factory=lambda: NOW,
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
        "intrebari_ramase": 9,
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


@pytest.mark.parametrize(
    ("question", "connection"),
    [
        ("NP 010-2022, art. 4.4.7.2", ConnectionFake()),
        ("Care este regula sintetică?", ConnectionFake()),
        ("art. 99.99.99", ConnectionFake(exact_rows=())),
        ("art. 4.4.7.2", ConnectionFake(exact_rows=(EXACT_ROW, EXACT_ROW[:-1] + ("hash-b",)))),
        ("art. 4.4.7.2 și art. 4.6.(1)", ConnectionFake()),
    ],
)
def test_raspunsul_public_nu_contine_niciodata_identificatori_tehnici(api, question, connection):
    """Verifica raspunsul HTTP real (nu doar promptul intern) pe toate statusurile posibile."""
    response = configure(api, connection, EmbedderFake(), GeneratorFake()).post(
        "/intreaba", json={"intrebare": question}
    )

    assert response.status_code == 200
    corp = response.text
    assert "source_key" not in corp
    assert "doc-1" not in corp, "document_id intern nu trebuie sa apara in raspunsul public"
    assert "_extras.txt" not in corp
    assert "extras.txt" not in corp


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
        access_control_config_factory=lambda: ACCESS_RUNTIME_CONFIG,
        now_factory=lambda: NOW,
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
    response = configure(api, ConnectionFake()).get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def _assert_cookie_attributes(response, *, secure):
    header = response.headers["set-cookie"]
    assert "normativai_anon=" in header
    assert "Max-Age=31536000" in header
    assert "HttpOnly" in header
    assert "Path=/" in header
    assert "SameSite=lax" in header
    assert ("Secure" in header) is secure


def test_get_fara_cookie_emite_cookie_si_nu_il_roteste_valid(api):
    client = configure(api, ConnectionFake())

    first = client.get("/")
    second = client.get("/")

    assert first.status_code == 200
    _assert_cookie_attributes(first, secure=False)
    assert "set-cookie" not in second.headers


def test_get_secure_true_emite_toate_atributele_cookie(api):
    runtime_config = main.AnonymousAccessControlRuntimeConfig(
        ACCESS_RUNTIME_CONFIG.access_control, cookie_secure=True
    )

    response = configure(api, ConnectionFake(), runtime_config=runtime_config).get("/")

    assert response.status_code == 200
    _assert_cookie_attributes(response, secure=True)


def test_cookie_falsificat_este_inlocuit_fail_closed_la_post(api):
    client = configure(api, ConnectionFake())
    client.cookies.set("normativai_anon", "v1.invalid.1.invalid")

    response = client.post("/intreaba", json={"intrebare": "art. 4.4.7.2"})

    assert response.status_code == 200
    _assert_cookie_attributes(response, secure=False)


def test_cookie_expirat_este_inlocuit_la_post(api):
    expired_token, _ = main.issue_anonymous_cookie(
        ACCESS_RUNTIME_CONFIG.access_control, now=NOW - timedelta(days=366)
    )

    client = configure(api, ConnectionFake())
    client.cookies.set("normativai_anon", expired_token)

    response = client.post("/intreaba", json={"intrebare": "art. 4.4.7.2"})

    assert response.status_code == 200
    _assert_cookie_attributes(response, secure=False)


@pytest.mark.parametrize(("raw", "expected"), [(" true ", True), ("FALSE", False)])
def test_configurarea_cookie_secure_accepta_numai_bool_strict(monkeypatch, raw, expected):
    monkeypatch.setenv("ANONYMOUS_COOKIE_SIGNING_KEY", "abcdefghijklmnopqrstuvwxyz0123456789")
    monkeypatch.setenv("ANONYMOUS_IP_HASH_KEY", "9876543210zyxwvutsrqponmlkjihgfedcba")
    monkeypatch.setenv("ANONYMOUS_COOKIE_SECURE", raw)

    assert main._anonymous_access_control_config().cookie_secure is expected


@pytest.mark.parametrize("raw", [None, "", "1", "yes", " falsee "])
def test_configurarea_cookie_secure_invalida_este_eroare_generica(monkeypatch, raw):
    monkeypatch.setenv("ANONYMOUS_COOKIE_SIGNING_KEY", "abcdefghijklmnopqrstuvwxyz0123456789")
    monkeypatch.setenv("ANONYMOUS_IP_HASH_KEY", "9876543210zyxwvutsrqponmlkjihgfedcba")
    if raw is None:
        monkeypatch.delenv("ANONYMOUS_COOKIE_SECURE", raising=False)
    else:
        monkeypatch.setenv("ANONYMOUS_COOKIE_SECURE", raw)

    with pytest.raises(main.DependencyConfigurationError, match="configurație indisponibilă"):
        main._anonymous_access_control_config()


def test_post_valid_fara_cookie_emite_fallback_si_confirma_rate_apoi_quota(api):
    connection = ConnectionFake()
    response = configure(api, connection).post("/intreaba", json={"intrebare": "art. 4.4.7.2"})

    assert response.status_code == 200
    assert response.json()["intrebari_ramase"] == 9
    _assert_cookie_attributes(response, secure=False)
    assert connection.commits == 2
    assert connection.rollbacks == 0
    rate_increment = next(index for index, (sql, _) in enumerate(connection.calls) if "SET request_count" in sql)
    quota_reservation = next(index for index, (sql, _) in enumerate(connection.calls) if "anonymous_usage" in sql)
    assert rate_increment < quota_reservation


def test_rate_limit_429_are_retry_after_si_nu_rezerva_quota(api):
    connection = ConnectionFake(minute_count=6, hour_count=6)
    embedder = EmbedderFake()
    generator = GeneratorFake()

    response = configure(api, connection, embedder, generator).post(
        "/intreaba", json={"intrebare": "art. 4.4.7.2"}
    )

    assert response.status_code == 429
    assert response.json() == {
        "code": "rate_limited",
        "detail": "Prea multe cereri. Încearcă din nou mai târziu.",
    }
    assert response.headers["retry-after"] == "4"
    assert "normativai_anon=" in response.headers["set-cookie"]
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert all("anonymous_usage" not in sql for sql, _ in connection.calls)
    assert embedder.calls == generator.calls == 0


def test_quota_403_are_intrebari_ramase_zero_si_face_rollback(api):
    connection = ConnectionFake(quota_results=(None,))
    embedder = EmbedderFake()
    generator = GeneratorFake()

    response = configure(api, connection, embedder, generator).post(
        "/intreaba", json={"intrebare": "art. 4.4.7.2"}
    )

    assert response.status_code == 403
    assert response.json() == {
        "code": "quota_exhausted",
        "detail": "Ai folosit toate cele 10 întrebări disponibile în acest browser.",
        "intrebari_ramase": 0,
    }
    assert connection.commits == 1
    assert connection.rollbacks == 1
    assert embedder.calls == generator.calls == 0


def test_rollback_db_esuat_la_eroare_cunoscuta_devine_503_generic(api):
    connection = ConnectionFake(
        error=psycopg2.OperationalError("db"),
        rollback_error=psycopg2.OperationalError("rollback db"),
    )

    response = configure(api, connection).post("/intreaba", json={"intrebare": "art. 4.4.7.2"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Serviciul este temporar indisponibil."}
    assert connection.rollbacks == 1
    assert connection.closed


def test_rollback_db_esuat_la_quota_epuizata_devine_503_generic(api):
    connection = ConnectionFake(
        quota_results=(None,), rollback_error=psycopg2.OperationalError("rollback db")
    )

    response = configure(api, connection).post("/intreaba", json={"intrebare": "art. 4.4.7.2"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Serviciul este temporar indisponibil."}
    assert connection.rollbacks == 1
    assert connection.closed


def test_rollback_db_esuat_la_eroare_neasteptata_devine_503_generic(api):
    connection = ConnectionFake(rollback_error=psycopg2.OperationalError("rollback db"))

    response = configure(
        api, connection, EmbedderFake(), GeneratorFake(error=RuntimeError("defect sintetic"))
    ).post("/intreaba", json={"intrebare": "art. 4.4.7.2"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Serviciul este temporar indisponibil."}
    assert connection.rollbacks == 1
    assert connection.closed


def test_eroare_tehnica_face_rollback_quota_dupa_commit_rate(api):
    connection = ConnectionFake()

    response = configure(
        api, connection, EmbedderFake(), GeneratorFake(error=main.ProviderUnavailableError())
    ).post("/intreaba", json={"intrebare": "art. 4.4.7.2"})

    assert response.status_code == 503
    assert connection.commits == 1
    assert connection.rollbacks == 1
    assert connection.closed


def test_eroarea_neasteptata_face_rollback_si_este_repropagata(api):
    connection = ConnectionFake()

    with pytest.raises(RuntimeError, match="defect sintetic"):
        configure(
            api, connection, EmbedderFake(), GeneratorFake(error=RuntimeError("defect sintetic"))
        ).post("/intreaba", json={"intrebare": "art. 4.4.7.2"})

    assert connection.commits == 1
    assert connection.rollbacks == 1
    assert connection.closed


@pytest.mark.parametrize("client", [None, SimpleNamespace(), SimpleNamespace(host=None), SimpleNamespace(host="invalid")])
def test_extragerea_ip_absent_sau_invalid_este_eroare_dependenta(client):
    request = SimpleNamespace(client=client)

    with pytest.raises(main.ServiceDependencyError):
        main._request_ip_hash(request, ACCESS_RUNTIME_CONFIG)


def test_ip_invalid_opreste_inainte_de_rate_quota_si_provideri(api, monkeypatch):
    connection = ConnectionFake()
    embedder = EmbedderFake()
    generator = GeneratorFake()
    monkeypatch.setattr(main, "hash_ip", lambda *_args: (_ for _ in ()).throw(ValueError("IP invalid")))

    response = configure(api, connection, embedder, generator).post(
        "/intreaba", json={"intrebare": "art. 4.4.7.2"}
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Serviciul este temporar indisponibil."}
    assert connection.calls == []
    assert connection.commits == connection.rollbacks == 0
    assert not connection.closed
    assert embedder.calls == generator.calls == 0


@pytest.mark.parametrize(
    ("allowed", "minute_count", "hour_count"),
    [
        (True, 6, 6),  # Nu permite depășirea limitelor când flag-ul este contradictoriu.
        (False, 1, 1),  # Nu blochează limite valide când flag-ul este contradictoriu.
        (True, 0, 1),
        (True, -1, 1),
        (True, True, 1),
        (True, 1, False),
        (True, 1.0, 1),
        (True, "1", 1),
        (1, 1, 1),
    ],
)
def test_rezultat_rate_invalid_devine_503_fara_quota_retrieval_sau_provideri(
    api, monkeypatch, allowed, minute_count, hour_count
):
    connection = ConnectionFake()
    embedder = EmbedderFake()
    generator = GeneratorFake()
    rate_result = RateLimitResult(
        allowed,
        NOW.replace(second=0, microsecond=0),
        NOW.replace(minute=0, second=0, microsecond=0),
        minute_count,
        hour_count,
    )

    monkeypatch.setattr(
        main.PostgresAccessControlRepository,
        "check_and_increment_rate_limit",
        lambda *_args, **_kwargs: rate_result,
    )
    response = configure(api, connection, embedder, generator).post(
        "/intreaba", json={"intrebare": "art. 4.4.7.2"}
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Serviciul este temporar indisponibil."}
    # Tranzacția rate a fost deja confirmată; rezultatul invalid nu deschide tranzacția quota.
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert all("anonymous_usage" not in sql for sql, _ in connection.calls)
    assert all("SELECT document.document_id" not in sql for sql, _ in connection.calls)
    assert embedder.calls == generator.calls == 0


def test_rate_limit_foloseste_numai_request_client_host_nu_antet_proxy(api):
    connection = ConnectionFake()

    response = configure(api, connection).post(
        "/intreaba",
        json={"intrebare": "art. 4.4.7.2"},
        headers={"X-Forwarded-For": "203.0.113.9"},
    )

    lock_parameters = next(parameters for sql, parameters in connection.calls if "pg_advisory_xact_lock" in sql)
    assert response.status_code == 200
    assert lock_parameters == (main.hash_ip("127.0.0.1", ACCESS_RUNTIME_CONFIG.access_control),)


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
