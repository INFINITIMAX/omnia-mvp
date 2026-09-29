"""Contract mock-first pentru evaluatorul R18 (retrieval_eval), izolat de DB/rețea."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import retrieval_eval as evaluation
from retrieval_eval import GoldCase, GoldExpectation
from generation_core import MissingCitationError, PublicCitation, UngroundedReferenceError


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


def test_peste_36_de_cazuri_respinge_setul(tmp_path):
    cazuri = [caz_valid(id=f"C{index:02d}") for index in range(37)]
    with pytest.raises(evaluation.RealEvaluationError, match="invalid_set"):
        evaluation.load_gold_set(scrie_set(tmp_path, cazuri))


def test_exact_36_de_cazuri_este_acceptat(tmp_path):
    cazuri = [caz_valid(id=f"C{index:02d}") for index in range(36)]
    cases = evaluation.load_gold_set(scrie_set(tmp_path, cazuri))
    assert len(cases) == 36


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


# --- 7. Generare (R23) -------------------------------------------------------------------


def test_generare_fara_run_respinge_cu_exit_2_fara_niciun_apel(tmp_path, capsys, monkeypatch):
    cale = scrie_set(tmp_path, [caz_valid()])

    def _pica(*_args, **_kwargs):
        raise AssertionError("nu ar trebui apelat fără --run")

    monkeypatch.setattr(evaluation, "_open_db_connection", _pica)
    monkeypatch.setattr(evaluation, "_build_runtime_embedder", _pica)
    monkeypatch.setattr(evaluation, "_build_production_generator", _pica)

    exit_code = evaluation.main(["--set", str(cale), "--generare"])

    assert exit_code == 2
    assert "generare_requires_run" in capsys.readouterr().err


def test_fara_generare_nu_construieste_generator_si_raportul_ramane_neschimbat(monkeypatch, tmp_path):
    evidence = (make_evidence(document_id="doc_a", articol_normalizat="2.1"),)
    case = GoldCase("C1", "exact", "întrebare?", (GoldExpectation("doc_a", "2.1"),))
    install_fakes(monkeypatch, results={"întrebare?": SimpleNamespace(status="found", evidence=evidence)})

    def _pica():
        raise AssertionError("generator_factory nu trebuie apelat fără generation=True")

    report = evaluation.run_evaluation(
        [case], tmp_path / "raport.json",
        connection_factory=ConnectionFake,
        embedder_factory=EmbedderDelegateFake,
        generation=False,
        generator_factory=_pica,
    )

    assert "generare" not in report["sumar"]
    assert "generation_calls" not in report["sumar"]
    assert set(report["cazuri"][0]) == {"id", "tip", "status", "gasit", "rang", "dovezi"}


class _GenerationServiceStub:
    """Nivelul înalt (`GenerationService.generate`) izolat, pentru testarea directă a `_run_generation`."""

    def __init__(self, outcome):
        self._outcome = outcome

    def generate(self, _question, _evidence):
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome


def _generated(raspuns, citari=()):
    return SimpleNamespace(raspuns=raspuns, citari=citari)


def test_run_generation_raspuns_normal_devine_raspuns_cu_metrici_corecte():
    case = GoldCase("C1", "exact", "?", (GoldExpectation("doc_a", "2.1"),))
    evidence = (make_evidence(document_id="doc_a", articol_normalizat="2.1", content="Textul complet al art 2.1."),)
    citare = PublicCitation(id="C1", cod_document="X", titlu_document="Y", articol="2.1", citat="Textul complet al art 2.1.")
    service = _GenerationServiceStub(_generated("Răspuns [C1].", (citare,)))

    info = evaluation._run_generation(case, evidence, service)

    assert info["rezultat_final"] == "raspuns"
    assert info["citeaza_asteptat"] is True
    assert info["citate_literale"] is True
    assert info["vizibil_utilizator"] is None


def test_run_generation_ungrounded_reference_devine_refuz_generare_unsupported():
    case = GoldCase("C1", "exact", "?", ())
    evidence = (make_evidence(),)
    service = _GenerationServiceStub(UngroundedReferenceError("referință neatestată"))

    info = evaluation._run_generation(case, evidence, service)

    assert info["rezultat_final"] == "refuz_generare_unsupported"
    assert info["raspuns"] is None
    assert info["vizibil_utilizator"] == {"http_status": 200, "status_api": "unsupported_answer"}


def test_run_generation_not_found_structurat_devine_refuz_generare_not_found():
    case = GoldCase("N1", "negativ", "?", ())
    evidence = (make_evidence(),)
    service = _GenerationServiceStub(SimpleNamespace(status="not_found", raspuns="Nu am găsit.", citari=()))

    info = evaluation._run_generation(case, evidence, service)

    assert info["rezultat_final"] == "refuz_generare_not_found"
    assert info["raspuns"] is None
    assert info["vizibil_utilizator"] == {"http_status": 200, "status_api": "not_found"}


def test_run_generation_missing_citation_devine_eroare_generare_cu_clasa_si_continua():
    case = GoldCase("C1", "exact", "?", ())
    evidence = (make_evidence(),)
    service = _GenerationServiceStub(MissingCitationError("fără citare"))

    info = evaluation._run_generation(case, evidence, service)

    assert info["rezultat_final"] == "eroare_generare:MissingCitationError"
    assert info["vizibil_utilizator"] == {"http_status": 503, "status_api": None}


def test_run_generation_provider_unavailable_fara_cauza_devine_eroare_generare_si_continua():
    case = GoldCase("C1", "exact", "?", ())
    evidence = (make_evidence(),)
    eroare = evaluation.ProviderUnavailableError("răspuns trunchiat la max_tokens")
    assert eroare.__cause__ is None
    service = _GenerationServiceStub(eroare)

    info = evaluation._run_generation(case, evidence, service)

    assert info["rezultat_final"] == "eroare_generare:ProviderUnavailableError"
    assert info["vizibil_utilizator"] == {"http_status": 503, "status_api": None}


def test_run_generation_provider_unavailable_cu_cauza_se_propaga_si_opreste_rularea():
    case = GoldCase("C1", "exact", "?", ())
    evidence = (make_evidence(),)
    try:
        raise evaluation.ProviderUnavailableError("Anthropic indisponibil") from RuntimeError("rețea")
    except evaluation.ProviderUnavailableError as ridicata:
        service = _GenerationServiceStub(ridicata)
        with pytest.raises(evaluation.ProviderUnavailableError):
            evaluation._run_generation(case, evidence, service)


def test_vizibil_utilizator_mapeaza_fiecare_clasa_de_rezultat_final():
    assert evaluation._vizibil_utilizator("raspuns") is None
    assert evaluation._vizibil_utilizator("refuz_cautare") is None
    assert evaluation._vizibil_utilizator("refuz_generare_unsupported") == {
        "http_status": 200, "status_api": "unsupported_answer"
    }
    assert evaluation._vizibil_utilizator("eroare_generare:MissingCitationError") == {
        "http_status": 503, "status_api": None
    }
    assert evaluation._vizibil_utilizator("eroare_generare:ProviderUnavailableError") == {
        "http_status": 503, "status_api": None
    }


def test_citeaza_asteptat_fals_daca_documentul_citat_e_gresit():
    case = GoldCase("C1", "exact", "?", (GoldExpectation("doc_a", "2.1"),))
    evidence = (make_evidence(document_id="doc_b", articol_normalizat="2.1"),)
    citare = PublicCitation(id="C1", cod_document="X", titlu_document="Y", articol="2.1", citat="x")
    assert evaluation._citeaza_asteptat(case, evidence, (citare,)) is False


def test_citeaza_asteptat_adevarat_pentru_articol_copil_citat():
    case = GoldCase("C1", "exact", "?", (GoldExpectation("doc_a", "2.1"),))
    evidence = (make_evidence(document_id="doc_a", articol_normalizat="2.1.(1)"),)
    citare = PublicCitation(id="C1", cod_document="X", titlu_document="Y", articol="2.1.(1)", citat="x")
    assert evaluation._citeaza_asteptat(case, evidence, (citare,)) is True


def test_citate_literale_fals_daca_citatul_nu_apare_in_dovada():
    evidence = (make_evidence(content="Textul real din dovadă normativă."),)
    citare = PublicCitation(id="C1", cod_document="X", titlu_document="Y", articol="2.1", citat="Text inventat.")
    assert evaluation._citate_literale(evidence, (citare,)) is False


def test_citate_literale_adevarat_cu_whitespace_normalizat():
    evidence = (make_evidence(content="Textul   real\ndin dovadă."),)
    citare = PublicCitation(id="C1", cod_document="X", titlu_document="Y", articol="2.1", citat="Textul real din dovadă.")
    assert evaluation._citate_literale(evidence, (citare,)) is True


@pytest.mark.parametrize("text", [
    "Informația nu se regăsește în documentele furnizate.",
    "Informatia nu se regaseste in documentele furnizate.",
])
def test_declara_lipsa_functioneaza_indiferent_de_diacritice(text):
    assert evaluation._declara_lipsa(text) is True


def test_declara_lipsa_fals_pentru_un_raspuns_obisnuit():
    assert evaluation._declara_lipsa("Articolul 2.1 prevede grosimea minimă de perete.") is False


def install_generation_fake(monkeypatch, outcomes: dict[str, tuple[object, int]]):
    """Înlocuiește `GenerationService` cu un fake care numără apelurile de nivel jos
    (`generator.generate`), la fel cum face `_CountingGenerator` în producție, fără să
    depindă de validarea reală din `generation_core` (deja acoperită în alte teste)."""

    class GenerationServiceFake:
        def __init__(self, generator):
            self._generator = generator

        def generate(self, question, _evidence):
            outcome, n_apeluri_brute = outcomes[question]
            for _ in range(n_apeluri_brute):
                self._generator.generate("prompt", max_tokens=1)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    monkeypatch.setattr(evaluation, "GenerationService", GenerationServiceFake)


def test_refuz_de_cautare_nu_declanseaza_nicio_generare(monkeypatch, tmp_path):
    case = GoldCase("N1", "negativ", "q1", ())
    install_fakes(monkeypatch, results={"q1": SimpleNamespace(status="not_found", evidence=())})
    install_generation_fake(monkeypatch, outcomes={})

    report = evaluation.run_evaluation(
        [case], tmp_path / "raport.json",
        connection_factory=ConnectionFake,
        embedder_factory=EmbedderDelegateFake,
        generation=True,
        generator_factory=lambda: SimpleNamespace(generate=lambda *a, **k: "nu ar trebui apelat"),
    )

    assert report["cazuri"][0]["rezultat_final"] == "refuz_cautare"
    assert report["cazuri"][0]["vizibil_utilizator"] is None
    assert report["sumar"]["generation_calls"] == 0
    assert report["sumar"]["generare"]["rezultat_final_distributie"] == {"refuz_cautare": 1}


def test_gasit_cu_generare_reusita_devine_raspuns_si_numara_apelul(monkeypatch, tmp_path):
    evidence = (make_evidence(document_id="doc_a", articol_normalizat="2.1", content="text"),)
    case = GoldCase("C1", "exact", "intrebare?", (GoldExpectation("doc_a", "2.1"),))
    install_fakes(monkeypatch, results={"intrebare?": SimpleNamespace(status="found", evidence=evidence)})
    citare = PublicCitation(id="C1", cod_document="X", titlu_document="Y", articol="2.1", citat="text")
    outcome = SimpleNamespace(raspuns="Răspuns [C1].", citari=(citare,))
    install_generation_fake(monkeypatch, outcomes={"intrebare?": (outcome, 1)})

    report = evaluation.run_evaluation(
        [case], tmp_path / "raport.json",
        connection_factory=ConnectionFake,
        embedder_factory=EmbedderDelegateFake,
        generation=True,
        generator_factory=lambda: SimpleNamespace(generate=lambda *a, **k: "ok"),
    )

    assert report["cazuri"][0]["rezultat_final"] == "raspuns"
    assert report["sumar"]["generation_calls"] == 1
    assert report["sumar"]["generare"]["raspunsuri"] == 1
    assert report["sumar"]["generare"]["citeaza_asteptat"] == 1
    assert report["sumar"]["generare"]["citate_literale"] == 1


def test_citatul_publicat_in_raport_este_taiat_la_300_de_caractere(monkeypatch, tmp_path):
    evidence = (make_evidence(document_id="doc_a", articol_normalizat="2.1", content="a" * 400),)
    case = GoldCase("C1", "exact", "intrebare?", (GoldExpectation("doc_a", "2.1"),))
    install_fakes(monkeypatch, results={"intrebare?": SimpleNamespace(status="found", evidence=evidence)})
    citare = PublicCitation(id="C1", cod_document="X", titlu_document="Y", articol="2.1", citat="a" * 400)
    outcome = SimpleNamespace(raspuns="Răspuns [C1].", citari=(citare,))
    install_generation_fake(monkeypatch, outcomes={"intrebare?": (outcome, 1)})

    report = evaluation.run_evaluation(
        [case], tmp_path / "raport.json",
        connection_factory=ConnectionFake,
        embedder_factory=EmbedderDelegateFake,
        generation=True,
        generator_factory=lambda: SimpleNamespace(generate=lambda *a, **k: "ok"),
    )

    citat_raport = report["cazuri"][0]["citari"][0]["citat"]
    assert len(citat_raport) == 300
    assert citat_raport == "a" * 300


def test_raportul_de_generare_nu_publica_textul_intern_al_dovezii(monkeypatch, tmp_path):
    evidence = (make_evidence(document_id="doc_a", articol_normalizat="2.1", content="TEXT NORMATIV SECRET"),)
    case = GoldCase("C1", "exact", "intrebare?", (GoldExpectation("doc_a", "2.1"),))
    install_fakes(monkeypatch, results={"intrebare?": SimpleNamespace(status="found", evidence=evidence)})
    citare = PublicCitation(id="C1", cod_document="X", titlu_document="Y", articol="2.1", citat="fragment public")
    outcome = SimpleNamespace(raspuns="Răspuns [C1].", citari=(citare,))
    install_generation_fake(monkeypatch, outcomes={"intrebare?": (outcome, 1)})

    report = evaluation.run_evaluation(
        [case], tmp_path / "raport.json",
        connection_factory=ConnectionFake,
        embedder_factory=EmbedderDelegateFake,
        generation=True,
        generator_factory=lambda: SimpleNamespace(generate=lambda *a, **k: "ok"),
    )

    assert "TEXT NORMATIV SECRET" not in json.dumps(report, ensure_ascii=False)


def test_sumarul_generare_distribuie_si_numara_erorile_pe_clasa(monkeypatch, tmp_path):
    evidence = (make_evidence(document_id="doc_a", articol_normalizat="2.1"),)
    cases = [
        GoldCase("C1", "exact", "q1", (GoldExpectation("doc_a", "2.1"),)),
        GoldCase("C2", "exact", "q2", (GoldExpectation("doc_a", "2.1"),)),
        GoldCase("N1", "negativ", "q3", ()),
    ]
    install_fakes(monkeypatch, results={
        "q1": SimpleNamespace(status="found", evidence=evidence),
        "q2": SimpleNamespace(status="found", evidence=evidence),
        "q3": SimpleNamespace(status="out_of_scope", evidence=()),
    })
    citare = PublicCitation(id="C1", cod_document="X", titlu_document="Y", articol="2.1", citat="text")
    outcome_ok = SimpleNamespace(raspuns="Răspuns [C1].", citari=(citare,))
    install_generation_fake(monkeypatch, outcomes={
        "q1": (outcome_ok, 1),
        "q2": (MissingCitationError("fără citare"), 1),
    })

    report = evaluation.run_evaluation(
        cases, tmp_path / "raport.json",
        connection_factory=ConnectionFake,
        embedder_factory=EmbedderDelegateFake,
        generation=True,
        generator_factory=lambda: SimpleNamespace(generate=lambda *a, **k: "ok"),
    )

    sumar_generare = report["sumar"]["generare"]
    assert sumar_generare["rezultat_final_distributie"] == {
        "raspuns": 1, "eroare_generare:MissingCitationError": 1, "refuz_cautare": 1,
    }
    assert sumar_generare["erori_generare"] == {"eroare_generare:MissingCitationError": 1}
    assert sumar_generare["raspunsuri"] == 1
    assert report["sumar"]["generation_calls"] == 2


def test_plafonul_de_generari_include_reincercarea_si_opreste_rularea_fara_raport(monkeypatch, tmp_path):
    """Plafonul (`MAX_GENERATION_CALLS`) se aplică apelurilor de nivel jos (`_CountingGenerator`),
    nu cazurilor: un singur caz care declanșează reîncercarea (2 apeluri brute) trebuie să
    lovească un plafon de 1 la al doilea apel, exact ca la o rulare reală cu retry."""
    monkeypatch.setattr(evaluation, "MAX_GENERATION_CALLS", 1)
    evidence = (make_evidence(document_id="doc_a", articol_normalizat="2.1"),)
    case = GoldCase("C1", "exact", "intrebare?", (GoldExpectation("doc_a", "2.1"),))
    install_fakes(monkeypatch, results={"intrebare?": SimpleNamespace(status="found", evidence=evidence)})
    citare = PublicCitation(id="C1", cod_document="X", titlu_document="Y", articol="2.1", citat="text")
    outcome = SimpleNamespace(raspuns="Răspuns [C1].", citari=(citare,))
    install_generation_fake(monkeypatch, outcomes={"intrebare?": (outcome, 2)})
    raport_path = tmp_path / "raport.json"

    with pytest.raises(evaluation.RealEvaluationError, match="cost_limit"):
        evaluation.run_evaluation(
            [case], raport_path,
            connection_factory=ConnectionFake,
            embedder_factory=EmbedderDelegateFake,
            generation=True,
            generator_factory=lambda: SimpleNamespace(generate=lambda *a, **k: "ok"),
        )

    assert not raport_path.exists()
