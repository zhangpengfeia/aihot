"""出站 DNS、固定 IP、重定向和流大小限制，全部使用受控传输。"""

import socket

import httpx
import pytest

from app.infrastructure import feed_http
from app.infrastructure.feed_http import PublicFeedTransport, fetch_feed, public_addresses


def test_transport_pins_ip_and_preserves_host_and_tls_name(monkeypatch):
    resolutions = []

    def dns(host, port, **kwargs):
        resolutions.append(host)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]

    monkeypatch.setattr(feed_http.socket, "getaddrinfo", dns)
    calls = []

    def respond(request):
        calls.append(request)
        assert request.url.host == "8.8.8.8"
        assert request.headers["host"] == "example.com"
        assert request.extensions["sni_hostname"] == "example.com"
        return httpx.Response(200, content=b"RSS")

    with httpx.Client(transport=PublicFeedTransport(httpx.MockTransport(respond))) as client:
        assert fetch_feed("https://example.com/feed", client) == b"RSS"
    assert resolutions == ["example.com"]
    assert len(calls) == 1


@pytest.mark.parametrize(
    "ip",
    ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fc00::1", "224.0.0.1", "64:ff9b::7f00:1"],
)
def test_private_or_special_dns_addresses_rejected(monkeypatch, ip):
    monkeypatch.setattr(
        feed_http.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))],
    )
    with pytest.raises(ValueError, match="非公网"):
        public_addresses("example.com", 443)


def test_mixed_public_private_dns_rejected(monkeypatch):
    monkeypatch.setattr(
        feed_http.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))
            for ip in ["8.8.8.8", "192.168.0.1"]
        ],
    )
    with pytest.raises(ValueError):
        public_addresses("example.com", 443)


def test_redirect_to_private_literal_never_requested():
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(302, headers={"Location": "http://127.0.0.1/admin"})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client, pytest.raises(ValueError):
        fetch_feed("https://example.com/feed", client)
    assert len(calls) == 1


def test_redirect_domain_revalidated_and_blocked(monkeypatch):
    monkeypatch.setattr(
        feed_http.socket,
        "getaddrinfo",
        lambda host, *args, **kwargs: [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                ("8.8.8.8" if host == "example.com" else "10.0.0.1", 443),
            )
        ],
    )
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(302, headers={"Location": "https://other.example/feed"})

    with (
        httpx.Client(transport=PublicFeedTransport(httpx.MockTransport(respond))) as client,
        pytest.raises(ValueError),
    ):
        fetch_feed("https://example.com/feed", client)
    assert len(calls) == 1


def test_public_relative_redirect_and_size_limit():
    def respond(request):
        return (
            httpx.Response(302, headers={"Location": "/final"})
            if request.url.path == "/feed"
            else httpx.Response(200, content=b"x" * 2_000_001)
        )

    with (
        httpx.Client(transport=httpx.MockTransport(respond)) as client,
        pytest.raises(ValueError, match="2MB"),
    ):
        fetch_feed("https://example.com/feed", client)


def test_redirect_loop_stops_after_four_requests():
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(302, headers={"Location": "/feed"})

    with (
        httpx.Client(transport=httpx.MockTransport(respond)) as client,
        pytest.raises(ValueError, match="重定向"),
    ):
        fetch_feed("https://example.com/feed", client)
    assert len(calls) == 4


def test_transport_tries_another_validated_ip(monkeypatch):
    from app.infrastructure import feed_http

    calls = []
    monkeypatch.setattr(
        feed_http, "public_addresses", lambda *args: ["2001:4860:4860::8888", "1.1.1.1", "8.8.8.8"]
    )

    def respond(request):
        calls.append(request.url.host)
        if request.url.host == "1.1.1.1":
            raise httpx.ConnectError("unreachable", request=request)
        assert request.headers["host"] == "example.com"
        assert request.extensions["sni_hostname"] == "example.com"
        return httpx.Response(200, content=b"ok")

    with httpx.Client(
        transport=feed_http.PublicFeedTransport(httpx.MockTransport(respond))
    ) as client:
        assert client.get("https://example.com/feed").content == b"ok"
    assert calls == ["1.1.1.1", "8.8.8.8"]
