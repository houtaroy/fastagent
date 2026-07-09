from openai.types.shared.reasoning_effort import ReasoningEffort
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    DATABASE_URI: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/app"

    OPENAI_BASE_URL: str | None = None
    OPENAI_API_KEY: str = ""
    OPENAI_TRACING: bool = True

    AGENT_NAME: str = ""
    AGENT_MODEL: str = ""
    AGENT_MODEL_REASONING: ReasoningEffort = "none"
    # AGENT_PROMPT_FILE: str = "prompts/developer.md"
    # AGENT_CONTEXT_WINDOW: int = 10


settings = Settings()
