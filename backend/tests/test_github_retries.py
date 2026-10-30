"""GET 临时网络故障可恢复；耗尽重试和限流不发布假成功。"""

import httpx
import pytest

from app.core.config import Settings
from app.infrastructure.github import GitHubClient


@pytest.fixture
def client(monkeypatch):
    delays = []
    monkeypatch.setattr("app.infrastructure.github.time.sleep", delays.append)
    github = GitHubClient(Settings(request_interval=0))
    github.client.close()
    yield github, delays
    github.close()


def mock_http(github, respond):
    github.client = httpx.Client(
        base_url="https://api.github.com", transport=httpx.MockTransport(respond)
    )


@pytest.mark.parametrize(
    "error", [httpx.RemoteProtocolError, httpx.ReadTimeout, httpx.ConnectError, httpx.ProxyError]
)
def test_transient_failure_retries_same_request(client, error):
    github, delays = client
    calls = []

    def respond(request):
        calls.append(str(request.url))
        if len(calls) < 6:
            raise error("temporary failure", request=request)
        return httpx.Response(200, json={"items": ["success"]})

    mock_http(github, respond)
    assert github.get("/repos/example/skills/readme", {"ref": "main"}) == {"items": ["success"]}
    assert len(calls) == 6
    assert len(set(calls)) == 1
    assert [delay for delay in delays if delay] == [1, 2, 4, 8, 16]


def test_exhausted_failure_propagates_without_sensitive_logging(client, caplog):
    github, delays = client
    calls = []

    def respond(request):
        calls.append(request)
        raise httpx.RemoteProtocolError("proxy password should not appear", request=request)

    mock_http(github, respond)
    with pytest.raises(httpx.RemoteProtocolError):
        github.get("/repos/example/skills/readme")
    assert len(calls) == 6
    assert [delay for delay in delays if delay] == [1, 2, 4, 8, 16]
    assert "proxy password" not in caplog.text


@pytest.mark.parametrize("status", [401, 403, 429])
def test_authorization_and_limits_are_not_retried(client, status):
    github, delays = client
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(status)

    mock_http(github, respond)
    with pytest.raises((RuntimeError, httpx.HTTPStatusError)):
        github.get("/search/repositories")
    assert len(calls) == 1
    assert not any(delays)


def test_server_error_retry_still_works(client):
    github, delays = client
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(503) if len(calls) == 1 else httpx.Response(200, json={"ok": True})

    mock_http(github, respond)
    assert github.get("/repos/example/skills") == {"ok": True}
    assert len(calls) == 2
    assert [delay for delay in delays if delay] == [1]


def test_server_error_exhausts_five_retries(client, caplog):
    github, delays = client
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(503)

    mock_http(github, respond)
    with pytest.raises(httpx.HTTPStatusError):
        github.get("/repos/example/skills")
    assert len(calls) == 6
    assert [delay for delay in delays if delay] == [1, 2, 4, 8, 16]
    assert "第 5/5 次重试" in caplog.text
    assert "重试 5 次后仍失败" in caplog.text
