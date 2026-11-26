"""Time helpers. Everything is stored in UTC; convert to the business timezone only for display
and for date-based report boundaries."""

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def utcnow() -> datetime:
    return datetime.now(UTC)


def business_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().business_timezone)


def to_business_tz(value: datetime) -> datetime:
    return value.astimezone(business_tz())


def business_day_start_utc(day: date) -> datetime:
    """Midnight of `day` in Kigali, expressed in UTC. Use for report date filters."""
    return datetime.combine(day, time.min, tzinfo=business_tz()).astimezone(UTC)
