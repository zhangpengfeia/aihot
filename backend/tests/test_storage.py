"""容量清理按时间淘汰、保留用户资料、完整删除外键依赖；不连接业务库。"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import Base
from app.models import (
    CreationCard,
    KnowledgeCitation,
    KnowledgeTopic,
    PersonalItem,
    Ranking,
    Run,
    Snapshot,
)
from app.services import storage
from app.services.skills.collector import persist

AT = datetime(2026, 10, 1)


@pytest.fixture
def engine(monkeypatch):
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    monkeypatch.setattr(storage, "utcnow", lambda: AT + timedelta(days=30))
    yield engine
    engine.dispose()


def topic(session, index, age=0):
    item = KnowledgeTopic(
        url_hash=str(index),
        source_url=f"https://example.com/{index}",
        source_name="Test",
        title=f"测试 {index}",
        category="自然",
        topic_kind="知识探索",
        summary="旧数据" * 1000,
        video_angle="test",
        collected_at=AT + timedelta(days=age),
        last_seen=AT,
    )
    session.add(item)
    session.flush()
    session.add(
        KnowledgeCitation(
            topic_id=item.id, source_key="test", source_name="Test", channel="rss", observed_at=AT
        )
    )
    return item.id


def test_unicode_bytes_and_status(engine):
    with Session(engine) as session:
        topic(session, 1)
        session.commit()
        status = storage.storage_status(session, Settings())
        assert status["used_bytes"] > len(("旧数据" * 1000).encode("utf-8"))
        assert status["limit_bytes"] == 5_000_000_000
        assert status["cleanup_target_bytes"] == 4_500_000_000
        assert status["measurement"] == "estimated_live_data"


def test_cleanup_keeps_notes_favorites_cards_and_newest(engine):
    with Session(engine) as session:
        ids = [topic(session, i, age=i) for i in range(5)]
        session.add_all(
            [
                PersonalItem(
                    target_kind="topic",
                    target_id=ids[0],
                    favorite=True,
                    note="",
                    created_at=AT,
                    updated_at=AT,
                ),
                PersonalItem(
                    target_kind="topic",
                    target_id=ids[1],
                    favorite=False,
                    note="保留备注",
                    created_at=AT,
                    updated_at=AT,
                ),
                CreationCard(topic_id=ids[2], created_at=AT, updated_at=AT),
            ]
        )
        session.commit()
        before = storage.estimated_size(session)
    # 只需删除一条即可低于目标，受保护的更旧三条不应被误删。
    settings = Settings(
        database_max_size_gb=before / 1_000_000_000, database_cleanup_target_ratio=0.99
    )
    with storage.storage_guard(engine, settings):
        pass
    with Session(engine) as session:
        assert list(session.scalars(select(KnowledgeTopic.id).order_by(KnowledgeTopic.id))) == [
            ids[0],
            ids[1],
            ids[2],
            ids[4],
        ]
        assert (
            session.scalar(select(KnowledgeCitation).where(KnowledgeCitation.topic_id == ids[3]))
            is None
        )
        assert storage.estimated_size(session) < before


def test_oldest_run_deleted_as_complete_batch(engine):
    with Session(engine) as session:
        runs = []
        for index in range(4):
            at = AT + timedelta(days=index)
            run = Run(slot=at, started_at=at)
            session.add(run)
            session.flush()
            persist(
                session,
                run.id,
                1,
                [
                    (
                        {
                            "id": 1,
                            "full_name": "test/skills",
                            "stargazers_count": 10,
                            "forks_count": 0,
                        },
                        "README",
                        "test",
                        at,
                    )
                ],
            )
            runs.append(run.id)
        topic(session, 1, age=10)
        session.commit()
        result = storage.delete_oldest(session)
        session.commit()
        assert result["runs"] == 1
        assert result["snapshots"] == 1
        assert session.get(Run, runs[0]) is None
        assert session.scalar(select(Ranking).where(Ranking.run_id == runs[0])) is None
        assert session.scalar(select(Snapshot).where(Snapshot.run_id == runs[0])) is None
        assert all(session.get(Run, rid) for rid in runs[1:])


def test_protected_capacity_stops_and_oversized_batch_does_not_delete(engine):
    with Session(engine) as session:
        newest = topic(session, 1)
        session.commit()
        before = storage.estimated_size(session)
    settings = Settings(database_max_size_gb=(before - 1) / 1_000_000_000)
    with pytest.raises(storage.StorageLimitError, match="空间仍不足"):
        with storage.storage_guard(engine, settings):
            pytest.fail("must not write")
    with pytest.raises(storage.StorageLimitError, match="本次采集数据超过"):
        with storage.storage_guard(engine, settings, reserve_bytes=before * 2):
            pytest.fail("must not write")
    with Session(engine) as session:
        assert session.get(KnowledgeTopic, newest) is not None


def test_repeated_cleanup_at_same_threshold_does_not_keep_deleting(engine):
    with Session(engine) as session:
        for i in range(4):
            topic(session, i, age=i)
        session.commit()
        before = storage.estimated_size(session)
    settings = Settings(
        database_max_size_gb=before / 1_000_000_000, database_cleanup_target_ratio=0.99
    )
    with storage.storage_guard(engine, settings):
        pass
    with Session(engine) as session:
        count = len(list(session.scalars(select(KnowledgeTopic.id))))
    with storage.storage_guard(engine, settings):
        pass
    with Session(engine) as session:
        assert len(list(session.scalars(select(KnowledgeTopic.id)))) == count
