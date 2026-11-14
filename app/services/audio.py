"""Private media paths and constrained ffmpeg normalization."""
import json
import shutil
import subprocess
import wave
from pathlib import Path, PureWindowsPath
from app.config import settings


class AudioError(Exception):
    pass


def media_root() -> Path:
    root = (settings.data_dir / 'interview_audio').resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_media(relative: str) -> Path:
    if not relative or ':' in relative or '\\' in relative or Path(relative).is_absolute() or PureWindowsPath(relative).is_absolute():
        raise AudioError('无效媒体路径')
    root = media_root()
    candidate = (root / relative).resolve()
    if candidate == root or not candidate.is_relative_to(root):
        raise AudioError('无效媒体路径')
    return candidate


def check_tools() -> bool:
    return bool(shutil.which(settings.ffmpeg_path) and shutil.which(settings.ffprobe_path))


def normalize_audio(source: Path, destination: Path) -> None:
    if source.resolve() == destination.resolve() or destination.exists():
        raise AudioError('音频输出路径不可用')
    if not check_tools():
        raise AudioError('缺少 ffmpeg 或 ffprobe，无法处理音频')
    try:
        if not 0 < source.stat().st_size <= 20 * 1024 * 1024:
            raise AudioError('音频大小须在 20MB 以内且不能为空')
        probe = subprocess.run([settings.ffprobe_path, '-v', 'error', '-protocol_whitelist', 'file,pipe',
                                '-format_whitelist', 'matroska,webm,mov,mp3,wav,ogg',
                                '-show_streams', '-of', 'json', str(source.resolve())],
                               capture_output=True, text=True, timeout=30, shell=False, check=True)
        streams = json.loads(probe.stdout)['streams']
        if not isinstance(streams, list) or not all(isinstance(s, dict) for s in streams):
            raise AudioError('无效音频信息')
        if not any(s.get('codec_type') == 'audio' for s in streams) or any(s.get('codec_type') == 'video' for s in streams):
            raise AudioError('文件必须包含音轨且不能包含视频')
        subprocess.run([settings.ffmpeg_path, '-nostdin', '-v', 'error', '-protocol_whitelist', 'file,pipe',
                                '-format_whitelist', 'matroska,webm,mov,mp3,wav,ogg',
                        '-i', str(source.resolve()), '-map', '0:a:0', '-t', '91', '-vn', '-ac', '1',
                        '-ar', '16000', '-c:a', 'pcm_s16le', '-f', 'wav', '-n', str(destination.resolve())],
                       capture_output=True, timeout=30, shell=False, check=True)
        with wave.open(str(destination), 'rb') as wav:
            if (wav.getframerate() != 16000 or wav.getnchannels() != 1 or wav.getsampwidth() != 2
                    or not 0 < wav.getnframes() <= 90 * 16000):
                raise AudioError('音频必须有效且不超过 90 秒')
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError, wave.Error, EOFError, AudioError):
        destination.unlink(missing_ok=True)
        raise AudioError('音频无效或超过限制，请上传 90 秒以内的纯音频') from None
