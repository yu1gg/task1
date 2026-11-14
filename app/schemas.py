import re
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


# Resume models deliberately forbid unknown fields so AI output and editor input
# cannot silently add unsupported information.
ResumeText = Annotated[str, Field(max_length=120)]
ResumeBullet = Annotated[str, Field(max_length=60)]


class ResumeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ResumeEducation(ResumeModel):
    school: ResumeText = ""
    major: ResumeText = ""
    degree: ResumeText = ""
    period: ResumeText = ""


class ResumeSkill(ResumeModel):
    name: ResumeText
    evidence: ResumeText = ""


class ResumeProject(ResumeModel):
    name: ResumeText = ""
    role: ResumeText = ""
    period: ResumeText = ""
    bullets: list[ResumeBullet] = Field(default_factory=list, max_length=3)


class ResumeInternship(ResumeModel):
    company: ResumeText = ""
    role: ResumeText = ""
    period: ResumeText = ""
    bullets: list[ResumeBullet] = Field(default_factory=list, max_length=3)


def _resume_string_length(value: Any) -> int:
    if isinstance(value, str):
        return len(value)
    if isinstance(value, dict):
        return sum(_resume_string_length(item) for item in value.values())
    if isinstance(value, list):
        return sum(_resume_string_length(item) for item in value)
    return 0


class ResumeContent(ResumeModel):
    name: str = Field(min_length=1, max_length=64)
    phone: str = Field(default="", max_length=40)
    email: ResumeText = ""
    target_job: ResumeText = ""
    summary: ResumeText = ""
    education: list[ResumeEducation] = Field(default_factory=list, max_length=3)
    skills: list[ResumeSkill] = Field(default_factory=list, max_length=12)
    projects: list[ResumeProject] = Field(default_factory=list, max_length=3)
    internships: list[ResumeInternship] = Field(default_factory=list, max_length=3)
    awards: list[ResumeText] = Field(default_factory=list, max_length=5)

    @model_validator(mode="after")
    def limit_body(self):
        if _resume_string_length(self.model_dump()) > 1200:
            raise ValueError("简历正文最多1200字，请精简内容")
        return self
