"""集中管理配置；数据库连接字符串通过 URL.create 构造，支持密码中的特殊字符。"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

from app.core.sources import DEFAULT_SOURCES, FeedSource


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_database: str = "aihot"
    mysql_user: str = "aihot"
    mysql_password: str = ""
    github_token: str = ""
    knowledge_sources: list[FeedSource] = Field(
        default_factory=lambda: [FeedSource(**s) for s in DEFAULT_SOURCES]
    )
    # 搜索范围与读取上限可调整；排名始终限定于本轮成功观测的候选池。
    search_queries: list[str] = [
        '"agent skills" in:name,description,readme',
        '"claude skills" in:name,description,readme',
        '"codex skills" in:name,description,readme',
        "topic:agent-skills",
        "topic:claude-skills",
    ]
    candidate_limit: int = Field(default=200, ge=20, le=1000)
    tracked_limit: int = Field(default=200, ge=20, le=1000)
    request_interval: float = Field(default=2.1, ge=0)

    @property
    def database_url(self) -> URL:
        return URL.create(
            "mysql+pymysql",
            username=self.mysql_user,
            password=self.mysql_password,
            host=self.mysql_host,
            port=self.mysql_port,
            database=self.mysql_database,
            query={"charset": "utf8mb4"},
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
