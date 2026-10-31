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
    admin_username: str = "admin"
    admin_password: str = ""
    github_token: str = ""
    knowledge_sources: list[FeedSource] = Field(
        default_factory=lambda: [FeedSource(**s) for s in DEFAULT_SOURCES]
    )
    # 搜索范围与读取上限可调整；排名始终限定于本轮成功观测的候选池。
    search_queries: list[str] = [
        "topic:text-to-video",
        "topic:image-to-video",
        "topic:video-generation",
        "topic:text-to-speech",
        "topic:voice-cloning",
        "topic:talking-head",
        "topic:ai-animation",
        "topic:ai-video",
        "topic:automatic-speech-recognition",
        "topic:music-generation",
        "AI video editing in:name,description",
        "AI animation in:name,description",
        "AI office in:name,description",
        "AI spreadsheet in:name,description",
        "AI presentation in:name,description",
        "AI document in:name,description",
        "AI meeting in:name,description",
        "AI knowledge base in:name,description",
        "AI workflow automation in:name,description",
    ]
    candidate_limit: int = Field(default=500, ge=100, le=2000)
    tracked_limit: int = Field(default=200, ge=20, le=1000)
    request_interval: float = Field(default=2.1, ge=0)
    # 十进制 GB；控制有效数据估算量，不等于 MySQL 文件系统配额。
    database_max_size_gb: float = Field(default=5, ge=0.000001, allow_inf_nan=False)
    database_cleanup_target_ratio: float = Field(default=0.9, gt=0, lt=1)

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
