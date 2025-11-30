from beeai_framework import Agent, LLM
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
            instructions="You are a ranking agent. Evaluate and rank search results based on relevance to the query."
        )

    async def rank_results(self, query: str, results: List[dict]) -> List[RankedResult]:
        ranked = []
        for res in results:
            prompt = f"""
Evaluate the relevance of this menu item to the query "{query}".
Menu item: {res['metadata']['text']}
Price: ${res['metadata']['price']}
Restaurant: {res['metadata']['restaurant']}

Rate relevance from 0 to 10 (10 being perfect match). Return only the number.
"""
            response = await self.run(prompt)
            try:
                relevance = float(response.content.strip())
            except:
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