"""Teste FastAPI complet mockuite pentru integrarea Retrieval + Generation."""

import base64
import hashlib
import importlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import anthropic
import dotenv
import psycopg2
import pytest
from fastapi.testclient import TestClient
import voyageai

import main
from access_control import RateLimitResult
from generation_core import TRUNCATION_NOTICE, GeneratedText
from generation_fixture_helpers import RawGeneratorFake, simulated_provider_payload


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
        elif "INSERT INTO public.paid_call_budget" in sql:
            self.row = next(self.connection.budget_results)
        elif "SET request_count = request_count + 1" in sql:
            self.rows = [("minute", self.connection.minute_count), ("hour", self.connection.hour_count)]
        elif "SELECT document.document_id" in sql:
            self.rows = self.connection.catalog_rows
        elif "AS score" in sql:
            # Căutarea restrânsă la documentele preferate din context are propriile rânduri
            # numai dacă testul le cere explicit; altfel se comportă ca cea globală.
            restransa = "chunk.document_id = ANY(%s)" in sql
            if restransa and self.connection.semantic_scoped_rows is not None:
                self.rows = self.connection.semantic_scoped_rows
            else:
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
        semantic_scoped_rows=None,
        minute_count=1, hour_count=1, quota_results=((1,),), budget_results=((1,),) * 10,
        error=None, rollback_error=None,
    ):
        self.catalog_rows = catalog_rows
        self.exact_rows = exact_rows
        self.semantic_rows = semantic_rows
        self.semantic_scoped_rows = semantic_scoped_rows
        self.minute_count = minute_count
        self.hour_count = hour_count
        self.quota_results = iter(quota_results)
        self.budget_results = iter(budget_results)
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
    """Simulare provider JSON pentru regresii vechi; payloadurile invalide sunt RAW."""

    answer: str | GeneratedText = "Răspuns [C1]."
    calls: int = 0
    error: Exception | None = None
    prompt: str | None = None

    def generate(self, prompt, *, max_tokens):
        self.calls += 1
        self.prompt = prompt
        if self.error:
            raise self.error
        return simulated_provider_payload(self.answer, prompt)


@pytest.fixture
def api():
    original_dependencies = main.app.state.runtime_dependencies
    yield TestClient(main.app, client=("127.0.0.1", 50000))
    main.app.state.runtime_dependencies = original_dependencies


def configure(
    api, connection, embedder=None, generator=None, runtime_config=ACCESS_RUNTIME_CONFIG,
    budget_connection=None, daily_paid_call_limit=main.DEFAULT_DAILY_PAID_CALL_LIMIT,
):
    # Conexiune proprie pentru plafonul zilnic, distinctă de `connection`: altfel testele
    # care numără commit-uri/rollback-uri pe `connection` ar vedea efectele secundare ale
    # rezervării bugetului, care în producție se întâmplă pe o conexiune separată.
    resolved_budget_connection = budget_connection if budget_connection is not None else ConnectionFake()
    main.app.state.runtime_dependencies = main.RuntimeDependencies(
        connection_factory=lambda: connection,
        embedder_factory=lambda: embedder or EmbedderFake(),
        text_generator_factory=lambda: generator or GeneratorFake(),
        access_control_config_factory=lambda: runtime_config,
        now_factory=lambda: NOW,
        daily_paid_call_limit_factory=lambda: daily_paid_call_limit,
        budget_connection_factory=lambda: resolved_budget_connection,
    )
    return api


def _assert_no_technical_identifiers(response):
    """Verifica raspunsul HTTP real (nu doar promptul intern): niciun identificator tehnic
    intern nu trebuie sa se scurga catre client, indiferent de status."""
    corp = response.text
    assert "source_key" not in corp
    assert "doc-1" not in corp, "document_id intern nu trebuie sa apara in raspunsul public"
    assert "_extras.txt" not in corp
    assert "extras.txt" not in corp


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


def test_raspunsul_trunchiat_ajunge_marcat_la_client_fara_sa_schimbe_contractul(api):
    """Pachetul intern complet valid păstrează marcajul în `raspuns` și schema publică."""
    connection = ConnectionFake()
    generator = GeneratorFake(answer=GeneratedText("Răspuns [C1] tăiat la jum", truncated=True))

    response = configure(api, connection, generator=generator).post(
        "/intreaba", json={"intrebare": "NP 010-2022, art. 4.4.7.2"}
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"status", "raspuns", "citari", "intrebari_ramase"}
    assert body["status"] == "answered"
    assert body["raspuns"].endswith(TRUNCATION_NOTICE)
    assert body["raspuns"].startswith("Răspuns [C1] tăiat la jum")
    assert generator.calls == 1


def test_referinta_inventata_in_ambele_incercari_devine_refuz_onest_nu_503(api):
    """Refuzul e deliberat, deci NU se mai deghizează în pană de serviciu: 200 cu statusul
    public `unsupported_answer` și un mesaj care spune adevărul. Un 503 ar fi trimis
    utilizatorul să reîncerce aceeași întrebare, cheltuind bani pe un răspuns care oricum
    va fi refuzat."""
    connection = ConnectionFake()
    generator = GeneratorFake(answer="Conform STAS 6648, sarcina se calculează [C1].")

    response = configure(api, connection, generator=generator).post(
        "/intreaba", json={"intrebare": "NP 010-2022, art. 4.4.7.2"}
    )

    assert response.status_code == 200
    corp = response.json()
    assert corp["status"] == "unsupported_answer"
    assert corp["raspuns"] == main._UNSUPPORTED_ANSWER
    assert corp["citari"] == []
    assert generator.calls == 2
    assert connection.closed
    assert connection.commits >= 1, "refuzul e un rezultat normal, nu o eroare cu rollback"


def test_refuzul_neancorat_nu_scurge_referinta_inventata_sau_mecanismul(api):
    """Mesajul de refuz nu spune ce referință a fost inventată, nici că există o verificare
    de ancorare — sunt detalii interne, inutile utilizatorului și utile unui atacator."""
    connection = ConnectionFake()
    generator = GeneratorFake(answer="Conform STAS 6648 și C 107-2005 rezultă [C1].")

    response = configure(api, connection, generator=generator).post(
        "/intreaba", json={"intrebare": "NP 010-2022, art. 4.4.7.2"}
    )

    corp = response.text
    for interzis in ("STAS 6648", "C 107-2005", "Ungrounded", "referin\\u021b\\u0103 neancorat"):
        assert interzis not in corp
    _assert_no_technical_identifiers(response)


def test_forma_raspunsului_ramane_neschimbata_si_la_refuz(api):
    """Statusul nou nu adaugă și nu scoate câmpuri din contractul public."""
    connection = ConnectionFake()
    generator = GeneratorFake(answer="Conform STAS 6648 [C1].")

    response = configure(api, connection, generator=generator).post(
        "/intreaba", json={"intrebare": "NP 010-2022, art. 4.4.7.2"}
    )

    assert set(response.json()) == {"status", "raspuns", "citari", "intrebari_ramase"}


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
    """Verifica raspunsul HTTP real pe toate statusurile retrieval sub 200 (found/not_found/
    ambiguous_*); statusurile publice 422/403/429/503 sunt verificate cu acelasi helper direct
    in testele lor reprezentative (vezi _assert_no_technical_identifiers)."""
    response = configure(api, connection, EmbedderFake(), GeneratorFake()).post(
        "/intreaba", json={"intrebare": question}
    )

    assert response.status_code == 200
    _assert_no_technical_identifiers(response)


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
    _assert_no_technical_identifiers(response)


@pytest.mark.parametrize(
    ("connection", "embedder", "generator", "question"),
    [
        (ConnectionFake(error=psycopg2.OperationalError("db")), EmbedderFake(), GeneratorFake(), "art. 4.4.7.2"),
        (ConnectionFake(), EmbedderFake(error=main.ProviderUnavailableError()), GeneratorFake(), "întrebare semantică"),
        (ConnectionFake(), EmbedderFake(), GeneratorFake(error=main.ProviderUnavailableError()), "art. 4.4.7.2"),
        (ConnectionFake(), EmbedderFake(), RawGeneratorFake(json.dumps({"raspuns": "răspuns fără citare", "pasaje": []})), "art. 4.4.7.2"),
    ],
)
def test_erorile_dependentei_sunt_503_generic_si_conexiunea_se_inchide(
    api, connection, embedder, generator, question
):
    response = configure(api, connection, embedder, generator).post("/intreaba", json={"intrebare": question})

    assert response.status_code == 503
    assert response.json() == {"detail": "Serviciul este temporar indisponibil."}
    assert connection.closed
    _assert_no_technical_identifiers(response)


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

    generated = main.AnthropicTextGenerator(ClientFake()).generate("prompt", max_tokens=1200)
    assert generated == GeneratedText("răspuns", truncated=False)

    class MessagesDefect:
        def create(self, **_kwargs):
            raise anthropic.APIConnectionError(request=None)

    class ClientDefect:
        messages = MessagesDefect()

    with pytest.raises(main.ProviderUnavailableError):
        main.AnthropicTextGenerator(ClientDefect()).generate("prompt", max_tokens=1200)


@pytest.mark.parametrize(
    "stop_reason, truncated",
    [("max_tokens", True), ("end_turn", False), (None, False), ("stop_sequence", False)],
)
def test_adaptorul_anthropic_propaga_semnalul_de_trunchiere(stop_reason, truncated):
    """Numai `stop_reason == "max_tokens"` înseamnă răspuns tăiat de plafon; restul, nu."""

    class MessagesFake:
        def create(self, **_kwargs):
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text="răspuns")], stop_reason=stop_reason
            )

    class ClientFake:
        messages = MessagesFake()

    generated = main.AnthropicTextGenerator(ClientFake()).generate("prompt", max_tokens=1200)
    assert generated == GeneratedText("răspuns", truncated=truncated)


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
    _assert_no_technical_identifiers(response)


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
    _assert_no_technical_identifiers(response)


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
# --- Faza 7: trusted proxy, /health, pagini juridice și assets read-only ---


def _proxy_runtime_config(trusted_proxy_hops):
    return main.AnonymousAccessControlRuntimeConfig(
        ACCESS_RUNTIME_CONFIG.access_control,
        cookie_secure=False,
        trusted_proxy_hops=trusted_proxy_hops,
    )


def _lock_ip_hash(connection):
    parameters = next(
        parameters for sql, parameters in connection.calls if "pg_advisory_xact_lock" in sql
    )
    return parameters[0]


def _post_prin_proxy(api, connection, *, hops, forwarded=None):
    headers = {} if forwarded is None else {"X-Forwarded-For": forwarded}
    return configure(api, connection, runtime_config=_proxy_runtime_config(hops)).post(
        "/intreaba", json={"intrebare": "art. 4.4.7.2"}, headers=headers
    )


def _hash_direct():
    return main.hash_ip("127.0.0.1", ACCESS_RUNTIME_CONFIG.access_control)


def test_hops_zero_ignora_complet_forwarded_chiar_daca_e_valid(api):
    connection = ConnectionFake()

    response = _post_prin_proxy(api, connection, hops=0, forwarded="203.0.113.9")

    assert response.status_code == 200
    assert _lock_ip_hash(connection) == _hash_direct()


def test_forwarded_absent_cade_pe_ip_direct(api):
    connection = ConnectionFake()

    response = _post_prin_proxy(api, connection, hops=1)

    assert response.status_code == 200
    assert _lock_ip_hash(connection) == _hash_direct()


def test_forwarded_gol_cade_pe_ip_direct(api):
    connection = ConnectionFake()

    response = _post_prin_proxy(api, connection, hops=1, forwarded="")

    assert response.status_code == 200
    assert _lock_ip_hash(connection) == _hash_direct()


def test_forwarded_cu_prea_putine_elemente_cade_pe_ip_direct(api):
    connection = ConnectionFake()

    response = _post_prin_proxy(api, connection, hops=2, forwarded="203.0.113.9")

    assert response.status_code == 200
    assert _lock_ip_hash(connection) == _hash_direct()


@pytest.mark.parametrize(
    "forwarded",
    [
        "203.0.113.9, nu-e-ip",
        "203.0.113.9, 203.0.113.9:8080",
        "203.0.113.9, fe80::1%eth0",
        "203.0.113.9, ",
        "203.0.113.9, [2001:db8::1]",
    ],
)
def test_forwarded_cu_element_selectat_invalid_cade_pe_ip_direct(api, forwarded):
    connection = ConnectionFake()

    response = _post_prin_proxy(api, connection, hops=1, forwarded=forwarded)

    assert response.status_code == 200
    assert _lock_ip_hash(connection) == _hash_direct()


def test_forwarded_ignora_valorile_falsificate_din_stanga(api):
    connection = ConnectionFake()

    response = _post_prin_proxy(api, connection, hops=1, forwarded="1.2.3.4, 203.0.113.9")

    assert response.status_code == 200
    assert _lock_ip_hash(connection) == main.hash_ip(
        "203.0.113.9", ACCESS_RUNTIME_CONFIG.access_control
    )
    assert _lock_ip_hash(connection) != main.hash_ip(
        "1.2.3.4", ACCESS_RUNTIME_CONFIG.access_control
    )


def test_forwarded_alege_al_n_lea_element_numarand_de_la_dreapta(api):
    connection = ConnectionFake()

    response = _post_prin_proxy(
        api, connection, hops=2, forwarded="1.2.3.4, 203.0.113.9, 10.0.0.1"
    )

    assert response.status_code == 200
    assert _lock_ip_hash(connection) == main.hash_ip(
        "203.0.113.9", ACCESS_RUNTIME_CONFIG.access_control
    )


def test_forwarded_accepta_ipv6_pe_pozitia_de_incredere(api):
    connection = ConnectionFake()

    response = _post_prin_proxy(api, connection, hops=1, forwarded="1.2.3.4, 2001:db8::1")

    assert response.status_code == 200
    assert _lock_ip_hash(connection) == main.hash_ip(
        "2001:db8::1", ACCESS_RUNTIME_CONFIG.access_control
    )


@pytest.mark.parametrize(
    ("raw", "expected"), [(None, 0), ("0", 0), ("1", 1), (" 2 ", 2), ("10", 10)]
)
def test_trusted_proxy_hops_accepta_numai_intregi_nenegativi(monkeypatch, raw, expected):
    monkeypatch.setenv("ANONYMOUS_COOKIE_SIGNING_KEY", "abcdefghijklmnopqrstuvwxyz0123456789")
    monkeypatch.setenv("ANONYMOUS_IP_HASH_KEY", "9876543210zyxwvutsrqponmlkjihgfedcba")
    monkeypatch.setenv("ANONYMOUS_COOKIE_SECURE", "false")
    if raw is None:
        monkeypatch.delenv("TRUSTED_PROXY_HOPS", raising=False)
    else:
        monkeypatch.setenv("TRUSTED_PROXY_HOPS", raw)

    assert main._anonymous_access_control_config().trusted_proxy_hops == expected


@pytest.mark.parametrize("raw", ["", "-1", "1.5", "abc", "+1", "1,2", "١٢", "true"])
def test_trusted_proxy_hops_invalid_este_eroare_generica(monkeypatch, raw):
    monkeypatch.setenv("ANONYMOUS_COOKIE_SIGNING_KEY", "abcdefghijklmnopqrstuvwxyz0123456789")
    monkeypatch.setenv("ANONYMOUS_IP_HASH_KEY", "9876543210zyxwvutsrqponmlkjihgfedcba")
    monkeypatch.setenv("ANONYMOUS_COOKIE_SECURE", "false")
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", raw)

    with pytest.raises(main.DependencyConfigurationError, match="configurație indisponibilă"):
        main._anonymous_access_control_config()


def _configure_cu_configuratie_reala(api, connection):
    main.app.state.runtime_dependencies = main.RuntimeDependencies(
        connection_factory=lambda: connection,
        embedder_factory=EmbedderFake,
        text_generator_factory=GeneratorFake,
        now_factory=lambda: NOW,
    )
    return api


def test_trusted_proxy_hops_invalid_este_503_generic_la_pornirea_cererii(api, monkeypatch):
    monkeypatch.setenv("ANONYMOUS_COOKIE_SIGNING_KEY", "abcdefghijklmnopqrstuvwxyz0123456789")
    monkeypatch.setenv("ANONYMOUS_IP_HASH_KEY", "9876543210zyxwvutsrqponmlkjihgfedcba")
    monkeypatch.setenv("ANONYMOUS_COOKIE_SECURE", "false")
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "-1")
    connection = ConnectionFake()
    client = _configure_cu_configuratie_reala(api, connection)

    post_response = client.post("/intreaba", json={"intrebare": "art. 4.4.7.2"})
    get_response = client.get("/")

    assert post_response.status_code == get_response.status_code == 503
    assert post_response.json() == {"detail": "Serviciul este temporar indisponibil."}
    assert get_response.json() == {"detail": "Serviciul este temporar indisponibil."}
    assert connection.calls == []
    assert not connection.closed


def test_health_este_public_ieftin_si_fara_db_sau_provideri(api):
    connection = ConnectionFake()
    embedder = EmbedderFake()
    generator = GeneratorFake()

    response = configure(api, connection, embedder, generator).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert connection.calls == []
    assert connection.commits == connection.rollbacks == 0
    assert not connection.closed
    assert embedder.calls == generator.calls == 0
    assert "set-cookie" not in response.headers


def test_health_functioneaza_si_fara_configuratia_anonima(api, monkeypatch):
    monkeypatch.delenv("ANONYMOUS_COOKIE_SECURE", raising=False)
    monkeypatch.delenv("ANONYMOUS_COOKIE_SIGNING_KEY", raising=False)
    monkeypatch.delenv("ANONYMOUS_IP_HASH_KEY", raising=False)
    connection = ConnectionFake()

    response = _configure_cu_configuratie_reala(api, connection).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert connection.calls == []


@pytest.mark.parametrize("path", ["/termeni", "/confidentialitate"])
def test_paginile_juridice_sunt_servite_public(api, path):
    connection = ConnectionFake()

    response = configure(api, connection).get(path)

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert connection.calls == []
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize("path", ["/documents", "/documente"])
def test_ruta_documents_nu_exista_si_nu_poate_fi_reintrodusa_tacut(api, path):
    """Catalogul documentelor NU se expune public — decizie de produs a lui Lucian:
    lista completă arată exact ce acoperă și ce nu acoperă produsul, informație
    sensibilă competitiv. Din același motiv lista a fost scoasă din nav-ul UI la
    03-09-2026. O rută `GET /documents` a existat scurt (commit 9bd65d5, urmând
    backlog-ul din PLAN.md, care preceda decizia) și a fost eliminată.

    Testul nu verifică doar 404-ul: verifică și că nicio rută înregistrată în
    aplicație nu poartă un asemenea nume, ca o reintroducere sub altă cale sau
    altă metodă (`POST`, `/api/documents`, `/documente`) să nu treacă tăcut —
    același principiu ca testul anti-`innerHTML` și ca cel de drift al
    hash-urilor CSP: nu doar scoatem ceva, ci facem imposibilă revenirea lui
    neobservată."""
    connection = ConnectionFake()

    response = configure(api, connection).get(path)

    assert response.status_code == 404
    assert connection.calls == []

    cai_inregistrate = {getattr(ruta, "path", "") for ruta in main.app.routes}
    assert not any("document" in cale.lower() for cale in cai_inregistrate), (
        "o rută care expune catalogul documentelor a fost reintrodusă: "
        f"{sorted(cale for cale in cai_inregistrate if 'document' in cale.lower())}"
    )


@pytest.fixture
def asset_de_test():
    # Numele este ignorat de Git (vezi .gitignore), ca o intrerupere sa nu lase gunoi comisibil.
    asset = main._ASSETS_DIRECTORY / "test-asset.txt"
    asset.write_text("asset de test", encoding="utf-8")
    try:
        yield asset
    finally:
        asset.unlink(missing_ok=True)


def test_assets_serveste_fisierele_din_static_assets(api, asset_de_test):
    response = api.get("/assets/test-asset.txt")

    assert response.status_code == 200
    assert response.text == "asset de test"


def test_assets_returneaza_404_pentru_fisier_inexistent(api):
    assert api.get("/assets/nu-exista.woff2").status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/static/index.html",
        "/index.html",
        "/termeni.html",
        "/confidentialitate.html",
        "/assets/%2e%2e/index.html",
        "/assets/..%2findex.html",
        "/assets/%2e%2e%2fmain.py",
    ],
)
def test_niciun_alt_fisier_din_repo_nu_este_expus(api, path):
    response = api.get(path)

    assert response.status_code == 404
# --- Neregresie: antete X-Forwarded-For duplicate (finding F1) ---


def _post_cu_antete(api, connection, *, hops, headers):
    return configure(api, connection, runtime_config=_proxy_runtime_config(hops)).post(
        "/intreaba", json={"intrebare": "art. 4.4.7.2"}, headers=headers
    )


def test_antetele_forwarded_duplicate_sunt_unite_nu_doar_primul(api):
    connection = ConnectionFake()

    response = _post_cu_antete(
        api,
        connection,
        hops=1,
        headers=[("X-Forwarded-For", "9.9.9.9"), ("X-Forwarded-For", "203.0.113.9")],
    )

    assert response.status_code == 200
    assert _lock_ip_hash(connection) == main.hash_ip(
        "203.0.113.9", ACCESS_RUNTIME_CONFIG.access_control
    )
    assert _lock_ip_hash(connection) != main.hash_ip(
        "9.9.9.9", ACCESS_RUNTIME_CONFIG.access_control
    )


def test_antetele_forwarded_duplicate_respecta_doi_hopi_de_incredere(api):
    connection = ConnectionFake()

    response = _post_cu_antete(
        api,
        connection,
        hops=2,
        headers=[("X-Forwarded-For", "1.2.3.4"), ("X-Forwarded-For", "203.0.113.9, 10.0.0.1")],
    )

    assert response.status_code == 200
    assert _lock_ip_hash(connection) == main.hash_ip(
        "203.0.113.9", ACCESS_RUNTIME_CONFIG.access_control
    )


def test_clientul_nu_poate_impinge_pozitia_de_incredere_in_afara_ferestrei(api):
    connection = ConnectionFake()

    response = _post_cu_antete(
        api,
        connection,
        hops=1,
        headers=[
            ("X-Forwarded-For", "1.0.0.1, 1.0.0.2, 1.0.0.3"),
            ("X-Forwarded-For", "203.0.113.9"),
        ],
    )

    assert response.status_code == 200
    assert _lock_ip_hash(connection) == main.hash_ip(
        "203.0.113.9", ACCESS_RUNTIME_CONFIG.access_control
    )
    for falsificat in ("1.0.0.1", "1.0.0.2", "1.0.0.3"):
        assert _lock_ip_hash(connection) != main.hash_ip(
            falsificat, ACCESS_RUNTIME_CONFIG.access_control
        )


def test_antete_falsificate_diferite_nu_creeaza_bucket_nou_de_rate_limit(api):
    prima = ConnectionFake()
    a_doua = ConnectionFake()

    _post_cu_antete(
        api,
        prima,
        hops=1,
        headers=[("X-Forwarded-For", "1.0.0.1"), ("X-Forwarded-For", "203.0.113.9")],
    )
    _post_cu_antete(
        api,
        a_doua,
        hops=1,
        headers=[("X-Forwarded-For", "1.0.0.2"), ("X-Forwarded-For", "203.0.113.9")],
    )

    # Bucket-ul de rate limit rămâne același, deci limitele nu pot fi ocolite prin antete.
    assert _lock_ip_hash(prima) == _lock_ip_hash(a_doua)
    assert _lock_ip_hash(prima) == main.hash_ip(
        "203.0.113.9", ACCESS_RUNTIME_CONFIG.access_control
    )


def test_antete_forwarded_duplicate_goale_cad_pe_ip_direct(api):
    connection = ConnectionFake()

    response = _post_cu_antete(
        api, connection, hops=1, headers=[("X-Forwarded-For", ""), ("X-Forwarded-For", "")]
    )

    assert response.status_code == 200
    assert _lock_ip_hash(connection) == _hash_direct()


def test_antetele_duplicate_sunt_ignorate_complet_la_hops_zero(api):
    connection = ConnectionFake()

    response = _post_cu_antete(
        api,
        connection,
        hops=0,
        headers=[("X-Forwarded-For", "9.9.9.9"), ("X-Forwarded-For", "203.0.113.9")],
    )

    assert response.status_code == 200
    assert _lock_ip_hash(connection) == _hash_direct()


# --- Pagini juridice lipsă (finding F3) ---


@pytest.mark.parametrize("path", ["/termeni", "/confidentialitate"])
def test_pagina_juridica_lipsa_este_503_generic_fara_cale_absoluta(api, monkeypatch, tmp_path, path):
    monkeypatch.setattr(main, "_STATIC_DIRECTORY", tmp_path)

    response = configure(api, ConnectionFake()).get(path)

    assert response.status_code == 503
    assert response.json() == {"detail": "Serviciul este temporar indisponibil."}
    assert str(tmp_path) not in response.text
    assert ".html" not in response.text


# --- Antete de securitate HTTP ---


def test_antetele_de_securitate_sunt_prezente_pe_pagina_principala(api):
    response = configure(api, ConnectionFake()).get("/")

    csp = response.headers["content-security-policy"]
    assert "default-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "script-src 'sha256-" in csp
    assert "style-src 'unsafe-hashes' 'sha256-" in csp
    assert "'unsafe-inline'" not in csp
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers["permissions-policy"]
    assert "microphone=()" in response.headers["permissions-policy"]
    assert "geolocation=()" in response.headers["permissions-policy"]
    hsts = response.headers["strict-transport-security"]
    assert hsts.startswith("max-age=")
    assert "preload" not in hsts


@pytest.mark.parametrize("path", ["/health", "/nu-exista", "/termeni"])
def test_antetele_de_securitate_apar_pe_orice_raspuns_inclusiv_erori(api, path):
    response = configure(api, ConnectionFake()).get(path)

    for header in (
        "content-security-policy", "x-frame-options", "x-content-type-options",
        "referrer-policy", "permissions-policy", "strict-transport-security",
    ):
        assert header in response.headers


_STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
_INLINE_BLOCK = re.compile(r"<(script|style)(?:\s[^>]*)?>(.*?)</\1>", re.S)
_STYLE_ATTRIBUTE = re.compile(r'style="([^"]*)"')


def _csp_sha256(content: str) -> str:
    digest = hashlib.sha256(content.encode("utf-8")).digest()
    return "'sha256-" + base64.b64encode(digest).decode("ascii") + "'"


def _inline_hashes_from_static_files() -> tuple[set[str], set[str]]:
    """Recalculează, din conținutul REAL de pe disc, hash-urile pe care CSP-ul trebuie
    să le conțină — exact ce ar face un browser înainte să decidă dacă execută blocul."""
    script_hashes: set[str] = set()
    style_hashes: set[str] = set()
    for filename in ("index.html", "termeni.html", "confidentialitate.html"):
        text = (_STATIC_DIR / filename).read_text(encoding="utf-8")
        for tag, body in _INLINE_BLOCK.findall(text):
            (script_hashes if tag == "script" else style_hashes).add(_csp_sha256(body))
        for attribute_value in _STYLE_ATTRIBUTE.findall(text):
            style_hashes.add(_csp_sha256(attribute_value))
    return script_hashes, style_hashes


def test_hash_urile_csp_corespund_exact_continutului_static_curent():
    """Plasă de siguranță împotriva desincronizării: dacă cineva editează un <script>/<style>
    inline sau un atribut style="" din static/*.html fără să regenereze hash-ul din main.py,
    CSP-ul rămâne valid sintactic (testele de mai sus tot trec), dar browserul va bloca
    silențios blocul respectiv în producție. Acest test recalculează hash-urile din fișierele
    reale și le compară strict cu constantele din main.py, în ambele sensuri (lipsă și perimat)."""
    expected_scripts, expected_styles = _inline_hashes_from_static_files()
    actual_scripts = set(main._CSP_SCRIPT_HASHES)
    actual_styles = set(main._CSP_STYLE_HASHES)

    missing_scripts = expected_scripts - actual_scripts
    stale_scripts = actual_scripts - expected_scripts
    missing_styles = expected_styles - actual_styles
    stale_styles = actual_styles - expected_styles

    assert not (missing_scripts or stale_scripts or missing_styles or stale_styles), (
        "\n_CSP_SCRIPT_HASHES / _CSP_STYLE_HASHES din main.py nu mai corespund conținutului "
        "curent din static/index.html, static/termeni.html sau static/confidentialitate.html. "
        "Un <script>/<style> inline sau un atribut style=\"...\" a fost editat fără să se "
        "regenereze hash-ul CSP — browserul va bloca silențios acel bloc în producție.\n"
        f"De adăugat în _CSP_SCRIPT_HASHES (calculate acum din fișierele curente): {sorted(missing_scripts)}\n"
        f"De șters din _CSP_SCRIPT_HASHES (nu mai corespund niciunui <script> curent): {sorted(stale_scripts)}\n"
        f"De adăugat în _CSP_STYLE_HASHES (calculate acum din fișierele curente): {sorted(missing_styles)}\n"
        f"De șters din _CSP_STYLE_HASHES (nu mai corespund niciunui <style>/style=\"\" curent): {sorted(stale_styles)}\n"
    )


def test_raspunsul_intreaba_are_si_el_antetele_de_securitate(api):
    response = configure(api, ConnectionFake()).post("/intreaba", json={"intrebare": "art. 4.4.7.2"})

    assert response.status_code == 200
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


# --- Plafon zilnic global pentru apelurile plătite (Voyage/Anthropic) ---


def test_plafonul_zilnic_atins_opreste_generarea_platita_cu_raspuns_generic(api):
    connection = ConnectionFake()
    embedder = EmbedderFake()
    generator = GeneratorFake()
    budget_connection = ConnectionFake(budget_results=(None,))

    response = configure(
        api, connection, embedder, generator, budget_connection=budget_connection
    ).post("/intreaba", json={"intrebare": "art. 4.4.7.2"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Serviciul este temporar indisponibil."}
    assert embedder.calls == 0
    assert generator.calls == 0
    # Plafonul atins nu consumă quota personală (10/browser) a vizitatorului.
    assert connection.rollbacks == 1
    _assert_no_technical_identifiers(response)
    # Mesajul public nu scurge pragul, mecanismul sau cuvinte care ar trăda motivul intern.
    for leaked in ("plafon", "buget", "200", "DAILY_PAID_CALL_LIMIT", "zilnic"):
        assert leaked not in response.text.lower()


def test_plafonul_zilnic_nu_se_aplica_intrebarilor_fara_apel_platit(api):
    connection = ConnectionFake(exact_rows=())
    embedder = EmbedderFake()
    generator = GeneratorFake()
    budget_connection = ConnectionFake(budget_results=(None,))

    response = configure(
        api, connection, embedder, generator, budget_connection=budget_connection
    ).post("/intreaba", json={"intrebare": "art. 99.99.99"})

    assert response.status_code == 200
    assert response.json()["status"] == "not_found"
    assert embedder.calls == 0
    assert generator.calls == 0
    # Plafonul nici măcar nu e verificat pe o cale care nu costă nimic.
    assert budget_connection.calls == []


def test_plafonul_zilnic_numara_o_singura_data_intrebarea_semantica_gasita(api):
    connection = ConnectionFake()
    embedder = EmbedderFake()
    generator = GeneratorFake()
    budget_connection = ConnectionFake(budget_results=((1,),))

    response = configure(
        api, connection, embedder, generator, budget_connection=budget_connection
    ).post("/intreaba", json={"intrebare": "Care este regula sintetică?"})

    assert response.status_code == 200
    assert embedder.calls == 1
    assert generator.calls == 1
    # Un embed + un generate pentru aceeași întrebare = o singură rezervare de buget.
    reservations = [sql for sql, _ in budget_connection.calls if "INSERT INTO public.paid_call_budget" in sql]
    assert len(reservations) == 1


def test_plafonul_zilnic_permite_pana_la_prag_apoi_blocheaza(api):
    embedder = EmbedderFake()
    generator = GeneratorFake()
    budget_connection = ConnectionFake(budget_results=((1,), None))

    client = configure(
        api, ConnectionFake(quota_results=((1,), (2,))), embedder, generator,
        budget_connection=budget_connection, daily_paid_call_limit=1,
    )
    first = client.post("/intreaba", json={"intrebare": "Care este regula sintetică?"})
    second = client.post("/intreaba", json={"intrebare": "Care este regula sintetică?"})

    assert first.status_code == 200
    assert second.status_code == 503
    assert second.json() == {"detail": "Serviciul este temporar indisponibil."}


def test_plafonul_zilnic_se_reseteaza_pe_zi_calendaristica_utc_diferita(api, monkeypatch):
    captured_dates = []
    original = main.PostgresAccessControlRepository.reserve_paid_call

    def spy(self, *, now, daily_limit):
        captured_dates.append(now.date())
        return original(self, now=now, daily_limit=daily_limit)

    monkeypatch.setattr(main.PostgresAccessControlRepository, "reserve_paid_call", spy)
    budget_connection = ConnectionFake(budget_results=((1,), (1,)))

    for moment in (NOW, NOW + timedelta(days=1)):
        main.app.state.runtime_dependencies = main.RuntimeDependencies(
            connection_factory=lambda: ConnectionFake(),
            embedder_factory=lambda: EmbedderFake(),
            text_generator_factory=lambda: GeneratorFake(),
            access_control_config_factory=lambda: ACCESS_RUNTIME_CONFIG,
            now_factory=lambda moment=moment: moment,
            budget_connection_factory=lambda: budget_connection,
        )
        response = api.post("/intreaba", json={"intrebare": "art. 4.4.7.2"})
        assert response.status_code == 200

    assert captured_dates[1] - captured_dates[0] == timedelta(days=1)


def test_plafonul_zilnic_implicit_este_200_daca_lipseste_variabila_de_mediu(monkeypatch):
    monkeypatch.delenv("DAILY_PAID_CALL_LIMIT", raising=False)
    assert main._daily_paid_call_limit() == main.DEFAULT_DAILY_PAID_CALL_LIMIT == 200


@pytest.mark.parametrize("raw", ["0", "-1", "1.5", "abc", ""])
def test_plafonul_zilnic_invalid_este_eroare_generica(monkeypatch, raw):
    monkeypatch.setenv("DAILY_PAID_CALL_LIMIT", raw)

    with pytest.raises(main.DependencyConfigurationError):
        main._daily_paid_call_limit()


# --- Refuz local pentru calcule de proiectare ---


def test_calculul_de_proiect_este_refuzat_fara_retrieval_provider_sau_quota(api):
    connection = ConnectionFake()
    embedder = EmbedderFake()
    generator = GeneratorFake()
    budget_connection = ConnectionFake()

    response = configure(
        api, connection, embedder, generator, budget_connection=budget_connection
    ).post(
        "/intreaba",
        json={
            "intrebare": (
                "Pentru o hală de 200 kW, 4000 mp, 7 m, 28°C, în Buzău, "
                "calculează sarcina de răcire necesară."
            )
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "out_of_scope",
        "raspuns": (
            "NormativAI nu efectuează calcule sau dimensionări de proiect. "
            "Pot indica prevederile și datele cerute de normative."
        ),
        "citari": [],
        "intrebari_ramase": 10,
    }
    # Rate limit-ul se comite, însă rezervarea temporară de quota este restituită.
    assert connection.commits == 1
    assert connection.rollbacks == 1
    assert embedder.calls == generator.calls == 0
    assert budget_connection.calls == []
    executed_sql = "\n".join(sql for sql, _ in connection.calls)
    assert "SELECT document.document_id" not in executed_sql
    assert "documente_chunks" not in executed_sql


def test_calculul_debitului_minim_nu_ocoleste_refuzul_sau_quota(api):
    connection = ConnectionFake()
    embedder = EmbedderFake()
    generator = GeneratorFake()
    budget_connection = ConnectionFake()

    response = configure(
        api, connection, embedder, generator, budget_connection=budget_connection
    ).post(
        "/intreaba",
        json={
            "intrebare": "Calculează debitul minim necesar pentru ventilația halei mele de 4.000 mp."
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "out_of_scope",
        "raspuns": (
            "NormativAI nu efectuează calcule sau dimensionări de proiect. "
            "Pot indica prevederile și datele cerute de normative."
        ),
        "citari": [],
        "intrebari_ramase": 10,
    }
    assert connection.commits == 1
    assert connection.rollbacks == 1
    assert embedder.calls == generator.calls == 0
    assert budget_connection.calls == []
    executed_sql = "\n".join(sql for sql, _ in connection.calls)
    assert "SELECT document.document_id" not in executed_sql
    assert "documente_chunks" not in executed_sql


def test_stabiliti_debitul_minim_nu_ocoleste_refuzul_sau_quota(api):
    connection = ConnectionFake()
    embedder = EmbedderFake()
    generator = GeneratorFake()
    budget_connection = ConnectionFake()

    response = configure(
        api, connection, embedder, generator, budget_connection=budget_connection
    ).post(
        "/intreaba",
        json={
            "intrebare": "Stabiliți debitul minim necesar pentru ventilarea halei de 4.000 mp."
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "out_of_scope",
        "raspuns": (
            "NormativAI nu efectuează calcule sau dimensionări de proiect. "
            "Pot indica prevederile și datele cerute de normative."
        ),
        "citari": [],
        "intrebari_ramase": 10,
    }
    assert connection.commits == 1
    assert connection.rollbacks == 1
    assert embedder.calls == generator.calls == 0
    assert budget_connection.calls == []
    executed_sql = "\n".join(sql for sql, _ in connection.calls)
    assert "SELECT document.document_id" not in executed_sql
    assert "documente_chunks" not in executed_sql


def test_solicitarea_nominala_a_calculului_nu_ocoleste_refuzul_sau_quota(api):
    connection = ConnectionFake()
    embedder = EmbedderFake()
    generator = GeneratorFake()
    budget_connection = ConnectionFake()

    response = configure(
        api, connection, embedder, generator, budget_connection=budget_connection
    ).post(
        "/intreaba",
        json={
            "intrebare": (
                "Solicit calcularea capacității prevăzute de normativ pentru hala de 4.000 mp."
            )
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "out_of_scope",
        "raspuns": (
            "NormativAI nu efectuează calcule sau dimensionări de proiect. "
            "Pot indica prevederile și datele cerute de normative."
        ),
        "citari": [],
        "intrebari_ramase": 10,
    }
    assert connection.commits == 1
    assert connection.rollbacks == 1
    assert embedder.calls == generator.calls == 0
    assert budget_connection.calls == []
    executed_sql = "\n".join(sql for sql, _ in connection.calls)
    assert "SELECT document.document_id" not in executed_sql
    assert "documente_chunks" not in executed_sql


def test_solicitarea_nominala_politicoasa_nu_ocoleste_refuzul_sau_quota(api):
    connection = ConnectionFake()
    embedder = EmbedderFake()
    generator = GeneratorFake()
    budget_connection = ConnectionFake()

    response = configure(
        api, connection, embedder, generator, budget_connection=budget_connection
    ).post(
        "/intreaba",
        json={
            "intrebare": (
                "Solicit, vă rog, calcularea capacității prevăzute de normativ pentru hala de 4.000 mp."
            )
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "out_of_scope",
        "raspuns": (
            "NormativAI nu efectuează calcule sau dimensionări de proiect. "
            "Pot indica prevederile și datele cerute de normative."
        ),
        "citari": [],
        "intrebari_ramase": 10,
    }
    assert connection.commits == 1
    assert connection.rollbacks == 1
    assert embedder.calls == generator.calls == 0
    assert budget_connection.calls == []
    executed_sql = "\n".join(sql for sql, _ in connection.calls)
    assert "SELECT document.document_id" not in executed_sql
    assert "documente_chunks" not in executed_sql


def test_rollback_esuat_la_refuzul_de_calcul_este_fail_closed_503(api):
    connection = ConnectionFake(rollback_error=psycopg2.OperationalError("rollback db"))

    response = configure(api, connection).post(
        "/intreaba", json={"intrebare": "Calculează necesarul de răcire pentru hală."}
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Serviciul este temporar indisponibil."}
    assert connection.rollbacks == 1


# --- R06: pasajele invalide restituie quota, nu rate limit-ul sau bugetul consumat ---


class R06TransactionConnection(ConnectionFake):
    """Stare tranzacțională sintetică pentru a verifica quota și la cererea următoare."""

    def __init__(self, **kwargs):
        super().__init__(quota_results=((1,),) * 4, **kwargs)
        self.questions_used = 0
        self.pending_question = False
        self.rate_requests = 0
        self.pending_rate = 0
        self.events = []

    def cursor(self):
        class TransactionCursor(CursorFake):
            def execute(cursor, sql, parameters):
                super().execute(sql, parameters)
                if "SET request_count = request_count + 1" in sql:
                    self.pending_rate += 1
                    self.events.append("rate")
                elif "INSERT INTO public.anonymous_usage" in sql:
                    self.pending_question = True
                    cursor.row = (self.questions_used + 1,)
                    self.events.append("quota")

        cursor = TransactionCursor(self)
        self.cursors.append(cursor)
        return cursor

    def commit(self):
        super().commit()
        self.questions_used += int(self.pending_question)
        self.rate_requests += self.pending_rate
        self.pending_question = False
        self.pending_rate = 0
        self.events.append("commit")

    def rollback(self):
        super().rollback()
        self.pending_question = False
        self.pending_rate = 0
        self.events.append("rollback")


def _r06_payload(answer="Răspuns [C1].", quote="fragment public"):
    return json.dumps({
        "raspuns": answer, "pasaje": [{"id": "C1", "citat": quote}],
    }, ensure_ascii=False)


@pytest.mark.parametrize("payload", [
    pytest.param(_r06_payload(quote="pasaj fabricat"), id="pasaj-invalid"),
    pytest.param(_r06_payload(answer="Conform STAS 987654321 [C1].", quote="pasaj fabricat"), id="invalid-inainte-de-retry"),
    pytest.param('{"raspuns":"Răspuns [C1]."}', id="pasaje-lipsa"),
    pytest.param(GeneratedText(_r06_payload()[:-1], truncated=True), id="json-incomplet-trunchiat"),
    pytest.param(GeneratedText(_r06_payload(quote="fabricat"), truncated=True), id="pasaj-invalid-trunchiat"),
])
def test_r06_pasaj_invalid_503_rollback_quota_exact_fara_retry_cu_rate_si_buget_pastrate(api, payload):
    connection = R06TransactionConnection()
    budget_connection = ConnectionFake()
    generator = RawGeneratorFake(payload)
    embedder = EmbedderFake()
    client = configure(api, connection, embedder, generator, budget_connection=budget_connection)
    # Cookie valid înainte de eroare: ambele întrebări aparțin aceluiași vizitator.
    assert client.get("/").status_code == 200

    response = client.post("/intreaba", json={"intrebare": "art. 4.4.7.2"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Serviciul este temporar indisponibil."}
    assert generator.calls == 1 and embedder.calls == 0
    assert generator.max_tokens == 1200
    assert connection.commits == 1 and connection.rollbacks == 1
    assert connection.events == ["rate", "commit", "quota", "rollback"]
    assert connection.questions_used == 0 and not connection.pending_question
    assert connection.rate_requests == 1
    assert connection.closed
    assert budget_connection.commits == 1 and budget_connection.rollbacks == 0
    assert len([sql for sql, _ in budget_connection.calls if "INSERT INTO public.paid_call_budget" in sql]) == 1
    _assert_no_technical_identifiers(response)
    assert "fabricat" not in response.text and "987654321" not in response.text

    # Aceeași conexiune sintetică păstrează starea comisă, nu valori quota scriptate.
    generator.answer = _r06_payload()
    second = client.post("/intreaba", json={"intrebare": "art. 4.4.7.2"})
    assert second.status_code == 200
    assert second.json()["intrebari_ramase"] == 9
    assert connection.questions_used == 1 and connection.rate_requests == 2
    assert connection.commits == 3 and connection.rollbacks == 1
    assert generator.calls == 2
    assert budget_connection.commits == 2 and budget_connection.rollbacks == 0
    quota_parameters = [parameters for sql, parameters in connection.calls if "INSERT INTO public.anonymous_usage" in sql]
    assert len(quota_parameters) == 2 and quota_parameters[0] == quota_parameters[1]


def test_r06_pasaj_invalid_rollback_esuat_ramane_503_fara_retry(api):
    connection = R06TransactionConnection(rollback_error=psycopg2.OperationalError("rollback fictiv"))
    budget_connection = ConnectionFake()
    generator = RawGeneratorFake(_r06_payload(quote="fabricat"))

    response = configure(api, connection, generator=generator, budget_connection=budget_connection).post(
        "/intreaba", json={"intrebare": "art. 4.4.7.2"}
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Serviciul este temporar indisponibil."}
    assert connection.commits == 1 and connection.rollbacks == 1
    assert connection.closed and connection.rate_requests == 1
    assert generator.calls == 1
    assert budget_connection.commits == 1 and budget_connection.rollbacks == 0
    _assert_no_technical_identifiers(response)


@pytest.mark.parametrize("truncated", [False, True])
def test_r06_endpoint_afiseaza_pasajul_literal_dupa_600_si_schema_publica(truncated, api):
    quote = "Carcasa fictivă este turcoaz."
    content = "Decor fictiv. " * 60 + quote
    row = EXACT_ROW[:6] + (content, EXACT_ROW[7])
    connection = ConnectionFake(exact_rows=(row,))
    answer = f"{quote} [C1]"
    generator = RawGeneratorFake(GeneratedText(_r06_payload(answer, quote), truncated=truncated))
    assert content.index(quote) > 600

    response = configure(api, connection, generator=generator).post(
        "/intreaba", json={"intrebare": "art. 4.4.7.2"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "answered",
        "raspuns": answer + (f"\n\n{TRUNCATION_NOTICE}" if truncated else ""),
        "citari": [{
            "id": "C1", "cod_document": row[2], "titlu_document": row[3],
            "articol": row[4], "citat": quote,
        }],
        "intrebari_ramase": 9,
    }
    assert quote in row[6] and quote != row[6][:600]
    assert generator.calls == 1 and generator.max_tokens == 1200
    assert connection.commits == 2 and connection.rollbacks == 0
    _assert_no_technical_identifiers(response)


def test_r06_referinta_inventata_cu_pasaj_valid_pastreaza_retry_si_consumul_quota(api):
    connection = R06TransactionConnection()
    budget_connection = ConnectionFake()
    generator = RawGeneratorFake(_r06_payload(answer="Conform STAS 987654321 [C1]."))

    response = configure(api, connection, generator=generator, budget_connection=budget_connection).post(
        "/intreaba", json={"intrebare": "art. 4.4.7.2"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "unsupported_answer", "raspuns": main._UNSUPPORTED_ANSWER,
        "citari": [], "intrebari_ramase": 9,
    }
    assert generator.calls == 2
    assert connection.questions_used == 1 and connection.rate_requests == 1
    assert connection.commits == 2 and connection.rollbacks == 0
    assert budget_connection.commits == 1 and budget_connection.rollbacks == 0
    assert len([sql for sql, _ in budget_connection.calls if "INSERT INTO public.paid_call_budget" in sql]) == 1


# --- Context conversațional: scope semantic fără fallback global ---

P118_CATALOG_ROW = ("doc-p118", "P 118/2-2013", "7.183")
I7_CATALOG_ROW = ("doc-i7", "I7-2011", "6.3.1")
P118_SEMANTIC_ROW = (1, "doc-p118", "P 118/2-2013", "P 118/2", "7.183", "7.183", "obstacole sub sprinklere", "p118", 0.90)
I7_SEMANTIC_DECOY_ROW = (2, "doc-i7", "I7-2011", "I7", "6.3.1", "6.3.1", "obstacole electrice", "i7", 0.90)
TUR_CONTEXT_SPRINKLERE = {
    "intrebare": "Unde găsesc detalii despre obstacolele de la sprinklere?",
    "coduri_documente": ["P 118/2-2013"],
}
INTREBARE_ELIPTICA = "Ok dar spune-mi exact când am un obstacol?"


def _connection_sprinklere(*, scoped_rows):
    """P 118/2 este scopul, iar I7 este decoy-ul disponibil doar în global."""
    return ConnectionFake(
        catalog_rows=(P118_CATALOG_ROW, I7_CATALOG_ROW),
        semantic_rows=(I7_SEMANTIC_DECOY_ROW,),
        semantic_scoped_rows=scoped_rows,
    )


def _interogari_semantice(connection):
    """Întoarce în ordine dacă SQL-ul semantic este scoped și parametrii săi."""
    return [
        ("chunk.document_id = ANY(%s)" in sql, parameters)
        for sql, parameters in connection.calls
        if "AS score" in sql
    ]


def test_api_fara_context_face_o_singura_cautare_semantica_globala(api):
    connection = ConnectionFake()

    response = configure(api, connection).post(
        "/intreaba", json={"intrebare": "Care este regula sintetică?"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "answered"
    assert [scoped for scoped, _ in _interogari_semantice(connection)] == [False]


def test_api_sprinklere_context_cauta_global_fara_filtru_p118(api):
    connection = _connection_sprinklere(scoped_rows=(P118_SEMANTIC_ROW,))

    response = configure(api, connection).post(
        "/intreaba",
        json={"intrebare": INTREBARE_ELIPTICA, "context_conversatie": [TUR_CONTEXT_SPRINKLERE]},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "answered"
    # D11: citarea istorică nu filtrează; aceeași fixture globală este acum eligibilă.
    assert [citation["cod_document"] for citation in response.json()["citari"]] == ["I7-2011"]
    assert _interogari_semantice(connection) == [(False, ("[0.1,0.2]", "[0.1,0.2]", 5))]
    assert response.json()["intrebari_ramase"] == 9


@pytest.mark.parametrize("scoped_rows", [(), (P118_SEMANTIC_ROW[:-1] + (0.49,),)])
def test_api_sprinklere_scoped_miss_istoric_nu_impiedica_generarea_din_global(api, scoped_rows):
    connection = _connection_sprinklere(scoped_rows=scoped_rows)
    embedder = EmbedderFake()
    generator = GeneratorFake()

    response = configure(api, connection, embedder, generator).post(
        "/intreaba",
        json={"intrebare": INTREBARE_ELIPTICA, "context_conversatie": [TUR_CONTEXT_SPRINKLERE]},
    )

    assert response.status_code == 200
    # D11: miss-ul ipotetic scoped nu mai e consultat; dovada globală permite generarea.
    assert response.json()["status"] == "answered"
    assert generator.calls == 1
    assert embedder.calls == 1
    assert [citation["cod_document"] for citation in response.json()["citari"]] == ["I7-2011"]
    assert _interogari_semantice(connection) == [(False, ("[0.1,0.2]", "[0.1,0.2]", 5))]
    assert response.json()["intrebari_ramase"] == 9


@pytest.mark.parametrize(
    "context",
    [
        [{"intrebare": ""}],
        [{"intrebare": "x" * (main.MAX_QUESTION_CHARS + 1)}],
        [{"intrebare": "ok", "camp_nerecunoscut": 1}],
        [{"intrebare": "ok", "coduri_documente": "NP 010-2022"}],
        [{"coduri_documente": ["NP 010-2022"]}],
        [{"intrebare": "ok"}] * (main.MAX_CONTEXT_TURNS + 1),
        "nu-e-o-lista",
    ],
)
def test_api_context_invalid_este_422_inainte_de_dependente(api, context):
    connection = ConnectionFake()
    embedder = EmbedderFake()
    generator = GeneratorFake()

    response = configure(api, connection, embedder, generator).post(
        "/intreaba", json={"intrebare": "Care este regula sintetică?", "context_conversatie": context}
    )

    assert response.status_code == 422
    assert connection.calls == []
    assert embedder.calls == generator.calls == 0
    _assert_no_technical_identifiers(response)


@pytest.mark.parametrize("phrase", ["doar din", "numai din", "exclusiv din"])
@pytest.mark.parametrize("code", ["XX 999-2099", "NP 777-2099", "NP 010-2099"])
def test_api_d13_cod_absent_clarifica_si_consuma_quota_rate_fara_apel_platit(api, phrase, code):
    # Refolosim simularea tranzacțională existentă; nu modificăm testele sau runtime-ul R06.
    connection = R06TransactionConnection()
    embedder = EmbedderFake()
    generator = GeneratorFake()
    budget_connection = ConnectionFake()
    client = configure(api, connection, embedder, generator, budget_connection=budget_connection)
    request = {
        "intrebare": f"Răspunde {phrase} {code} despre marcajele pieselor fictive.",
        "context_conversatie": [{"intrebare": "Ce marcaje au piesele fictive?", "coduri_documente": ["NP 010-2022"]}],
    }

    first = client.post("/intreaba", json=request)

    assert first.status_code == 200
    assert first.json() == {
        "status": "ambiguous_reference", "raspuns": main._AMBIGUOUS_REFERENCE,
        "citari": [], "intrebari_ramase": 9,
    }
    assert connection.questions_used == 1 and connection.rate_requests == 1
    assert connection.commits == 2 and connection.rollbacks == 0
    assert connection.events == ["rate", "commit", "quota", "commit"]
    assert connection.closed
    assert embedder.calls == generator.calls == 0
    assert budget_connection.calls == []
    assert budget_connection.commits == budget_connection.rollbacks == 0
    # Catalogul de metadata este necesar pentru rezolvarea codului; dovezile nu sunt citite.
    assert len([sql for sql, _ in connection.calls if "SELECT document.document_id" in sql]) == 1
    assert all("chunk.content_hash" not in sql and "AS score" not in sql for sql, _ in connection.calls)
    _assert_no_technical_identifiers(first)

    second = client.post("/intreaba", json=request)

    assert second.status_code == 200
    assert second.json()["status"] == "ambiguous_reference"
    assert second.json()["intrebari_ramase"] == 8
    assert connection.questions_used == connection.rate_requests == 2
    assert connection.commits == 4 and connection.rollbacks == 0
    quota_parameters = [parameters for sql, parameters in connection.calls if "INSERT INTO public.anonymous_usage" in sql]
    assert len(quota_parameters) == 2 and quota_parameters[0] == quota_parameters[1]
    assert embedder.calls == generator.calls == 0
    assert budget_connection.calls == []
    assert all("chunk.content_hash" not in sql and "AS score" not in sql for sql, _ in connection.calls)


@pytest.mark.parametrize("phrase", ["doar din", "numai din", "exclusiv din"])
@pytest.mark.parametrize("scoped_rows", [(), (SEMANTIC_ROW[:-1] + (0.49,),)])
def test_api_d12_scope_explicit_fara_dovezi_nu_face_fallback_global(api, phrase, scoped_rows):
    connection = ConnectionFake(semantic_scoped_rows=scoped_rows)
    embedder = EmbedderFake()
    generator = GeneratorFake()
    budget_connection = ConnectionFake()

    response = configure(api, connection, embedder, generator, budget_connection=budget_connection).post(
        "/intreaba", json={"intrebare": f"Răspunde {phrase} NP 010-2022 despre marcajele fictive."}
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "not_found", "raspuns": main._NOT_FOUND, "citari": [], "intrebari_ramase": 9,
    }
    assert _interogari_semantice(connection) == [(True, ("[0.1,0.2]", ["doc-1"], "[0.1,0.2]", 5))]
    assert embedder.calls == 1 and generator.calls == 0
    assert connection.commits == 2 and connection.rollbacks == 0
    assert budget_connection.commits == 1


@pytest.mark.parametrize("phrase", ["doar din", "numai din", "exclusiv din"])
def test_api_d12_scope_explicit_gasit_pastreaza_citatul_r06_si_schema(api, phrase):
    connection = ConnectionFake(semantic_scoped_rows=(SEMANTIC_ROW,))
    embedder = EmbedderFake()
    generator = GeneratorFake()
    budget_connection = ConnectionFake()

    response = configure(api, connection, embedder, generator, budget_connection=budget_connection).post(
        "/intreaba", json={"intrebare": f"Răspunde {phrase} NP 010-2022 despre marcajele fictive."}
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "answered", "raspuns": "Răspuns [C1].",
        "citari": [{"id": "C1", "cod_document": "NP 010-2022", "titlu_document": "Titlu oficial",
                    "articol": "4.4.7.2", "citat": "fragment public"}],
        "intrebari_ramase": 9,
    }
    assert _interogari_semantice(connection) == [(True, ("[0.1,0.2]", ["doc-1"], "[0.1,0.2]", 5))]
    assert embedder.calls == generator.calls == 1
    assert budget_connection.commits == 1
    assert connection.commits == 2 and connection.rollbacks == 0


def test_api_d11_comparatia_multi_document_pastreaza_maparea_si_ordinea_citarilor_r06(api):
    connection = ConnectionFake(
        catalog_rows=(P118_CATALOG_ROW, I7_CATALOG_ROW),
        semantic_rows=(P118_SEMANTIC_ROW, I7_SEMANTIC_DECOY_ROW),
    )
    embedder = EmbedderFake()
    generator = RawGeneratorFake(json.dumps({
        "raspuns": "Marcaje fictive [C2], apoi [C1].",
        "pasaje": [{"id": "C1", "citat": "obstacole sub sprinklere"},
                   {"id": "C2", "citat": "obstacole electrice"}],
    }))
    budget_connection = ConnectionFake()

    response = configure(api, connection, embedder, generator, budget_connection=budget_connection).post(
        "/intreaba", json={"intrebare": "Compară P 118/2-2013 și I7-2011 privind marcajele fictive."}
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"status", "raspuns", "citari", "intrebari_ramase"}
    assert body["status"] == "answered" and body["intrebari_ramase"] == 9
    assert body["raspuns"] == "Marcaje fictive [C2], apoi [C1]."
    assert [(item["id"], item["cod_document"], item["articol"], item["citat"]) for item in body["citari"]] == [
        ("C2", "I7-2011", "6.3.1", "obstacole electrice"),
        ("C1", "P 118/2-2013", "7.183", "obstacole sub sprinklere"),
    ]
    assert _interogari_semantice(connection) == [(False, ("[0.1,0.2]", "[0.1,0.2]", 5))]
    assert embedder.calls == generator.calls == 1
    assert generator.max_tokens == 1200 and budget_connection.commits == 1
    _assert_no_technical_identifiers(response)


def test_api_d14_nu_doar_din_nu_introduce_filtru_scoped(api):
    connection = ConnectionFake()
    embedder = EmbedderFake()
    generator = GeneratorFake()

    response = configure(api, connection, embedder, generator).post(
        "/intreaba", json={"intrebare": "Răspunde nu doar din NP 010-2022 despre marcajele fictive."}
    )

    assert response.status_code == 200 and response.json()["status"] == "answered"
    assert _interogari_semantice(connection) == [(False, ("[0.1,0.2]", "[0.1,0.2]", 5))]
    assert embedder.calls == generator.calls == 1
    assert response.json()["intrebari_ramase"] == 9
