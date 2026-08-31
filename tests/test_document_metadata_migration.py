from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20260831165749_document_metadata.sql"
)
DOCUMENTATIE = Path(__file__).resolve().parents[1] / "supabase" / "DOCUMENT_METADATA_MIGRATION.md"


def test_migrarea_contine_contractul_document_sursa_si_fail_fast():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "create table public.documente" in sql
    assert "create table if not exists" not in sql
    assert "add column if not exists" not in sql
    assert "unique (document_id, source_key)" in sql
    assert "foreign key (document_id, sursa)" in sql
    assert "references public.documente (document_id, source_key)" in sql
    assert "Preflight oprit" in sql
    assert "and atthasdef" in sql
    assert "cheia primară a documente_chunks trebuie să fie exact (id)" in sql
    assert "documente_chunks conține deja coloane din această migrare" in sql


def test_migrarea_contine_contractul_chunk_si_securitatea():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "articol_normalizat text" in sql
    assert "content_hash text" in sql
    assert "chunk_order integer" in sql
    assert "md5(text)" in sql
    assert "row_number() over (partition by document_id order by id)::integer" in sql
    assert "^[a-z0-9().-]+$" in sql
    assert "chr(160) || chr(8239)" in sql
    assert "status in ('indexed_pending_validation', 'approved', 'disabled')" in sql
    assert "btrim(chunk.text) = ''" in sql
    assert "documente_chunks_document_id_articol_normalizat_idx" in sql
    assert "on public.documente_chunks (document_id, articol_normalizat)" in sql
    assert "alter table public.documente enable row level security" in sql
    assert "alter table public.documente_chunks enable row level security" in sql
    assert "revoke all on table public.documente from anon, authenticated" in sql
    assert "revoke all on table public.documente_chunks from anon, authenticated" in sql


def test_migrarea_include_probe_postgresql_pentru_spatiile_pdf():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "'3.2.' || chr(160) || '(B).'" in sql
    assert "'3.2.' || chr(8239) || '(B).'" in sql
    assert "rezultat_nbsp <> '3.2.(b)'" in sql
    assert "rezultat_nnbsp <> '3.2.(b)'" in sql
    assert "Test intern normalizare oprit" in sql


def test_documentatia_separa_gate_rollback_si_granturi():
    documentatie = DOCUMENTATIE.read_text(encoding="utf-8")

    assert "## Gate de validare SQL executat" in documentatie
    assert "în interiorul unei singure tranzacții controlate extern" in documentatie
    assert "a eliminat exclusiv liniile standalone `BEGIN;` și `COMMIT;`" in documentatie
    assert "## Aplicare persistentă executată" in documentatie
    assert "aplicarea persistentă au fost executate" in documentatie
    assert "BEGIN READ ONLY" in documentatie
    assert "exact 694 rânduri originale" in documentatie
    assert "ROLLBACK" in documentatie
    assert "## Rollback structural" in documentatie
    assert "## Restaurare granturi: separată și numai cu aprobare explicită" in documentatie
    assert "rolbypassrls" in documentatie
    assert "grant select, insert, update, delete" in documentatie
    assert "supabase db reset" not in documentatie
