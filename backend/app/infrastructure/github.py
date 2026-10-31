"""仅通过 GitHub 官方 API 采集，不运行仓库代码或跟随 README 外部链接。"""

import base64
import logging
import re
import time

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)
MAX_RETRIES = 5


class GitHubClient:
    def __init__(self, settings: Settings):
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"
        self.client = httpx.Client(
            base_url="https://api.github.com", headers=headers, timeout=30, follow_redirects=True
        )
        self.interval = settings.request_interval

    def close(self):
        self.client.close()

    def get(self, path: str, params: dict | None = None):
        """临时断连、超时和服务错误失败后最多重试五次；限流立即终止批次。"""
        for attempt in range(MAX_RETRIES + 1):
            time.sleep(self.interval)
            try:
                response = self.client.get(path, params=params)
            except (
                httpx.NetworkError,
                httpx.TimeoutException,
                httpx.RemoteProtocolError,
                httpx.ProxyError,
            ) as exc:
                if attempt == MAX_RETRIES:
                    logger.error(
                        "GitHub 请求重试 %s 次后仍失败（%s）", MAX_RETRIES, type(exc).__name__
                    )
                    raise
                # 仅记录错误类型，避免异常文本中的代理地址或凭据进入日志。
                logger.warning(
                    "GitHub 请求暂时失败（%s），等待 %s 秒后进行第 %s/%s 次重试",
                    type(exc).__name__,
                    2**attempt,
                    attempt + 1,
                    MAX_RETRIES,
                )
                time.sleep(2**attempt)
                continue
            if response.status_code == 404:
                return None
            if response.status_code in (403, 429):
                raise RuntimeError("GitHub 拒绝请求或限流；请检查 Token、权限及调用额度")
            if response.status_code >= 500:
                if attempt < MAX_RETRIES:
                    logger.warning(
                        "GitHub 请求暂时失败（HTTP %s），等待 %s 秒后进行第 %s/%s 次重试",
                        response.status_code,
                        2**attempt,
                        attempt + 1,
                        MAX_RETRIES,
                    )
                    time.sleep(2**attempt)
                    continue
                logger.error(
                    "GitHub 请求重试 %s 次后仍失败（HTTP %s）", MAX_RETRIES, response.status_code
                )
            response.raise_for_status()
            return response.json()
        raise RuntimeError("GitHub 请求重试失败")

    def discover(self, queries: list[str]) -> list[dict]:
        """每个关键词分别按 Star 和最近更新搜索，兼顾成熟项目与新项目。"""
        found = {}
        for index, query in enumerate(queries, 1):
            for sort in ("stars", "updated"):
                data = self.get(
                    "/search/repositories",
                    {
                        "q": f"{query} archived:false fork:false",
                        "sort": sort,
                        "order": "desc",
                        "per_page": 100,
                    },
                )
                if data is None or data.get("incomplete_results"):
                    raise RuntimeError("GitHub 搜索未完成，本轮不发布不完整榜单")
                for repo in data["items"]:
                    found[repo["id"]] = repo
                logger.info(
                    "GitHub 搜索进度 %s/%s，排序=%s，本次返回=%s，累计去重仓库=%s",
                    index,
                    len(queries),
                    sort,
                    len(data["items"]),
                    len(found),
                )
        return list(found.values())

    def readme(self, name: str) -> str:
        data = self.get(f"/repos/{name}/readme")
        if not data or data.get("encoding") != "base64":
            return ""
        # 控制资料大小；只保存文本，前端按纯文本展示以避免注入。
        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")[:100_000]


def classify(repo: dict, readme: str) -> str | None:
    """返回可追溯的识别依据。是规则识别而非人工认证，允许用户检查误判。"""
    if repo.get("archived") or repo.get("fork") or repo.get("private"):
        return None
    from app.services.skills.analysis import MEDIA_TAGS, RuleAnalyzer

    text = f"{repo['full_name']} {repo.get('description') or ''} {' '.join(repo.get('topics', []))} {readme}"
    ai = re.search(
        r"\b(?:ai|llm|tts|asr|rag|diffusion|transformer|whisper)\b|artificial.intelligence|machine.learning|deep.learning|人工智能|大模型|智能",
        text,
        re.I,
    )
    analysis = RuleAnalyzer().analyze(repo, readme)
    video_skill = re.search(r"\bSKILL\.md\b|\bskills?\b", text, re.I)
    if (ai or video_skill) and MEDIA_TAGS.intersection(analysis.tags):
        return "；".join(analysis.evidence)[:500]
    return None
