from __future__ import annotations

from typing import List, Optional, Union

from pydantic import Field

from .base import SmokeBaseModel


class CidrInfo(SmokeBaseModel):
    """表示 `cidr` 字段的结构：`{"base": "1.2.3.4", "mask": 24}`。"""

    base: Optional[str] = None
    mask: Optional[int] = None


class CidrListItem(SmokeBaseModel):
    """黑名单 YAML 中 `items` 列表的单条记录。

    该结构被 YAMLParserCIDR/NS/ASN 共用：
    - IP 黑名单：使用 `ip` 或 `cidr`；
    - NS 黑名单：使用 `ns`；
    - ASN 黑名单：使用 `asn`；
    其他字段保持为 extra 以兼容现有结构（例如 `disable`、`pass`、备注等）。
    """

    ip: Optional[str] = None
    cidr: Optional[CidrInfo] = None
    asn: Optional[int] = None

    ns: Optional[Union[str, List[str]]] = None

    disable: Optional[bool] = None


class CidrYamlDocument(SmokeBaseModel):
    """CIDR/NS/ASN 黑名单 YAML 顶层结构。"""

    Schema: str
    Schema_version: str
    items: List[CidrListItem] = Field(default_factory=list)
