"""API FastAPI pentru fluxul NormativAI mock-first, fără clienți externi la import."""

from __future__ import annotations

import os
from typing import Annotated, Callable, Literal, Protocol, Sequence

import psycopg2
from anthropic import Anthropic
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
import voyageai

from generation_core import GenerationService, GenerationValidationError, PublicCitation
from retrieval_core import (
    MAX_QUESTION_CHARS,
    PostgresApprovedCatalogRepository,
    PostgresRetrievalRepository,
    RetrievalService,
)


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
        if self._client is None:
            self._client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
        response = self._client.embed([question], model=self.model, input_type="query")
        return response.embeddings[0]


class AnthropicTextGenerator:
    """Adaptor lazy pentru Anthropic; clientul HTTP apare numai când există dovezi."""

    model = "claude-sonnet-4-6"

    def __init__(self, client: object | None = None) -> None:
        self._client = client

    def generate(self, prompt: str, *, max_tokens: int) -> str:
        if self._client is None:
            self._client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


def _open_db_connection() -> object:
    """Deschide conexiunea numai în timpul unei cereri, nu la import."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
    )


def get_connection_factory() -> Callable[[], object]:
    return _open_db_connection


def get_embedder() -> QueryEmbedder:
    return VoyageQueryEmbedder()


def get_text_generator() -> TextGenerator:
    return AnthropicTextGenerator()


app = FastAPI()


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
def intreaba(
    cerere: IntrebareRequest,
    connection_factory: Annotated[Callable[[], object], Depends(get_connection_factory)],
    embedder: Annotated[QueryEmbedder, Depends(get_embedder)],
    text_generator: Annotated[TextGenerator, Depends(get_text_generator)],
) -> IntreabaResponse:
    """Recuperează dovezi aprobate și generează cel mult un răspuns citat."""
    connection: object | None = None
    try:
        connection = connection_factory()
        parser = PostgresApprovedCatalogRepository(connection).load().create_parser()
        retrieval = RetrievalService(parser, PostgresRetrievalRepository(connection), embedder)
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

        generated = GenerationService(text_generator).generate(cerere.intrebare, result.evidence)
        return IntreabaResponse(
            status="answered",
            raspuns=generated.raspuns,
            citari=[CitationResponse.from_public(item) for item in generated.citari],
        )
    except GenerationValidationError as error:
        raise HTTPException(status_code=503, detail="Serviciul este temporar indisponibil.") from error
    except Exception as error:
        raise HTTPException(status_code=503, detail="Serviciul este temporar indisponibil.") from error
    finally:
        if connection is not None:
            connection.close()
