-- Decizie explicită Lucian: documentele inițiale sunt eligibile pentru retrieval.
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
                ('np010_2022', 'NP 010-2022'),
                ('np057_02', 'NP 057-02')
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
    where document_id in ('np010_2022', 'np057_02')
      and status = 'indexed_pending_validation';

    if (
        select count(*)
        from public.documente
        where document_id in ('np010_2022', 'np057_02')
          and status = 'approved'
    ) <> 2 then
        raise exception 'Aprobare oprită: cele două documente nu sunt approved.';
    end if;
end $$;

commit;
