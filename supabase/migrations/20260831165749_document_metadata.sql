-- Schema metadata documente Omnia.
-- Această migrare rulează o singură dată. Orice schemă parțială sau date
-- incompatibile produc eroare și întreaga tranzacție este anulată.

begin;

-- Preflight: tabelul vechi trebuie să aibă exact tipurile și PK-ul pe care se
-- bazează backfill-ul. Nu încercăm să reparăm automat o schemă necunoscută.
do $$
declare
    id_attnum smallint;
begin
    if to_regclass('public.documente') is not null then
        raise exception 'Preflight oprit: public.documente există deja; migrarea nu este reaplicabilă.';
    end if;

    if to_regclass('public.documente_chunks') is null then
        raise exception 'Preflight oprit: public.documente_chunks lipsește.';
    end if;

    if not exists (
        select 1
        from pg_attribute
        where attrelid = 'public.documente_chunks'::regclass
          and attname = 'id'
          and atttypid = 'integer'::regtype
          and attnotnull
          and atthasdef
          and not attisdropped
    ) or not exists (
        select 1
        from pg_attribute
        where attrelid = 'public.documente_chunks'::regclass
          and attname in ('sursa', 'articol', 'text')
          and atttypid = 'text'::regtype
          and not attisdropped
        group by attrelid
        having count(*) = 3
    ) then
        raise exception 'Preflight oprit: documente_chunks necesită id integer NOT NULL și sursa/articol/text text.';
    end if;

    select attnum
    into id_attnum
    from pg_attribute
    where attrelid = 'public.documente_chunks'::regclass
      and attname = 'id'
      and not attisdropped;

    if not exists (
        select 1
        from pg_constraint
        where conrelid = 'public.documente_chunks'::regclass
          and contype = 'p'
          and conkey = array[id_attnum]::smallint[]
    ) then
        raise exception 'Preflight oprit: cheia primară a documente_chunks trebuie să fie exact (id).';
    end if;

    if exists (
        select 1
        from pg_attribute
        where attrelid = 'public.documente_chunks'::regclass
          and attname in ('document_id', 'articol_normalizat', 'content_hash', 'chunk_order')
          and not attisdropped
    ) then
        raise exception 'Preflight oprit: documente_chunks conține deja coloane din această migrare.';
    end if;
end $$;

-- Test comportamental executat chiar de PostgreSQL pentru spațiile PDF. O
-- diferență de semantică față de Python oprește migrarea înainte de orice DDL.
do $$
declare
    spatii_eliminate text := E' \t\n\r\f\v' || chr(160) || chr(8239);
    rezultat_nbsp text;
    rezultat_nnbsp text;
begin
    select regexp_replace(
        lower(translate('3.2.' || chr(160) || '(B).', spatii_eliminate, '')),
        E'\\.+$',
        ''
    ) into rezultat_nbsp;

    select regexp_replace(
        lower(translate('3.2.' || chr(8239) || '(B).', spatii_eliminate, '')),
        E'\\.+$',
        ''
    ) into rezultat_nnbsp;

    if rezultat_nbsp <> '3.2.(b)' or rezultat_nnbsp <> '3.2.(b)' then
        raise exception 'Test intern normalizare oprit: U+00A0/U+202F nu respectă contractul.';
    end if;
end $$;

-- Catalogul păstrează atât cheile individuale, cât și perechea necesară FK-ului
-- compus document–sursă.
create table public.documente (
    document_id text primary key,
    source_key text not null unique,
    cod_oficial text not null,
    titlu_oficial text not null,
    an integer not null,
    status text not null,
    created_at timestamptz not null default now(),
    constraint documente_document_id_source_key_key unique (document_id, source_key),
    constraint documente_document_id_nevid_check check (btrim(document_id) <> ''),
    constraint documente_source_key_nevid_check check (btrim(source_key) <> ''),
    constraint documente_cod_oficial_nevid_check check (btrim(cod_oficial) <> ''),
    constraint documente_titlu_oficial_nevid_check check (btrim(titlu_oficial) <> ''),
    constraint documente_an_valid_check check (an between 1800 and 9999),
    constraint documente_status_valid_check check (
        status in ('indexed_pending_validation', 'approved', 'disabled')
    )
);

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
    );

-- Coloanele noi pornesc nullable doar pe durata backfill-ului acestei tranzacții.
alter table public.documente_chunks
    add column document_id text,
    add column articol_normalizat text,
    add column content_hash text,
    add column chunk_order integer;

-- Backfill document_id exclusiv din perechile aprobate document–sursă.
update public.documente_chunks as chunk
set document_id = document.document_id
from public.documente as document
where chunk.sursa = document.source_key;

-- Contract identic cu Python: elimină whitespace ASCII și cele două spații
-- non-breaking întâlnite frecvent în PDF-uri (U+00A0, U+202F), apoi normalizează.
update public.documente_chunks
set articol_normalizat = regexp_replace(
    lower(
        translate(
            articol,
            E' \t\n\r\f\v' || chr(160) || chr(8239),
            ''
        )
    ),
    E'\\.+$',
    ''
);

-- md5(text) este funcție PostgreSQL built-in; nu introduce extensii noi.
update public.documente_chunks
set content_hash = md5(text);

-- id este cheia primară existentă și departajarea stabilă în fiecare document.
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

-- Refuzăm explicit surse necunoscute, perechi document–sursă incompatibile,
-- text/articol lipsă și orice rezultat care nu respectă contractul ASCII.
do $$
begin
    if exists (
        select 1
        from public.documente_chunks as chunk
        left join public.documente as document
          on document.document_id = chunk.document_id
         and document.source_key = chunk.sursa
        where document.document_id is null
           or chunk.articol_normalizat is null
           or chunk.articol_normalizat !~ '^[a-z0-9().-]+$'
           or chunk.text is null
           or btrim(chunk.text) = ''
           or chunk.content_hash is null
           or chunk.chunk_order is null
    ) then
        raise exception
            'Backfill oprit: există perechi document_id/sursa incompatibile sau metadata chunk invalidă.';
    end if;
end $$;

alter table public.documente_chunks
    alter column sursa set not null,
    alter column document_id set not null,
    alter column articol_normalizat set not null,
    alter column content_hash set not null,
    alter column chunk_order set not null,
    add constraint documente_chunks_articol_normalizat_ascii_check
        check (articol_normalizat ~ '^[a-z0-9().-]+$'),
    add constraint documente_chunks_document_id_sursa_fkey
        foreign key (document_id, sursa)
        references public.documente (document_id, source_key)
        on update restrict
        on delete restrict,
    add constraint documente_chunks_document_id_chunk_order_key
        unique (document_id, chunk_order);

-- Indexul exact acoperă și prefixul document_id necesar FK-ului compus.
create index documente_chunks_document_id_articol_normalizat_idx
    on public.documente_chunks (document_id, articol_normalizat);
create index documente_chunks_content_hash_idx
    on public.documente_chunks (content_hash);

-- Tabelele publice rămân inaccesibile pentru clienți până la o decizie separată.
alter table public.documente enable row level security;
alter table public.documente_chunks enable row level security;
revoke all on table public.documente from anon, authenticated;
revoke all on table public.documente_chunks from anon, authenticated;

commit;
