from beeai_framework import Agent, LLM
from openai import OpenAI
from config.settings import settings
from pydantic import BaseModel
from typing import Optional

class ParsedQuery(BaseModel):
    keywords: str
    price_max: Optional[float] = None
    dietary: Optional[str] = None
    location: Optional[str] = None

class QueryParserAgent(Agent):
    def __init__(self):
        if settings.deepseek_api_key:
            self.client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
            self.model = "deepseek-chat"
        elif settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
            self.model = "gpt-3.5-turbo"
        else:
            raise ValueError("No API key set for LLM")
        super().__init__(instructions="Parse restaurant search queries into keywords and filters. Return only valid JSON.")

    async def parse_query(self, query: str) -> ParsedQuery:
        prompt = f"""
Parse the following restaurant search query into structured components. Return a JSON object with: keywords, price_max, dietary, location. Query: '{query}' Respond only with valid JSON.
"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        import json
        try:
            data = json.loads(response.choices[0].message.content.strip())
            return ParsedQuery(**data)
        except Exception:
            return ParsedQuery(keywords=query)