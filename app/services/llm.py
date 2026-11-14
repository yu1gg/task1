import json
import time
from typing import Any, Protocol

import httpx

from app.config import settings


class LLMError(Exception):
    pass


class LLMProtocol(Protocol):
    def chat_json(self, system: str, user: str) -> dict[str, Any]:
        ...


class LLMClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 60.0,
        max_retries: int = 2,
        transport: httpx.BaseTransport | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.transport = transport

    def chat_json(self, system: str, user: str) -> dict[str, Any]:
        if not self.api_key:
            raise LLMError("未配置 DEEPSEEK_API_KEY，请先在 .env 中填写")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(
                    timeout=self.timeout,
                    transport=self.transport,
                ) as client:
                    response = client.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                        },
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()

                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                if not isinstance(parsed, dict):
                    raise ValueError("LLM 返回的 JSON 不是对象")
                return parsed
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status_code = exc.response.status_code
                if 400 <= status_code < 500 and status_code != 429:
                    break
                if attempt < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))

        raise LLMError(f"LLM 调用失败：{last_error}")


def get_llm_client() -> LLMClient:
    return LLMClient(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        model=settings.llm_model,
        timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )
