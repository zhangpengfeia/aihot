"""知识资料采集：RSS/Atom 摘要摘录与选题提示，不将新发布等同于热门。

不抓取付费全文，不调用文章内链接。标题、摘要均保留原始语言，切入角度是
规则模板建议，不代表原文事实结论。各来源单独提交，避免单源失败阻断全部数据。
"""

import hashlib
import logging
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree as ET

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.feed_http import feed_client, fetch_feed
from app.knowledge_management import active_sources, source_key
from app.knowledge_sources import FeedSource
from app.models import (
    KnowledgeCitation,
    KnowledgeSourceState,
    KnowledgeTopic,
    ManagedKnowledgeSource,
)
from app.time_utils import time_slot, utcnow

logger = logging.getLogger(__name__)


ANGLE_TEMPLATES = {
    "科技": "用一个实际场景解释“{title}”：它解决了什么问题？和已有方法相比改变了哪一步？用演示展示原理，结论以原文为准。",
    "商业": "从“{title}”切入：谁的成本、需求或收入发生变化？用一个普通人的消费场景解释，并核对原文数据及日期。",
    "历史": "围绕“{title}”讲一个时间线故事：先抛出一个疑问，再交代背景、证据与影响，区分史料事实和推测。",
    "自然": "从“{title}”提一个为什么：用日常比喻解释机制，再用原始观察或研究支撑，标出尚未确定之处。",
    "生活": "把“{title}”转成一个日常问题：先展示困扰，再梳理原文提供的解释或方法，用可验证的示例收尾。",
}


def plain_text(value: str) -> str:
    """移除标签和脚本，只保存文本；前端仍使用 React 转义而非 HTML 注入。"""
    value = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", value, flags=re.I | re.S)
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def canonical_url(value: str) -> str | None:
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username:
            return None
        query = [(k, v) for k, v in parse_qsl(parsed.query) if not k.lower().startswith("utm_")]
        return urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path, urlencode(query), ""))
    except ValueError:
        return None


def parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (ValueError, TypeError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    # 不知道时区时不猜测发布日期，缺失日期保留为空。
    return parsed.astimezone(UTC).replace(tzinfo=None) if parsed.tzinfo else None


def classify_region(title: str, summary: str, source: FeedSource) -> tuple[str, str]:
    """地区为选题整理标签；跨国话题优先归入涉及中国的国内题材，并保留依据。"""
    content = f"{title} {summary}"
    if re.search(
        r"中国|国内|北京|上海|深圳|广州|杭州|国产|\b(?:china|chinese|beijing|shanghai)\b",
        content,
        re.I,
    ):
        return "国内", "标题或摘要包含中国相关关键词"
    if re.search(
        r"美国|英国|日本|德国|法国|韩国|海外|国外|\b(?:nasa|american|british|japan|european|united states|united kingdom)\b",
        content,
        re.I,
    ):
        return "国外", "标题或摘要包含海外地区关键词"
    return source.region, "无明确地区关键词，使用来源默认地区"


def parse_feed(content: bytes, source: FeedSource) -> list[dict]:
    """支持 RSS 2.0 和 Atom；限制大小并拒绝 DTD/实体声明。"""
    if len(content) > 2_000_000 or re.search(rb"<!\s*(DOCTYPE|ENTITY)", content, re.I):
        raise ValueError("订阅源过大或包含不支持的 XML 声明")
    root = ET.fromstring(content)
    if root.tag not in ("rss", "{http://www.w3.org/2005/Atom}feed"):
        raise ValueError("来源未返回 RSS/Atom")
    result = []
    atom = {"a": "http://www.w3.org/2005/Atom"}
    entries = root.findall("./channel/item") if root.tag == "rss" else root.findall("a:entry", atom)
    for item in entries[: source.item_limit]:
        if root.tag == "rss":
            title, url = item.findtext("title", ""), item.findtext("link", "")
            summary = item.findtext("description", "")
            published = item.findtext("pubDate", "")
        else:
            title = item.findtext("a:title", "", atom)
            link = next(
                (
                    e
                    for e in item.findall("a:link", atom)
                    if e.get("rel", "alternate") == "alternate"
                ),
                None,
            )
            url = link.get("href", "") if link is not None else ""
            summary = item.findtext("a:summary", "", atom) or item.findtext("a:content", "", atom)
            published = item.findtext("a:published", "", atom)
        title, url = plain_text(title)[:500], canonical_url(url.strip())
        if not title or not url:
            continue
        region, region_basis = classify_region(title, plain_text(summary), source)
        result.append(
            {
                "region": region,
                "region_basis": region_basis,
                "url_hash": hashlib.sha256(url.encode()).hexdigest(),
                "source_url": url,
                "source_name": source.name,
                "feed_source_key": source_key(source.url),
                "category": source.category,
                "topic_kind": source.topic_kind,
                "title": title,
                "summary": plain_text(summary)[:600] or "订阅源未提供摘要，请阅读原文。",
                "published_at": parse_date(published),
                "video_angle": ANGLE_TEMPLATES.get(
                    source.category,
                    "围绕“{title}”提出一个问题，结合原始资料解释原因、举例并核对事实。",
                ).format(title=title),
            }
        )
    return result


def save_topics(session: Session, records: list[dict], now: datetime) -> int:
    """批量查询减少云数据库往返；原文链接去重，同时保留每个发现渠道。"""
    if not records:
        return 0
    hashes = {row["url_hash"] for row in records}
    entities = {
        item.url_hash: item
        for item in session.scalars(
            select(KnowledgeTopic).where(KnowledgeTopic.url_hash.in_(hashes))
        )
    }
    added = 0
    for raw in records:
        record = {k: v for k, v in raw.items() if k not in {"channel", "score"}}
        entity = entities.get(record["url_hash"])
        if entity is None:
            entity = KnowledgeTopic(**record, collected_at=now, last_seen=now)
            entities[record["url_hash"]] = entity
            session.add(entity)
            added += 1
        elif entity.feed_source_key in (None, record.get("feed_source_key")):
            for key, value in record.items():
                if key != "published_at" or value is not None:
                    setattr(entity, key, value)
        entity.last_seen = now
    session.flush()
    citations = {
        (row.topic_id, row.source_key): row
        for row in session.scalars(
            select(KnowledgeCitation).where(
                KnowledgeCitation.topic_id.in_([e.id for e in entities.values()])
            )
        )
    }
    for raw in records:
        key = raw.get("feed_source_key")
        if not key:
            continue
        entity = entities[raw["url_hash"]]
        citation = citations.get((entity.id, key))
        if citation is None:
            citation = KnowledgeCitation(topic_id=entity.id, source_key=key)
            citations[(entity.id, key)] = citation
            session.add(citation)
        citation.source_name, citation.channel = raw["source_name"], raw.get("channel", "rss")
        citation.score, citation.observed_at = raw.get("score"), now
    session.flush()
    return added


def collect_knowledge(settings, engine=None, client=None) -> dict:
    from app.db import get_engine

    engine = engine or get_engine()
    stats = {"sources": 0, "failed": 0, "added": 0}
    factory = sessionmaker(engine, expire_on_commit=False)
    with engine.connect() as lock:
        if lock.scalar(text("SELECT GET_LOCK('aihot.knowledge', 0)")) != 1:
            return stats
        http = client or feed_client()
        try:
            with factory() as session:
                sources = active_sources(session, settings)
            for source in sources:
                key = source_key(source.url)
                now = utcnow()
                with factory() as session:
                    configured = session.scalar(
                        select(ManagedKnowledgeSource).where(
                            ManagedKnowledgeSource.source_key == key
                        )
                    )
                    if configured is not None and not configured.enabled:
                        continue
                    state = session.get(KnowledgeSourceState, key)
                    if (
                        state
                        and state.last_success
                        and time_slot(state.last_success) == time_slot(now)
                    ):
                        continue
                try:
                    from app.knowledge_adapters import collect_source

                    records = collect_source(source, lambda url: fetch_feed(url, http))
                    if not records:
                        raise ValueError("订阅源中没有有效条目")
                    with factory.begin() as session:
                        added = save_topics(session, records, now)
                        state = session.get(KnowledgeSourceState, key) or KnowledgeSourceState(
                            source_key=key
                        )
                        state.name, state.url, state.category = (
                            source.name,
                            str(source.url),
                            source.category,
                        )
                        state.status, state.last_attempt, state.last_success = (
                            "success",
                            now,
                            utcnow(),
                        )
                        state.item_count, state.error = len(records), None
                        session.add(state)
                    stats["sources"] += 1
                    stats["added"] += added
                    logger.info(
                        "接口采集完成：%s，读取 %s 条，新增 %s 条", source.name, len(records), added
                    )
                except SQLAlchemyError:
                    # 数据库故障不算来源故障；事务已回滚，停止本轮等待下次重连。
                    raise
                except Exception as exc:
                    logger.warning("知识来源采集失败：%s (%s)", source.name, type(exc).__name__)
                    with factory.begin() as session:
                        state = session.get(KnowledgeSourceState, key) or KnowledgeSourceState(
                            source_key=key
                        )
                        state.name, state.url, state.category = (
                            source.name,
                            str(source.url),
                            source.category,
                        )
                        state.status, state.last_attempt, state.error = (
                            "failed",
                            now,
                            type(exc).__name__,
                        )
                        session.add(state)
                    stats["failed"] += 1
        finally:
            if client is None:
                http.close()
            try:
                lock.execute(text("SELECT RELEASE_LOCK('aihot.knowledge')"))
            except SQLAlchemyError:
                logger.warning("数据库连接失效，服务端会在连接关闭后释放采集锁")
    return stats
