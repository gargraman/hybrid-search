"""
Orchestrator for multi-agent search pipeline.

Coordinates the execution of multiple agents in sequence:
1. QueryParserAgent - Parses natural language queries
2. SearchAgent - Performs semantic search
3. QualityAgent - Filters for quality and relevance
4. VerificationAgent - Verifies business rule compliance
5. RankingAgent - Scores and ranks results
"""
from typing import Optional
from asyncpg import Pool
from qdrant_client import QdrantClient

from src.agents.query_parser import QueryParserAgent
from src.agents.search_agent import SearchAgent
from src.agents.ranking_agent import RankingAgent
from src.agents.quality_agent import QualityAgent
from src.agents.verification_agent import VerificationAgent


class Orchestrator:
    """
    Orchestrates the multi-agent search pipeline.

    Manages the lifecycle of all agents and coordinates their execution.
    """

    def __init__(
        self,
        db_pool: Optional[Pool] = None,
        qdrant_client: Optional[QdrantClient] = None
    ):
        """
        Initialize the orchestrator with shared resources.

        Args:
            db_pool: PostgreSQL connection pool for database operations
            qdrant_client: Qdrant client for vector search operations
        """
        self.parser = QueryParserAgent()
        self.searcher = SearchAgent(db_pool=db_pool, qdrant_client=qdrant_client)
        self.quality = QualityAgent()
        self.verification = VerificationAgent()
        self.ranker = RankingAgent()

    async def run_search(self, query: str, top_k: int = 10):
        """
        Execute the full multi-agent search pipeline.

        Args:
            query: Natural language search query
            top_k: Maximum number of results to return

        Returns:
            List of ranked search results

        Pipeline:
            1. Parse query into structured filters
            2. Perform semantic search with filters
            3. Filter results for quality and safety
            4. Verify results against business rules
            5. Rank results by relevance
        """
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
