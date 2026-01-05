from typing import Optional
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Unified application configuration with environment variable support.

    All settings can be configured via environment variables.
    Database credentials use SecretStr for security.
    """

    # Database settings (consolidated from db_config.py)
    postgres_dsn: str = Field(
        default="postgresql://user:password@localhost:5432/restaurantdb",
        description="PostgreSQL connection string"
    )
    qdrant_host: str = Field(
        default="localhost",
        description="Qdrant server host"
    )
    qdrant_port: int = Field(
        default=6333,
        ge=1,
        le=65535,
        description="Qdrant server port"
    )
    qdrant_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Qdrant API key (optional)"
    )

    # LLM settings
    deepseek_api_key: Optional[SecretStr] = Field(
        default=None,
        description="DeepSeek API key for LLM operations"
    )
    openai_api_key: Optional[SecretStr] = Field(
        default=None,
        description="OpenAI API key (fallback LLM)"
    )
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com",
        description="DeepSeek API base URL"
    )
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API base URL"
    )

    # Whoosh search settings
    whoosh_index_path: str = Field(
        default="./whoosh_index",
        description="Path to Whoosh index directory"
    )

    # RRF (Reciprocal Rank Fusion) settings
    rrf_k: int = Field(
        default=60,
        ge=1,
        description="RRF k parameter for hybrid search fusion"
    )

    # Chat settings
    chat_summarization_threshold: int = Field(
        default=10,
        ge=1,
        description="Number of messages before triggering summarization"
    )
    chat_max_iterations: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum iterations for chat agent"
    )
    chat_max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retries for chat operations"
    )
    chat_summary_max_tokens: int = Field(
        default=500,
        ge=100,
        le=2000,
        description="Maximum tokens for chat summaries"
    )
    chat_recent_messages_count: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of recent messages to keep in context"
    )

    @field_validator('rrf_k')
    @classmethod
    def validate_rrf_k(cls, v: int) -> int:
        """Ensure RRF k parameter is positive."""
        if v < 1:
            raise ValueError("rrf_k must be positive")
        return v

    @field_validator('postgres_dsn')
    @classmethod
    def validate_postgres_dsn(cls, v: str) -> str:
        """Validate PostgreSQL DSN format."""
        if not v.startswith(('postgresql://', 'postgres://')):
            raise ValueError("postgres_dsn must start with postgresql:// or postgres://")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Allow extra fields for forward compatibility
        extra = "ignore"


# Singleton instance
settings = Settings()
