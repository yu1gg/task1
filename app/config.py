from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI 职业发展平台"
    database_url: str = "sqlite:///./data/app.db"
    session_secret: str = "dev-only-change-me"
    teacher_invite_code: str = ""
    data_dir: Path = Path("data")
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    llm_timeout_seconds: float = 60.0
    llm_max_retries: int = 2
    siliconflow_api_key: str = ""
    speech_base_url: str = "https://api.siliconflow.cn/v1"
    asr_model: str = "FunAudioLLM/SenseVoiceSmall"
    tts_model: str = "FunAudioLLM/CosyVoice2-0.5B"
    tts_voice: str = "FunAudioLLM/CosyVoice2-0.5B:alex"
    speech_timeout_seconds: float = Field(default=60, gt=0, le=180)
    speech_max_retries: int = Field(default=2, ge=0, le=2)
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    interview_question_count: int = Field(default=5, ge=5, le=8)
    interview_worker_enabled: bool = True
    resume_export_worker_enabled: bool = True


settings = Settings()
