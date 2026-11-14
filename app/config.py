from pathlib import Path

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


settings = Settings()
