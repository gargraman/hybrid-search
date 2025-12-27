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

settings = Settings()