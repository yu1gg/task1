import json
from types import SimpleNamespace

import httpx
import pytest

from app.services.job_skills import extract_job_skills
from app.services.llm import LLMClient, LLMError


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def chat_json(self, system, user):
        self.calls += 1
        return self.payload


def make_job():
    return SimpleNamespace(
        title="AI 算法实习生",
        description="负责模型训练与数据处理",
        requirements="熟悉 Python 和 PyTorch",
        company=SimpleNamespace(name="示例科技有限公司"),
    )


def test_normalizes_chinese_importance_and_level():
    fake = FakeLLM(
        {
            "summary": "AI 算法实习",
            "responsibilities": ["模型训练"],
            "skills": [
                {
                    "name": "Python",
                    "category": "编程",
                    "importance": "必须",
                    "required_level": "高级",
                }
            ],
        }
    )

    result = extract_job_skills(make_job(), fake)

    assert fake.calls == 1
    assert result.skills[0].name == "Python"
    assert result.skills[0].importance == "must"
    assert result.skills[0].required_level == 5


def test_dedupes_skill_names_case_insensitively():
    fake = FakeLLM(
        {
            "skills": [
                {"name": "Python", "required_level": 3},
                {"name": " python ", "required_level": 4},
            ]
        }
    )

    result = extract_job_skills(make_job(), fake)

    assert len(result.skills) == 1
    assert result.skills[0].required_level == 3


def test_invalid_payload_raises_llm_error():
    fake = FakeLLM({"skills": [{"name": ""}]})

    with pytest.raises(LLMError):
        extract_job_skills(make_job(), fake)


def test_missing_api_key_raises_llm_error():
    client = LLMClient(
        api_key="",
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
    )

    with pytest.raises(LLMError):
        client.chat_json("system", "user")


def test_chat_json_success_with_mock_transport():
    def handler(request):
        assert request.url.path == "/chat/completions"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"summary":"ok","skills":[]}'
                        }
                    }
                ]
            },
        )

    client = LLMClient(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        transport=httpx.MockTransport(handler),
    )

    assert client.chat_json("system", "user") == {"summary": "ok", "skills": []}


@pytest.mark.parametrize("structured_output", [False, True])
def test_schema_mode_is_opt_in(structured_output):
    from pydantic import BaseModel

    class Reply(BaseModel):
        answer: str

    def handler(request):
        response_format = json.loads(request.content)["response_format"]
        if structured_output:
            assert response_format["type"] == "json_schema"
            expected = Reply.model_json_schema()
            expected["additionalProperties"] = False
            assert response_format["json_schema"]["schema"] == expected
        else:
            assert response_format == {"type": "json_object"}
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"answer":"ok"}'}}]})

    client = LLMClient("test-key", "http://127.0.0.1:11434/v1", "test-model",
                       max_retries=0, transport=httpx.MockTransport(handler),
                       structured_output=structured_output)
    assert client.chat_json("system", "user", response_model=Reply) == {"answer": "ok"}


def test_strict_schema_requires_all_fields_and_forbids_extras_at_each_level():
    from app.services.interview_ai import ReportText
    from app.services.resume import ResumeSelection

    schemas = []

    def handler(request):
        schemas.append(json.loads(request.content)["response_format"]["json_schema"]["schema"])
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}}]})

    client = LLMClient("test-key", "http://127.0.0.1:11434/v1", "test-model",
                       max_retries=0, transport=httpx.MockTransport(handler), structured_output=True)
    client.chat_json("system", "user", response_model=ResumeSelection)
    client.chat_json("system", "user", response_model=ReportText)
    resume, report = schemas
    for schema in (resume, resume["$defs"]["ExperienceSelection"], report):
        assert set(schema["required"]) == set(schema["properties"])
        assert schema["additionalProperties"] is False
    assert "default" not in resume["properties"]["summary"]


def test_chat_json_does_not_retry_unauthorized():
    calls = {"count": 0}

    def handler(request):
        calls["count"] += 1
        return httpx.Response(401, json={"error": "unauthorized"})

    client = LLMClient(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        max_retries=2,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMError):
        client.chat_json("system", "user")

    assert calls["count"] == 1


class SequencedLLM:
    def __init__(self, payloads):
        self.payloads = payloads
        self.calls = 0

    def chat_json(self, system, user):
        self.calls += 1
        index = min(self.calls - 1, len(self.payloads) - 1)
        return self.payloads[index]


def test_validation_failure_retries_with_feedback_then_succeeds():
    fake = SequencedLLM(
        [
            {"skills": [{"name": ""}]},
            {"skills": [{"name": "Python", "required_level": 3}]},
        ]
    )

    result = extract_job_skills(make_job(), fake)

    assert fake.calls == 2
    assert result.skills[0].name == "Python"


def test_validation_failure_retries_twice_then_raises():
    fake = SequencedLLM([{"skills": [{"name": ""}]}])

    with pytest.raises(LLMError):
        extract_job_skills(make_job(), fake)

    assert fake.calls == 3


def test_schema_strips_names_and_extended_importance():
    from app.schemas import JobSkillExtraction

    parsed = JobSkillExtraction.model_validate(
        {
            "skills": [
                {
                    "name": "  Python  ",
                    "category": "   ",
                    "importance": "硬性要求",
                }
            ]
        }
    )
    assert parsed.skills[0].name == "Python"
    assert parsed.skills[0].category == "通用"
    assert parsed.skills[0].importance == "must"


def test_build_user_prompt_wraps_and_truncates():
    from app.services.job_skills import build_user_prompt

    job = make_job()
    job.description = "x" * 5000
    prompt = build_user_prompt(job)

    assert "<job_data>" in prompt
    assert "</job_data>" in prompt
    assert "x" * 4000 in prompt
    assert "x" * 4001 not in prompt


def test_chat_json_retries_500_then_raises(monkeypatch):
    monkeypatch.setattr("app.services.llm.time.sleep", lambda _: None)
    calls = {"count": 0}

    def handler(request):
        calls["count"] += 1
        return httpx.Response(500, json={"error": "server"})

    client = LLMClient(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        max_retries=2,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMError):
        client.chat_json("system", "user")

    assert calls["count"] == 3


def test_chat_json_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr("app.services.llm.time.sleep", lambda _: None)
    calls = {"count": 0}

    def handler(request):
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(500, json={"error": "server"})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ok": true}'}}]},
        )

    client = LLMClient(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        max_retries=2,
        transport=httpx.MockTransport(handler),
    )

    assert client.chat_json("system", "user") == {"ok": True}
    assert calls["count"] == 2


def test_chat_json_retries_429_then_succeeds(monkeypatch):
    monkeypatch.setattr("app.services.llm.time.sleep", lambda _: None)
    calls = {"count": 0}

    def handler(request):
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"ok": true}'}}]},
        )

    client = LLMClient(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        max_retries=2,
        transport=httpx.MockTransport(handler),
    )

    assert client.chat_json("system", "user") == {"ok": True}
    assert calls["count"] == 2


def test_chat_json_retries_malformed_json(monkeypatch):
    monkeypatch.setattr("app.services.llm.time.sleep", lambda _: None)
    calls = {"count": 0}

    def handler(request):
        calls["count"] += 1
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "not-json"}}]},
        )

    client = LLMClient(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        max_retries=2,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(LLMError):
        client.chat_json("system", "user")

    assert calls["count"] == 3
