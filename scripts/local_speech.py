"""Local speech service for this Windows installation, bound to loopback only."""

from contextlib import asynccontextmanager
import os
from pathlib import Path
import subprocess
import wave
from tempfile import TemporaryDirectory
from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field

from app.config import settings
from app.services.audio import INTERVIEW_MAX_SECONDS

SCRIPT_DIR = Path(__file__).resolve().parent
MODEL_PATH = SCRIPT_DIR.parent / "data" / "local-ai" / "whisper-small"
UPLOAD_LIMIT = 20 * 1024 * 1024
SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2


@asynccontextmanager
async def lifespan(app: FastAPI):
    from faster_whisper import WhisperModel

    app.state.whisper = WhisperModel(
        str(MODEL_PATH), device="cpu", compute_type="int8",
        cpu_threads=4, local_files_only=True,
    )
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/healthz")
def health():
    return {"status": "ok", "service": "task1-local-speech"}


def _pcm_samples(pcm: bytes):
    import numpy as np

    return np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768


@app.post("/v1/audio/transcriptions")
def transcribe(request: Request, file: Annotated[UploadFile, File()],
               model: Annotated[Literal["whisper-small"], Form()]):
    try:
        with file.file as upload:
            if not 0 < upload.seek(0, os.SEEK_END) <= UPLOAD_LIMIT:
                raise HTTPException(413, "音频为空或超出大小限制")
            upload.seek(0)
            with wave.open(upload, "rb") as audio:
                if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, SAMPLE_WIDTH, SAMPLE_RATE):
                    raise ValueError("Expected 16 kHz mono PCM")
                frames = audio.getnframes()
                if not 0 < frames <= INTERVIEW_MAX_SECONDS * SAMPLE_RATE:
                    raise ValueError("Unexpected number of WAV frames")
                # Read an extra frame to catch odd-sized PCM data chunks.
                pcm = audio.readframes(frames + 1)
                if len(pcm) != frames * SAMPLE_WIDTH:
                    raise ValueError("WAV frame count does not match PCM data")
        samples = _pcm_samples(pcm)
        segments, _ = request.app.state.whisper.transcribe(
            samples, language="zh", beam_size=3, vad_filter=True,
            initial_prompt="以下是一段中文求职面试回答。请忠实转写。",
        )
        text = "".join(segment.text for segment in segments).strip()
    except (ValueError, RuntimeError, OSError, EOFError, wave.Error) as exc:
        raise HTTPException(422, "无法转写该音频") from exc
    return {"text": text}


class SpeechRequest(BaseModel):
    model: Literal["windows-sapi"]
    voice: Literal["Microsoft Huihui Desktop"]
    input: str = Field(min_length=1, max_length=8000)
    response_format: Literal["mp3"]


@app.post("/v1/audio/speech")
def synthesize(request: SpeechRequest):
    with TemporaryDirectory(prefix="task1-tts-") as directory:
        wave = Path(directory) / "speech.wav"
        environment = dict(os.environ, TASK1_TTS_WAVE=str(wave), TASK1_TTS_VOICE=request.voice)
        try:
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(SCRIPT_DIR / "speak_local.ps1")],
                input=request.input.encode("utf-8"), env=environment, timeout=45,
                capture_output=True, check=True,
            )
            result = subprocess.run(
                [settings.ffmpeg_path, "-nostdin", "-loglevel", "error", "-i", str(wave),
                 "-f", "mp3", "pipe:1"],
                capture_output=True, timeout=10, check=True,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise HTTPException(503, "本机朗读服务暂不可用") from exc
    return Response(result.stdout, media_type="audio/mpeg")
