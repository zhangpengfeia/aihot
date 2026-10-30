"""HTTP 写入来源校验，供知识管理和工作空间共用。"""

from urllib.parse import urlsplit

from fastapi import HTTPException, Request


def same_origin_writes(request: Request):
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("origin")
    if request.headers.get("sec-fetch-site") == "cross-site" or (
        origin and urlsplit(origin).netloc != request.headers.get("host")
    ):
        raise HTTPException(403, "仅允许同源页面修改工作空间")
    if request.method in {"PUT", "PATCH", "POST"} and not request.headers.get(
        "content-type", ""
    ).startswith("application/json"):
        raise HTTPException(415, "请使用 application/json")
