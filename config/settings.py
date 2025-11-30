import os
from typing import Optional

class Settings:
    # LLM settings
    deepseek_api_key: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    deepseek_base_url: str = "https://api.deepseek.com"
    openai_base_url: str = "https://api.openai.com/v1"

    # Elasticsearch
    es_host: str = os.getenv("ES_HOST", "localhost")
    es_port: int = int(os.getenv("ES_PORT", "9200"))
    es_scheme: str = os.getenv("ES_SCHEME", "http")

    # Chroma
    chroma_path: str = "./chroma_db"

    # Whoosh
    whoosh_index_path: str = "./whoosh_index"

settings = Settings()