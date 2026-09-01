-- Controale anonime NormativAI: quota per browser și rate limit HMAC per IP.
-- Draft neaplicat. Orice preflight incompatibil oprește tranzacția integral.
-- Nu stochează niciodată cookie-ul sau IP-ul brut.

begin;

do $$
begin
    if to_regclass('public.anonymous_usage') is not null then
        raise exception 'Preflight oprit: public.anonymous_usage există deja.';
    end if;
    if to_regclass('public.rate_limit_buckets') is not null then
        raise exception 'Preflight oprit: public.rate_limit_buckets există deja.';
    end if;
    if not exists (select 1 from pg_roles where rolname = 'anon')
       or not exists (select 1 from pg_roles where rolname = 'authenticated') then
        raise exception 'Preflight oprit: rolurile anon/authenticated lipsesc.';
    end if;
end $$;

create table public.anonymous_usage (
    visitor_hash text primary key,
    questions_used integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint anonymous_usage_visitor_hash_sha256_check
        check (visitor_hash ~ '^[0-9a-f]{64}$'),
    constraint anonymous_usage_questions_used_check
        check (questions_used between 0 and 10),
    constraint anonymous_usage_updated_after_created_check
        check (updated_at >= created_at)
);

create table public.rate_limit_buckets (
    ip_hash text not null,
    bucket_kind text not null,
    bucket_start timestamptz not null,
    request_count integer not null default 0,
    expires_at timestamptz not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (ip_hash, bucket_kind, bucket_start),
    constraint rate_limit_buckets_ip_hash_sha256_check
        check (ip_hash ~ '^[0-9a-f]{64}$'),
    constraint rate_limit_buckets_kind_check
        check (bucket_kind in ('minute', 'hour')),
    -- Plafonarea este în repository: și tentativele blocate rămân auditate numeric.
    constraint rate_limit_buckets_request_count_nonnegative_check
        check (request_count >= 0),
    constraint rate_limit_buckets_retention_check
        check (expires_at = bucket_start + interval '24 hours'),
    constraint rate_limit_buckets_updated_after_created_check
        check (updated_at >= created_at)
);

create index rate_limit_buckets_expiry_cleanup_idx
    on public.rate_limit_buckets (expires_at);

-- FastAPI este singurul client DB; RLS fără politici și revoke explicit păstrează
-- aceste contoare inaccesibile din browser chiar dacă ar exista un client public.
alter table public.anonymous_usage enable row level security;
alter table public.rate_limit_buckets enable row level security;
revoke all on table public.anonymous_usage from anon, authenticated;
revoke all on table public.rate_limit_buckets from anon, authenticated;

commit;

-- Rollback structural (numai după aprobare, într-o tranzacție separată):
-- begin;
-- drop table public.rate_limit_buckets;
-- drop table public.anonymous_usage;
-- commit;
