"""可选的 MySQL 8.0 集成测试：必须使用专用空的 *_test 数据库。"""

import os
from datetime import timedelta

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import Base
from app.models import Run, Snapshot
from app.services.skills import collector


@pytest.mark.skipif(os.getenv("AIHOT_TEST_MYSQL") != "1", reason="未配置专用 MySQL 测试库")
def test_mysql_collection_atomicity_and_lock(monkeypatch):
    settings = Settings()
    if not settings.mysql_database.endswith("_test"):
        pytest.fail("MYSQL_DATABASE 必须以 _test 结尾，禁止使用业务数据库")
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    if inspect(engine).get_table_names():
        pytest.fail("集成测试必须使用空数据库，不会清理已有数据")
    Base.metadata.create_all(engine)

    class FakeGitHub:
        broken = False

        def discover(self, queries):
            if self.broken:
                raise RuntimeError("测试网络故障")
            return [self.get("")]

        def get(self, path):
            return {"id": 1, "full_name": "sample/skills", "stargazers_count": 20, "forks_count": 1}

        def readme(self, name):
            return "Use SKILL.md"

    github = FakeGitHub()
    try:
        assert collector.collect(settings, engine, github)
        assert not collector.collect(settings, engine, github)  # 窗口幂等
        with engine.connect() as other:
            assert other.scalar(text("SELECT GET_LOCK('aihot.collect', 0)")) == 1
            assert not collector.collect(settings, engine, github)
            other.execute(text("SELECT RELEASE_LOCK('aihot.collect')"))
        later = collector.utcnow() + timedelta(minutes=30)
        monkeypatch.setattr(collector, "utcnow", lambda: later)
        github.broken = True
        with pytest.raises(RuntimeError, match="测试网络故障"):
            collector.collect(settings, engine, github)
        with Session(engine) as db:
            assert len(list(db.scalars(select(Snapshot)))) == 1
            assert list(db.scalars(select(Run.status).order_by(Run.slot))) == ["success", "failed"]
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
