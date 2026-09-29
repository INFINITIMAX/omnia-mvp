"""Teste sintetice pentru integrarea `RetrievalService` + `rewriter` (R30). Fără DB/rețea:
dependențele sunt fake-uri locale, distincte de cele din `test_retrieval_core.py` fiindcă au
nevoie să distingă rezultatele pe embedding (original vs. rescris), nu doar pe request."""

from retrieval_core import (
    ArticleParser,
    Evidence,
    RetrievalService,
    SEMANTIC_TOP_K,
)


ALIASES = {"doc-np010": ("NP010", "NP 010-2022")}
KNOWN = {"doc-np010": ("4.4.7.2",)}


def evidence(chunk_id, *, article="1.1", content_hash=None, score=0.9, document_id="doc-np010"):
    return Evidence(
        chunk_id, document_id, "NP TEST-2026", "Titlu sintetic", article,
        ArticleParser.normalize_article(article), "fragment sintetic",
        content_hash or f"hash-{chunk_id}", score, chunk_order=0,
    )


class RewriterFake:
    def __init__(self, rewritten=None):
        self._rewritten = rewritten
        self.calls = []

    def rewrite(self, question):
        self.calls.append(question)
        return question if self._rewritten is None else self._rewritten


class EmbedderFake:
    """Un vector distinct per apel, ca să distingem embedding-ul original de rescriere
    fără să depindem de textul trimis (rescrierea poate fi diferită de la caz la caz)."""

    def __init__(self):
        self.calls = 0

    def embed_query(self, _question):
        self.calls += 1
        return (float(self.calls),)


class SequencedRepositoryFake:
    """Întoarce rândurile pe rând, o listă per apel semantic (indiferent scoped/global),
    ca să simulăm rezultate diferite pentru embedding-ul original și cel rescris."""

    def __init__(self, semantic_sequence=(), exact=()):
        self._sequence = list(semantic_sequence)
        self._exact = exact
        self.exact_calls = 0
        self.global_calls = []
        self.scoped_calls = []

    def find_exact(self, document_id, article_normalized):
        self.exact_calls += 1
        return self._exact

    def find_semantic(self, embedding, top_k):
        self.global_calls.append((embedding, top_k))
        return self._sequence[len(self.global_calls) + len(self.scoped_calls) - 1]

    def find_semantic_in_documents(self, embedding, top_k, document_ids):
        self.scoped_calls.append((embedding, top_k, document_ids))
        return self._sequence[len(self.global_calls) + len(self.scoped_calls) - 1]


def service(repository, embedder, rewriter=None, **config):
    return RetrievalService(ArticleParser(ALIASES, KNOWN), repository, embedder, rewriter=rewriter, **config)


# --- Rute care nu ating deloc rescrierea -------------------------------------------------


def test_ruta_exacta_nu_apeleaza_rewriter_nici_embedder():
    repository = SequencedRepositoryFake(exact=[evidence(1, article="4.4.7.2")])
    embedder = EmbedderFake()
    rewriter = RewriterFake(rewritten="cu totul altă întrebare")

    result = service(repository, embedder, rewriter).retrieve("NP010, art. 4.4.7.2")

    assert result.status == "found"
    assert rewriter.calls == []
    assert embedder.calls == 0


def test_cod_de_normativ_necunoscut_d25_nu_apeleaza_rewriter_nici_embedder():
    repository = SequencedRepositoryFake()
    embedder = EmbedderFake()
    rewriter = RewriterFake(rewritten="rescriere care n-ar trebui văzută")

    result = service(repository, embedder, rewriter).retrieve("Ce prevede I 13-2015 la art. 5.12?")

    assert result.status == "ambiguous_reference"
    assert rewriter.calls == []
    assert embedder.calls == 0


# --- Ruta semantică: rescrierea adaugă un al doilea embedding, combinat pe scor maxim ------


def test_semantic_global_combina_cele_doua_embeddinguri_pe_scor_maxim_si_respecta_top_k():
    original = [evidence(1, article="1.1", content_hash="h1", score=0.70), evidence(2, article="2.2", content_hash="h2", score=0.60)]
    rewritten = [evidence(2, article="2.2", content_hash="h2", score=0.90), evidence(3, article="3.3", content_hash="h3", score=0.55)]
    repository = SequencedRepositoryFake(semantic_sequence=[original, rewritten])
    embedder = EmbedderFake()
    rewriter = RewriterFake(rewritten="întrebare rescrisă, diferită de original")

    result = service(repository, embedder, rewriter, semantic_top_k=2).retrieve("întrebare originală")

    assert result.status == "found"
    assert embedder.calls == 2  # un embedding pentru fiecare variantă a întrebării
    assert rewriter.calls == ["întrebare originală"]
    # chunk 2 apare în ambele liste: câștigă scorul mai mare (0.90, din rescriere);
    # chunk 3 e eliminat de `semantic_top_k=2`, nu de pragul minim de scor.
    assert [item.chunk_id for item in result.evidence] == [2, 1]
    assert [item.score for item in result.evidence] == [0.90, 0.70]


def test_rescriere_identica_dupa_normalizarea_spatiilor_ramane_pe_un_singur_embedding():
    repository = SequencedRepositoryFake(semantic_sequence=[[evidence(1, score=0.9)]])
    embedder = EmbedderFake()
    # Whitespace suplimentar, dar identic "din punct de vedere al conținutului" cu întrebarea.
    rewriter = RewriterFake(rewritten="  ce   spune   normativul  ")

    result = service(repository, embedder, rewriter).retrieve("ce spune normativul")

    assert result.status == "found"
    assert embedder.calls == 1
    assert rewriter.calls == ["ce spune normativul"]
    assert repository.global_calls == [((1.0,), SEMANTIC_TOP_K)]


def test_scope_d12_cu_rewriter_foloseste_document_ids_pentru_ambele_embeddinguri():
    original = [evidence(1, article="1.1", content_hash="h1", score=0.9)]
    rewritten = [evidence(2, article="2.2", content_hash="h2", score=0.95)]
    repository = SequencedRepositoryFake(semantic_sequence=[original, rewritten])
    embedder = EmbedderFake()
    rewriter = RewriterFake(rewritten="rescriere pentru scope")

    result = service(repository, embedder, rewriter).retrieve("Răspunde doar din NP010 despre traseu?")

    assert result.status == "found"
    assert repository.global_calls == []
    assert len(repository.scoped_calls) == 2
    assert all(document_ids == ("doc-np010",) for _embedding, _top_k, document_ids in repository.scoped_calls)
    assert [item.chunk_id for item in result.evidence] == [2, 1]


def test_fara_rewriter_ramane_un_singur_embedding_ca_inainte_de_r30():
    repository = SequencedRepositoryFake(semantic_sequence=[[evidence(1, score=0.9)]])
    embedder = EmbedderFake()

    result = service(repository, embedder, rewriter=None).retrieve("întrebare fără rescriere")

    assert result.status == "found"
    assert embedder.calls == 1
    assert repository.global_calls == [((1.0,), SEMANTIC_TOP_K)]
