"""公开 API 适配层：不同响应统一为知识记录，所有网络请求复用受限公网传输。

通用 JSON 支持点路径字段映射，不执行表达式；API 响应里的文章链接只保存，
不会继续抓取。Hacker News 子请求固定到官方域名，控制最大条目数。
"""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from urllib.parse import quote, urlsplit

from app.knowledge import (
    ANGLE_TEMPLATES,
    canonical_url,
    classify_region,
    parse_date,
    parse_feed,
    plain_text,
)
from app.knowledge_management import source_key
from app.time_utils import utcnow


def record(source, title, url, summary="", published=None, score=None):
    url = canonical_url(str(url))
    title = plain_text(str(title or ""))[:500]
    if not url or not title:
        return None
    summary = plain_text(str(summary or ""))[:1000] or "接口未提供正文摘要，请阅读原始资料。"
    region, basis = classify_region(title, summary, source)
    if isinstance(published, (int, float)):
        try:
            published = datetime.fromtimestamp(published, UTC).replace(tzinfo=None)
        except (ValueError, OverflowError, OSError):
            published = None
    elif not isinstance(published, datetime):
        published = parse_date(str(published or ""))
    return dict(
        url_hash=hashlib.sha256(url.encode()).hexdigest(),
        source_url=url,
        source_name=source.name,
        feed_source_key=source_key(source.url),
        title=title,
        summary=summary,
        category=source.category,
        region=region,
        region_basis=basis,
        topic_kind=source.topic_kind,
        published_at=published,
        channel=source.adapter,
        score=score if isinstance(score, int) and not isinstance(score, bool) else None,
        video_angle=ANGLE_TEMPLATES.get(
            source.category, "从“{title}”提出一个问题，核对原始证据，用实例解释原因和影响。"
        ).format(title=title),
    )


def value_at(item, path, default=""):
    for key in path.split(".") if path else []:
        if isinstance(item, list) and key.isdigit() and int(key) < len(item):
            item = item[int(key)]
        elif isinstance(item, dict):
            item = item.get(key, default)
        else:
            return default
    return item


def collect_source(source, fetch):
    """fetch 接收 URL 返回有大小限制的字节，方便真实采集与测试共用。"""
    if source.adapter == "rss":
        return parse_feed(fetch(str(source.url)), source)
    url = str(source.url)
    if source.adapter == "hackernews":
        if urlsplit(url).hostname != "hacker-news.firebaseio.com":
            raise ValueError("Hacker News 适配器仅支持官方 Firebase API")
        ids = json.loads(fetch(url))
        if not isinstance(ids, list) or any(type(i) is not int or i < 1 for i in ids):
            raise ValueError("Hacker News 返回了无效的条目列表")

        def fetch_item(item_id):
            item = json.loads(fetch(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"))
            if (
                not isinstance(item, dict)
                or item.get("deleted")
                or item.get("dead")
                or item.get("type") != "story"
            ):
                return None
            # 社区投票是可追溯热度，标题本身不冒充文章摘要。
            summary = (
                item.get("text") or "接口只提供标题与社区指标，未提供文章摘要；请打开原文核实内容。"
            )
            return record(
                source,
                item.get("title", ""),
                item.get("url") or f"https://news.ycombinator.com/item?id={item_id}",
                summary,
                item.get("time"),
                item.get("score"),
            )

        with ThreadPoolExecutor(max_workers=4) as pool:
            return [row for row in pool.map(fetch_item, ids[: min(source.item_limit, 100)]) if row]
    if source.adapter == "wikipedia":
        if urlsplit(url).hostname not in {"en.wikipedia.org", "zh.wikipedia.org"}:
            raise ValueError("百科适配器仅支持 Wikipedia 官方事件 API")
        today = utcnow()
        data = json.loads(fetch(f"{url.rstrip('/')}/{today.month:02d}/{today.day:02d}"))
        events = data.get("events") if isinstance(data, dict) else None
        if not isinstance(events, list):
            raise ValueError("百科 API 未返回历史事件列表")
        rows = []
        for event in events[: source.item_limit]:
            pages = event.get("pages") or []
            page = next(
                (p for p in pages if p.get("content_urls", {}).get("desktop", {}).get("page")), None
            )
            if not page:
                continue
            row = record(
                source,
                f"{event.get('year', '')}年：{event.get('text', '')}",
                page["content_urls"]["desktop"]["page"],
                event.get("text", ""),
            )
            if row:
                # 历史事件年份不等于文章发布日期，故发布日期保留为空。
                rows.append(row)
        return rows
    payload = json.loads(fetch(url))
    options = source.options
    entries = value_at(payload, options.get("items_path", ""), [])
    if not isinstance(entries, list):
        raise ValueError("JSON API 条目路径不是数组，请检查字段映射")
    rows = []
    for item in entries[: source.item_limit]:
        row = record(
            source,
            value_at(item, options.get("title_field", "title")),
            (
                options.get("url_prefix", "")
                + quote(str(value_at(item, options.get("url_field", "url"))), safe="")
            )
            if options.get("url_prefix")
            else value_at(item, options.get("url_field", "url")),
            value_at(item, options.get("summary_field", "summary")),
            value_at(item, options.get("date_field", "published_at")),
            value_at(item, options.get("score_field", ""), None)
            if options.get("score_field")
            else None,
        )
        if row:
            rows.append(row)
    return rows
