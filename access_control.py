"""Controale anonime pure pentru NormativAI, fără FastAPI sau clienți externi."""

from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable

ANONYMOUS_QUOTA_LIMIT = 10
RATE_LIMIT_PER_MINUTE = 5
RATE_LIMIT_PER_HOUR = 30
COOKIE_MAX_AGE = timedelta(days=365)
IP_BUCKET_RETENTION = timedelta(hours=24)
# Plafon implicit prudent pentru apelurile plătite (Voyage + Anthropic) pe zi calendaristică
# UTC; suprascris de variabila de mediu `DAILY_PAID_CALL_LIMIT` (vezi main.py și DEPLOYMENT.md).
DEFAULT_DAILY_PAID_CALL_LIMIT = 200
_MIN_SECRET_BYTES = 32
_COOKIE_VERSION = "v1"


@dataclass(frozen=True)
class AccessControlConfig:
    """Configurația fixă și cheile server-side ale controalelor anonime."""

    cookie_signing_key: bytes
    ip_hash_key: bytes
    quota_limit: int = ANONYMOUS_QUOTA_LIMIT
    rate_limit_per_minute: int = RATE_LIMIT_PER_MINUTE
    rate_limit_per_hour: int = RATE_LIMIT_PER_HOUR
    cookie_max_age: timedelta = COOKIE_MAX_AGE
    ip_bucket_retention: timedelta = IP_BUCKET_RETENTION

    def __post_init__(self) -> None:
        _require_secret(self.cookie_signing_key, "cookie_signing_key")
        _require_secret(self.ip_hash_key, "ip_hash_key")
        if hmac.compare_digest(self.cookie_signing_key, self.ip_hash_key):
            raise ValueError("cheia IP trebuie să fie diferită de cheia cookie")
        if self.quota_limit != ANONYMOUS_QUOTA_LIMIT:
            raise ValueError("quota_limit trebuie să fie exact 10")
        if self.rate_limit_per_minute != RATE_LIMIT_PER_MINUTE:
            raise ValueError("rate_limit_per_minute trebuie să fie exact 5")
        if self.rate_limit_per_hour != RATE_LIMIT_PER_HOUR:
            raise ValueError("rate_limit_per_hour trebuie să fie exact 30")
        if self.cookie_max_age != COOKIE_MAX_AGE:
            raise ValueError("cookie_max_age trebuie să fie exact 365 zile")
        if self.ip_bucket_retention != IP_BUCKET_RETENTION:
            raise ValueError("ip_bucket_retention trebuie să fie exact 24 ore")


@dataclass(frozen=True)
class AnonymousVisitor:
    """Identitatea derivată care poate fi stocată; ID-ul brut nu părăsește cookie-ul."""

    visitor_hash: str
    issued_at: datetime


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    minute_bucket_start: datetime
    hour_bucket_start: datetime
    minute_count: int = 0
    hour_count: int = 0


def _require_secret(value: object, name: str) -> bytes:
    if not isinstance(value, bytes) or len(value) < _MIN_SECRET_BYTES:
        raise ValueError(f"{name} trebuie să fie bytes cu cel puțin {_MIN_SECRET_BYTES} octeți")
    if len(set(value)) < 8:
        raise ValueError(f"{name} este prea slab; folosește un secret aleator")
    return value


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("timpul trebuie să includă fusul orar")
    return value.astimezone(UTC)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    if not value or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_" for character in value):
        raise ValueError("base64url invalid")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _mac(key: bytes, payload: bytes) -> bytes:
    return hmac.new(key, payload, hashlib.sha256).digest()


def _visitor_hash(config: AccessControlConfig, visitor_id: bytes) -> str:
    return _mac(config.cookie_signing_key, b"visitor-hash\x00" + visitor_id).hex()


def issue_anonymous_cookie(
    config: AccessControlConfig,
    *,
    now: datetime,
    random_bytes: Callable[[int], bytes] = secrets.token_bytes,
) -> tuple[str, AnonymousVisitor]:
    """Emite un token semnat, cu 256 biți aleatori și data emiterii verificabilă."""
    issued_at = _utc(now)
    visitor_id = random_bytes(32)
    if not isinstance(visitor_id, bytes) or len(visitor_id) != 32:
        raise ValueError("generatorul cookie trebuie să returneze exact 32 octeți")
    payload = f"{_COOKIE_VERSION}.{_b64encode(visitor_id)}.{int(issued_at.timestamp())}".encode("ascii")
    token = payload.decode("ascii") + "." + _b64encode(_mac(config.cookie_signing_key, payload))
    return token, AnonymousVisitor(_visitor_hash(config, visitor_id), issued_at)


def verify_anonymous_cookie(
    token: object, config: AccessControlConfig, *, now: datetime
) -> AnonymousVisitor | None:
    """Validează fail-closed tokenul; valoarea falsificată sau expirată nu este acceptată."""
    if not isinstance(token, str):
        return None
    try:
        version, encoded_id, issued_raw, encoded_signature = token.split(".")
        if version != _COOKIE_VERSION or not issued_raw.isascii() or not issued_raw.isdecimal():
            return None
        issued_timestamp = int(issued_raw)
        visitor_id = _b64decode(encoded_id)
        supplied_signature = _b64decode(encoded_signature)
        if len(visitor_id) != 32 or len(supplied_signature) != hashlib.sha256().digest_size:
            return None
        payload = f"{version}.{encoded_id}.{issued_raw}".encode("ascii")
        if not hmac.compare_digest(supplied_signature, _mac(config.cookie_signing_key, payload)):
            return None
        issued_at = datetime.fromtimestamp(issued_timestamp, UTC)
        checked_now = _utc(now)
        if issued_at > checked_now or checked_now - issued_at > config.cookie_max_age:
            return None
        return AnonymousVisitor(_visitor_hash(config, visitor_id), issued_at)
    except (OverflowError, ValueError):
        return None


def canonicalize_ip(value: object) -> str:
    """Acceptă numai o adresă IP literală și returnează forma canonică, fără zona IPv6."""
    if not isinstance(value, str) or not value or value != value.strip() or "%" in value:
        raise ValueError("IP invalid")
    try:
        return str(ipaddress.ip_address(value))
    except ValueError as error:
        raise ValueError("IP invalid") from error


def hash_ip(value: object, config: AccessControlConfig) -> str:
    """Derivă identificatorul DB HMAC-SHA-256; IP-ul brut nu este returnat."""
    canonical_ip = canonicalize_ip(value)
    return _mac(config.ip_hash_key, b"ip-hash\x00" + canonical_ip.encode("ascii")).hex()


def rate_limit_windows(now: datetime) -> RateLimitResult:
    """Produce ferestre UTC stabile pentru bucket-urile minute și oră."""
    instant = _utc(now)
    minute = instant.replace(second=0, microsecond=0)
    hour = minute.replace(minute=0)
    return RateLimitResult(True, minute, hour)


class PostgresAccessControlRepository:
    """Repository DB-API fără commit implicit; callerul controlează tranzacțiile."""

    _RESERVE_QUESTION_SQL = """
        INSERT INTO public.anonymous_usage AS usage (visitor_hash, questions_used)
        VALUES (%s, 1)
        ON CONFLICT (visitor_hash) DO UPDATE
        SET questions_used = usage.questions_used + 1, updated_at = now()
        WHERE usage.questions_used < %s
        RETURNING questions_used
    """
    _RESERVE_PAID_CALL_SQL = """
        INSERT INTO public.paid_call_budget AS budget (bucket_date, request_count)
        VALUES (%s, 1)
        ON CONFLICT (bucket_date) DO UPDATE
        SET request_count = budget.request_count + 1, updated_at = now()
        WHERE budget.request_count < %s
        RETURNING request_count
    """
    _LOCK_IP_SQL = """
        SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))
    """
    _ENSURE_BUCKETS_SQL = """
        INSERT INTO public.rate_limit_buckets (
            ip_hash, bucket_kind, bucket_start, request_count, expires_at
        )
        VALUES
            (%s, 'minute', %s, 0, %s + interval '24 hours'),
            (%s, 'hour', %s, 0, %s + interval '24 hours')
        ON CONFLICT (ip_hash, bucket_kind, bucket_start) DO NOTHING
    """
    _INCREMENT_AND_READ_BUCKETS_SQL = """
        UPDATE public.rate_limit_buckets
        SET request_count = request_count + 1, updated_at = now()
        WHERE ip_hash = %s
          AND ((bucket_kind = 'minute' AND bucket_start = %s)
            OR (bucket_kind = 'hour' AND bucket_start = %s))
        RETURNING bucket_kind, request_count
    """
    _CLEANUP_SQL = """
        DELETE FROM public.rate_limit_buckets
        WHERE expires_at <= %s
    """

    def __init__(self, connection: object) -> None:
        self._connection = connection

    def reserve_question(self, visitor_hash: str) -> int | None:
        """Rezervă atomic o întrebare și returnează numărul folosit, fără commit implicit."""
        _require_hash(visitor_hash, "visitor_hash")
        cursor = self._connection.cursor()
        try:
            cursor.execute(self._RESERVE_QUESTION_SQL, (visitor_hash, ANONYMOUS_QUOTA_LIMIT))
            row = cursor.fetchone()
            return int(row[0]) if row is not None else None
        finally:
            cursor.close()

    def reserve_paid_call(self, *, now: datetime, daily_limit: int) -> int | None:
        """Rezervă atomic un apel plătit (Voyage/Anthropic) pentru ziua calendaristică UTC
        curentă; `None` înseamnă că plafonul zilei a fost deja atins, fără commit implicit."""
        if type(daily_limit) is not int or daily_limit <= 0:
            raise ValueError("daily_limit trebuie să fie întreg pozitiv")
        bucket_date = _utc(now).date()
        cursor = self._connection.cursor()
        try:
            cursor.execute(self._RESERVE_PAID_CALL_SQL, (bucket_date, daily_limit))
            row = cursor.fetchone()
            return int(row[0]) if row is not None else None
        finally:
            cursor.close()

    def check_and_increment_rate_limit(self, ip_hash: str, *, now: datetime) -> RateLimitResult:
        """Actualizează ambele ferestre atomic; se folosește într-o tranzacție dedicată."""
        _require_hash(ip_hash, "ip_hash")
        windows = rate_limit_windows(now)
        cursor = self._connection.cursor()
        try:
            # Lock-ul per hash face cele patru operații atomice în tranzacția callerului.
            cursor.execute(self._LOCK_IP_SQL, (ip_hash,))
            cursor.execute(
                self._ENSURE_BUCKETS_SQL,
                (ip_hash, windows.minute_bucket_start, windows.minute_bucket_start,
                 ip_hash, windows.hour_bucket_start, windows.hour_bucket_start),
            )
            # Fiecare tentativă validă crește ambele bucket-uri, inclusiv una blocată.
            cursor.execute(
                self._INCREMENT_AND_READ_BUCKETS_SQL,
                (ip_hash, windows.minute_bucket_start, windows.hour_bucket_start),
            )
            counts = dict(cursor.fetchall())
            allowed = (
                set(counts) == {"minute", "hour"}
                and counts["minute"] <= RATE_LIMIT_PER_MINUTE
                and counts["hour"] <= RATE_LIMIT_PER_HOUR
            )
            return RateLimitResult(
                allowed,
                windows.minute_bucket_start,
                windows.hour_bucket_start,
                int(counts.get("minute", 0)),
                int(counts.get("hour", 0)),
            )
        finally:
            cursor.close()

    def cleanup_expired_rate_limit_buckets(self, *, now: datetime) -> int:
        """Șterge doar bucket-uri expirate; callerul alege explicit commit-ul."""
        cursor = self._connection.cursor()
        try:
            cursor.execute(self._CLEANUP_SQL, (_utc(now),))
            return int(cursor.rowcount)
        finally:
            cursor.close()


def _require_hash(value: object, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{name} invalid")
    try:
        int(value, 16)
    except ValueError as error:
        raise ValueError(f"{name} invalid") from error
    return value
