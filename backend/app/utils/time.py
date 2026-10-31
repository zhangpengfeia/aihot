"""UTC 时间与半小时时间窗口工具。"""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def time_slot(now: datetime) -> datetime:
    return now.replace(minute=now.minute // 30 * 30, second=0, microsecond=0)


SHANGHAI = ZoneInfo("Asia/Shanghai")


def iso(value: datetime | None):
    return value.replace(tzinfo=UTC).isoformat() if value else None


def week_slot(now: datetime) -> datetime:
    local = now.replace(tzinfo=UTC).astimezone(SHANGHAI)
    monday = (local - timedelta(days=local.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return monday.astimezone(UTC).replace(tzinfo=None)
