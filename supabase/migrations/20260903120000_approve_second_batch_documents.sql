-- Decizie explicită Lucian: al doilea lot de documente e eligibil pentru retrieval.
-- Migrarea este idempotentă, dar eșuează dacă identitatea sau statusul lor diferă.

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
                ('i9_2022', 'I9-2022'),
                ('p118_1_2025', 'P 118/1-2025'),
                ('p118_2_2013_modificari', 'P 118/2-2013 (modificat 2018)'),
                ('spitale_2022', 'NP 015-2022')
        ) as asteptat(document_id, cod_oficial)
        left join public.documente as document
          on document.document_id = asteptat.document_id
        where document.document_id is null
           or document.cod_oficial <> asteptat.cod_oficial
           or document.status not in ('indexed_pending_validation', 'approved')
    ) then
        raise exception 'Aprobare oprită: identitate sau status document incompatibil.';
    end if;

    update public.documente
    set status = 'approved'
    where document_id in ('i9_2022', 'p118_1_2025', 'p118_2_2013_modificari', 'spitale_2022')
      and status = 'indexed_pending_validation';

    if (
        select count(*)
        from public.documente
        where document_id in ('i9_2022', 'p118_1_2025', 'p118_2_2013_modificari', 'spitale_2022')
          and status = 'approved'
    ) <> 4 then
        raise exception 'Aprobare oprită: nu toate cele 4 documente sunt approved.';
    end if;
end $$;

commit;
