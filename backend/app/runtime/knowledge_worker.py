"""知识库独立调度，无 GitHub Token 也可以运行；与 GitHub worker 隔离。"""

import argparse
import logging
import time
from datetime import timedelta

from app.core.config import get_settings
from app.services.knowledge.collector import collect_knowledge
from app.utils.time import time_slot, utcnow


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    while True:
        failed = False
        try:
            result = collect_knowledge(get_settings())
            logging.info("知识采集结果：%s", result)
            failed = result["failed"] > 0
        except Exception:
            logging.exception("知识采集异常，等待下次调度")
            failed = True
        if args.once:
            if failed:
                raise SystemExit(1)
            return
        next_slot = time_slot(utcnow()) + timedelta(minutes=30)
        time.sleep(max(1, (next_slot - utcnow()).total_seconds()))


if __name__ == "__main__":
    main()
