-- Decizie explicită Lucian (29-09-2026, R29): NP 127:2009 (securitatea la incendiu a parcajelor
-- subterane; ordin și text în MO nr. 74/02.02.2010) intră în retrieval. Motiv: feedback de la
-- testare (debitul de desfumare 600/900 m³/h pe autoturism, distanța de 8 m a gurilor de
-- evacuare a fumului). Importat prin `populare_db.py --document np127_2009`.
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
        where document.document_id = 'np127_2009'
          and document.cod_oficial = 'NP 127:2009'
          and document.status in ('indexed_pending_validation', 'approved')
          and (
              select count(*)
              from public.documente_chunks as chunk
              where chunk.document_id = document.document_id
                and chunk.embedding is not null
          ) = 191
    ) then
        raise exception 'Aprobare oprită: identitate, status sau număr de chunk-uri incompatibil.';
    end if;

    update public.documente
    set status = 'approved'
    where document_id = 'np127_2009'
      and status = 'indexed_pending_validation';

    if (select status from public.documente where document_id = 'np127_2009') <> 'approved' then
        raise exception 'Aprobare oprită: np127_2009 nu e approved.';
    end if;
end $$;

commit;
