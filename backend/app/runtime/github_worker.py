"""GitHub 独立采集进程：每周一北京时间 00:00 执行；--once 立即执行。"""

import argparse
import logging
import time
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.services.skills.collector import collect
from app.utils.time import utcnow

logger = logging.getLogger(__name__)


SHANGHAI = ZoneInfo("Asia/Shanghai")


def next_collection_at(now: datetime) -> datetime:
    """返回不早于当前时间的北京时间周一 00:00，以 UTC 无时区值供调度。"""
    local = now.replace(tzinfo=UTC).astimezone(SHANGHAI)
    target = local.replace(hour=0, minute=0, second=0, microsecond=0)
    target += timedelta(days=(7 - local.weekday()) % 7)
    if target < local:
        target += timedelta(days=7)
    return target.astimezone(UTC).replace(tzinfo=None)


def wait_until(target: datetime):
    while (remaining := (target - utcnow()).total_seconds()) > 0:
        # 分段等待，系统时钟调整后重新计算距离执行时间。
        time.sleep(min(remaining, 60))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="只执行当前批次")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    if not settings.github_token:
        raise SystemExit("请先在 .env 配置 GITHUB_TOKEN；默认采集量超过匿名 API 额度")
    target = next_collection_at(utcnow())
    while True:
        if not args.once:
            logger.info("下次 GitHub 采集：%s", target.replace(tzinfo=UTC).astimezone(SHANGHAI))
            wait_until(target)
        try:
            changed = collect(settings)
            logger.info("本轮完成，是否更新：%s", changed)
        except Exception:
            logger.exception("采集失败，上一期榜单仍然可用")
            if args.once:
                raise
        if args.once:
            break
        # 严格选择后续执行点，避免瞬间完成时重复触发同一个 00:00。
        target = next_collection_at(utcnow() + timedelta(microseconds=1))


if __name__ == "__main__":
    main()
