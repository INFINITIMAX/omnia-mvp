from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20260831220000_approve_initial_documents.sql"
)


def test_migrarea_aproba_numai_documentele_initiale_identificate_oficial():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "('np010_2022', 'NP 010-2022')" in sql
    assert "('np057_02', 'NP 057-02')" in sql
    assert "set status = 'approved'" in sql
    assert "document_id in ('np010_2022', 'np057_02')" in sql
    assert "status = 'indexed_pending_validation'" in sql
    assert "source_key" not in sql


def test_migrarea_este_atomica_idempotenta_si_fail_safe():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert sql.count("begin;") >= 1
    assert sql.rstrip().endswith("commit;")
    assert "to_regclass('public.documente') is null" in sql
    assert "document.status not in ('indexed_pending_validation', 'approved')" in sql
    assert "cele două documente nu sunt approved" in sql
    assert "where document_id in ('np010_2022', 'np057_02')\n      and status = 'indexed_pending_validation'" in sql
