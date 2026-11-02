"""长青知识来源与选题角度在现有采集链路中的兼容性。"""

from app.core.evergreen_sources import EVERGREEN_SOURCES
from app.core.sources import DEFAULT_SOURCES, FeedSource
from app.services.knowledge.adapters import collect_source


def test_evergreen_catalog_and_explainer_angles():
    urls = [row["url"] for row in EVERGREEN_SOURCES]
    assert len(urls) >= 40 and len(set(urls)) == len(urls)
    assert {row["region"] for row in EVERGREEN_SOURCES} == {"国内", "国外"}
    assert all(row in DEFAULT_SOURCES for row in EVERGREEN_SOURCES)
    for raw in EVERGREEN_SOURCES:
        source = FeedSource(**raw)
        assert source.enabled and source.topic_kind == "知识探索"
        records = collect_source(
            source,
            lambda _: (
                b"""<rss version="2.0"><channel><item>
          <title>How computers evolved</title><link>https://example.org/computer-history</link>
          <description>A timeline with original evidence.</description>
          </item></channel></rss>"""
            ),
        )
        assert len(records) == 1
        assert records[0]["topic_kind"] == "知识探索"
        assert records[0]["category"] == source.category
        assert "How computers evolved" in records[0]["video_angle"]
        assert records[0]["source_name"] == source.name
