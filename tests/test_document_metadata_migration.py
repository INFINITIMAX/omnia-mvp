from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[1]
    / "supabase"
    / "migrations"
    / "20260831165749_document_metadata.sql"
)


def test_migrarea_document_metadata_contine_contractul_aprobat():
    sql = MIGRATION.read_text(encoding="utf-8")

    assert "create table if not exists public.documente" in sql
    assert "document_id text primary key" in sql
    assert "source_key text not null unique" in sql
    assert "NP010_extras.txt" in sql
    assert "NP0572002_extras.txt" in sql
    assert "add column if not exists document_id text" in sql
    assert "add column if not exists articol_normalizat text" in sql
    assert "add column if not exists content_hash text" in sql
    assert "add column if not exists chunk_order integer" in sql
    assert "add constraint documente_chunks_pkey primary key (id)" in sql
    assert "foreign key (document_id)" in sql
    assert "references public.documente (document_id)" in sql
    assert "md5(text)" in sql
    assert "row_number() over (partition by document_id order by id)::integer" in sql
    assert "documente_chunks_document_id_articol_normalizat_idx" in sql
    assert "on public.documente_chunks (document_id, articol_normalizat)" in sql
    assert "documente_chunks_content_hash_idx" in sql
    assert "alter table public.documente enable row level security" in sql
    assert "alter table public.documente_chunks enable row level security" in sql
    assert "revoke all on table public.documente from anon, authenticated" in sql
    assert "revoke all on table public.documente_chunks from anon, authenticated" in sql


def test_documentatia_migrarii_include_rollback_si_validare_locala():
    documentatie = (
        Path(__file__).resolve().parents[1]
        / "supabase"
        / "DOCUMENT_METADATA_MIGRATION.md"
    ).read_text(encoding="utf-8")

    assert "## Validări executate local" in documentatie
    assert "## Rollback manual" in documentatie
    assert "python -m pytest -q  -> 7 passed" in documentatie
    assert "git diff --check     -> fără erori" in documentatie
    assert "supabase db reset" not in documentatie
    assert "drop constraint if exists documente_chunks_document_id_fkey" in documentatie
    assert "articol_normalizat" in documentatie
    assert "content_hash" in documentatie
    assert "chunk_order" in documentatie
