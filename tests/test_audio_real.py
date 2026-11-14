"""Real codec checks; skipped on hosts without ffmpeg/ffprobe."""
import subprocess
import wave

import pytest

from app.config import settings
from app.services.audio import AudioError, check_tools, normalize_audio

pytestmark = pytest.mark.skipif(not check_tools(), reason="ffmpeg/ffprobe not installed")


@pytest.mark.parametrize("suffix,codec", [("wav", "pcm_s16le"), ("mp3", "libmp3lame"), ("webm", "libopus"), ("m4a", "aac")])
def test_real_audio_and_misleading_extension(tmp_path, suffix, codec):
    original = tmp_path / ("fixture." + suffix)
    subprocess.run([settings.ffmpeg_path, "-nostdin", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.3",
                    "-c:a", codec, str(original)], check=True, capture_output=True, timeout=20)
    renamed = original.with_suffix(".wrong")
    original.rename(renamed)
    target = tmp_path / "normalized.wav"
    normalize_audio(renamed, target)
    with wave.open(str(target)) as wav:
        assert wav.getnchannels() == 1 and wav.getframerate() == 16000
        assert 0 < wav.getnframes() <= 16000


def test_real_overlong_audio_is_rejected_without_truncating(tmp_path):
    original = tmp_path / "long.wav"
    with wave.open(str(original), "wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 16000 * 91)
    target = tmp_path / "result.wav"
    with pytest.raises(AudioError):
        normalize_audio(original, target)
    assert original.exists() and not target.exists()


def test_real_corrupt_media_is_rejected(tmp_path):
    original = tmp_path / "fake.mp3"
    original.write_text("this is not audio")
    with pytest.raises(AudioError):
        normalize_audio(original, tmp_path / "result.wav")
