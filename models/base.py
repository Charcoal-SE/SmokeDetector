from __future__ import annotations

from typing import Any, Mapping, Type, TypeVar

from pydantic import BaseModel, ConfigDict


SelfT = TypeVar("SelfT", bound="SmokeBaseModel")


class SmokeBaseModel(BaseModel):
    """Base model for SmokeDetector data structures.

    - 默认允许未知字段（extra='allow'），用于平滑接入现有 JSON/YAML 结构；
    - 提供 from_dict/from_json/from_yaml 与 to_dict/to_json/to_yaml 工具方法，统一序列化入口。
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @classmethod
    def from_dict(cls: Type[SelfT], data: Mapping[str, Any] | None) -> SelfT:
        """构造模型实例，兼容 None 输入。"""
        if data is None:
            data = {}
        return cls.model_validate(data)

    @classmethod
    def from_json(cls: Type[SelfT], data: str | bytes) -> SelfT:
        """从 JSON 字符串/字节构造模型实例。"""
        return cls.model_validate_json(data)

    @classmethod
    def from_yaml(cls: Type[SelfT], data: str | bytes) -> SelfT:
        """从 YAML 文本构造模型实例（内部先 safe_load 为 dict，再做校验）。"""
        import yaml

        if not data:
            raw: Any = {}
        else:
            raw = yaml.safe_load(data)
        if raw is None:
            raw = {}
        return cls.from_dict(raw)

    def to_dict(self, **kwargs: Any) -> dict[str, Any]:
        """导出为 dict，默认：使用别名、忽略 None。"""
        default_kwargs = {"by_alias": True, "exclude_none": True}
        default_kwargs.update(kwargs)
        return self.model_dump(**default_kwargs)

    def to_json(self, **kwargs: Any) -> str:
        """导出为 JSON 字符串，默认：使用别名、忽略 None。"""
        default_kwargs = {"by_alias": True, "exclude_none": True}
        default_kwargs.update(kwargs)
        return self.model_dump_json(**default_kwargs)

    def to_yaml(self, **kwargs: Any) -> str:
        """导出为 YAML 字符串，默认：使用别名、忽略 None。"""
        import yaml

        default_kwargs = {"by_alias": True, "exclude_none": True}
        default_kwargs.update(kwargs)
        return yaml.safe_dump(self.to_dict(**default_kwargs), sort_keys=False, allow_unicode=True)
