# Migrare metadata documente

## Garanții structurale

Migrarea este **fail-fast** și se aplică o singură dată. Preflight-ul verifică înainte de orice `ALTER` că `public.documente_chunks` există, are tipurile vechi așteptate (`id integer NOT NULL`, `sursa/articol/text text`) și cheia primară exactă `(id)`. De asemenea, refuză coloane rămase dintr-o aplicare parțială.

`public.documente` conține atât `UNIQUE(document_id, source_key)`, cât și cheile individuale. `documente_chunks` primește FK-ul compus `(document_id, sursa) -> documente(document_id, source_key)`. Backfill-ul refuză orice sursă sau pereche document–sursă incompatibilă.

## Normalizare și metadata chunk

`articol_normalizat` are contractul ASCII `^[a-z0-9().-]+$`.

1. se elimină **numai** whitespace ASCII: spațiu, tab, LF, CR, FF, VT;
2. literele devin minuscule;
3. punctele terminale sunt eliminate;
4. orice alt caracter, inclusiv whitespace Unicode, oprește importul/backfill-ul.

Exemplu acceptat: ` 3.2. (B). L. ` devine `3.2.(b).l`.

`content_hash` este `md5(text)`, funcție PostgreSQL built-in; nu necesită extensie. Nu este unic: hash-uri egale sunt candidate pentru deduplicare controlată la retrieval. `chunk_order` este `row_number()` după `id`, unic în document.

Importerul validează `document_id`, `source_key`, `cod_oficial`, `titlu_oficial`, `an` și `status`. Statusurile permise sunt `indexed_pending_validation`, `approved` și `disabled`. De asemenea, refuză documentele fără chunk-uri și validează toate articolele/textele înainte de DB sau Voyage. Apoi verifică/upsertează documentul înainte de `DELETE` și înainte de primul apel Voyage. Un conflict document–sursă oprește importul fără cost Voyage.

## Preflight operator înainte de aplicare

Planner-ul a verificat că rolul backend curent este owner, are `BYPASSRLS` și drepturi read/write. Operatorul confirmă aceeași situație local, înainte de aplicare, fără a crea roluri sau parole:

```sql
select
    current_user as rol_curent,
    c.relowner::regrole = current_user::regrole as este_owner,
    r.rolbypassrls,
    has_table_privilege(current_user, 'public.documente_chunks', 'select,insert,update,delete') as are_read_write
from pg_class as c
join pg_roles as r on r.rolname = current_user
where c.oid = 'public.documente_chunks'::regclass;

select relrowsecurity
from pg_class
where oid = 'public.documente_chunks'::regclass;

select policyname
from pg_policies
where schemaname = 'public'
  and tablename = 'documente_chunks';
```

Rezultatul așteptat: owner `true`, `rolbypassrls = true`, read/write `true`, RLS activ și zero politici.

## Gate obligatoriu de validare SQL

Nu s-a executat SQL real în acest worktree. Înainte de aplicare remote, este obligatorie rularea migrației într-o instanță locală, în tranzacție, urmată de verificări și `ROLLBACK`. Acest gate nu este înlocuit de testele Python.

```sql
begin;
-- Operatorul aplică aici conținutul exact al migrării în baza locală.

select document_id, source_key
from public.documente
order by document_id;

select count(*) as chunkuri_incomplete
from public.documente_chunks
where document_id is null
   or sursa is null
   or articol_normalizat !~ '^[a-z0-9().-]+$'
   or content_hash is null
   or chunk_order is null;

select document_id, chunk_order, count(*)
from public.documente_chunks
group by document_id, chunk_order
having count(*) > 1;

select conname, pg_get_constraintdef(oid)
from pg_constraint
where conrelid = 'public.documente_chunks'::regclass
  and conname in (
      'documente_chunks_document_id_sursa_fkey',
      'documente_chunks_document_id_chunk_order_key',
      'documente_chunks_articol_normalizat_ascii_check'
  );

explain (costs false)
select id
from public.documente_chunks
where document_id = '<document_id_local>'
  and articol_normalizat = '<articol_normalizat_local>';

rollback;
```

## Rollback structural

Folosește numai după backup și numai dacă nicio migrare ulterioară nu depinde de schemă. Nu restaurează acces public.

```sql
begin;

alter table public.documente_chunks
    drop constraint documente_chunks_document_id_sursa_fkey,
    drop constraint documente_chunks_document_id_chunk_order_key,
    drop constraint documente_chunks_articol_normalizat_ascii_check;
drop index public.documente_chunks_document_id_articol_normalizat_idx;
drop index public.documente_chunks_content_hash_idx;
alter table public.documente_chunks
    drop column document_id,
    drop column articol_normalizat,
    drop column content_hash,
    drop column chunk_order;
drop table public.documente;

commit;
```

## Restaurare granturi: separată și numai cu aprobare explicită

Snapshot-ul inițial verificat de Planner: `documente_chunks` avea RLS activ, zero politici, iar `anon`/`authenticated` aveau granturi, dar nu vedeau rânduri din cauza RLS. Migrarea revocă granturile pentru ambele roluri.

Rollback-ul structural de mai sus **nu** restaurează granturi. Numai dacă Lucian cere explicit rollback total, operatorul poate restaura snapshot-ul cunoscut:

```sql
-- Numai cu aprobare explicită de rollback total; RLS rămâne activ, fără politici.
grant select, insert, update, delete on table public.documente_chunks to anon, authenticated;
```

Nu se acordă niciun grant pentru `public.documente`, care nu exista înainte de migrare.

## Riscuri rămase

- Gate-ul SQL local cu rollback este obligatoriu și încă neexecutat.
- MD5 este identificator practic de duplicate, nu mecanism criptografic; coliziunile rămân teoretic posibile.
- Orice document nou trebuie să respecte metadata completă și contractul ASCII al articolului.
- RLS fără politici și granturile revocate blochează clienții `anon`/`authenticated`; backend-ul owner/BYPASSRLS trebuie păstrat exclusiv server-side.
