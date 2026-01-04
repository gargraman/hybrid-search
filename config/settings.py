import os
from typing import Optional

class Settings:
    # LLM settings
    deepseek_api_key: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    deepseek_base_url: str = "https://api.deepseek.com"
    openai_base_url: str = "https://api.openai.com/v1"

    # Deprecated integrations (Chroma, Elasticsearch) intentionally removed

    # Whoosh
    whoosh_index_path: str = "./whoosh_index"

    # RRF settings
    rrf_k: int = 60

    # Chat settings
    chat_summarization_threshold: int = int(os.getenv("CHAT_SUMMARIZATION_THRESHOLD", "10"))
    chat_max_iterations: int = int(os.getenv("CHAT_MAX_ITERATIONS", "5"))
    chat_max_retries: int = int(os.getenv("CHAT_MAX_RETRIES", "3"))
    chat_summary_max_tokens: int = int(os.getenv("CHAT_SUMMARY_MAX_TOKENS", "500"))
    chat_max_iterations: int = int(os.getenv("CHAT_MAX_ITERATIONS", "5"))
    chat_max_retries: int = int(os.getenv("CHAT_MAX_RETRIES", "3"))
    chat_recent_messages_count: int = int(os.getenv("CHAT_RECENT_MESSAGES", "5"))

settings = Settings()