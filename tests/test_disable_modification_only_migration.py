from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20260927120000_disable_modification_only_documents.sql"
)
DOCUMENTE = "document_id in ('i13_2015_modificari', 'p118_2_2013_modificari')"


def test_migrarea_dezactiveaza_numai_cele_doua_ordine_de_modificare_identificate_oficial():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "('i13_2015_modificari', 'I 13-2015 (modificat 2023)')" in sql
    assert "('p118_2_2013_modificari', 'P 118/2-2013 (modificat 2018)')" in sql
    assert "set status = 'disabled'" in sql
    assert f"where {DOCUMENTE}\n      and status = 'approved'" in sql
    assert "delete" not in sql.lower()
    assert "documente_chunks" not in sql


def test_migrarea_este_atomica_idempotenta_si_fail_safe():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert sql.count("begin;") == 1
    assert sql.rstrip().endswith("commit;")
    assert "to_regclass('public.documente') is null" in sql
    assert "document.status not in ('approved', 'disabled')" in sql
    assert "cele două documente nu sunt disabled" in sql
