-- Identitatea persistentă a PDF-urilor ingerate automat.
-- Migrarea este numai versionată; aplicarea cere aprobare separată.

begin;

do $$
begin
    if to_regclass('public.documente') is null then
        raise exception 'Preflight oprit: public.documente lipsește.';
    end if;
    if to_regclass('public.document_ingestion_sources') is not null then
        raise exception 'Preflight oprit: public.document_ingestion_sources există deja.';
    end if;
    if not exists (select 1 from pg_roles where rolname = 'anon')
       or not exists (select 1 from pg_roles where rolname = 'authenticated') then
        raise exception 'Preflight oprit: rolurile anon/authenticated lipsesc.';
    end if;
end $$;

create table public.document_ingestion_sources (
    source_sha256 text primary key,
    document_id text not null unique,
    original_filename text not null,
    created_at timestamptz not null default now(),
    constraint document_ingestion_sources_sha256_check
        check (source_sha256 ~ '^[0-9a-f]{64}$'),
    constraint document_ingestion_sources_filename_nonempty_check
        check (btrim(original_filename) <> ''),
    constraint document_ingestion_sources_document_fkey
        foreign key (document_id)
        references public.documente (document_id)
        on update restrict
        on delete restrict
);

-- Browserul nu poate afla nici hash-ul PDF-ului, nici istoricul ingestion-ului.
alter table public.document_ingestion_sources enable row level security;
revoke all on table public.document_ingestion_sources from anon, authenticated;

commit;

-- Rollback structural (numai după aprobare, într-o tranzacție separată):
-- begin;
-- drop table public.document_ingestion_sources;
-- commit;
