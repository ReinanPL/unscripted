from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "production"] = "development"

    llm_provider: Literal["gemini_aistudio"] = "gemini_aistudio"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    cors_allowed_origin: str = "http://localhost:5173"

    postgres_user: str = "unscripted"
    postgres_password: str = "changeme"
    postgres_db: str = "unscripted"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


def get_settings() -> Settings:
    return Settings()
