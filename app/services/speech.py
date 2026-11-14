"""Bounded, synchronous SiliconFlow speech adapter with safe public errors."""
from pathlib import Path
from typing import Protocol
import time
import httpx
from app.config import settings


class SpeechError(Exception):
    pass


class SpeechProtocol(Protocol):
    def transcribe(self, path: Path) -> str: ...
    def synthesize(self, text: str) -> bytes: ...


class SpeechClient:
    def __init__(self, api_key: str, base_url: str, asr_model: str, tts_model: str,
                 voice: str, timeout: float, max_retries: int = 2,
                 transport: httpx.BaseTransport | None = None):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.asr_model, self.tts_model, self.voice = asr_model, tts_model, voice
        self.timeout, self.max_retries, self.transport = timeout, max_retries, transport

    def _request(self, endpoint: str, limit: int, **kwargs) -> bytes:
        if not self.api_key:
            raise SpeechError('未配置 SILICONFLOW_API_KEY')
        for attempt in range(self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                    with client.stream('POST', self.base_url + endpoint,
                                       headers={'Authorization': f'Bearer {self.api_key}'}, **kwargs) as response:
                        if response.status_code >= 400:
                            if (response.status_code == 429 or response.status_code >= 500) and attempt < self.max_retries:
                                time.sleep(0.5 * (attempt + 1))
                                continue
                            raise SpeechError('语音服务请求失败，请稍后重试')
                        result = bytearray()
                        for chunk in response.iter_bytes():
                            if len(result) + len(chunk) > limit:
                                raise SpeechError('语音服务响应超出限制')
                            result.extend(chunk)
                        return bytes(result)
            except (httpx.TimeoutException, httpx.TransportError):
                if attempt == self.max_retries:
                    raise SpeechError('语音服务连接失败或超时') from None
                time.sleep(0.5 * (attempt + 1))
        raise SpeechError('语音服务请求失败')

    def transcribe(self, path: Path) -> str:
        import json
        try:
            if path.stat().st_size > 20 * 1024 * 1024:
                raise SpeechError('音频超出大小限制')
            # Immutable bytes allow safe multipart replay on retries.
            content = path.read_bytes()
        except OSError:
            raise SpeechError('无法读取待转写音频') from None
        raw = self._request('/audio/transcriptions', 128 * 1024,
                            data={'model': self.asr_model},
                            files={'file': ('audio.wav', content, 'audio/wav')})
        try:
            value = json.loads(raw)['text']
            if not isinstance(value, str) or not value.strip() or len(value) > 8000:
                raise ValueError()
            return value.strip()
        except (ValueError, KeyError, TypeError):
            raise SpeechError('语音转写返回无效文本') from None

    def synthesize(self, text: str) -> bytes:
        if not isinstance(text, str) or not text.strip() or len(text) > 8000:
            raise SpeechError('语音合成文本必须为 1 至 8000 字符')
        result = self._request('/audio/speech', 5 * 1024 * 1024,
                               json={'model': self.tts_model, 'voice': self.voice,
                                     'input': text, 'response_format': 'mp3'})
        if not (result.startswith(b'ID3') or (len(result) > 1 and result[0] == 255 and result[1] & 224 == 224)):
            raise SpeechError('语音合成返回无效音频')
        return result


def get_speech_client() -> SpeechClient:
    return SpeechClient(settings.siliconflow_api_key, settings.speech_base_url,
                        settings.asr_model, settings.tts_model, settings.tts_voice,
                        settings.speech_timeout_seconds, settings.speech_max_retries)
