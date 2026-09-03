"""Teste locale/mockuite pentru nucleul anonim; fără FastAPI, DB reală sau servicii externe."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from access_control import (
    ANONYMOUS_QUOTA_LIMIT,
    COOKIE_MAX_AGE,
    DEFAULT_DAILY_PAID_CALL_LIMIT,
    IP_BUCKET_RETENTION,
    RATE_LIMIT_PER_HOUR,
    RATE_LIMIT_PER_MINUTE,
    AccessControlConfig,
    PostgresAccessControlRepository,
    canonicalize_ip,
    hash_ip,
    issue_anonymous_cookie,
    rate_limit_windows,
    verify_anonymous_cookie,
)

NOW = datetime(2026, 9, 1, 12, 34, 56, tzinfo=UTC)
COOKIE_KEY = bytes(range(32))
IP_KEY = bytes(range(32, 64))


def config(**changes):
    return AccessControlConfig(COOKIE_KEY, IP_KEY, **changes)


class CursorFake:
    def __init__(self, responses=(), rowcount=0):
        self.responses = iter(responses)
        self.rowcount = rowcount
        self.calls = []
        self.returned_rows = []
        self.closed = False

    def execute(self, sql, parameters):
        self.calls.append((sql, parameters))

    def fetchone(self):
        return next(self.responses, None)

    def fetchall(self):
        rows = next(self.responses, [])
        self.returned_rows.append(rows)
        return rows

    def close(self):
        self.closed = True


class ConnectionFake:
    def __init__(self, cursor):
        self.cursor_instance = cursor
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_cookie_round_trip_stocheaza_numai_hashul_derivat():
    token, visitor = issue_anonymous_cookie(config(), now=NOW, random_bytes=lambda _: b"a" * 32)

    verified = verify_anonymous_cookie(token, config(), now=NOW + timedelta(seconds=1))

    assert verified == visitor
    assert len(visitor.visitor_hash) == 64
    assert "a" * 32 not in visitor.visitor_hash
    assert token.count(".") == 3


@pytest.mark.parametrize("tampered", ["v1.invalid.1.invalid", "v2.a.1.a", "v1.a.1.a"])
def test_cookie_falsificat_este_refuzat_fail_closed(tampered):
    assert verify_anonymous_cookie(tampered, config(), now=NOW) is None


def test_cookie_expirat_sau_din_viitor_este_refuzat():
    token, _ = issue_anonymous_cookie(config(), now=NOW, random_bytes=lambda _: b"b" * 32)

    assert verify_anonymous_cookie(token, config(), now=NOW + COOKIE_MAX_AGE) is not None
    assert verify_anonymous_cookie(token, config(), now=NOW + COOKIE_MAX_AGE + timedelta(seconds=1)) is None
    assert verify_anonymous_cookie(token, config(), now=NOW - timedelta(seconds=1)) is None


@pytest.mark.parametrize("key", [b"", b"x" * 31, b"x" * 32, "nu-bytes"])
def test_secretele_slabe_sau_nepotrivite_sunt_refuzate(key):
    with pytest.raises(ValueError):
        AccessControlConfig(key, IP_KEY)


def test_cheile_cookie_si_ip_trebuie_separate_si_constantele_sunt_stricte():
    with pytest.raises(ValueError, match="diferită"):
        AccessControlConfig(COOKIE_KEY, COOKIE_KEY)
    with pytest.raises(ValueError, match="exact 10"):
        config(quota_limit=11)
    with pytest.raises(ValueError, match="exact 5"):
        config(rate_limit_per_minute=6)
    with pytest.raises(ValueError, match="exact 30"):
        config(rate_limit_per_hour=31)
    with pytest.raises(ValueError, match="365"):
        config(cookie_max_age=timedelta(days=364))
    with pytest.raises(ValueError, match="24"):
        config(ip_bucket_retention=timedelta(hours=23))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("192.0.2.1", "192.0.2.1"), ("2001:0db8:0:0:0:0:0:1", "2001:db8::1")],
)
def test_ip_este_canonicalizat(raw, expected):
    assert canonicalize_ip(raw) == expected


@pytest.mark.parametrize("raw", ["", " 192.0.2.1", "1.2.3.999", "host.example", "fe80::1%eth0", None])
def test_ip_invalid_este_refuzat(raw):
    with pytest.raises(ValueError, match="IP invalid"):
        canonicalize_ip(raw)


def test_hash_ip_este_determinist_si_folosește_cheia_ip_nu_cheia_cookie():
    first = hash_ip("2001:0db8:0:0:0:0:0:1", config())
    second = hash_ip("2001:db8::1", config())
    changed_key = hash_ip("2001:db8::1", AccessControlConfig(COOKIE_KEY, bytes(range(64, 96))))

    assert first == second
    assert first != changed_key
    assert len(first) == 64


def test_rezervarea_quota_1_la_10_si_a_11a_foloseste_sql_parametrizat_fara_commit():
    cursor = CursorFake(responses=[(number,) for number in range(1, 11)] + [None])
    connection = ConnectionFake(cursor)
    repository = PostgresAccessControlRepository(connection)
    visitor_hash = "a" * 64

    assert [repository.reserve_question(visitor_hash) for _ in range(11)] == list(range(1, 11)) + [None]

    sql, parameters = cursor.calls[0]
    assert "ON CONFLICT (visitor_hash) DO UPDATE" in sql
    assert "WHERE usage.questions_used < %s" in sql
    assert parameters == (visitor_hash, ANONYMOUS_QUOTA_LIMIT)
    assert connection.commits == connection.rollbacks == 0
    assert cursor.closed


def test_contractul_quota_lasa_rollback_ul_erorii_tehnice_callerului():
    cursor = CursorFake(responses=[(1,)])
    connection = ConnectionFake(cursor)

    assert PostgresAccessControlRepository(connection).reserve_question("b" * 64)
    connection.rollback()  # contract caller: nu există commit ascuns în repository

    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_rate_limit_contorizeaza_6_7_minut_si_31_32_ora_fara_commit_ascuns():
    cursor = CursorFake(
        responses=[[("minute", count), ("hour", count)] for count in range(1, 8)]
        + [[("minute", 1), ("hour", count)] for count in range(1, 33)]
    )
    connection = ConnectionFake(cursor)
    repository = PostgresAccessControlRepository(connection)

    minute_results = [repository.check_and_increment_rate_limit("c" * 64, now=NOW).allowed for _ in range(7)]
    hour_results = [
        repository.check_and_increment_rate_limit("d" * 64, now=NOW + timedelta(minutes=1)).allowed
        for _ in range(32)
    ]

    assert minute_results == [True] * RATE_LIMIT_PER_MINUTE + [False, False]
    assert hour_results == [True] * RATE_LIMIT_PER_HOUR + [False, False]
    assert cursor.returned_rows[5] == [("minute", 6), ("hour", 6)]
    assert cursor.returned_rows[6] == [("minute", 7), ("hour", 7)]
    assert cursor.returned_rows[7 + 30] == [("minute", 1), ("hour", 31)]
    assert cursor.returned_rows[7 + 31] == [("minute", 1), ("hour", 32)]
    sql, parameters = cursor.calls[0]
    assert "pg_advisory_xact_lock" in sql
    assert parameters == ("c" * 64,)
    assert any("RETURNING bucket_kind, request_count" in statement for statement, _ in cursor.calls)
    assert sum("SET request_count = request_count + 1" in statement for statement, _ in cursor.calls) == 39
    assert connection.commits == connection.rollbacks == 0


def test_rezervarea_bugetului_zilnic_respecta_pragul_fara_commit_ascuns():
    cursor = CursorFake(responses=[(number,) for number in range(1, 4)] + [None])
    connection = ConnectionFake(cursor)
    repository = PostgresAccessControlRepository(connection)

    assert [repository.reserve_paid_call(now=NOW, daily_limit=3) for _ in range(4)] == [1, 2, 3, None]

    sql, parameters = cursor.calls[0]
    assert "ON CONFLICT (bucket_date) DO UPDATE" in sql
    assert "WHERE budget.request_count < %s" in sql
    assert parameters == (NOW.date(), 3)
    assert connection.commits == connection.rollbacks == 0
    assert cursor.closed


def test_bugetul_zilnic_este_scopat_pe_data_calendaristica_utc():
    cursor = CursorFake(responses=[(1,), (1,)])
    connection = ConnectionFake(cursor)
    repository = PostgresAccessControlRepository(connection)

    repository.reserve_paid_call(now=NOW, daily_limit=DEFAULT_DAILY_PAID_CALL_LIMIT)
    repository.reserve_paid_call(now=NOW + timedelta(days=1), daily_limit=DEFAULT_DAILY_PAID_CALL_LIMIT)

    first_date = cursor.calls[0][1][0]
    second_date = cursor.calls[1][1][0]
    assert second_date - first_date == timedelta(days=1)
    # miezul nopții calendaristice e UTC, nu ora locală (EET); vezi DEPLOYMENT.md.
    assert first_date == NOW.date()


@pytest.mark.parametrize("daily_limit", [0, -1, 1.5, "200", True])
def test_rezervarea_bugetului_refuza_prag_invalid(daily_limit):
    connection = ConnectionFake(CursorFake())

    with pytest.raises(ValueError):
        PostgresAccessControlRepository(connection).reserve_paid_call(now=NOW, daily_limit=daily_limit)


def test_ferestrele_sunt_utc_si_cleanup_ul_este_parametrizat():
    windows = rate_limit_windows(datetime(2026, 9, 1, 15, 34, 56, tzinfo=UTC))
    cursor = CursorFake(rowcount=2)
    repository = PostgresAccessControlRepository(ConnectionFake(cursor))

    assert windows.minute_bucket_start == datetime(2026, 9, 1, 15, 34, tzinfo=UTC)
    assert windows.hour_bucket_start == datetime(2026, 9, 1, 15, 0, tzinfo=UTC)
    assert repository.cleanup_expired_rate_limit_buckets(now=NOW) == 2
    sql, parameters = cursor.calls[0]
    assert "WHERE expires_at <= %s" in sql
    assert parameters == (NOW,)
    assert IP_BUCKET_RETENTION == timedelta(hours=24)


def test_migrarea_are_constraints_rls_revoke_preflight_si_retention():
    sql = (Path(__file__).resolve().parents[1] / "supabase" / "migrations" /
           "20260831230000_anonymous_access_controls.sql").read_text(encoding="utf-8")

    assert "create table public.anonymous_usage" in sql
    assert "create table public.rate_limit_buckets" in sql
    assert "questions_used between 0 and 10" in sql
    assert "request_count >= 0" in sql
    assert "request_count between 0 and 5" not in sql
    assert "request_count between 0 and 30" not in sql
    assert "primary key (ip_hash, bucket_kind, bucket_start)" in sql
    assert "expires_at = bucket_start + interval '24 hours'" in sql
    assert "rate_limit_buckets_expiry_cleanup_idx" in sql
    assert "Preflight oprit" in sql
    assert "enable row level security" in sql
    assert "revoke all on table public.anonymous_usage from anon, authenticated" in sql
    assert "revoke all on table public.rate_limit_buckets from anon, authenticated" in sql


def test_migrarea_bugetului_zilnic_are_constraints_rls_revoke_si_preflight():
    sql = (Path(__file__).resolve().parents[1] / "supabase" / "migrations" /
           "20260903120000_paid_call_daily_budget.sql").read_text(encoding="utf-8")

    assert "create table public.paid_call_budget" in sql
    assert "bucket_date date primary key" in sql
    assert "request_count >= 0" in sql
    assert "Preflight oprit" in sql
    assert "enable row level security" in sql
    assert "revoke all on table public.paid_call_budget from anon, authenticated" in sql


def test_auditul_nu_lasa_ip_cookie_brut_sau_source_key_in_schema_si_cod():
    source = (Path(__file__).resolve().parents[1] / "access_control.py").read_text(encoding="utf-8")
    migration = (Path(__file__).resolve().parents[1] / "supabase" / "migrations" /
                 "20260831230000_anonymous_access_controls.sql").read_text(encoding="utf-8")

    assert "source_key" not in source
    assert "source_key" not in migration
    assert "ip_address text" not in migration
    assert "cookie text" not in migration
    assert "visitor_id text" not in migration
