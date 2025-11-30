from src.agents.query_parser import QueryParserAgent
from src.agents.search_agent import SearchAgent
from src.agents.ranking_agent import RankingAgent
from src.agents.quality_agent import QualityAgent
from src.agents.verification_agent import VerificationAgent

class Orchestrator:
    def __init__(self):
        self.parser = QueryParserAgent()
        self.searcher = SearchAgent()
        self.quality = QualityAgent()
        self.verification = VerificationAgent()
        self.ranker = RankingAgent()

    async def run_search(self, query: str, top_k: int = 10):
        # Step 1: Parse query
        parsed = await self.parser.parse_query(query)
        
        # Step 2: Perform search
        search_results = await self.searcher.perform_search(
            parsed.keywords, top_k, parsed.price_max, parsed.dietary, parsed.location
        )
        
        # Step 3: Filter results for quality
        quality_results = await self.quality.filter_results(query, [r.dict() for r in search_results])
        
        # Step 4: Verify results
        verified_results = await self.verification.verify_results(quality_results)
        
        # Step 5: Rank results
        ranked_results = await self.ranker.rank_results(query, verified_results)
        
        return ranked_results