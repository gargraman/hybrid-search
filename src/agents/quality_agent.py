from beeai_framework import Agent
from typing import List, Dict

class QualityAgent(Agent):
    def __init__(self):
        super().__init__(instructions="You are a quality assurance agent. Validate and filter search results for relevance, completeness, and safety. Return only high-quality results.")

    async def filter_results(self, query: str, results: List[Dict]) -> List[Dict]:
        # Example: filter out results with missing price or description
        filtered = [r for r in results if r['metadata'].get('price') and r['metadata'].get('description')]
        # TODO: Add LLM-based validation for relevance, safety, etc.
        return filtered
