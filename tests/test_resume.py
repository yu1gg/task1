import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas import ResumeContent
from app.services.resume import generate_resume, resume_text_length
from app.services.llm import LLMError


class FakeLLM:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def chat_json(self, system, user):
        self.calls.append((system, user))
        result = next(self.responses)
        if isinstance(result, Exception):
            raise result
        return result


def sources():
    return (
        SimpleNamespace(real_name="张三"),
        SimpleNamespace(summary="学习 Python", education_json=[],
                        skills_json=[{"name": "Python", "evidence": "课程项目"}],
                        projects_json=[{"name": "课程项目", "role": "开发", "period": "2026", "description": "实现接口\n完成测试"}],
                        internships_json=[], awards_json=[{"name": "校奖"}]),
        SimpleNamespace(title="Python实习", description="开发API", requirements="Python", skills=[]),
    )


def selection(**changes):
    result = dict(summary=True, education=[], skills=[0],
                  projects=[{"id": 0, "lines": [1, 0]}], internships=[], awards=[0])
    result.update(changes)
    return result


def test_generates_only_source_facts_in_selected_order():
    llm = FakeLLM([selection()])
    content = generate_resume(*sources(), llm)
    assert content.name == "张三"
    assert content.phone == content.email == ""
    assert content.projects[0].bullets == ["完成测试", "实现接口"]
    assert content.awards == ["校奖"]
    assert "开发API" not in content.model_dump_json()
    assert resume_text_length(content) > 0
    ids = json.loads(llm.calls[0][1])["available_ids"]
    assert ids["projects"] == [{"id": 0, "lines": [0, 1]}]
    assert ids["education"] == []


@pytest.mark.parametrize("bad", [selection(skills=[4]), selection(skills=[0, 0]),
                                  selection(company="编造公司"),
                                  selection(projects=[{"id": 0, "lines": [20]}]),
                                  selection(summary="编造简介")])
def test_invalid_source_selection_retries_then_fails(bad):
    llm = FakeLLM([bad, bad, bad])
    with pytest.raises(LLMError):
        generate_resume(*sources(), llm)
    assert len(llm.calls) == 3


def test_invalid_selection_can_be_corrected():
    llm = FakeLLM([selection(skills=[99]), selection()])
    assert generate_resume(*sources(), llm).skills[0].name == "Python"
    assert "校验" in llm.calls[1][1]


def test_empty_profile_does_not_call_llm():
    user, profile, job = sources()
    profile.summary = ""
    profile.skills_json = profile.projects_json = profile.awards_json = []
    llm = FakeLLM([])
    with pytest.raises(ValueError):
        generate_resume(user, profile, job, llm)
    assert llm.calls == []


def test_upstream_failure_preserved():
    with pytest.raises(LLMError, match="timeout"):
        generate_resume(*sources(), FakeLLM([LLMError("timeout")]))


def test_long_source_not_silently_truncated():
    user, profile, job = sources()
    profile.projects_json[0]["description"] = "字" * 61
    bad = selection(projects=[{"id": 0, "lines": [0]}])
    with pytest.raises(LLMError):
        generate_resume(user, profile, job, FakeLLM([bad] * 3))


def test_schema_rejects_extra_and_limits():
    with pytest.raises(ValidationError):
        ResumeContent(name="同学", invented=True)
    with pytest.raises(ValidationError):
        ResumeContent(name="同学", summary="字" * 121)
    with pytest.raises(ValidationError):
        ResumeContent(name="同学", skills=[{"name": "Python"}] * 13)


def test_schema_total_body_limit():
    entries = [{"name": "字" * 120, "role": "字" * 120, "period": "字" * 120,
                "bullets": ["字" * 60] * 3}] * 3
    with pytest.raises(ValidationError, match="1200"):
        ResumeContent(name="同学", projects=entries)
