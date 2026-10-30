"""远程分类、分页、缓存、异常回退及 API 合并验证。"""

import httpx
import pytest

from app.services.knowledge import categories as module
from app.services.knowledge.categories import CategoryCatalog, fetch_categories


def payload(*names, **extra):
    return {
        "query": {"categorymembers": [{"ns": 14, "title": f"Category:{name}"} for name in names]},
        **extra,
    }


def test_remote_pagination_and_normalization():
    calls = []

    def respond(request):
        calls.append(request)
        if len(calls) == 1:
            assert request.url.params["cmtitle"] == "Category:主要话题分类"
            assert request.url.params["cmtype"] == "subcat"
            return httpx.Response(
                200,
                json=payload(
                    "商業",
                    "自然",
                    "主要话题条目",
                    **{"continue": {"cmcontinue": "next", "continue": "-||"}},
                ),
            )
        assert request.url.params["cmcontinue"] == "next"
        return httpx.Response(200, json=payload("商业", "教育"))

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        assert set(fetch_categories(client)) == {"商业", "自然", "教育"}
    assert len(calls) == 2


def test_cache_and_failed_refresh_keep_success(monkeypatch):
    now = [0]
    monkeypatch.setattr(module, "monotonic", lambda: now[0])
    catalog = CategoryCatalog()
    calls = []

    def respond(request):
        calls.append(request)
        if len(calls) > 1:
            raise httpx.ConnectError("offline", request=request)
        return httpx.Response(200, json=payload("教育"))

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        first = catalog.get(client)
        assert first["status"] == "success"
        assert catalog.get(client) == first
        assert len(calls) == 1
        now[0] += 86401
        stale = catalog.get(client)
        assert stale["status"] == "stale"
        assert stale["categories"] == ["教育"]
        assert stale["updated_at"] == first["updated_at"]
        catalog.get(client)
        assert len(calls) == 2


@pytest.mark.parametrize(
    "body", [{}, {"error": {}}, payload(), {"query": {"categorymembers": ["invalid"]}}]
)
def test_invalid_remote_falls_back_and_throttles(body):
    catalog = CategoryCatalog()
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json=body)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = catalog.get(client)
        assert result["status"] == "fallback"
        assert result["categories"] == []
        assert result["error"]
        catalog.get(client)
        assert len(calls) == 1


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(429),
        httpx.Response(500),
        httpx.Response(200, text="invalid json"),
        httpx.Response(200, json={"query": None}),
    ],
)
def test_remote_errors_do_not_break_catalog(response):
    with httpx.Client(transport=httpx.MockTransport(lambda request: response)) as client:
        assert CategoryCatalog().get(client)["status"] == "fallback"
