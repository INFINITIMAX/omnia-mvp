-- Decizie explicită Lucian (27-09-2026): documentele care conțin doar ordinul de
-- modificare, fără textul de bază, încalcă regula de conținut și ies din retrieval.
-- `disabled` păstrează chunk-urile în DB; revenirea se face explicit, nu prin reimport.
-- Migrarea este idempotentă, dar eșuează dacă identitatea sau statusul lor diferă.

begin;

do $$
begin
    if to_regclass('public.documente') is null then
        raise exception 'Dezactivare oprită: public.documente lipsește.';
    end if;

    if exists (
        select 1
        from (
            values
                ('i13_2015_modificari', 'I 13-2015 (modificat 2023)'),
                ('p118_2_2013_modificari', 'P 118/2-2013 (modificat 2018)')
        ) as asteptat(document_id, cod_oficial)
        left join public.documente as document
          on document.document_id = asteptat.document_id
        where document.document_id is null
           or document.cod_oficial <> asteptat.cod_oficial
           or document.status not in ('approved', 'disabled')
    ) then
        raise exception 'Dezactivare oprită: identitate sau status document incompatibil.';
    end if;

    update public.documente
    set status = 'disabled'
    where document_id in ('i13_2015_modificari', 'p118_2_2013_modificari')
      and status = 'approved';

    if (
        select count(*)
        from public.documente
        where document_id in ('i13_2015_modificari', 'p118_2_2013_modificari')
          and status = 'disabled'
    ) <> 2 then
        raise exception 'Dezactivare oprită: cele două documente nu sunt disabled.';
    end if;
end $$;

commit;
