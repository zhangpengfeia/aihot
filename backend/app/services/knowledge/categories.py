"""免费 MediaWiki 分类接口；进程内缓存，失败时保留上次成功结果。"""

from datetime import timedelta
from threading import Lock
from time import monotonic

import httpx

from app.utils.time import utcnow

API_URL = "https://zh.wikipedia.org/w/api.php"
SOURCE_URL = "https://zh.wikipedia.org/wiki/Category:主要话题分类"
# 对齐现有资料标签，避免同一分类以繁简两种名称重复出现。
ALIASES = {"商業": "商业", "歷史": "历史"}


class CategoryCatalog:
    def __init__(self):
        self._lock = Lock()
        self._categories = []
        self._updated_at = None
        self._retry_at = 0.0
        self._error = None

    def get(self, client=None):
        if monotonic() >= self._retry_at and self._lock.acquire(blocking=False):
            try:
                try:
                    if client is None:
                        with httpx.Client(
                            timeout=4,
                            headers={"User-Agent": "AIHot/0.1 (knowledge category catalog)"},
                            follow_redirects=False,
                        ) as remote:
                            categories = fetch_categories(remote)
                    else:
                        categories = fetch_categories(client)
                    self._categories = categories
                    self._updated_at = utcnow()
                    self._error = None
                    self._retry_at = monotonic() + timedelta(days=1).total_seconds()
                except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
                    self._error = f"远程分类同步失败（{type(exc).__name__}），已使用缓存或本地分类"
                    self._retry_at = monotonic() + 300
            finally:
                self._lock.release()
        return {
            "categories": list(self._categories),
            "status": "stale"
            if self._error and self._categories
            else ("fallback" if not self._categories else "success"),
            "source_name": "维基百科主要话题分类",
            "source_url": SOURCE_URL,
            "updated_at": self._updated_at,
            "error": self._error,
        }


def fetch_categories(client):
    categories = set()
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": "Category:主要话题分类",
        "cmtype": "subcat",
        "cmlimit": "500",
        "format": "json",
        "formatversion": "2",
    }
    for _ in range(5):
        response = client.get(API_URL, params=params)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or "error" in payload:
            raise ValueError("MediaWiki 接口异常")
        query = payload.get("query")
        if not isinstance(query, dict):
            raise ValueError("分类响应格式异常")
        members = query.get("categorymembers")
        if not isinstance(members, list):
            raise ValueError("分类列表格式异常")
        for member in members:
            if not isinstance(member, dict):
                raise ValueError("分类条目格式异常")
            title = member.get("title")
            if member.get("ns") != 14 or not isinstance(title, str) or ":" not in title:
                continue
            name = title.split(":", 1)[1].strip()
            if name in {"主要话题条目", "主要話題條目"}:
                continue
            if name and len(name) <= 50:
                categories.add(ALIASES.get(name, name))
        continuation = payload.get("continue")
        if not continuation:
            if not categories:
                raise ValueError("远程分类为空")
            return sorted(categories)
        if not isinstance(continuation, dict) or not isinstance(
            continuation.get("cmcontinue"), str
        ):
            raise ValueError("分类分页格式异常")
        params["cmcontinue"] = continuation["cmcontinue"]
        params["continue"] = continuation.get("continue", "-||")
    raise ValueError("分类分页超过上限")


catalog = CategoryCatalog()


def get_category_catalog():
    return catalog.get()
