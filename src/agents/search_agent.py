from beeai_framework import Agent, LLM
from config.settings import settings
from src.search.qdrant_postgres_search import search_menu_items
from src.utils.docling_input import parse_restaurant_json_with_docling
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
        # Load LLM context from input JSON via docling
        self.llm_context = parse_restaurant_json_with_docling("input/restaurant1.json")
        super().__init__(
            llm=llm,
            instructions=f"You are a search agent. Use the following restaurant data for context:\n{self.llm_context}\nPerform hybrid search on restaurant data based on keywords and filters."
        )

    async def perform_search(self, keywords: str, top_k: int = 10, price_max: Optional[float] = None, dietary: Optional[str] = None, location: Optional[str] = None) -> List[SearchResult]:
        # Use Qdrant+Postgres for semantic search
        query_embedding = get_embedding(keywords)
        results = await search_menu_items(query_embedding, top_k)
        # Apply filters (price, dietary, location)
        filtered = []
        for r in results:
            meta = r["metadata"]
            if price_max and meta.get("price", 0) > price_max:
                continue
            if dietary and dietary.lower() not in meta.get("description", "").lower():
                continue
            if location and location.lower() not in meta.get("address", "").lower():
                continue
            filtered.append(SearchResult(**r))
        return filtered