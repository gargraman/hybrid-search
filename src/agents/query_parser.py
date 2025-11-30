from beeai_framework import Agent, LLM
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
            instructions="You are a query parser agent. Parse restaurant search queries into keywords and filters. Return only valid JSON."
        )

    async def parse_query(self, query: str) -> ParsedQuery:
        prompt = f"""
Parse the following restaurant search query into structured components.
Return a JSON object with:
- keywords: the main search terms (e.g., "tacos", "pizza")
- price_max: maximum price if mentioned (e.g., 15 for "under 15"), null otherwise
- dietary: dietary restrictions if mentioned (e.g., "vegan", "gluten-free"), null otherwise
- location: location if mentioned (e.g., "near Harvard"), null otherwise

Query: "{query}"

Respond only with valid JSON.
"""
        response = await self.run(prompt)
        import json
        try:
            data = json.loads(response.content.strip())
            return ParsedQuery(**data)
        except:
            return ParsedQuery(keywords=query)