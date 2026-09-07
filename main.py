"""API FastAPI pentru fluxul NormativAI mock-first, fără clienți externi la import."""

from __future__ import annotations

import ipaddress
import math
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Callable, Literal, Protocol, Sequence

import psycopg2
from anthropic import Anthropic, AnthropicError
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
import voyageai
from voyageai.error import VoyageError

from access_control import (
    ANONYMOUS_QUOTA_LIMIT,
    DEFAULT_DAILY_PAID_CALL_LIMIT,
    RATE_LIMIT_PER_HOUR,
    RATE_LIMIT_PER_MINUTE,
    AccessControlConfig,
    PostgresAccessControlRepository,
    RateLimitResult,
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


class DailyBudgetExhaustedError(ServiceDependencyError):
    """Plafonul zilnic pentru apelurile plătite (Voyage/Anthropic) a fost atins."""


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


class _PaidCallBudgetGuard:
    """Rezervă cel mult o dată, per cerere, plafonul zilnic global, indiferent câte apeluri
    plătite (Voyage și/sau Anthropic) declanșează întrebarea; folosește o conexiune DB proprie,
    izolată de tranzacția de quota/generare, ca numărul să rămână corect chiar dacă restul
    cererii eșuează și face rollback după ce banii au fost deja cheltuiți."""

    def __init__(
        self, connection_factory: Callable[[], object], *, now: datetime, daily_limit: int
    ) -> None:
        self._connection_factory = connection_factory
        self._now = now
        self._daily_limit = daily_limit
        self._reserved = False

    def reserve(self) -> None:
        if self._reserved:
            return
        connection = self._connection_factory()
        try:
            repository = PostgresAccessControlRepository(connection)
            result = repository.reserve_paid_call(now=self._now, daily_limit=self._daily_limit)
            connection.commit()
        finally:
            connection.close()
        if result is None:
            raise DailyBudgetExhaustedError("plafon zilnic epuizat")
        self._reserved = True


class BudgetGatedEmbedder:
    """Îmbracă un `QueryEmbedder` real; refuză apelul dacă plafonul zilnic e atins."""

    def __init__(self, inner: QueryEmbedder, guard: _PaidCallBudgetGuard) -> None:
        self._inner = inner
        self._guard = guard

    def embed_query(self, question: str) -> Sequence[float]:
        self._guard.reserve()
        return self._inner.embed_query(question)


class BudgetGatedTextGenerator:
    """Îmbracă un `TextGenerator` real; refuză apelul dacă plafonul zilnic e atins."""

    def __init__(self, inner: TextGenerator, guard: _PaidCallBudgetGuard) -> None:
        self._inner = inner
        self._guard = guard

    def generate(self, prompt: str, *, max_tokens: int) -> str:
        self._guard.reserve()
        return self._inner.generate(prompt, max_tokens=max_tokens)


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
    """Configurația anonimă server-side, atributul cookie-ului și proxy-urile de încredere."""

    access_control: AccessControlConfig
    cookie_secure: bool
    trusted_proxy_hops: int = 0


def _trusted_proxy_hops() -> int:
    """Citește numărul de proxy-uri de încredere; absent înseamnă zero, restul e fail-closed."""
    raw = os.getenv("TRUSTED_PROXY_HOPS")
    if raw is None:
        return 0
    normalized = raw.strip()
    if not normalized.isascii() or not normalized.isdecimal():
        raise DependencyConfigurationError("configurație indisponibilă")
    return int(normalized)


def _daily_paid_call_limit() -> int:
    """Citește plafonul zilnic de apeluri plătite; absent înseamnă valoarea implicită prudentă,
    orice altă valoare invalidă e fail-closed (503), la fel ca restul configurației."""
    raw = os.getenv("DAILY_PAID_CALL_LIMIT")
    if raw is None:
        return DEFAULT_DAILY_PAID_CALL_LIMIT
    normalized = raw.strip()
    if not normalized.isascii() or not normalized.isdecimal() or int(normalized) <= 0:
        raise DependencyConfigurationError("configurație indisponibilă")
    return int(normalized)


def _anonymous_access_control_config() -> AnonymousAccessControlRuntimeConfig:
    """Citește strict configurația anonimă numai când o cerere are nevoie de ea."""
    cookie_secure = os.getenv("ANONYMOUS_COOKIE_SECURE")
    if cookie_secure is None:
        raise DependencyConfigurationError("configurație indisponibilă")
    normalized_secure = cookie_secure.strip().casefold()
    if normalized_secure not in {"true", "false"}:
        raise DependencyConfigurationError("configurație indisponibilă")
    trusted_proxy_hops = _trusted_proxy_hops()
    try:
        return AnonymousAccessControlRuntimeConfig(
            AccessControlConfig(
                _required_environment("ANONYMOUS_COOKIE_SIGNING_KEY").encode("utf-8"),
                _required_environment("ANONYMOUS_IP_HASH_KEY").encode("utf-8"),
            ),
            cookie_secure=normalized_secure == "true",
            trusted_proxy_hops=trusted_proxy_hops,
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
    daily_paid_call_limit_factory: Callable[[], int] = _daily_paid_call_limit
    # Conexiune proprie, distinctă de `connection_factory`: plafonul zilnic trebuie să rămână
    # corect chiar dacă restul tranzacției cererii curente face rollback (vezi _PaidCallBudgetGuard).
    budget_connection_factory: Callable[[], object] = _open_db_connection


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.state.runtime_dependencies = RuntimeDependencies(
    connection_factory=_open_db_connection,
    embedder_factory=VoyageQueryEmbedder,
    text_generator_factory=AnthropicTextGenerator,
)

_COOKIE_NAME = "normativai_anon"

_STATIC_DIRECTORY = Path(__file__).resolve().parent / "static"
_ASSETS_DIRECTORY = _STATIC_DIRECTORY / "assets"
app.mount(
    "/assets",
    # `check_dir=False`: un director absent degradează la 404, nu blochează pornirea.
    StaticFiles(directory=_ASSETS_DIRECTORY, check_dir=False),
    name="assets",
)


# Hash-urile sha256 de mai jos corespund exact conținutului blocurilor inline din
# static/index.html, static/termeni.html și static/confidentialitate.html (verificat manual:
# niciuna dintre pagini nu încarcă altceva decât fonturile self-hostate din /assets și
# fetch('/intreaba') same-origin). O modificare a acelor blocuri inline cere hash-uri noi aici,
# altfel pagina se rupe silențios sub CSP.
_CSP_SCRIPT_HASHES = ("'sha256-wfoebk3dRcLt0TUKvQJMsflmH7cMMqd1bLqr+51WZD4='",)  # static/index.html <script>
_CSP_STYLE_HASHES = (
    "'sha256-O6XdWM+9BJcW7sYoiLi+ZU4Fe3ZZnfh+F+q9HsU7b+A='",  # static/index.html <style>
    "'sha256-kUyxp8kcWn+qR+O4JbENkEzXFLSQLF+bM6N26VjKs0c='",  # static/termeni.html <style>
    "'sha256-303Ph9pYTBdqEAWSTPYw5296I5SBQDxpsmFJ3UO3iMo='",  # static/confidentialitate.html <style>
    "'sha256-iRTSbo/Ydn205oSWi3GzwimCP8819GmmNR28mXK/M70='",  # static/termeni.html style="margin-top: 40px;"
)
_CONTENT_SECURITY_POLICY = "; ".join((
    "default-src 'none'",
    "script-src " + " ".join(_CSP_SCRIPT_HASHES),
    "style-src 'unsafe-hashes' " + " ".join(_CSP_STYLE_HASHES),
    "font-src 'self'",
    "connect-src 'self'",
    "img-src 'self'",
    "base-uri 'none'",
    "form-action 'self'",
    "frame-ancestors 'none'",
))
_PERMISSIONS_POLICY = ", ".join((
    "camera=()", "microphone=()", "geolocation=()", "payment=()", "usb=()",
    "magnetometer=()", "gyroscope=()", "accelerometer=()", "fullscreen=()",
))
_SECURITY_HEADERS = {
    "Content-Security-Policy": _CONTENT_SECURITY_POLICY,
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": _PERMISSIONS_POLICY,
    # Fără `preload`: Railway redirecționează deja 301 către HTTPS, dar înscrierea în lista de
    # preload a browserelor e o decizie separată, ireversibilă fără proces manual de eliminare.
    "Strict-Transport-Security": "max-age=15552000",
}


@app.middleware("http")
async def _security_headers_middleware(request: Request, call_next):
    """Adaugă antetele de securitate pe fiecare răspuns, inclusiv pe erori și pe fișierele statice."""
    response = await call_next(request)
    for header, value in _SECURITY_HEADERS.items():
        response.headers[header] = value
    return response


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


@app.get("/health")
def health() -> dict[str, str]:
    """Healthcheck public și ieftin: nu atinge DB-ul, providerii sau configurația."""
    return {"status": "ok"}


def _static_page_response(file_name: str) -> FileResponse:
    """Servește o pagină statică fixă; absența ei devine 503 generic, ca la `/`."""
    path = _STATIC_DIRECTORY / file_name
    try:
        if not path.is_file():
            raise ServiceDependencyError("pagină statică indisponibilă")
        return FileResponse(path, stat_result=os.stat(path))
    except OSError as error:
        raise ServiceDependencyError("pagină statică indisponibilă") from error


@app.get("/termeni")
def pagina_termeni() -> FileResponse:
    """Servește exclusiv pagina juridică Termeni, dintr-o cale fixă."""
    try:
        return _static_page_response("termeni.html")
    except ServiceDependencyError as error:
        raise HTTPException(status_code=503, detail="Serviciul este temporar indisponibil.") from error


@app.get("/confidentialitate")
def pagina_confidentialitate() -> FileResponse:
    """Servește exclusiv pagina juridică de confidențialitate, dintr-o cale fixă."""
    try:
        return _static_page_response("confidentialitate.html")
    except ServiceDependencyError as error:
        raise HTTPException(status_code=503, detail="Serviciul este temporar indisponibil.") from error


class DocumentPublic(BaseModel):
    cod_oficial: str
    titlu_oficial: str
    an: int


class DocumenteResponse(BaseModel):
    documente: list[DocumentPublic]


_SQL_DOCUMENTE_APROBATE = (
    "SELECT cod_oficial, titlu_oficial, an FROM public.documente WHERE status = %s ORDER BY cod_oficial"
)


def _documente_aprobate(connection: object) -> list[DocumentPublic]:
    """Citește doar metadata publică (cod oficial, titlu, an) a documentelor aprobate —
    fără document_id, source_key sau alt identificator intern (vezi CitationResponse mai jos,
    același principiu: doar ce e sigur pentru un vizitator anonim)."""
    cursor = connection.cursor()
    try:
        cursor.execute(_SQL_DOCUMENTE_APROBATE, ("approved",))
        rows = cursor.fetchall()
    finally:
        cursor.close()
    return [
        DocumentPublic(cod_oficial=str(cod), titlu_oficial=str(titlu), an=int(an))
        for cod, titlu, an in rows
    ]


@app.get("/documents", response_model=DocumenteResponse)
def documente() -> DocumenteResponse:
    """Catalogul public al documentelor aprobate — fără cookie, quota sau rate limit,
    la fel ca /termeni și /confidentialitate: e o listă statică ieftină, nu declanșează
    niciun apel plătit și nu justifică fricțiunea controalelor anonime."""
    connection: object | None = None
    try:
        dependencies: RuntimeDependencies = app.state.runtime_dependencies
        connection = dependencies.connection_factory()
        return DocumenteResponse(documente=_documente_aprobate(connection))
    except (ServiceDependencyError, psycopg2.Error) as error:
        raise HTTPException(status_code=503, detail="Serviciul este temporar indisponibil.") from error
    finally:
        if connection is not None:
            connection.close()


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


_FORWARDED_FOR_HEADER = "X-Forwarded-For"


def _is_ip_literal(value: str) -> bool:
    """Acceptă numai o adresă IP literală, fără zonă IPv6 și fără port."""
    if "%" in value:
        return False
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def _client_ip(request: Request, trusted_proxy_hops: int) -> str:
    """Alege IP-ul clientului; folosește `X-Forwarded-For` doar pe pozițiile de încredere."""
    host = getattr(request.client, "host", None)
    if host is None:
        raise ServiceDependencyError("IP client indisponibil")
    if trusted_proxy_hops <= 0:
        return host
    # Un proxy poate adăuga un antet separat în loc să extindă valoarea existentă;
    # `getlist` le vede pe toate, `get` ar returna numai prima, adică pe cea a clientului.
    forwarded = ", ".join(request.headers.getlist(_FORWARDED_FOR_HEADER))
    if not forwarded.strip():
        return host
    entries = [entry.strip() for entry in forwarded.split(",")]
    if len(entries) < trusted_proxy_hops:
        return host
    candidate = entries[-trusted_proxy_hops]
    if not _is_ip_literal(candidate):
        return host
    return candidate


def _request_ip_hash(request: Request, runtime_config: AnonymousAccessControlRuntimeConfig) -> str:
    """Derivă hash-ul IP din adresa aleasă fail-closed pentru numărul de proxy-uri de încredere."""
    host = _client_ip(request, runtime_config.trusted_proxy_hops)
    try:
        return hash_ip(host, runtime_config.access_control)
    except ValueError as error:
        raise ServiceDependencyError("IP client invalid") from error


def _validate_rate_limit_result(rate_result: object) -> RateLimitResult:
    """Acceptă numai rezultatul rate-limit coerent, după commit-ul tranzacției dedicate."""
    if not isinstance(rate_result, RateLimitResult):
        raise ServiceDependencyError("rezultat rate limit invalid")
    if type(rate_result.minute_count) is not int or type(rate_result.hour_count) is not int:
        raise ServiceDependencyError("rezultat rate limit invalid")
    if rate_result.minute_count < 1 or rate_result.hour_count < 1:
        raise ServiceDependencyError("rezultat rate limit invalid")
    expected_allowed = (
        rate_result.minute_count <= RATE_LIMIT_PER_MINUTE
        and rate_result.hour_count <= RATE_LIMIT_PER_HOUR
    )
    if rate_result.allowed is not expected_allowed:
        raise ServiceDependencyError("rezultat rate limit inconsistent")
    return rate_result


def _retry_after_seconds(rate_result: RateLimitResult, now: datetime) -> int:
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
    rate_transaction_committed = False
    quota_transaction_active = False
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
        rate_transaction_committed = True
        rate_result = _validate_rate_limit_result(rate_result)
        if not rate_result.allowed:
            return _control_error_response(
                429,
                {"code": "rate_limited", "detail": "Prea multe cereri. Încearcă din nou mai târziu."},
                token,
                runtime_config,
                retry_after=_retry_after_seconds(rate_result, now),
            )

        quota_transaction_active = True
        questions_used = access_repository.reserve_question(visitor.visitor_hash)
        if questions_used is None:
            if not _rollback_succeeds(connection):
                raise HTTPException(status_code=503, detail="Serviciul este temporar indisponibil.")
            quota_transaction_active = False
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

        budget_guard = _PaidCallBudgetGuard(
            dependencies.budget_connection_factory, now=now, daily_limit=dependencies.daily_paid_call_limit_factory()
        )
        parser = PostgresApprovedCatalogRepository(connection).load().create_parser()
        retrieval = RetrievalService(
            parser,
            PostgresRetrievalRepository(connection),
            BudgetGatedEmbedder(dependencies.embedder_factory(), budget_guard),
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
            generator = BudgetGatedTextGenerator(dependencies.text_generator_factory(), budget_guard)
            generated = GenerationService(generator).generate(
                cerere.intrebare, result.evidence
            )
            answer = IntreabaResponse(
                status="answered",
                raspuns=generated.raspuns,
                citari=[CitationResponse.from_public(item) for item in generated.citari],
                intrebari_ramase=intrebari_ramase,
            )
        connection.commit()
        quota_transaction_active = False
        if token is not None:
            _set_anonymous_cookie(response, token, runtime_config)
        return answer
    except HTTPException:
        raise
    except (GenerationValidationError, ServiceDependencyError, psycopg2.Error) as error:
        if connection is not None and (not rate_transaction_committed or quota_transaction_active) and not _rollback_succeeds(connection):
            raise HTTPException(status_code=503, detail="Serviciul este temporar indisponibil.") from error
        raise HTTPException(status_code=503, detail="Serviciul este temporar indisponibil.") from error
    except Exception as error:
        if connection is not None and (not rate_transaction_committed or quota_transaction_active) and not _rollback_succeeds(connection):
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
