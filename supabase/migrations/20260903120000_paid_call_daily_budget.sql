-- Plafon global zilnic pentru apelurile plătite (Voyage embed + Anthropic generate).
-- Un singur contor global, pe zi calendaristică UTC (vezi DEPLOYMENT.md pentru fusul orar).
-- Nu stochează niciun IP, cookie sau conținut de întrebare.

begin;

do $$
begin
    if to_regclass('public.paid_call_budget') is not null then
        raise exception 'Preflight oprit: public.paid_call_budget există deja.';
    end if;
end $$;

create table public.paid_call_budget (
    bucket_date date primary key,
    request_count integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint paid_call_budget_request_count_nonnegative_check
        check (request_count >= 0),
    constraint paid_call_budget_updated_after_created_check
        check (updated_at >= created_at)
);

-- FastAPI este singurul client DB; RLS fără politici și revoke explicit păstrează
-- acest contor inaccesibil din browser chiar dacă ar exista un client public.
alter table public.paid_call_budget enable row level security;
revoke all on table public.paid_call_budget from anon, authenticated;

commit;

-- Rollback structural (numai după aprobare, într-o tranzacție separată):
-- begin;
-- drop table public.paid_call_budget;
-- commit;
