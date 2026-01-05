"""
Search Agent for performing semantic search with filters.

Uses Qdrant + PostgreSQL for hybrid search and applies filters
for price, dietary restrictions, and location.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from asyncpg import Pool
from qdrant_client import QdrantClient

from beeai_framework import Agent, LLM  # type: ignore
from config.settings import settings
from pydantic import BaseModel

from src.db.qdrant import get_embedding
from src.search.qdrant_postgres_search import search_menu_items


class SearchResult(BaseModel):
    """Search result model."""
    id: str
    score: float
    metadata: Dict


def _summarize_restaurant(data: Dict) -> str:
    """
    Summarize restaurant data for LLM context.

    Args:
        data: Restaurant data dictionary

    Returns:
        Formatted summary string
    """
    restaurant = data.get("restaurant", {})
    name = restaurant.get("name", "Unknown Restaurant")
    type_ = restaurant.get("type") or ""
    location = restaurant.get("address", {})
    address = ", ".join(filter(None, [location.get("street"), location.get("city"), location.get("state")]))
    ratings = data.get("ratings", {})
    avg_rating = ratings.get("average_rating")
    review_count = ratings.get("ezCater_review_count")

    menu = data.get("menu", {})
    groups = menu.get("items", []) if isinstance(menu, dict) else []
    highlights: List[str] = []
    for group in groups:
        category = group.get("category", "Uncategorized")
        item_names = [item.get("name") for item in group.get("items", []) if item.get("name")]
        if item_names:
            highlights.append(f"{category}: {', '.join(item_names[:3])}")
        if len(highlights) >= 5:
            break

    lines = [f"{name} ({type_})" if type_ else name]
    if address:
        lines.append(f"Location: {address}")
    if avg_rating is not None or review_count is not None:
        rating_line = "Rating: "
        rating_line += f"{avg_rating}" if avg_rating is not None else "N/A"
        if review_count is not None:
            rating_line += f" ({review_count} reviews)"
        lines.append(rating_line)
    if highlights:
        lines.append("Highlights: " + "; ".join(highlights))
    description = restaurant.get("description")
    if description:
        lines.append(f"Description: {description}")
    return "\n".join(lines)


def _load_llm_context(max_files: int = 20, max_chars: int = 8000) -> str:
    """
    Load LLM context from restaurant JSON files.

    Args:
        max_files: Maximum number of files to load
        max_chars: Maximum total characters to load

    Returns:
        Concatenated context string
    """
    base_path = Path("input")
    if not base_path.exists():
        return ""

    contexts: List[str] = []
    total_chars = 0
    for json_file in sorted(base_path.rglob("*.json")):
        try:
            with json_file.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            context = _summarize_restaurant(data)
        except Exception:
            # Silently skip files that can't be parsed
            continue
        segment = f"Source: {json_file}\n{context}"
        contexts.append(segment)
        total_chars += len(segment)
        if len(contexts) >= max_files or total_chars >= max_chars:
            break
    return "\n\n".join(contexts)


class SearchAgent(Agent):
    """
    Agent for performing semantic search with filters.

    Uses Qdrant + PostgreSQL for vector search and applies
    post-search filters for price, dietary restrictions, and location.
    """

    def __init__(
        self,
        db_pool: Optional[Pool] = None,
        qdrant_client: Optional[QdrantClient] = None
    ):
        """
        Initialize the search agent.

        Args:
            db_pool: PostgreSQL connection pool for database operations
            qdrant_client: Qdrant client for vector search operations
        """
        # Store connection resources
        self.db_pool = db_pool
        self.qdrant_client = qdrant_client

        # Initialize LLM client with proper SecretStr handling
        if settings.deepseek_api_key:
            llm = LLM(
                model="deepseek-chat",
                api_key=settings.deepseek_api_key.get_secret_value(),
                base_url=settings.deepseek_base_url
            )
        elif settings.openai_api_key:
            llm = LLM(
                model="gpt-3.5-turbo",
                api_key=settings.openai_api_key.get_secret_value(),
                base_url=settings.openai_base_url
            )
        else:
            raise ValueError("No API key set for LLM")

        # Load LLM context from available restaurant JSON files
        self.llm_context = _load_llm_context()

        super().__init__(
            llm=llm,
            instructions=(
                f"You are a search agent. Use the following restaurant data for context:\n"
                f"{self.llm_context}\n"
                f"Perform hybrid search on restaurant data based on keywords and filters."
            )
        )

    async def perform_search(
        self,
        keywords: str,
        top_k: int = 10,
        price_max: Optional[float] = None,
        dietary: Optional[str] = None,
        location: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Perform semantic search with filters.

        Args:
            keywords: Search keywords
            top_k: Maximum number of results
            price_max: Maximum price filter
            dietary: Dietary restriction filter
            location: Location filter

        Returns:
            List of filtered search results
        """
        # Use Qdrant+Postgres for semantic search with injected resources
        query_embedding = get_embedding(keywords)
        results = await search_menu_items(
            query_embedding,
            top_k,
            qdrant_client=self.qdrant_client,
            db_pool=self.db_pool
        )

        # Apply filters (price, dietary, location)
        filtered = []
        for r in results:
            meta = r["metadata"]

            # Price filter
            if price_max and meta.get("price", 0) > price_max:
                continue

            # Dietary filter (check both description and text fields)
            if dietary:
                description = meta.get("description", "").lower()
                text = meta.get("text", "").lower()
                if dietary.lower() not in description and dietary.lower() not in text:
                    continue

            # Location filter (check address, city, and state)
            if location:
                location_lower = location.lower()
                address = meta.get("address", "").lower()
                city = meta.get("city", "").lower()
                state = meta.get("state", "").lower()
                if not any(location_lower in field for field in [address, city, state]):
                    continue

            filtered.append(SearchResult(**r))

        return filtered
