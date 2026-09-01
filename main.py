"""API FastAPI pentru fluxul NormativAI mock-first, fără clienți externi la import."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Annotated, Callable, Literal, Protocol, Sequence

import psycopg2
from anthropic import Anthropic, AnthropicError
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
import voyageai
from voyageai.error import VoyageError

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
class RuntimeDependencies:
    """Fabrici injectabile; endpointul le apelează numai după validarea corpului."""

    connection_factory: Callable[[], object]
    embedder_factory: Callable[[], QueryEmbedder]
    text_generator_factory: Callable[[], TextGenerator]


app = FastAPI()
app.state.runtime_dependencies = RuntimeDependencies(
    connection_factory=_open_db_connection,
    embedder_factory=VoyageQueryEmbedder,
    text_generator_factory=AnthropicTextGenerator,
)


@app.get("/")
def pagina_principala() -> FileResponse:
    return FileResponse("static/index.html")


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


_NOT_FOUND = "Nu am găsit această informație în documentele aprobate."
_AMBIGUOUS_ARTICLE = "Am găsit versiuni neconcordante ale articolului solicitat."
_AMBIGUOUS_REFERENCE = "Întrebarea conține referințe ambigue; te rog precizează documentul sau articolul."


@app.post("/intreaba", response_model=IntreabaResponse)
def intreaba(cerere: IntrebareRequest) -> IntreabaResponse:
    """Recuperează dovezi aprobate și generează cel mult un răspuns citat."""
    connection: object | None = None
    try:
        dependencies: RuntimeDependencies = app.state.runtime_dependencies
        connection = dependencies.connection_factory()
        parser = PostgresApprovedCatalogRepository(connection).load().create_parser()
        retrieval = RetrievalService(
            parser,
            PostgresRetrievalRepository(connection),
            dependencies.embedder_factory(),
        )
        result = retrieval.retrieve(cerere.intrebare)

        if result.status == "not_found":
            return IntreabaResponse(status="not_found", raspuns=_NOT_FOUND, citari=[])
        if result.status == "ambiguous_article":
            return IntreabaResponse(
                status="ambiguous_article", raspuns=_AMBIGUOUS_ARTICLE, citari=[]
            )
        if result.status == "ambiguous_reference":
            return IntreabaResponse(
                status="ambiguous_reference", raspuns=_AMBIGUOUS_REFERENCE, citari=[]
            )

        generated = GenerationService(dependencies.text_generator_factory()).generate(
            cerere.intrebare, result.evidence
        )
        return IntreabaResponse(
            status="answered",
            raspuns=generated.raspuns,
            citari=[CitationResponse.from_public(item) for item in generated.citari],
        )
    except (GenerationValidationError, ServiceDependencyError, psycopg2.Error) as error:
        raise HTTPException(status_code=503, detail="Serviciul este temporar indisponibil.") from error
    finally:
        if connection is not None:
            try:
                connection.close()
            except psycopg2.Error as error:
                raise HTTPException(
                    status_code=503, detail="Serviciul este temporar indisponibil."
                ) from error
