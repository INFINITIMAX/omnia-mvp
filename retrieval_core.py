"""Nucleul testabil de recuperare pentru NormativAI, fără clienți externi concreți."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Literal, Mapping, Protocol, Sequence

MAX_QUESTION_CHARS = 1000
SEMANTIC_TOP_K = 5
SEMANTIC_MIN_SCORE = 0.50
MAX_CONTEXT_CHARS = 12000

_ARTICLE_NORMALIZED = re.compile(r"^[a-z0-9().-]+$")
_ARTICLE_PART = r"(?:[0-9a-z]+|\(\s*[0-9a-z]+\s*\))"
_ARTICLE_MARKER = re.compile(
    r"\b(?:articolul|art\.)\s*"
    rf"([0-9]+(?:\s*\.\s*{_ARTICLE_PART})*\s*\.?)",
    re.IGNORECASE,
)
_UNMARKED_ARTICLE = re.compile(
    rf"(?<![0-9a-z.])([0-9]+(?:\s*\.\s*{_ARTICLE_PART}){{2,}}\s*\.?)(?![0-9a-z.])",
    re.IGNORECASE,
)
_ANNEX_REFERENCE = re.compile(
    r"\banexa\s*([0-9]+(?:\s*\.\s*[0-9]+)*\s*\.?)", re.IGNORECASE
)
_WHITESPACE = re.compile(r"[ \t\n\r\f\v\u00a0\u202f]+")
_ALIAS_CHARACTERS = re.compile(r"[^a-z0-9]+")
_ALIAS_PARTS = re.compile(r"[a-z]+|[0-9]+")
_ALIAS_SEPARATOR = r"[ \t\n\r\f\v\u00a0\u202f-]*"


@dataclass(frozen=True)
class ParsedReference:
    """Referința sigură extrasă din întrebare; articolul marcat e explicit."""

    document_id: str | None
    article_normalized: str | None
    has_explicit_article: bool
    requires_clarification: bool = False


@dataclass(frozen=True)
class Evidence:
    """Dovada internă permisă mai departe către etapa de generare."""

    chunk_id: int
    document_id: str
    cod_document: str
    titlu_document: str
    articol: str
    articol_normalizat: str
    content: str
    content_hash: str
    score: float | None = None


@dataclass(frozen=True)
class RetrievalResult:
    """Rezultatul tipat al recuperării; erorile infrastructurii se propagă."""

    status: Literal["found", "not_found", "ambiguous_article", "ambiguous_reference"]
    evidence: tuple[Evidence, ...]


class Embedder(Protocol):
    """Contract injectabil; implementarea Voyage rămâne în afara acestui modul."""

    def embed_query(self, question: str) -> Sequence[float]: ...


class ArticleParser:
    """Parsează coduri injectate din metadata și articole fără a ghici numerele."""

    def __init__(
        self,
        document_aliases: Mapping[str, Sequence[str]],
        known_articles: Mapping[str, Sequence[str]] | None = None,
    ) -> None:
        self._alias_patterns = tuple(
            (self._compile_document_alias(alias), document_id)
            for document_id, aliases in document_aliases.items()
            for alias in aliases
        )
        self._known_articles = {
            document_id: frozenset(self.normalize_article(article) for article in articles)
            for document_id, articles in (known_articles or {}).items()
        }

    @staticmethod
    def normalize_article(value: str) -> str:
        """Aplică exact contractul DB: whitespace eliminat, lowercase, puncte finale."""
        if not isinstance(value, str):
            raise ValueError("articolul trebuie să fie text")
        normalized = _WHITESPACE.sub("", value).lower().rstrip(".")
        if not normalized or not _ARTICLE_NORMALIZED.fullmatch(normalized):
            raise ValueError("articolul normalizat trebuie să respecte [a-z0-9().-]+")
        return normalized

    @staticmethod
    def normalize_document_alias(value: str) -> str:
        """Face codurile oficiale comparabile indiferent de spații și cratime."""
        if not isinstance(value, str):
            raise ValueError("aliasul documentului trebuie să fie text")
        normalized = _ALIAS_CHARACTERS.sub("", value.lower())
        if not normalized:
            raise ValueError("aliasul documentului nu poate fi gol")
        return normalized

    @staticmethod
    def _compile_document_alias(value: str) -> re.Pattern[str]:
        ArticleParser.normalize_document_alias(value)
        parts = _ALIAS_PARTS.findall(value.lower())
        pattern = _ALIAS_SEPARATOR.join(re.escape(part) for part in parts)
        return re.compile(rf"(?<![a-z0-9]){pattern}(?![a-z0-9])", re.IGNORECASE)

    def parse(self, question: str) -> ParsedReference:
        """Acceptă un articol doar cu marker sau, fără marker, doar din catalogul injectat."""
        if not isinstance(question, str):
            raise ValueError("întrebarea trebuie să fie text")
        document_ids = self._find_documents(question)
        if len(document_ids) > 1:
            return ParsedReference(None, None, False, requires_clarification=True)
        document_id = next(iter(document_ids), None)
        marked = [
            self.normalize_article(match.group(1))
            for match in _ARTICLE_MARKER.finditer(question)
        ]
        annexes = [
            self.normalize_article("anexa " + match.group(1))
            for match in _ANNEX_REFERENCE.finditer(question)
        ]
        explicit_articles = marked + annexes
        if len(set(explicit_articles)) > 1:
            return ParsedReference(document_id, None, False, requires_clarification=True)
        if explicit_articles:
            return ParsedReference(document_id, explicit_articles[0], True)

        candidates = [
            self.normalize_article(match.group(1))
            for match in _UNMARKED_ARTICLE.finditer(question)
            if self._is_known_article(self.normalize_article(match.group(1)), document_id)
        ]
        if len(set(candidates)) > 1:
            return ParsedReference(document_id, None, False, requires_clarification=True)
        if candidates:
            return ParsedReference(document_id, candidates[0], False)
        return ParsedReference(document_id, None, False)

    def _find_documents(self, question: str) -> frozenset[str]:
        return frozenset(
            document_id
            for pattern, document_id in self._alias_patterns
            if pattern.search(question)
        )

    def _is_known_article(self, article: str, document_id: str | None) -> bool:
        if document_id is not None:
            return article in self._known_articles.get(document_id, frozenset())
        return any(article in articles for articles in self._known_articles.values())


@dataclass(frozen=True)
class ApprovedDocumentCatalog:
    """Metadata internă minimă pentru parser, fără chei de sursă sau text brut."""

    document_aliases: Mapping[str, Sequence[str]]
    known_articles: Mapping[str, Sequence[str]]

    def create_parser(self) -> ArticleParser:
        return ArticleParser(self.document_aliases, self.known_articles)


class PostgresApprovedCatalogRepository:
    """Citește numai codurile oficiale și articolele documentelor aprobate."""

    _SQL = """
        SELECT document.document_id, document.cod_oficial, chunk.articol_normalizat
        FROM public.documente AS document
        JOIN public.documente_chunks AS chunk ON chunk.document_id = document.document_id
        WHERE document.status = %s
        ORDER BY document.document_id, chunk.articol_normalizat
    """

    def __init__(self, connection: object) -> None:
        self._connection = connection

    def load(self) -> ApprovedDocumentCatalog:
        cursor = self._connection.cursor()
        try:
            cursor.execute(self._SQL, ("approved",))
            aliases: dict[str, tuple[str, ...]] = {}
            articles: dict[str, list[str]] = {}
            for document_id, cod_oficial, articol_normalizat in cursor.fetchall():
                document = str(document_id)
                aliases.setdefault(document, self._official_code_aliases(str(cod_oficial)))
                articles.setdefault(document, []).append(str(articol_normalizat))
            return ApprovedDocumentCatalog(aliases, articles)
        finally:
            cursor.close()

    @staticmethod
    def _official_code_aliases(cod_oficial: str) -> tuple[str, ...]:
        """Derivă doar variante de separare și abrevierea fără anul final al codului oficial."""
        parts = _ALIAS_PARTS.findall(cod_oficial.lower())
        compact = "".join(parts)
        aliases = [cod_oficial, compact]
        if len(parts) > 1 and len(parts[-1]) == 4 and parts[-1].isdigit():
            aliases.append("".join(parts[:-1]))
        return tuple(dict.fromkeys(aliases))


class PostgresRetrievalRepository:
    """Repository PostgreSQL: toate valorile variabile sunt parametri DB-API."""

    _SELECT_FIELDS = """
        chunk.id, chunk.document_id, document.cod_oficial, document.titlu_oficial,
        chunk.articol, chunk.articol_normalizat, chunk.text, chunk.content_hash
    """
    _FROM_DOCUMENTS = """
        FROM public.documente_chunks AS chunk
        JOIN public.documente AS document ON document.document_id = chunk.document_id
    """

    def __init__(self, connection: object) -> None:
        self._connection = connection

    def find_exact(self, document_id: str | None, article_normalized: str) -> list[Evidence]:
        if document_id is None:
            sql = (
                "SELECT " + self._SELECT_FIELDS + self._FROM_DOCUMENTS
                + " WHERE document.status = 'approved' AND chunk.articol_normalizat = %s"
                + " ORDER BY chunk.document_id, chunk.chunk_order, chunk.id"
            )
            parameters = (article_normalized,)
        else:
            sql = (
                "SELECT " + self._SELECT_FIELDS + self._FROM_DOCUMENTS
                + " WHERE document.status = 'approved' AND chunk.document_id = %s AND chunk.articol_normalizat = %s"
                + " ORDER BY chunk.chunk_order, chunk.id"
            )
            parameters = (document_id, article_normalized)
        cursor = self._connection.cursor()
        try:
            cursor.execute(sql, parameters)
            return [self._evidence_from_row(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def find_semantic(self, embedding: Sequence[float], top_k: int) -> list[Evidence]:
        self._require_positive_integer(top_k, "top_k")
        vector = self._vector_literal(embedding)
        sql = "SELECT " + self._SELECT_FIELDS + """
            , 1 - (chunk.embedding <=> %s::vector) AS score
        """ + self._FROM_DOCUMENTS + """
            WHERE document.status = 'approved' AND chunk.embedding IS NOT NULL
            ORDER BY chunk.embedding <=> %s::vector
            LIMIT %s
        """
        cursor = self._connection.cursor()
        try:
            cursor.execute(sql, (vector, vector, top_k))
            return [self._evidence_from_row(row, score=row[8]) for row in cursor.fetchall()]
        finally:
            cursor.close()

    @staticmethod
    def _require_positive_integer(value: object, name: str) -> int:
        if type(value) is not int or value <= 0:
            raise ValueError(f"{name} trebuie să fie întreg pozitiv")
        return value

    @staticmethod
    def _vector_literal(embedding: Sequence[float]) -> str:
        if not embedding:
            raise ValueError("embedding-ul nu poate fi gol")
        try:
            values = [float(value) for value in embedding]
        except (TypeError, ValueError) as error:
            raise ValueError("embedding invalid") from error
        if not all(math.isfinite(value) for value in values):
            raise ValueError("embedding-ul trebuie să conțină numai valori finite")
        return "[" + ",".join(str(value) for value in values) + "]"

    @staticmethod
    def _evidence_from_row(row: Sequence[object], score: object | None = None) -> Evidence:
        return Evidence(
            chunk_id=int(row[0]), document_id=str(row[1]), cod_document=str(row[2]),
            titlu_document=str(row[3]), articol=str(row[4]), articol_normalizat=str(row[5]),
            content=str(row[6]), content_hash=str(row[7]),
            score=None if score is None else float(score),
        )


class RetrievalService:
    """Alege exact sau semantic, apoi aplică deduplicarea și limita de context."""

    def __init__(
        self,
        parser: ArticleParser,
        repository: PostgresRetrievalRepository,
        embedder: Embedder,
        *,
        semantic_top_k: int = SEMANTIC_TOP_K,
        semantic_min_score: float = SEMANTIC_MIN_SCORE,
        max_context_chars: int = MAX_CONTEXT_CHARS,
    ) -> None:
        self._parser = parser
        self._repository = repository
        self._embedder = embedder
        self._semantic_top_k = PostgresRetrievalRepository._require_positive_integer(
            semantic_top_k, "semantic_top_k"
        )
        if not isinstance(semantic_min_score, (int, float)) or not math.isfinite(semantic_min_score):
            raise ValueError("semantic_min_score trebuie să fie un număr finit")
        self._semantic_min_score = float(semantic_min_score)
        self._max_context_chars = PostgresRetrievalRepository._require_positive_integer(
            max_context_chars, "max_context_chars"
        )

    def retrieve(self, question: str) -> RetrievalResult:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("întrebarea trebuie să fie text nevid")
        if len(question) > MAX_QUESTION_CHARS:
            raise ValueError("întrebarea depășește limita permisă")

        reference = self._parser.parse(question)
        if reference.requires_clarification:
            return RetrievalResult("ambiguous_reference", ())
        if reference.article_normalized is not None:
            exact = self._repository.find_exact(reference.document_id, reference.article_normalized)
            if self._has_ambiguous_article(exact):
                return RetrievalResult("ambiguous_article", ())
            evidence = self._limit_context(self._deduplicate(exact, preserve_documents=True))
            return RetrievalResult("found", evidence) if evidence else RetrievalResult("not_found", ())

        semantic = self._repository.find_semantic(self._embedder.embed_query(question), self._semantic_top_k)
        accepted = [item for item in semantic if item.score is not None and item.score >= self._semantic_min_score]
        if self._has_ambiguous_article(accepted):
            return RetrievalResult("ambiguous_article", ())
        evidence = self._limit_context(self._deduplicate(accepted))
        return RetrievalResult("found", evidence) if evidence else RetrievalResult("not_found", ())

    @staticmethod
    def _has_ambiguous_article(evidence: Sequence[Evidence]) -> bool:
        hashes_by_article: dict[tuple[str, str], set[str]] = {}
        for item in evidence:
            hashes_by_article.setdefault((item.document_id, item.articol_normalizat), set()).add(item.content_hash)
        return any(len(hashes) > 1 for hashes in hashes_by_article.values())

    @staticmethod
    def _deduplicate(
        evidence: Sequence[Evidence], *, preserve_documents: bool = False
    ) -> tuple[Evidence, ...]:
        unique: dict[str | tuple[str, str], Evidence] = {}
        for item in evidence:
            key: str | tuple[str, str] = (
                (item.document_id, item.content_hash) if preserve_documents else item.content_hash
            )
            unique.setdefault(key, item)
        return tuple(unique.values())

    def _limit_context(self, evidence: Sequence[Evidence]) -> tuple[Evidence, ...]:
        selected: list[Evidence] = []
        used_chars = 0
        for item in evidence:
            if used_chars + len(item.content) > self._max_context_chars:
                break
            selected.append(item)
            used_chars += len(item.content)
        return tuple(selected)
