from beeai_framework import Agent
from typing import List, Dict
from openai import OpenAI
from config.settings import settings

class QualityAgent(Agent):
    def __init__(self):
        if settings.deepseek_api_key:
            self.client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
            self.model = "deepseek-chat"
        elif settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
            self.model = "gpt-3.5-turbo"
        else:
            raise ValueError("No API key set for LLM")
        super().__init__(instructions="Validate and filter search results for relevance, completeness, and safety.")

    async def filter_results(self, query: str, results: List[Dict]) -> List[Dict]:
        filtered = []
        for r in results:
            prompt = f"Is this menu item relevant and safe for query '{query}'? {r['metadata']['text']} (Price: ${r['metadata']['price']}) Restaurant: {r['metadata']['restaurant']}\nReturn 'yes' or 'no'."
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            if response.choices[0].message.content.strip().lower() == 'yes':
                filtered.append(r)
        return filtered
