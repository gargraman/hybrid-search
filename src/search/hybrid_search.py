"""
Hybrid search combining semantic (Qdrant) and keyword (Whoosh) search.

Uses Reciprocal Rank Fusion (RRF) to merge results from both search methods.
"""
import asyncio
from typing import Dict, List, Optional
from asyncpg import Pool
from qdrant_client import QdrantClient

from config.settings import settings
from src.db.qdrant import get_embedding
from src.search.qdrant_postgres_search import search_menu_items
from whoosh.index import open_dir
from whoosh.qparser import MultifieldParser


def filter_results(
    results: List[Dict],
    price_max: Optional[float] = None,
    dietary: Optional[str] = None,
    location: Optional[str] = None,
) -> List[Dict]:
    """
    Apply post-search filters to results.

    Args:
        results: List of search results
        price_max: Maximum price filter
        dietary: Dietary restriction filter (substring match)
        location: Location filter (substring match in address, city, or state)

    Returns:
        Filtered list of results
    """
    filtered: List[Dict] = []
    dietary_term = dietary.lower() if dietary else None
    location_term = location.lower() if location else None

    for res in results:
        meta = res["metadata"]
        price = float(meta.get("price", 0))

        # Price filter
        if price_max is not None and price > price_max:
            continue

        # Dietary filter (check description and text blob)
        if dietary_term:
            description = (meta.get("description") or "").lower()
            text_blob = (meta.get("text") or "").lower()
            if dietary_term not in description and dietary_term not in text_blob:
                continue

        # Location filter (check address, city, and state)
        if location_term:
            address_blob = " ".join([
                meta.get("address", ""),
                meta.get("city", ""),
                meta.get("state", ""),
            ]).lower()
            if location_term not in address_blob:
                continue

        filtered.append(res)

    return filtered


async def _semantic_search_async(
    query: str,
    top_k: int,
    qdrant_client: Optional[QdrantClient] = None,
    db_pool: Optional[Pool] = None
) -> List[Dict]:
    """
    Perform async semantic search using Qdrant + PostgreSQL.

    Args:
        query: Search query text
        top_k: Maximum number of results
        qdrant_client: Qdrant client instance
        db_pool: PostgreSQL connection pool

    Returns:
        List of enriched search results
    """
    query_vector = get_embedding(query)
    results = await search_menu_items(
        query_vector,
        top_k,
        qdrant_client=qdrant_client,
        db_pool=db_pool
    )

    enriched: List[Dict] = []
    for item in results:
        metadata = item.get("metadata", {})
        # Ensure text field exists
        metadata.setdefault(
            "text",
            " ".join(filter(None, [metadata.get("name"), metadata.get("description")])),
        )
        enriched.append({
            "id": item.get("id"),
            "score": float(item.get("score", 0.0)),
            "metadata": metadata,
        })

    return enriched


def semantic_search(
    query: str,
    top_k: int = 10,
    qdrant_client: Optional[QdrantClient] = None,
    db_pool: Optional[Pool] = None
) -> List[Dict]:
    """
    Perform semantic search with async event loop handling.

    Handles both running and non-running event loop scenarios.

    Args:
        query: Search query text
        top_k: Maximum number of results
        qdrant_client: Qdrant client instance
        db_pool: PostgreSQL connection pool

    Returns:
        List of search results
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already in an event loop, create a new one for this operation
        new_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(new_loop)
            return new_loop.run_until_complete(
                _semantic_search_async(query, top_k, qdrant_client, db_pool)
            )
        except Exception:
            return []
        finally:
            new_loop.close()
            asyncio.set_event_loop(loop)

    # No event loop running, create one
    try:
        return asyncio.run(_semantic_search_async(query, top_k, qdrant_client, db_pool))
    except Exception:
        return []


def keyword_search_whoosh(query: str, top_k: int = 10) -> List[Dict]:
    """
    Perform keyword search using Whoosh full-text index.

    Args:
        query: Search query text
        top_k: Maximum number of results

    Returns:
        List of search results with BM25 scores
    """
    try:
        ix = open_dir(settings.whoosh_index_path)
    except OSError:
        return []

    with ix.searcher() as searcher:
        parser = MultifieldParser(["text", "restaurant", "cuisine", "category"], schema=ix.schema)
        parsed_query = parser.parse(query)
        hits = searcher.search(parsed_query, limit=top_k)

        results: List[Dict] = []
        for hit in hits:
            # Extract and convert numeric fields
            price_value = hit.get("price")
            rating_value = hit.get("rating")
            latitude_value = hit.get("latitude")
            longitude_value = hit.get("longitude")
            review_count_value = hit.get("review_count")

            metadata = {
                "text": hit.get("text", ""),
                "restaurant": hit.get("restaurant", ""),
                "restaurant_type": hit.get("restaurant_type", ""),
                "address": hit.get("address", ""),
                "city": hit.get("city", ""),
                "state": hit.get("state", ""),
                "latitude": float(latitude_value) if latitude_value is not None else None,
                "longitude": float(longitude_value) if longitude_value is not None else None,
                "cuisine": hit.get("cuisine", ""),
                "category": hit.get("category", ""),
                "price": float(price_value) if price_value is not None else 0.0,
                "rating": float(rating_value) if rating_value is not None else 0.0,
                "review_count": int(review_count_value) if review_count_value is not None else 0,
                "description": hit.get("description", ""),
                "restaurant_description": hit.get("restaurant_description", ""),
                "restaurant_history": hit.get("restaurant_history", ""),
                "contact_phone": hit.get("contact_phone", ""),
                "contact_website": hit.get("contact_website", ""),
                "rewards": hit.get("rewards", ""),
            }
            results.append({"id": hit.get("id"), "score": float(hit.score), "metadata": metadata})

        return results


def _merge_results(semantic: List[Dict], lexical: List[Dict]) -> List[Dict]:
    """
    Merge semantic and lexical search results using Reciprocal Rank Fusion (RRF).

    RRF formula: score = sum(1 / (k + rank)) for each appearance of an item

    Args:
        semantic: Results from semantic search
        lexical: Results from lexical search

    Returns:
        Merged and ranked results
    """
    # Assign ranks based on order (1-based)
    semantic_ranks = {item["id"]: rank + 1 for rank, item in enumerate(semantic)}
    lexical_ranks = {item["id"]: rank + 1 for rank, item in enumerate(lexical)}

    combined: Dict[str, Dict] = {}

    # Collect all unique items
    all_items = set(semantic_ranks.keys()) | set(lexical_ranks.keys())

    for item_id in all_items:
        metadata = {}

        # Merge metadata from both sources (PostgreSQL takes precedence)
        semantic_meta = {}
        lexical_meta = {}

        if item_id in [s["id"] for s in semantic]:
            semantic_meta = next(s["metadata"] for s in semantic if s["id"] == item_id)

        if item_id in [l["id"] for l in lexical]:
            lexical_meta = next(l["metadata"] for l in lexical if l["id"] == item_id)

        # Semantic metadata first, then lexical
        metadata.update(semantic_meta)
        metadata.update(lexical_meta)  # lexical overwrites if conflict

        # Collect ranks from both methods
        ranks = []
        if item_id in semantic_ranks:
            ranks.append(semantic_ranks[item_id])
        if item_id in lexical_ranks:
            ranks.append(lexical_ranks[item_id])

        # Compute RRF score: sum(1 / (k + rank))
        rrf_score = sum(1 / (settings.rrf_k + rank) for rank in ranks)

        combined[item_id] = {
            "id": item_id,
            "score": rrf_score,
            "metadata": metadata,
        }

    # Sort by RRF score descending
    merged_results = list(combined.values())
    return sorted(merged_results, key=lambda item: item["score"], reverse=True)


def hybrid_search(
    query: str,
    top_k: int = 10,
    price_max: Optional[float] = None,
    dietary: Optional[str] = None,
    location: Optional[str] = None,
    qdrant_client: Optional[QdrantClient] = None,
    db_pool: Optional[Pool] = None
) -> List[Dict]:
    """
    Perform hybrid search combining semantic and keyword search with RRF.

    Args:
        query: Search query text
        top_k: Maximum number of results to return
        price_max: Maximum price filter
        dietary: Dietary restriction filter
        location: Location filter
        qdrant_client: Qdrant client instance (injected from app.state)
        db_pool: PostgreSQL connection pool (injected from app.state)

    Returns:
        Filtered and merged search results

    Algorithm:
        1. Perform semantic search (Qdrant + PostgreSQL)
        2. Perform keyword search (Whoosh)
        3. Merge results using RRF
        4. Apply post-merge filters
        5. Return top_k results
    """
    # Fetch 2x results from each method for better RRF merging
    semantic_results = semantic_search(query, top_k * 2, qdrant_client, db_pool)
    lexical_results = keyword_search_whoosh(query, top_k * 2)

    # Merge using RRF
    merged = _merge_results(semantic_results, lexical_results)

    # Apply filters
    filtered = filter_results(merged, price_max=price_max, dietary=dietary, location=location)

    # Return top_k results
    return filtered[:top_k]
