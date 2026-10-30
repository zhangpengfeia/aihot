"""GitHub 每日调度按北京时间计算，手动采集无需等待。"""

from datetime import datetime
from types import SimpleNamespace

import pytest

from app.runtime import github_worker as worker


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        ("2026-10-30T15:59:59", "2026-10-30T16:00:00"),
        ("2026-10-30T16:00:00", "2026-10-30T16:00:00"),
        ("2026-10-30T16:00:01", "2026-10-31T16:00:00"),
        ("2026-12-31T19:00:00", "2027-01-01T16:00:00"),
    ],
)
def test_next_collection_beijing_midnight(now, expected):
    assert worker.next_collection_at(datetime.fromisoformat(now)) == datetime.fromisoformat(
        expected
    )


def test_worker_waits_before_first_collection(monkeypatch):
    calls = []
    monkeypatch.setattr("sys.argv", ["worker"])
    monkeypatch.setattr(worker, "get_settings", lambda: SimpleNamespace(github_token="test"))
    monkeypatch.setattr(worker, "utcnow", lambda: datetime(2026, 10, 30, 10))

    def wait(target):
        calls.append(("wait", target))

    def collect(settings):
        calls.append(("collect", None))
        raise KeyboardInterrupt

    monkeypatch.setattr(worker, "wait_until", wait)
    monkeypatch.setattr(worker, "collect", collect)
    with pytest.raises(KeyboardInterrupt):
        worker.main()
    assert calls == [("wait", datetime(2026, 10, 30, 16)), ("collect", None)]


def test_once_collects_immediately(monkeypatch):
    calls = []
    monkeypatch.setattr("sys.argv", ["worker", "--once"])
    monkeypatch.setattr(worker, "get_settings", lambda: SimpleNamespace(github_token="test"))
    monkeypatch.setattr(worker, "collect", lambda settings: calls.append("collect"))
    monkeypatch.setattr(
        worker, "wait_until", lambda target: pytest.fail("manual run must not wait")
    )
    worker.main()
    assert calls == ["collect"]


@pytest.mark.parametrize("fail_first", [False, True])
def test_next_run_is_tomorrow_even_after_failure(monkeypatch, fail_first):
    from datetime import timedelta

    now = [datetime(2026, 10, 30, 10)]
    scheduled = []
    count = [0]
    monkeypatch.setattr("sys.argv", ["worker"])
    monkeypatch.setattr(worker, "get_settings", lambda: SimpleNamespace(github_token="test"))
    monkeypatch.setattr(worker, "utcnow", lambda: now[0])

    def wait(target):
        scheduled.append(target)
        now[0] = target + timedelta(seconds=1)

    def collect(settings):
        count[0] += 1
        if count[0] == 2:
            raise KeyboardInterrupt
        if fail_first:
            raise RuntimeError("network error")
        return True

    monkeypatch.setattr(worker, "wait_until", wait)
    monkeypatch.setattr(worker, "collect", collect)
    with pytest.raises(KeyboardInterrupt):
        worker.main()
    assert scheduled == [datetime(2026, 10, 30, 16), datetime(2026, 10, 31, 16)]
