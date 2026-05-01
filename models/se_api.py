from __future__ import annotations

from typing import List, Optional

from pydantic import Field

from .base import SmokeBaseModel


class StackExchangeOwner(SmokeBaseModel):
    """Stack Exchange API 中 `owner` 字段的子结构。"""

    display_name: Optional[str] = None
    link: Optional[str] = None
    reputation: Optional[int] = None


class StackExchangePostItem(SmokeBaseModel):
    """Stack Exchange 帖子条目（问题或答案）。"""

    title: Optional[str] = None
    body: Optional[str] = None
    body_markdown: Optional[str] = None
    owner: Optional[StackExchangeOwner] = None

    # 嵌套回答与摘要标记（与 API 字段名保持一致）
    answers: Optional[List["StackExchangePostItem"]] = None
    BodyIsSummary: Optional[bool] = None

    site: Optional[str] = None
    question_id: Optional[int] = None
    answer_id: Optional[int] = None
    link: Optional[str] = None

    score: Optional[int] = None
    up_vote_count: Optional[int] = None
    down_vote_count: Optional[int] = None

    creation_date: Optional[int] = None
    last_edit_date: Optional[int] = None
    edited: Optional[bool] = None

    # 与现有代码兼容的字段名
    IsAnswer: Optional[bool] = None


class StackExchangePostResponse(SmokeBaseModel):
    """Stack Exchange 帖子相关 API 的标准响应结构。"""

    items: List[StackExchangePostItem] = Field(default_factory=list)
    has_more: Optional[bool] = None
    backoff: Optional[int] = None
    error_message: Optional[str] = None
    quota_remaining: Optional[int] = None


class StackExchangeSiteItem(SmokeBaseModel):
    """`/sites` API 单个站点条目。"""

    site_url: str
    api_site_parameter: str


class StackExchangeSitesResponse(SmokeBaseModel):
    """Stack Exchange `/sites` API 响应。"""

    items: List[StackExchangeSiteItem] = Field(default_factory=list)
    has_more: Optional[bool] = None
    backoff: Optional[int] = None
    error_message: Optional[str] = None
