from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_TITLE: str = "Task Agent Denadata"

    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"

    # OPENAI settings
    OPENAI_API_KEY: str = Field(...)
    OPENAI_PROXY: str | None = None
    OPENAI_MODEL: str = "gpt-5.4-mini"

    # SQLITE settings
    DB_PATH: str = "memory.db"

    # CSV settings
    TASK_CSV: str = Field(...)
    USERS_CSV: str = Field(...)


settings = Settings()
