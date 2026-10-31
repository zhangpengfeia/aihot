"""采集接口和分类管理的输入模型。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.core.sources import FeedSource
from app.infrastructure.feed_http import validate_feed_url


class SourceCreate(FeedSource):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    enabled: bool = True

    @field_validator("url")
    @classmethod
    def public_url(cls, value):
        validate_feed_url(str(value))
        return value


class SourceUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str | None = Field(None, min_length=1, max_length=200)
    category: str | None = Field(None, min_length=1, max_length=50)
    region: Literal["国内", "国外"] | None = None
    topic_kind: Literal["热点候选", "知识探索"] | None = None
    enabled: bool | None = None
    url: HttpUrl | None = None
    adapter: Literal["rss", "hackernews", "wikipedia", "json", "hotlist"] | None = None
    item_limit: int | None = Field(None, ge=1, le=200)
    options: dict[str, str] | None = None

    @field_validator("url")
    @classmethod
    def public_url(cls, value):
        if value is not None:
            validate_feed_url(str(value))
        return value


class CategoryMerge(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    source: str = Field(min_length=1, max_length=50)
    target: str = Field(min_length=1, max_length=50)


class CategoryVisibility(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(min_length=1, max_length=50)
    hidden: bool


class CategoryName(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(min_length=1, max_length=50)
