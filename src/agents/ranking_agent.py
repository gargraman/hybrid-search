from beeai_framework import Agent, LLM
from openai import OpenAI
from config.settings import settings
from pydantic import BaseModel
from typing import List

class RankedResult(BaseModel):
    id: str
    score: float
    metadata: dict
    relevance_score: float

class RankingAgent(Agent):
    def __init__(self):
        if settings.deepseek_api_key:
            self.client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
            self.model = "deepseek-chat"
        elif settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
            self.model = "gpt-3.5-turbo"
        else:
            raise ValueError("No API key set for LLM")
        super().__init__(
            instructions="Rank search results for relevance."
        )

    async def rank_results(self, query: str, results: List[dict]) -> List[RankedResult]:
        ranked = []
        for res in results:
            prompt = f"Rate relevance of this menu item to query '{query}': {res['metadata']['text']} (Price: ${res['metadata']['price']}) Restaurant: {res['metadata']['restaurant']}\nReturn a number 0-10."
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            try:
                relevance = float(response.choices[0].message.content.strip())
            except Exception:
                relevance = res['score'] * 10  # fallback
            ranked.append(RankedResult(
                id=res['id'],
                score=res['score'],
                metadata=res['metadata'],
                relevance_score=relevance
            ))
        # Sort by relevance
        ranked.sort(key=lambda x: x.relevance_score, reverse=True)
        return ranked