-- Schema metadata documente Omnia.
-- Migrarea este strictă: orice chunk nemapabil sau fără metadata derivată oprește
-- tranzacția, astfel încât nu rămâne o stare parțială.

begin;

-- Catalogul folosește identificatorul tehnic din metadata.json ca cheie primară.
create table if not exists public.documente (
    document_id text primary key,
    source_key text not null unique,
    cod_oficial text not null,
    titlu_oficial text not null,
    an integer not null,
    status text not null,
    created_at timestamptz not null default now(),
    constraint documente_document_id_nevid_check check (btrim(document_id) <> ''),
    constraint documente_source_key_nevid_check check (btrim(source_key) <> ''),
    constraint documente_cod_oficial_nevid_check check (btrim(cod_oficial) <> ''),
    constraint documente_titlu_oficial_nevid_check check (btrim(titlu_oficial) <> ''),
    constraint documente_an_valid_check check (an between 1800 and 9999),
    constraint documente_status_nevid_check check (btrim(status) <> '')
);

-- Cele două intrări aprobate sunt idempotente: o reluare păstrează metadata deja
-- existentă, în loc să o rescrie fără o decizie explicită.
insert into public.documente (
    document_id, source_key, cod_oficial, titlu_oficial, an, status
)
values
    (
        'np010_2022',
        'NP010_extras.txt',
        'NP 010-2022',
        'Normativ privind proiectarea, realizarea și exploatarea construcțiilor pentru școli și licee',
        2022,
        'indexed_pending_validation'
    ),
    (
        'np057_02',
        'NP0572002_extras.txt',
        'NP 057-02',
        'Normativ privind proiectarea clădirilor de locuințe (revizuire NP 016-96)',
        2002,
        'indexed_pending_validation'
    )
on conflict (document_id) do nothing;

-- Coloanele sunt întâi nullable, pentru a permite backfill-ul sigur al datelor existente.
alter table public.documente_chunks
    add column if not exists document_id text,
    add column if not exists articol_normalizat text,
    add column if not exists content_hash text,
    add column if not exists chunk_order integer;

-- `id` este identitatea unică a chunk-ului; articolul nu devine cheie unică.
do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'documente_chunks_pkey'
          and conrelid = 'public.documente_chunks'::regclass
    ) then
        alter table public.documente_chunks
            add constraint documente_chunks_pkey primary key (id);
    end if;
end $$;

-- Leagă fiecare chunk existent de catalog prin source_key.
update public.documente_chunks as chunk
set document_id = document.document_id
from public.documente as document
where chunk.sursa = document.source_key
  and chunk.document_id is null;

-- Normalizarea exactă pentru lookup: elimină orice spațiu, convertește la litere
-- mici și elimină toate punctele terminale. Punctuația internă rămâne neschimbată.
update public.documente_chunks
set articol_normalizat = regexp_replace(
    lower(regexp_replace(btrim(articol), '[[:space:]]+', '', 'g')),
    '\.+$',
    ''
);

-- md5(text) este funcție PostgreSQL built-in; nu cere extensia pgcrypto.
-- Hash-ul se calculează pe textul exact stocat, pentru detectarea duplicatelor identice.
update public.documente_chunks
set content_hash = md5(text);

-- Ordinea este stabilă: id-ul existent este ordinea de departajare în fiecare document.
with chunkuri_ordonate as (
    select
        id,
        row_number() over (partition by document_id order by id)::integer as chunk_order
    from public.documente_chunks
)
update public.documente_chunks as chunk
set chunk_order = ordonat.chunk_order
from chunkuri_ordonate as ordonat
where chunk.id = ordonat.id;

-- Nu continuăm spre constrângeri dacă datele existente nu pot fi reprezentate sigur.
do $$
begin
    if exists (
        select 1
        from public.documente_chunks
        where document_id is null
           or articol_normalizat is null
           or articol_normalizat = ''
           or content_hash is null
           or chunk_order is null
    ) then
        raise exception
            'Backfill oprit: există documente_chunks fără document_id, articol_normalizat, content_hash sau chunk_order.';
    end if;
end $$;

alter table public.documente_chunks
    alter column document_id set not null,
    alter column articol_normalizat set not null,
    alter column content_hash set not null,
    alter column chunk_order set not null;

-- PostgreSQL nu acceptă ADD CONSTRAINT IF NOT EXISTS, de aceea verificăm explicit.
do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'documente_chunks_document_id_fkey'
          and conrelid = 'public.documente_chunks'::regclass
    ) then
        alter table public.documente_chunks
            add constraint documente_chunks_document_id_fkey
            foreign key (document_id)
            references public.documente (document_id)
            on update restrict
            on delete restrict;
    end if;

    if not exists (
        select 1
        from pg_constraint
        where conname = 'documente_chunks_document_id_chunk_order_key'
          and conrelid = 'public.documente_chunks'::regclass
    ) then
        alter table public.documente_chunks
            add constraint documente_chunks_document_id_chunk_order_key
            unique (document_id, chunk_order);
    end if;
end $$;

-- Lookup exact folosește valoarea normalizată. Indexul de hash permite găsirea
-- eficientă a conținutului identic, fără a impune unicitate asupra datelor istorice.
create index if not exists documente_chunks_document_id_articol_normalizat_idx
    on public.documente_chunks (document_id, articol_normalizat);
create index if not exists documente_chunks_content_hash_idx
    on public.documente_chunks (content_hash);

-- Apărare în profunzime: clienții anonimi/autentificați nu primesc acces până când
-- o migrare ulterioară adaugă explicit granturi și politici justificate.
alter table public.documente enable row level security;
alter table public.documente_chunks enable row level security;
revoke all on table public.documente from anon, authenticated;
revoke all on table public.documente_chunks from anon, authenticated;

commit;
