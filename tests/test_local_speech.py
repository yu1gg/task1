from io import BytesIO
import struct
from types import SimpleNamespace
import wave

from fastapi.testclient import TestClient
import pytest

from scripts import local_speech


def wav_bytes(frames, *, channels=1, width=2, rate=16000):
    buffer = BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setparams((channels, width, rate, 0, "NONE", "not compressed"))
        audio.writeframes(b"\x00" * (frames * channels * width))
    return buffer.getvalue()


def odd_pcm_chunk():
    payload = bytearray(wav_bytes(2))
    payload.extend(b"\x00")
    struct.pack_into("<I", payload, 4, len(payload) - 8)
    struct.pack_into("<I", payload, 40, 5)
    return bytes(payload)


@pytest.fixture
def speech_client(monkeypatch):
    dispatched = []

    def transcribe(samples, **kwargs):
        dispatched.append(len(samples))
        return [SimpleNamespace(text="  测试内容  ")], None

    monkeypatch.setattr(local_speech.app.state, "whisper",
                        SimpleNamespace(transcribe=transcribe), raising=False)
    monkeypatch.setattr(local_speech, "_pcm_samples",
                        lambda pcm: range(len(pcm) // 2), raising=False)
    return TestClient(local_speech.app), dispatched


def upload(client, content):
    return client.post(
        "/v1/audio/transcriptions", data={"model": "whisper-small"},
        files={"file": ("answer.wav", content, "audio/wav")},
    )


def test_exactly_ninety_seconds_is_accepted(speech_client):
    client, dispatched = speech_client
    response = upload(client, wav_bytes(90 * 16000))

    assert response.status_code == 200
    assert response.json() == {"text": "测试内容"}
    assert dispatched == [90 * 16000]


@pytest.mark.parametrize("make_payload", [
    pytest.param(lambda: wav_bytes(90 * 16000 + 1), id="over-duration"),
    pytest.param(lambda: wav_bytes(0), id="no-frames"),
    pytest.param(lambda: wav_bytes(2, channels=2), id="stereo"),
    pytest.param(lambda: wav_bytes(2, width=1), id="wrong-sample-width"),
    pytest.param(lambda: wav_bytes(2, rate=8000), id="wrong-sample-rate"),
    pytest.param(lambda: wav_bytes(2)[:-2], id="truncated-frame-data"),
    pytest.param(odd_pcm_chunk, id="odd-pcm-chunk-size"),
    pytest.param(lambda: b"invalid audio", id="invalid-header"),
])
def test_rejects_invalid_wav_before_inference(speech_client, make_payload):
    client, dispatched = speech_client
    assert upload(client, make_payload()).status_code == 422
    assert dispatched == []


def test_speech_health_identifies_local_sidecar(speech_client):
    client, _ = speech_client
    assert client.get("/healthz").json() == {"status": "ok", "service": "task1-local-speech"}
