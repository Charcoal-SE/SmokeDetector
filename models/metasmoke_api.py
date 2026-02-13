from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Field

from .base import SmokeBaseModel


class MetasmokeReasonItem(SmokeBaseModel):
    """`/api/v2.0/reasons` 中的单条 reason 记录。"""

    reason_name: Optional[str] = None
    weight: Optional[float] = None


class MetasmokeReasonsPage(SmokeBaseModel):
    """`/api/v2.0/reasons` 页结果。"""

    items: List[MetasmokeReasonItem] = Field(default_factory=list)
    has_more: Optional[bool] = None


class MetasmokeGenericPage(SmokeBaseModel):
    """通用的 Metasmoke 分页响应结构，用于缓存等场景。"""

    items: List[Dict[str, Any]] = Field(default_factory=list)
    has_more: Optional[bool] = None
    backoff: Optional[int] = None
