"""UTC 时间与半小时时间窗口工具。"""

from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def time_slot(now: datetime) -> datetime:
    return now.replace(minute=now.minute // 30 * 30, second=0, microsecond=0)
