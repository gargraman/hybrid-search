from beeai_framework import Agent, LLM
from config.settings import settings
from src.search.hybrid_search import hybrid_search
from pydantic import BaseModel
from typing import List, Dict, Optional

class SearchResult(BaseModel):
    id: str
    score: float
    metadata: Dict

class SearchAgent(Agent):
    def __init__(self):
        if settings.deepseek_api_key:
            llm = LLM(
                model="deepseek-chat",
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url
            )
        elif settings.openai_api_key:
            llm = LLM(
                model="gpt-3.5-turbo",
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url
            )
        else:
            raise ValueError("No API key set for LLM")
        super().__init__(
            llm=llm,
            instructions="You are a search agent. Perform hybrid search on restaurant data based on keywords and filters."
        )

    async def perform_search(self, keywords: str, top_k: int = 10, price_max: Optional[float] = None, dietary: Optional[str] = None, location: Optional[str] = None) -> List[SearchResult]:
        # Perform the search
        results = hybrid_search(keywords, top_k, price_max, dietary, location)
        return [SearchResult(**res) for res in results]