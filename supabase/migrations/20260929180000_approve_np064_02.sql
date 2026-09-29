-- Decizie explicită Lucian (29-09-2026, D28): NP 064-02 (mansarde) intră în retrieval ca
-- excepție punctuală de la regula „doar Monitorul Oficial” (textul e în Buletinul Construcțiilor).
-- Importat prin `populare_db.py --document np064_02` ca `indexed_pending_validation`.
-- Migrarea este idempotentă, dar eșuează dacă identitatea, statusul sau chunk-urile diferă.

begin;

do $$
begin
    if to_regclass('public.documente') is null then
        raise exception 'Aprobare oprită: public.documente lipsește.';
    end if;

    if not exists (
        select 1
        from public.documente as document
        where document.document_id = 'np064_02'
          and document.cod_oficial = 'NP 064-02'
          and document.status in ('indexed_pending_validation', 'approved')
          and (
              select count(*)
              from public.documente_chunks as chunk
              where chunk.document_id = document.document_id
                and chunk.embedding is not null
          ) = 322
    ) then
        raise exception 'Aprobare oprită: identitate, status sau număr de chunk-uri incompatibil.';
    end if;

    update public.documente
    set status = 'approved'
    where document_id = 'np064_02'
      and status = 'indexed_pending_validation';

    if (select status from public.documente where document_id = 'np064_02') <> 'approved' then
        raise exception 'Aprobare oprită: np064_02 nu e approved.';
    end if;
end $$;

commit;
