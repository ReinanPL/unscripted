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

    # ===== LLM (multi-provider — ADR-045) =====
    # `llm_provider` seleciona a implementação. Cada provider tem dois modelos:
    # - `*_MODEL_REASONING` é usado pelo RefereeAgent (output_schema=Ruling).
    # - `*_MODEL_NARRATIVE` é usado pelo Narrator/NPCActor (streaming de prosa).
    # Quando `*_MODEL_NARRATIVE` está vazio, faz fallback para o REASONING
    # (single-model preservado — útil para Gemini/OpenAI).
    llm_provider: Literal["gemini_aistudio", "groq", "openai"] = "gemini_aistudio"

    # Gemini (Google AI Studio)
    gemini_api_key: str = ""
    gemini_model_reasoning: str = "gemini-2.5-flash"
    gemini_model_narrative: str = ""

    # Groq (via LiteLlm — wrapper do ADK)
    groq_api_key: str = ""
    groq_model_reasoning: str = "llama-3.3-70b-versatile"
    groq_model_narrative: str = "llama-3.1-8b-instant"

    # OpenAI (via LiteLlm)
    openai_api_key: str = ""
    openai_model_reasoning: str = "gpt-4o-mini"
    openai_model_narrative: str = ""

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

    voice_provider: Literal["stub"] = "stub"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


def get_settings() -> Settings:
    return Settings()
