-- Decizie explicită Lucian (29-09-2026, R26 / D27): P 118/2-2013 și P 118/3-2015, consolidate
-- cu Ordinele 6.026/2018 și 6.025/2018 (proveniență vizibilă în citare), intră în retrieval.
-- Importate prin `populare_db.py --document …` ca `indexed_pending_validation`; aici trec în
-- `approved`. `p118_2_2013_modificari` rămâne `disabled` (D23).
-- Migrarea este idempotentă, dar eșuează dacă identitatea, statusul sau chunk-urile diferă.

begin;

do $$
begin
    if to_regclass('public.documente') is null then
        raise exception 'Aprobare oprită: public.documente lipsește.';
    end if;

    if exists (
        select 1
        from (
            values
                ('p118_2_2013', 'P 118/2-2013', 1856),
                ('p118_3_2015', 'P 118/3-2015', 384)
        ) as asteptat(document_id, cod_oficial, chunkuri)
        left join public.documente as document
          on document.document_id = asteptat.document_id
        where document.document_id is null
           or document.cod_oficial <> asteptat.cod_oficial
           or document.status not in ('indexed_pending_validation', 'approved')
           or (
               select count(*)
               from public.documente_chunks as chunk
               where chunk.document_id = asteptat.document_id
                 and chunk.embedding is not null
           ) <> asteptat.chunkuri
    ) then
        raise exception 'Aprobare oprită: identitate, status sau număr de chunk-uri incompatibil.';
    end if;

    update public.documente
    set status = 'approved'
    where document_id in ('p118_2_2013', 'p118_3_2015')
      and status = 'indexed_pending_validation';

    if (
        select count(*)
        from public.documente
        where document_id in ('p118_2_2013', 'p118_3_2015')
          and status = 'approved'
    ) <> 2 then
        raise exception 'Aprobare oprită: cele două documente nu sunt approved.';
    end if;

    if (
        select status from public.documente where document_id = 'p118_2_2013_modificari'
    ) <> 'disabled' then
        raise exception 'Aprobare oprită: p118_2_2013_modificari trebuie să rămână disabled.';
    end if;
end $$;

commit;
