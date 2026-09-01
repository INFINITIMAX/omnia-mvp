"""API FastAPI pentru fluxul NormativAI mock-first, fără clienți externi la import."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Callable, Literal, Protocol, Sequence

import psycopg2
from anthropic import Anthropic, AnthropicError
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator
import voyageai
from voyageai.error import VoyageError

from access_control import (
    ANONYMOUS_QUOTA_LIMIT,
    RATE_LIMIT_PER_HOUR,
    RATE_LIMIT_PER_MINUTE,
    AccessControlConfig,
    PostgresAccessControlRepository,
    hash_ip,
    issue_anonymous_cookie,
    verify_anonymous_cookie,
)
from generation_core import GenerationService, GenerationValidationError, PublicCitation
load_dotenv()

from retrieval_core import (
    MAX_QUESTION_CHARS,
    PostgresApprovedCatalogRepository,
    PostgresRetrievalRepository,
    RetrievalService,
)


class ServiceDependencyError(Exception):
    """Eroare sigură a unei dependențe externe sau a configurației sale."""


class DependencyConfigurationError(ServiceDependencyError):
    """Configurația necesară pentru o dependență lipsește sau este invalidă."""


class ProviderUnavailableError(ServiceDependencyError):
    """Un SDK extern nu poate furniza un răspuns utilizabil."""


class QueryEmbedder(Protocol):
    """Contract injectabil pentru embedding-ul unei singure întrebări."""

    def embed_query(self, question: str) -> Sequence[float]: ...


class TextGenerator(Protocol):
    """Contract injectabil pentru textul generat din promptul validat."""

    def generate(self, prompt: str, *, max_tokens: int) -> str: ...


class VoyageQueryEmbedder:
    """Adaptor lazy pentru Voyage; clientul HTTP apare numai la prima căutare semantică."""

    model = "voyage-3.5"

    def __init__(self, client: object | None = None) -> None:
        self._client = client

    def embed_query(self, question: str) -> Sequence[float]:
        try:
            if self._client is None:
                self._client = voyageai.Client(api_key=_required_environment("VOYAGE_API_KEY"))
            response = self._client.embed([question], model=self.model, input_type="query")
        except VoyageError as error:
            raise ProviderUnavailableError("Voyage indisponibil") from error
        return self._validated_embedding(response)

    @staticmethod
    def _validated_embedding(response: object) -> tuple[float, ...]:
        embeddings = getattr(response, "embeddings", None)
        if not isinstance(embeddings, Sequence) or isinstance(embeddings, (str, bytes)) or not embeddings:
            raise ProviderUnavailableError("răspuns Voyage invalid")
        vector = embeddings[0]
        if not isinstance(vector, Sequence) or isinstance(vector, (str, bytes)) or not vector:
            raise ProviderUnavailableError("vector Voyage invalid")
        if any(type(value) not in (int, float) or not math.isfinite(float(value)) for value in vector):
            raise ProviderUnavailableError("vector Voyage invalid")
        return tuple(float(value) for value in vector)


class AnthropicTextGenerator:
    """Adaptor lazy pentru Anthropic; clientul HTTP apare numai când există dovezi."""

    model = "claude-sonnet-4-6"

    def __init__(self, client: object | None = None) -> None:
        self._client = client

    def generate(self, prompt: str, *, max_tokens: int) -> str:
        try:
            if self._client is None:
                self._client = Anthropic(api_key=_required_environment("ANTHROPIC_API_KEY"))
            response = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        except AnthropicError as error:
            raise ProviderUnavailableError("Anthropic indisponibil") from error
        return self._validated_text(response)

    @staticmethod
    def _validated_text(response: object) -> str:
        content = getattr(response, "content", None)
        if not isinstance(content, Sequence) or isinstance(content, (str, bytes)) or not content:
            raise ProviderUnavailableError("răspuns Anthropic invalid")
        texts = [
            block.text
            for block in content
            if getattr(block, "type", None) == "text"
            and isinstance(getattr(block, "text", None), str)
            and block.text.strip()
        ]
        if not texts:
            raise ProviderUnavailableError("răspuns Anthropic invalid")
        return "\n".join(texts)


def _required_environment(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise DependencyConfigurationError("configurație indisponibilă")
    return value


def _open_db_connection() -> object:
    """Deschide conexiunea numai în timpul unei cereri, nu la import."""
    return psycopg2.connect(
        host=_required_environment("DB_HOST"),
        dbname=_required_environment("DB_NAME"),
        user=_required_environment("DB_USER"),
        password=_required_environment("DB_PASSWORD"),
        port=_required_environment("DB_PORT"),
    )


@dataclass(frozen=True)
class AnonymousAccessControlRuntimeConfig:
    """Configurația anonimă server-side și atributul HTTP al cookie-ului."""

    access_control: AccessControlConfig
    cookie_secure: bool


def _anonymous_access_control_config() -> AnonymousAccessControlRuntimeConfig:
    """Citește strict configurația anonimă numai când o cerere are nevoie de ea."""
    cookie_secure = os.getenv("ANONYMOUS_COOKIE_SECURE")
    if cookie_secure is None:
        raise DependencyConfigurationError("configurație indisponibilă")
    normalized_secure = cookie_secure.strip().casefold()
    if normalized_secure not in {"true", "false"}:
        raise DependencyConfigurationError("configurație indisponibilă")
    try:
        return AnonymousAccessControlRuntimeConfig(
            AccessControlConfig(
                _required_environment("ANONYMOUS_COOKIE_SIGNING_KEY").encode("utf-8"),
                _required_environment("ANONYMOUS_IP_HASH_KEY").encode("utf-8"),
            ),
            cookie_secure=normalized_secure == "true",
        )
    except ValueError as error:
        raise DependencyConfigurationError("configurație indisponibilă") from error


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class RuntimeDependencies:
    """Fabrici injectabile; endpointul le apelează numai după validarea corpului."""

    connection_factory: Callable[[], object]
    embedder_factory: Callable[[], QueryEmbedder]
    text_generator_factory: Callable[[], TextGenerator]
    access_control_config_factory: Callable[[], AnonymousAccessControlRuntimeConfig] = _anonymous_access_control_config
    now_factory: Callable[[], datetime] = _utc_now


app = FastAPI()
app.state.runtime_dependencies = RuntimeDependencies(
    connection_factory=_open_db_connection,
    embedder_factory=VoyageQueryEmbedder,
    text_generator_factory=AnthropicTextGenerator,
)

_COOKIE_NAME = "normativai_anon"


def _anonymous_visitor_for_request(
    request: Request, runtime_config: AnonymousAccessControlRuntimeConfig, *, now: datetime
):
    visitor = verify_anonymous_cookie(
        request.cookies.get(_COOKIE_NAME), runtime_config.access_control, now=now
    )
    if visitor is not None:
        return visitor, None
    token, visitor = issue_anonymous_cookie(runtime_config.access_control, now=now)
    return visitor, token


def _set_anonymous_cookie(
    response: Response, token: str, runtime_config: AnonymousAccessControlRuntimeConfig
) -> None:
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        max_age=365 * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        path="/",
        secure=runtime_config.cookie_secure,
    )


@app.get("/")
def pagina_principala(request: Request) -> FileResponse:
    try:
        dependencies: RuntimeDependencies = app.state.runtime_dependencies
        runtime_config = dependencies.access_control_config_factory()
        _, token = _anonymous_visitor_for_request(
            request, runtime_config, now=dependencies.now_factory()
        )
        response = FileResponse("static/index.html")
        if token is not None:
            _set_anonymous_cookie(response, token, runtime_config)
        return response
    except ServiceDependencyError as error:
        raise HTTPException(status_code=503, detail="Serviciul este temporar indisponibil.") from error


class IntrebareRequest(BaseModel):
    intrebare: Annotated[str, Field(min_length=1, max_length=MAX_QUESTION_CHARS)]

    @field_validator("intrebare")
    @classmethod
    def intrebare_nevida(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("întrebarea nu poate fi goală")
        return value


class CitationResponse(BaseModel):
    id: str
    cod_document: str
    titlu_document: str
    articol: str
    citat: str

    @classmethod
    def from_public(cls, citation: PublicCitation) -> "CitationResponse":
        return cls(**citation.__dict__)


class IntreabaResponse(BaseModel):
    status: Literal["answered", "not_found", "ambiguous_article", "ambiguous_reference"]
    raspuns: str
    citari: list[CitationResponse]
    intrebari_ramase: Annotated[int, Field(ge=0, le=9)]


_NOT_FOUND = "Nu am găsit această informație în documentele aprobate."
_AMBIGUOUS_ARTICLE = "Am găsit versiuni neconcordante ale articolului solicitat."
_AMBIGUOUS_REFERENCE = "Întrebarea conține referințe ambigue; te rog precizează documentul sau articolul."


def _request_ip_hash(request: Request, runtime_config: AnonymousAccessControlRuntimeConfig) -> str:
    """Extrage strict IP-ul direct al clientului, fără antete de proxy."""
    client = request.client
    host = getattr(client, "host", None)
    if host is None:
        raise ServiceDependencyError("IP client indisponibil")
    try:
        return hash_ip(host, runtime_config.access_control)
    except ValueError as error:
        raise ServiceDependencyError("IP client invalid") from error


def _retry_after_seconds(rate_result: object, now: datetime) -> int:
    delays = []
    if rate_result.minute_count > RATE_LIMIT_PER_MINUTE:
        delays.append(rate_result.minute_bucket_start + timedelta(minutes=1) - now)
    if rate_result.hour_count > RATE_LIMIT_PER_HOUR:
        delays.append(rate_result.hour_bucket_start + timedelta(hours=1) - now)
    if not delays:
        raise ServiceDependencyError("rezultat rate limit inconsistent")
    return max(1, math.ceil(max(delays).total_seconds()))


def _rollback_succeeds(connection: object) -> bool:
    """Încearcă rollback; un eșec DB nu trebuie să ajungă la client."""
    try:
        connection.rollback()
    except psycopg2.Error:
        return False
    return True


def _control_error_response(
    status_code: int, content: dict[str, object], token: str | None,
    runtime_config: AnonymousAccessControlRuntimeConfig, *, retry_after: int | None = None,
) -> JSONResponse:
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
    response = JSONResponse(status_code=status_code, content=content, headers=headers)
    if token is not None:
        _set_anonymous_cookie(response, token, runtime_config)
    return response


@app.post("/intreaba", response_model=IntreabaResponse)
def intreaba(
    cerere: IntrebareRequest, request: Request, response: Response
) -> IntreabaResponse | JSONResponse:
    """Aplică controalele anonime înainte de retrieval și generare."""
    connection: object | None = None
    try:
        dependencies: RuntimeDependencies = app.state.runtime_dependencies
        runtime_config = dependencies.access_control_config_factory()
        now = dependencies.now_factory()
        visitor, token = _anonymous_visitor_for_request(request, runtime_config, now=now)
        ip_hash = _request_ip_hash(request, runtime_config)
        connection = dependencies.connection_factory()
        access_repository = PostgresAccessControlRepository(connection)
        rate_result = access_repository.check_and_increment_rate_limit(ip_hash, now=now)
        connection.commit()
        if not rate_result.allowed:
            return _control_error_response(
                429,
                {"code": "rate_limited", "detail": "Prea multe cereri. Încearcă din nou mai târziu."},
                token,
                runtime_config,
                retry_after=_retry_after_seconds(rate_result, now),
            )

        questions_used = access_repository.reserve_question(visitor.visitor_hash)
        if questions_used is None:
            if not _rollback_succeeds(connection):
                raise HTTPException(status_code=503, detail="Serviciul este temporar indisponibil.")
            return _control_error_response(
                403,
                {
                    "code": "quota_exhausted",
                    "detail": "Ai folosit toate cele 10 întrebări disponibile în acest browser.",
                    "intrebari_ramase": 0,
                },
                token,
                runtime_config,
            )
        intrebari_ramase = ANONYMOUS_QUOTA_LIMIT - questions_used

        parser = PostgresApprovedCatalogRepository(connection).load().create_parser()
        retrieval = RetrievalService(
            parser,
            PostgresRetrievalRepository(connection),
            dependencies.embedder_factory(),
        )
        result = retrieval.retrieve(cerere.intrebare)

        if result.status == "not_found":
            answer = IntreabaResponse(
                status="not_found", raspuns=_NOT_FOUND, citari=[], intrebari_ramase=intrebari_ramase
            )
        elif result.status == "ambiguous_article":
            answer = IntreabaResponse(
                status="ambiguous_article", raspuns=_AMBIGUOUS_ARTICLE, citari=[], intrebari_ramase=intrebari_ramase
            )
        elif result.status == "ambiguous_reference":
            answer = IntreabaResponse(
                status="ambiguous_reference", raspuns=_AMBIGUOUS_REFERENCE, citari=[], intrebari_ramase=intrebari_ramase
            )
        else:
            generated = GenerationService(dependencies.text_generator_factory()).generate(
                cerere.intrebare, result.evidence
            )
            answer = IntreabaResponse(
                status="answered",
                raspuns=generated.raspuns,
                citari=[CitationResponse.from_public(item) for item in generated.citari],
                intrebari_ramase=intrebari_ramase,
            )
        connection.commit()
        if token is not None:
            _set_anonymous_cookie(response, token, runtime_config)
        return answer
    except HTTPException:
        raise
    except (GenerationValidationError, ServiceDependencyError, psycopg2.Error) as error:
        if connection is not None and not _rollback_succeeds(connection):
            raise HTTPException(status_code=503, detail="Serviciul este temporar indisponibil.") from error
        raise HTTPException(status_code=503, detail="Serviciul este temporar indisponibil.") from error
    except Exception as error:
        if connection is not None and not _rollback_succeeds(connection):
            raise HTTPException(status_code=503, detail="Serviciul este temporar indisponibil.") from error
        raise
    finally:
        if connection is not None:
            try:
                connection.close()
            except psycopg2.Error as error:
                raise HTTPException(
                    status_code=503, detail="Serviciul este temporar indisponibil."
                ) from error
