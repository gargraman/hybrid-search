from beeai_framework import Agent
from typing import List, Dict

class VerificationAgent(Agent):
    def __init__(self):
        super().__init__(instructions="You are a verification agent. Check search results for factual accuracy and compliance with business rules.")

    async def verify_results(self, results: List[Dict]) -> List[Dict]:
        # Example: verify price is within allowed range
        verified = [r for r in results if 0 < r['metadata'].get('price', 0) < 1000]
        # TODO: Add LLM-based verification for business rules
        return verified
