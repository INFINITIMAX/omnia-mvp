"""Contract mock-first pentru evaluatorul R18 (retrieval_eval), izolat de DB/rețea."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import retrieval_eval as evaluation
from retrieval_eval import GoldCase, GoldExpectation


REPO_ROOT = Path(__file__).resolve().parent.parent


def caz_valid(**overrides):
    valori = {
        "id": "C01",
        "tip": "exact",
        "intrebare": "Ce prevede art. 2.1 din P 118/1-2025?",
        "asteptat": [{"document_id": "p118_1_2025", "articol": "2.1"}],
    }
    valori.update(overrides)
    return valori


def scrie_set(tmp_path: Path, cazuri, versiune: int = 1) -> Path:
    cale = tmp_path / "set.json"
    cale.write_text(json.dumps({"versiune": versiune, "cazuri": cazuri}, ensure_ascii=False), encoding="utf-8")
    return cale


# --- 1. Validarea setului -----------------------------------------------------------


def test_set_minim_valid_este_acceptat(tmp_path):
    cale = scrie_set(tmp_path, [caz_valid()])
    cases = evaluation.load_gold_set(cale)
    assert len(cases) == 1
    assert cases[0].asteptat == (GoldExpectation("p118_1_2025", "2.1"),)


def test_set_negativ_valid_este_acceptat(tmp_path):
    cale = scrie_set(tmp_path, [caz_valid(id="N1", tip="negativ", asteptat=[])])
    cases = evaluation.load_gold_set(cale)
    assert cases[0].tip == "negativ"
    assert cases[0].asteptat == ()


@pytest.mark.parametrize(
    "cazuri",
    [
        [{"id": "C01", "tip": "exact", "intrebare": "x?"}],  # cheie lipsă (asteptat)
        [dict(caz_valid(), extra="nu")],  # cheie în plus
    ],
)
def test_chei_lipsa_sau_in_plus_resping_setul(tmp_path, cazuri):
    with pytest.raises(evaluation.RealEvaluationError, match="invalid_set"):
        evaluation.load_gold_set(scrie_set(tmp_path, cazuri))


def test_id_duplicat_respinge_setul(tmp_path):
    cazuri = [caz_valid(id="DUP"), caz_valid(id="DUP", intrebare="Altă întrebare, art. 3.1 din P 118/1-2025?")]
    with pytest.raises(evaluation.RealEvaluationError, match="invalid_set"):
        evaluation.load_gold_set(scrie_set(tmp_path, cazuri))


def test_tip_necunoscut_respinge_setul(tmp_path):
    with pytest.raises(evaluation.RealEvaluationError, match="invalid_set"):
        evaluation.load_gold_set(scrie_set(tmp_path, [caz_valid(tip="altceva")]))


def test_peste_30_de_cazuri_respinge_setul(tmp_path):
    cazuri = [caz_valid(id=f"C{index:02d}") for index in range(31)]
    with pytest.raises(evaluation.RealEvaluationError, match="invalid_set"):
        evaluation.load_gold_set(scrie_set(tmp_path, cazuri))


def test_exact_30_de_cazuri_este_acceptat(tmp_path):
    cazuri = [caz_valid(id=f"C{index:02d}") for index in range(30)]
    cases = evaluation.load_gold_set(scrie_set(tmp_path, cazuri))
    assert len(cases) == 30


def test_asteptat_gol_la_non_negativ_respinge_setul(tmp_path):
    with pytest.raises(evaluation.RealEvaluationError, match="invalid_set"):
        evaluation.load_gold_set(scrie_set(tmp_path, [caz_valid(asteptat=[])]))


def test_asteptat_nevid_la_negativ_respinge_setul(tmp_path):
    cazuri = [caz_valid(id="N1", tip="negativ", asteptat=[{"document_id": "p118_1_2025", "articol": "2.1"}])]
    with pytest.raises(evaluation.RealEvaluationError, match="invalid_set"):
        evaluation.load_gold_set(scrie_set(tmp_path, cazuri))


def test_articol_invalid_respinge_setul(tmp_path):
    cazuri = [caz_valid(asteptat=[{"document_id": "p118_1_2025", "articol": "!!invalid!!"}])]
    with pytest.raises(evaluation.RealEvaluationError, match="invalid_set"):
        evaluation.load_gold_set(scrie_set(tmp_path, cazuri))


def test_setul_real_set_aur_trece_validarea():
    cases = evaluation.load_gold_set(REPO_ROOT / "evaluare" / "set_aur.json")
    assert 1 <= len(cases) <= evaluation.MAX_CASES
    assert len({case.id for case in cases}) == len(cases)


def test_fara_run_nu_construieste_nicio_conexiune_sau_embedder(tmp_path, monkeypatch):
    cale = scrie_set(tmp_path, [caz_valid()])

    def _pica(*_args, **_kwargs):
        raise AssertionError("nu ar trebui apelat fără --run")

    monkeypatch.setattr(evaluation, "_open_db_connection", _pica)
    monkeypatch.setattr(evaluation, "_build_runtime_embedder", _pica)

    assert evaluation.main(["--set", str(cale)]) == 0


# --- Fixtures pentru run_evaluation izolat de Postgres/Voyage -----------------------


class ConnectionFake:
    def __init__(self):
        self.sessions = []
        self.rollbacks = 0
        self.closes = 0

    def set_session(self, **kwargs):
        self.sessions.append(kwargs)

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closes += 1


class CatalogFake:
    def __init__(self, _connection):
        pass

    def load(self):
        return SimpleNamespace(create_parser=lambda: "parser-fake")


class RepositoryFake:
    def __init__(self, _connection):
        pass


def make_evidence(document_id="p118_1_2025", articol_normalizat="2.3.2.1.2", content="text normativ secret"):
    return evaluation.Evidence(
        chunk_id=1,
        document_id=document_id,
        cod_document="P 118/1-2025",
        titlu_document="Titlu",
        articol="2.3.2.1.2",
        articol_normalizat=articol_normalizat,
        content=content,
        content_hash="hash",
    )


def install_fakes(monkeypatch, results: dict[str, object], calls: list[str] | None = None):
    """Înlocuiește Postgres*/RetrievalService cu fake-uri controlate; embedder rămâne separat."""

    class RetrievalServiceFake:
        def __init__(self, parser, repository, embedder):
            self.parser = parser
            self.repository = repository
            self.embedder = embedder

        def retrieve(self, question):
            if calls is not None:
                calls.append(question)
            outcome = results[question]
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    monkeypatch.setattr(evaluation, "PostgresApprovedCatalogRepository", CatalogFake)
    monkeypatch.setattr(evaluation, "PostgresRetrievalRepository", RepositoryFake)
    monkeypatch.setattr(evaluation, "RetrievalService", RetrievalServiceFake)


class EmbedderDelegateFake:
    def __init__(self):
        self.calls = 0

    def embed_query(self, _question):
        self.calls += 1
        return (0.1, 0.2)


# --- 2. Potrivirea --------------------------------------------------------------------


def test_articol_exact_este_gasit_cu_rangul_corect():
    case = GoldCase(
        "C1", "exact", "întrebare?", (GoldExpectation("doc_a", "2.3.2.1.2"),)
    )
    evidence = (
        make_evidence(document_id="doc_a", articol_normalizat="9.9.9"),
        make_evidence(document_id="doc_a", articol_normalizat="2.3.2.1.2"),
    )
    gasit, rang, dovezi = evaluation._score(case, evidence)
    assert gasit is True
    assert rang == 2
    assert dovezi == [
        {"document_id": "doc_a", "articol_normalizat": "9.9.9"},
        {"document_id": "doc_a", "articol_normalizat": "2.3.2.1.2"},
    ]


@pytest.mark.parametrize("articol_copil", ["2.3.2.1.2.(1)", "2.3.2.1.2.1"])
def test_copil_direct_al_articolului_asteptat_este_gasit(articol_copil):
    case = GoldCase("C1", "exact", "?", (GoldExpectation("doc_a", "2.3.2.1.2"),))
    evidence = (make_evidence(document_id="doc_a", articol_normalizat=articol_copil),)
    gasit, rang, _ = evaluation._score(case, evidence)
    assert (gasit, rang) == (True, 1)


def test_copil_al_altui_articol_din_set_este_gasit():
    case = GoldCase("C1", "exact", "?", (GoldExpectation("doc_a", "4.2.4.3"),))
    evidence = (make_evidence(document_id="doc_a", articol_normalizat="4.2.4.3.(4)"),)
    gasit, rang, _ = evaluation._score(case, evidence)
    assert (gasit, rang) == (True, 1)


def test_prefix_fara_separator_nu_este_gasit():
    case = GoldCase("C1", "exact", "?", (GoldExpectation("doc_a", "4.4.11"),))
    evidence = (make_evidence(document_id="doc_a", articol_normalizat="4.4.1"),)
    gasit, rang, _ = evaluation._score(case, evidence)
    assert (gasit, rang) == (False, None)


def test_alt_document_cu_acelasi_articol_nu_este_gasit():
    case = GoldCase("C1", "exact", "?", (GoldExpectation("doc_a", "2.3.2.1.2"),))
    evidence = (make_evidence(document_id="doc_b", articol_normalizat="2.3.2.1.2"),)
    gasit, rang, _ = evaluation._score(case, evidence)
    assert (gasit, rang) == (False, None)


# --- 3. Negative -----------------------------------------------------------------------


@pytest.mark.parametrize("status", ["not_found", "ambiguous_reference", "ambiguous_article", "out_of_scope"])
def test_negativ_corect_pentru_statusuri_de_refuz(status):
    case = GoldCase("N1", "negativ", "?", ())
    assert evaluation._is_correct(case, status, gasit=False) is True


def test_negativ_gresit_daca_statusul_este_found():
    case = GoldCase("N1", "negativ", "?", ())
    assert evaluation._is_correct(case, "found", gasit=False) is False


def test_negativ_cu_ambiguous_article_este_tratat_ca_refuz_corect():
    """`ambiguous_article` e un status de refuz legitim (vezi `RetrievalResult.status` din
    retrieval_core), inclus explicit în `_REFUSAL_STATUSES`: un caz negativ care produce
    `ambiguous_article` trebuie marcat corect, la fel ca `not_found`/`ambiguous_reference`/
    `out_of_scope`."""
    case = GoldCase("N1", "negativ", "?", ())
    assert evaluation._is_correct(case, "ambiguous_article", gasit=False) is True


def test_pozitiv_gasit_si_status_found_este_corect():
    case = GoldCase("C1", "exact", "?", (GoldExpectation("doc_a", "2.1"),))
    assert evaluation._is_correct(case, "found", gasit=True) is True


def test_pozitiv_status_found_dar_negasit_este_gresit():
    case = GoldCase("C1", "exact", "?", (GoldExpectation("doc_a", "2.1"),))
    assert evaluation._is_correct(case, "found", gasit=False) is False


# --- 4. Poarta anti-calcul -------------------------------------------------------------


def test_poarta_anti_calcul_evita_embeddingul_si_cautarea(monkeypatch, tmp_path):
    intrebare_calcul = "Calculează debitul de aer proaspăt necesar pentru o sală de clasă de 60 m²."
    case = GoldCase("N1", "negativ", intrebare_calcul, ())
    apeluri: list[str] = []
    install_fakes(monkeypatch, results={}, calls=apeluri)
    embedder_delegate = EmbedderDelegateFake()

    report = evaluation.run_evaluation(
        [case], tmp_path / "raport.json",
        connection_factory=ConnectionFake,
        embedder_factory=lambda: embedder_delegate,
    )

    assert apeluri == []  # retrieval.retrieve nu a fost apelat deloc
    assert embedder_delegate.calls == 0
    assert report["cazuri"][0]["status"] == "out_of_scope"
    assert report["cazuri"][0]["gasit"] is False
    assert report["cazuri"][0]["rang"] is None
    assert report["sumar"]["corecte"] == 1  # negativ + out_of_scope => corect


# --- 5. Sumar ----------------------------------------------------------------------------


def _evaluat(case_id, tip, corect, rang, document_id="doc_a"):
    case = GoldCase(case_id, tip, "?", () if tip == "negativ" else (GoldExpectation(document_id, "1.1"),))
    return {"case": case, "status": "x", "gasit": rang is not None, "rang": rang, "corect": corect}


def test_sumar_calculeaza_acuratete_pe_tip_si_pe_document_si_recall():
    evaluated = [
        _evaluat("E1", "exact", True, 1, document_id="doc_a"),
        _evaluat("E2", "exact", False, None, document_id="doc_a"),
        _evaluat("S1", "semantic", True, 3, document_id="doc_b"),
        _evaluat("S2", "semantic", True, 6, document_id="doc_b"),
        _evaluat("N1", "negativ", True, None),
    ]

    sumar = evaluation._build_summary(evaluated, embedding_calls=4)

    assert sumar["total"] == 5
    assert sumar["corecte"] == 4
    assert sumar["acuratete_totala"] == pytest.approx(4 / 5)
    assert sumar["pe_tip"]["exact"] == {"total": 2, "corecte": 1, "acuratete": pytest.approx(0.5)}
    assert sumar["pe_tip"]["semantic"] == {"total": 2, "corecte": 2, "acuratete": pytest.approx(1.0)}
    assert sumar["pe_tip"]["negativ"] == {"total": 1, "corecte": 1, "acuratete": pytest.approx(1.0)}
    assert sumar["pe_document"]["doc_a"]["total"] == 2
    assert sumar["pe_document"]["doc_a"]["corecte"] == 1
    assert sumar["pe_document"]["doc_b"] == {"total": 2, "corecte": 2, "acuratete": pytest.approx(1.0)}
    # recall@1 și recall@5 se calculează doar pe cazurile pozitive (exact+semantic = 4 din 5)
    assert sumar["recall_at_1"] == pytest.approx(1 / 4)  # doar E1 are rang 1
    assert sumar["recall_at_5"] == pytest.approx(2 / 4)  # E1 (rang 1) și S1 (rang 3) <= 5; S2 (rang 6) nu
    assert sumar["embedding_calls"] == 4


def test_plafonul_de_embeddinguri_blocheaza_al_treizecisiunulea_apel():
    class DelegateOk:
        def embed_query(self, question):
            return (0.1,)

    counting = evaluation._CountingEmbedder(DelegateOk(), evaluation.MAX_EMBEDDING_CALLS)
    for _ in range(evaluation.MAX_EMBEDDING_CALLS):
        counting.embed_query("întrebare")
    with pytest.raises(evaluation.RealEvaluationError, match="cost_limit"):
        counting.embed_query("întrebare de peste plafon")
    assert counting.calls == evaluation.MAX_EMBEDDING_CALLS


def test_eroare_de_provider_opreste_rularea_cu_cod_stabil_si_face_rollback(monkeypatch, tmp_path):
    case1 = GoldCase("C1", "exact", "prima?", (GoldExpectation("doc_a", "1.1"),))
    case2 = GoldCase("C2", "exact", "a_doua?", (GoldExpectation("doc_a", "1.1"),))
    connection = ConnectionFake()
    apeluri: list[str] = []
    install_fakes(
        monkeypatch,
        results={"prima?": RuntimeError("Voyage indisponibil"), "a_doua?": SimpleNamespace(status="found", evidence=())},
        calls=apeluri,
    )

    with pytest.raises(evaluation.RealEvaluationError, match="case_failed:C1:execution_error"):
        evaluation.run_evaluation(
            [case1, case2], tmp_path / "raport.json",
            connection_factory=lambda: connection,
            embedder_factory=EmbedderDelegateFake,
        )

    assert apeluri == ["prima?"]  # nu s-a mai încercat al doilea caz
    assert connection.rollbacks == connection.closes == 1
    assert not (tmp_path / "raport.json").exists()


def test_iesirea_stdout_este_ascii_inclusiv_cand_sumarul_contine_diacritice(monkeypatch, tmp_path, capsys):
    # document_id cu diacritice ajunge ca litera în cheile `pe_document` din sumar;
    # dacă cineva schimbă `ensure_ascii=True` în `False` la print(), acest test pică
    # pentru că litera brută "ă" ar apărea în stdout în loc de forma escapată ă.
    cale_set = scrie_set(tmp_path, [caz_valid(asteptat=[{"document_id": "docă", "articol": "2.1"}])])
    install_fakes(
        monkeypatch,
        results={
            caz_valid()["intrebare"]: SimpleNamespace(
                status="found", evidence=(make_evidence(document_id="docă", articol_normalizat="2.1"),)
            )
        },
    )
    monkeypatch.setattr(evaluation, "_open_db_connection", ConnectionFake)
    monkeypatch.setattr(evaluation, "_build_runtime_embedder", EmbedderDelegateFake)
    raport_path = tmp_path / "raport.json"

    exit_code = evaluation.main(["--set", str(cale_set), "--run", "--raport", str(raport_path)])

    assert exit_code == 0
    stdout = capsys.readouterr().out
    stdout.encode("ascii")  # nu ridică UnicodeEncodeError dacă e strict ASCII
    assert "ă" not in stdout
    assert "\\u0103" in stdout  # "ă" escapat, dovadă că ensure_ascii=True e activ


# --- 6. Raportul nu conține text normativ -----------------------------------------------


def test_raportul_nu_publica_textul_normativ_al_dovezilor(monkeypatch, tmp_path):
    case = GoldCase("C1", "exact", "întrebare?", (GoldExpectation("doc_a", "2.1"),))
    evidenta_secreta = make_evidence(document_id="doc_a", articol_normalizat="2.1", content="TEXT NORMATIV NEPUBLICABIL")
    install_fakes(monkeypatch, results={"întrebare?": SimpleNamespace(status="found", evidence=(evidenta_secreta,))})

    report = evaluation.run_evaluation(
        [case], tmp_path / "raport.json",
        connection_factory=ConnectionFake,
        embedder_factory=EmbedderDelegateFake,
    )

    serialized = json.dumps(report, ensure_ascii=False)
    assert "TEXT NORMATIV NEPUBLICABIL" not in serialized
    assert report["cazuri"][0]["dovezi"] == [{"document_id": "doc_a", "articol_normalizat": "2.1"}]
