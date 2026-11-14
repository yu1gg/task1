import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

IMPORTANCE_MAP = {
    "must": "must",
    "required": "must",
    "必须": "must",
    "必需": "must",
    "硬性": "must",
    "硬性要求": "must",
    "必备": "must",
    "必要条件": "must",
    "nice": "nice",
    "optional": "nice",
    "加分": "nice",
    "优先": "nice",
    "可选": "nice",
    "优先考虑": "nice",
    "加分项": "nice",
}

LEVEL_MAP = {
    "初级": 1,
    "入门": 1,
    "了解": 1,
    "中级": 3,
    "熟练": 3,
    "掌握": 3,
    "高级": 5,
    "精通": 5,
    "专家": 5,
}


class JobSkillItem(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    category: str = Field(default="通用", max_length=40)
    importance: str = "nice"
    required_level: int = 3

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: Any) -> str:
        if value is None:
            return ""
        return " ".join(str(value).strip().split())

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value: Any) -> str:
        if value is None:
            return "通用"
        text = " ".join(str(value).strip().split())
        return text or "通用"

    @field_validator("importance", mode="before")
    @classmethod
    def normalize_importance(cls, value: Any) -> str:
        text = str(value).strip().lower()
        return IMPORTANCE_MAP.get(text, "nice")

    @field_validator("required_level", mode="before")
    @classmethod
    def normalize_level(cls, value: Any) -> int:
        if isinstance(value, bool):
            return 3
        if isinstance(value, (int, float)):
            return max(1, min(5, int(value)))
        text = str(value).strip()
        if text in LEVEL_MAP:
            return LEVEL_MAP[text]
        digits = re.findall(r"\d", text)
        if digits:
            return max(1, min(5, int(digits[0])))
        return 3


class JobSkillExtraction(BaseModel):
    summary: str = Field(default="", max_length=500)
    responsibilities: list[str] = Field(default_factory=list, max_length=10)
    skills: list[JobSkillItem] = Field(default_factory=list, max_length=30)
