# Migrare metadata documente

## Ce conține

`migrations/20260831165749_document_metadata.sql` creează catalogul `public.documente` și adaugă în `public.documente_chunks`:

- `document_id`: legătura FK către document;
- `articol_normalizat`: cheia pentru căutarea exactă;
- `content_hash`: hash MD5 al textului pentru detectarea duplicatelor identice;
- `chunk_order`: poziție stabilă, unică în document.

`id` rămâne cheia primară a chunk-ului; `articol` nu devine unic. Migrarea este o singură tranzacție: un chunk nemapabil sau fără valori derivate oprește totul.

## Normalizarea aleasă

Pentru `articol_normalizat`, atât backfill-ul SQL, cât și importerul viitor aplică exact acești pași, în ordine:

1. elimină toate caracterele de spațiere;
2. transformă literele în minuscule;
3. elimină toate punctele de la final;
4. păstrează punctuația internă.

Exemplu: ` 3.2. (B). L. ` devine `3.2.(b).l`.

`content_hash` este `md5(text)`, funcție PostgreSQL built-in, fără `pgcrypto` sau altă extensie nouă. Pentru importurile viitoare, `populare_db.py` calculează același MD5 din textul UTF-8. Hash-ul servește la **detectare/deduplicare**, nu are constrângere `UNIQUE`: duplicatele istorice rămân inspectabile.

`chunk_order` se completează cu `row_number() over (partition by document_id order by id)`. Pentru importurile noi, importerul atribuie `1, 2, …` în ordinea deterministă a chunk-urilor produse.

## Validări executate local

La 31-08-2026 (EET) au rulat cu succes:

```text
python -m pytest -q  -> 7 passed
git diff --check     -> fără erori
```

Nu s-a aplicat SQL local sau remote: acest worktree nu are o configurație Supabase locală versionată. Înainte de o aplicare aprobată, rulează următoarele interogări **doar pe o instanță locală** și verifică rezultatele.

```sql
-- Catalogul și backfill-ul: exact două documente și 408/286 chunk-uri.
select document_id, source_key, cod_oficial, an, status
from public.documente
order by document_id;

select document_id, count(*) as numar_chunkuri
from public.documente_chunks
group by document_id
order by document_id;

-- Toate valorile derivate trebuie să fie complete.
select count(*) as chunkuri_incomplete
from public.documente_chunks
where document_id is null
   or articol_normalizat is null
   or content_hash is null
   or chunk_order is null;

-- Ordinea trebuie să fie unică în fiecare document.
select document_id, chunk_order, count(*)
from public.documente_chunks
group by document_id, chunk_order
having count(*) > 1;

-- Hash-uri egale: candidate pentru deduplicare la retrieval, nu erori SQL.
select content_hash, count(*) as duplicate_identice
from public.documente_chunks
group by content_hash
having count(*) > 1;

-- FK-ul, PK-ul, indexurile și RLS trebuie să existe.
select conname, contype, pg_get_constraintdef(oid)
from pg_constraint
where conrelid = 'public.documente_chunks'::regclass
  and conname in (
      'documente_chunks_pkey',
      'documente_chunks_document_id_fkey',
      'documente_chunks_document_id_chunk_order_key'
  )
order by conname;

select indexname, indexdef
from pg_indexes
where schemaname = 'public'
  and tablename = 'documente_chunks'
  and indexname in (
      'documente_chunks_document_id_articol_normalizat_idx',
      'documente_chunks_content_hash_idx'
  )
order by indexname;

select relname, relrowsecurity
from pg_class
where oid in ('public.documente'::regclass, 'public.documente_chunks'::regclass)
order by relname;

-- Nu trebuie să existe politici pentru aceste tabele.
select tablename, policyname
from pg_policies
where schemaname = 'public'
  and tablename in ('documente', 'documente_chunks');

-- Lookup-ul exact trebuie să folosească indexul nou.
explain (costs false)
select id
from public.documente_chunks
where document_id = '<document_id_local>'
  and articol_normalizat = '<articol_normalizat_local>';
```

## Rollback manual

Rulează rollback **numai după backup** și numai dacă nicio migrare ulterioară nu depinde de aceste coloane sau de `public.documente`. Acesta șterge catalogul și metadata nouă, dar nu șterge chunk-urile existente.

```sql
begin;

alter table public.documente_chunks
    drop constraint if exists documente_chunks_document_id_fkey;
alter table public.documente_chunks
    drop constraint if exists documente_chunks_document_id_chunk_order_key;
drop index if exists public.documente_chunks_document_id_articol_normalizat_idx;
drop index if exists public.documente_chunks_content_hash_idx;
alter table public.documente_chunks
    drop column if exists document_id,
    drop column if exists articol_normalizat,
    drop column if exists content_hash,
    drop column if exists chunk_order;
drop table if exists public.documente;

commit;
```

Rollback-ul nu elimină cheia primară `documente_chunks_pkey`, nu restabilește granturile/politicile/setarea RLS anterioare și nu inversează importuri noi realizate după migrare.

## Riscuri și limite

- Migrarea refuză surse istorice neaprobate și valori `articol`/`text` lipsă; ele necesită corectare sau backfill explicit.
- MD5 este suficient aici ca identificator practic de conținut identic, nu ca mecanism criptografic. O coliziune teoretică poate deduplica greșit; textul și articolul rămân disponibile pentru verificare internă.
- Reordonarea sau reinserarea chunk-urilor schimbă `chunk_order`; ordinea stabilă este garantată numai pentru setul de rânduri și `id`-urile existente.
- RLS activ fără politici și granturile revocate blochează clienții `anon`/`authenticated`; backend-ul administrativ trebuie validat separat.
- `source_key` rămâne intern și nu trebuie expus clientului.
