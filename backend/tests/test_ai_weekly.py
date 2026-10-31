"""周榜真实排名、周增长与模型扩展输出的契约验证。"""

from datetime import datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import Ranking, Run, Snapshot
from app.services.skills.analysis import ProjectAnalysis, analyze_project
from app.services.skills.collector import persist
from app.utils.time import week_slot


def test_scene_tags_and_model_adapter():
    analysis = analyze_project({"full_name": "demo/tts", "description": "AI text-to-speech"}, "")
    assert "配音" in analysis["tags"]
    assert "AI短视频与影音制作" in analysis["domains"]
    assert any("旁白" in case for case in analysis["use_cases"])
    assert analysis["knowledge_suggestions"]

    class ModelAdapter:
        def analyze(self, repo, readme):
            return ProjectAnalysis(
                source="llm",
                version="v2",
                model="future-model",
                tags=["二维动画"],
                core_features=["角色动画"],
                use_cases=["儿童知识动画"],
                knowledge_suggestions=["自然科普"],
            )

    result = analyze_project({"full_name": "demo/test"}, "untrusted README", ModelAdapter())
    assert result["source"] == "llm"
    assert result["tags"] == ["二维动画"]


def test_top100_week_growth_and_snapshot_analysis():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    start = datetime(2026, 10, 25, 16)
    with Session(engine) as db:
        for week, stars in [(0, 100), (1, 90)]:
            at = start + timedelta(days=7 * week)
            run = Run(slot=at, started_at=at, scope="ai-video-weekly-v2")
            db.add(run)
            db.flush()
            records = [
                (
                    {
                        "id": i,
                        "full_name": f"demo/tts-{i}",
                        "description": "AI text-to-speech",
                        "stargazers_count": stars,
                        "forks_count": 0,
                    },
                    "",
                    "test",
                    at,
                )
                for i in range(1, 106)
            ]
            persist(db, run.id, 105, records)
            db.commit()
            board = list(
                db.scalars(
                    select(Ranking)
                    .where(Ranking.run_id == run.id, Ranking.kind == "stars")
                    .order_by(Ranking.position)
                )
            )
            assert len(board) == 100
            assert db.get(Snapshot, board[0].snapshot_id).repo_id == 1
        current = db.get(Snapshot, board[0].snapshot_id)
        assert current.delta_7d == -10
        assert current.baseline_7d_at == start
        assert current.analysis["tags"] == ["配音"]
        assert current.analysis["source"] == "rules"
        growth = list(
            db.scalars(select(Ranking).where(Ranking.run_id == run.id, Ranking.kind == "growth"))
        )
        assert len(growth) == 100
    engine.dispose()


def test_week_bucket_uses_beijing_monday():
    assert week_slot(datetime(2026, 11, 1, 15, 59)) == datetime(2026, 10, 25, 16)
    assert week_slot(datetime(2026, 11, 1, 16)) == datetime(2026, 11, 1, 16)


def test_default_search_is_video_only():
    from app.core.config import Settings
    from app.infrastructure.github import classify

    queries = Settings(_env_file=None).search_queries
    assert not any(
        word in query
        for query in queries
        for word in ("office", "spreadsheet", "presentation", "meeting", "document")
    )
    assert any("skills" in query for query in queries)
    for description in [
        "AI spreadsheet assistant",
        "AI office automation",
        "LLM knowledge base RAG",
        "AI presentation generator",
    ]:
        assert classify({"full_name": "example/office", "description": description}, "") is None
    for description in [
        "AI text-to-video",
        "AI voiceover text-to-speech",
        "AI subtitle transcription",
        "SKILL.md for Remotion animation",
    ]:
        assert classify({"full_name": "example/video", "description": description}, "")
