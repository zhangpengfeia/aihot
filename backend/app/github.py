"""仅通过 GitHub 官方 API 采集，不运行仓库代码或跟随 README 外部链接。"""

import base64
import re
import time

import httpx

from app.config import Settings


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
        """临时服务错误有限重试；限流立即终止批次，避免继续冲击 GitHub。"""
        for attempt in range(3):
            time.sleep(self.interval)
            response = self.client.get(path, params=params)
            if response.status_code == 404:
                return None
            if response.status_code in (403, 429):
                raise RuntimeError("GitHub 拒绝请求或限流；请检查 Token、权限及调用额度")
            if response.status_code >= 500 and attempt < 2:
                time.sleep(2**attempt)
                continue
            response.raise_for_status()
            return response.json()
        raise RuntimeError("GitHub 请求重试失败")

    def discover(self, queries: list[str]) -> list[dict]:
        """每个关键词分别按 Star 和最近更新搜索，兼顾成熟项目与新项目。"""
        found = {}
        for query in queries:
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
    if re.search(r"\bSKILL\.md\b", readme, re.IGNORECASE):
        return "README 提及 SKILL.md"
    topics = set(repo.get("topics", []))
    if topics & {"agent-skills", "claude-skills", "codex-skills"}:
        return "GitHub Topics 包含 Agent/Claude/Codex Skills"
    text = f"{repo['full_name']} {repo.get('description') or ''} {readme}"
    if re.search(r"\b(?:agent|claude|codex)[ -]+skills?\b", text, re.IGNORECASE):
        return "项目资料包含 Agent/Claude/Codex Skills 关键词"
    return None
