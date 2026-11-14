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
