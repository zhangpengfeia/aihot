"""工作空间输入模型与合法状态。"""

from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator

TargetKind = Literal["repository", "topic"]
Stage = Literal["待筛选", "待创作", "制作中", "已发布"]


class PersonalWrite(BaseModel):
    favorite: bool | None = None
    note: str | None = Field(None, max_length=10000)


class CardCreate(BaseModel):
    topic_id: int = Field(gt=0)


class CardWrite(BaseModel):
    stage: Stage | None = None
    script: str | None = Field(None, max_length=100000)
    output_url: str | None = Field(None, max_length=2000)

    @field_validator("output_url")
    @classmethod
    def safe_url(cls, value):
        if value is None or not value.strip():
            return "" if value is not None else None
        value = value.strip()
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or any(c.isspace() for c in value)
        ):
            raise ValueError("成品链接必须是 http(s) URL")
        return value
