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

    embedding_provider: Literal["local"] = "local"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384
    rag_top_k_lore: int = 3
    rag_top_k_rules: int = 5

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
