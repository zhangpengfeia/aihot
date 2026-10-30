"""RSS 出站请求：仅公网 HTTP(S)，固定解析地址，每一跳重新校验。"""

import ipaddress
import socket
from time import monotonic
from urllib.parse import urljoin, urlsplit

import httpx

MAX_BYTES = 2_000_000


def public_ip(value):
    address = ipaddress.ip_address(value)
    if not address.is_global or address.is_multicast or address.is_reserved:
        return False
    if isinstance(address, ipaddress.IPv6Address):
        if address.sixtofour or address.teredo or address.ipv4_mapped:
            return False
        if address in ipaddress.ip_network("64:ff9b::/96") or address in ipaddress.ip_network(
            "64:ff9b:1::/48"
        ):
            return False
    return True


def validate_feed_url(value: str) -> str:
    value = value.strip()
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 80, 443)
            or parsed.fragment
            or any(c.isspace() for c in value)
            or len(value) > 2000
        ):
            raise ValueError("来源必须为不含凭证的公网 HTTP(S) 地址，仅支持 80/443 端口")
        host = parsed.hostname.rstrip(".").lower()
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            raise ValueError("不支持本机或内网来源")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not public_ip(host):
            raise ValueError("不支持本机或内网来源")
        return str(httpx.URL(value))
    except (ValueError, httpx.InvalidURL) as exc:
        raise ValueError("来源必须为不含凭证的公网 HTTP(S) 地址，仅支持 80/443 端口") from exc


def public_addresses(host, port):
    try:
        addresses = list(
            dict.fromkeys(
                info[4][0] for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            )
        )
    except OSError as exc:
        raise ValueError("来源域名解析失败") from exc
    if not addresses or any(not public_ip(ip) for ip in addresses):
        raise ValueError("来源解析到非公网地址，已拒绝访问")
    return addresses


class PublicFeedTransport(httpx.BaseTransport):
    def __init__(self, inner=None):
        self.inner = inner or httpx.HTTPTransport(
            retries=0, limits=httpx.Limits(max_keepalive_connections=0)
        )

    def handle_request(self, request):
        validate_feed_url(str(request.url))
        addresses = public_addresses(request.url.host, request.url.port)
        # 优先 IPv4，并在连接层失败时尝试另一个已校验的公网地址。
        # Host/TLS SNI 仍为原域名；不重新解析，继续防止 DNS 重绑定。
        addresses.sort(key=lambda ip: ipaddress.ip_address(ip).version)
        for index, address in enumerate(addresses[:2]):
            pinned = httpx.Request(
                request.method,
                request.url.copy_with(host=address),
                headers=request.headers,
                extensions={**request.extensions, "sni_hostname": request.url.host},
            )
            try:
                return self.inner.handle_request(pinned)
            except (httpx.ConnectError, httpx.ConnectTimeout):
                if index == min(2, len(addresses)) - 1:
                    raise
        raise httpx.ConnectError("来源没有可连接的公网地址")

    def close(self):
        self.inner.close()


def feed_client():
    return httpx.Client(
        transport=PublicFeedTransport(),
        trust_env=False,
        timeout=8,
        follow_redirects=False,
        headers={"User-Agent": "AIHot/0.5 RSS Reader"},
    )


def fetch_feed(url: str, client=None) -> bytes:
    if client is None:
        with feed_client() as http:
            return fetch_feed(url, http)
    deadline = monotonic() + 25
    current = validate_feed_url(str(url))
    for _ in range(4):
        if monotonic() >= deadline:
            raise ValueError("来源请求超过总时限")
        with client.stream("GET", current, follow_redirects=False) as response:
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("location")
                if not location:
                    raise ValueError("来源重定向缺少目标")
                current = validate_feed_url(urljoin(current, location))
                continue
            response.raise_for_status()
            payload = bytearray()
            for chunk in response.iter_bytes():
                if monotonic() >= deadline:
                    raise ValueError("来源请求超过总时限")
                payload.extend(chunk)
                if len(payload) > MAX_BYTES:
                    raise ValueError("订阅源超过 2MB 限制")
            return bytes(payload)
    raise ValueError("来源重定向超过 3 次，请填写最终订阅地址")


def get_feed_fetcher():
    return fetch_feed
