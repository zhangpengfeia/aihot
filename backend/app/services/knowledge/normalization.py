"""来源文本、日期、地区与订阅格式标准化。"""

import hashlib
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree as ET

from app.services.knowledge.management import source_key
from app.services.knowledge.sources import FeedSource

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
