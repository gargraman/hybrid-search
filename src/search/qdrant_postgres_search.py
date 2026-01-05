"""
Qdrant + PostgreSQL hybrid search implementation.

This module provides semantic search using Qdrant vector database
combined with metadata enrichment from PostgreSQL.
"""
from typing import List, Dict, Any, Optional
import asyncpg
from asyncpg import Pool
from qdrant_client import QdrantClient

from config.db_config import QDRANT_HOST, QDRANT_PORT, QDRANT_API_KEY, POSTGRES_DSN

VECTOR_SIZE = 384
COLLECTION_NAME = "menu_items"


def _safe_float(value: Any) -> Optional[float]:
    """Safely convert value to float."""
    if value is not None:
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    return None


def _safe_int(value: Any) -> Optional[int]:
    """Safely convert value to int."""
    if value is not None:
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    return None


async def search_menu_items(
    query_vector: List[float],
    top_k: int = 10,
    qdrant_client: Optional[QdrantClient] = None,
    db_pool: Optional[Pool] = None
) -> List[Dict[str, Any]]:
    """
    Search menu items using vector similarity in Qdrant and enrich with PostgreSQL metadata.

    Args:
        query_vector: 384-dimensional embedding vector for the search query
        top_k: Maximum number of results to return (default: 10)
        qdrant_client: Qdrant client instance (injected from app.state).
                      If None, creates a temporary client (not recommended for production).
        db_pool: PostgreSQL connection pool (injected from app.state).
                If None, creates a temporary connection (not recommended for production).

    Returns:
        List of search results with metadata. Each result contains:
        - id: External ID of the menu item
        - score: Similarity score from Qdrant
        - metadata: Dictionary with menu item and restaurant information

    Raises:
        asyncpg.PostgresError: If database operation fails
        Exception: If Qdrant search fails

    Example:
        >>> from src.db.qdrant import get_embedding
        >>> query_vec = get_embedding("vegan tacos")
        >>> results = await search_menu_items(query_vec, top_k=5, qdrant_client=client, db_pool=pool)
    """
    # Create temporary Qdrant client if not provided (fallback for backward compatibility)
    if qdrant_client is None:
        qdrant_client = QdrantClient(
            host=QDRANT_HOST,
            port=QDRANT_PORT,
            api_key=QDRANT_API_KEY,
            timeout=30
        )

    # Qdrant vector search
    results = qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k
    )

    # Extract external_ids from payload (not from point.id which is now UUID)
    external_ids = [point.payload.get("external_id", str(point.id)) for point in results]

    if not external_ids:
        return []

    # Enrich with PostgreSQL metadata using connection pool
    if db_pool:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    mi.external_id,
                    mi.category,
                    mi.name,
                    mi.description,
                    mi.price,
                    mi.restaurant_id,
                    r.name AS restaurant_name,
                    r.address,
                    r.city,
                    r.state,
                    r.latitude,
                    r.longitude,
                    r.cuisine,
                    r.rating,
                    r.review_count,
                    r.on_time_rate,
                    r.delivery_fee,
                    r.delivery_minimum
                FROM menu_items mi
                JOIN restaurants r ON mi.restaurant_id = r.id
                WHERE mi.external_id = ANY($1::text[])
                """,
                external_ids,
            )
    else:
        # Fallback: create temporary connection (not recommended for production)
        async with asyncpg.create_pool(
            POSTGRES_DSN,
            min_size=1,
            max_size=2,
            timeout=30
        ) as temp_pool:
            async with temp_pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        mi.external_id,
                        mi.category,
                        mi.name,
                        mi.description,
                        mi.price,
                        mi.restaurant_id,
                        r.name AS restaurant_name,
                        r.address,
                        r.city,
                        r.state,
                        r.latitude,
                        r.longitude,
                        r.cuisine,
                        r.rating,
                        r.review_count,
                        r.on_time_rate,
                        r.delivery_fee,
                        r.delivery_minimum
                    FROM menu_items mi
                    JOIN restaurants r ON mi.restaurant_id = r.id
                    WHERE mi.external_id = ANY($1::text[])
                    """,
                    external_ids,
                )

    # Build lookup map for efficient row access
    rows_by_id = {row["external_id"]: row for row in rows}

    # Merge Qdrant results with PostgreSQL metadata
    merged = []
    for point in results:
        payload = point.payload or {}
        # Use external_id from payload to look up PostgreSQL row
        key = payload.get("external_id", str(point.id))
        row = rows_by_id.get(key)

        # Skip if no data from either source
        if not row and not payload:
            continue

        # Merge metadata with PostgreSQL taking precedence
        metadata = {
            "id": key,
            "name": (row["name"] if row else None) or payload.get("name"),
            "description": (row["description"] if row else None) or payload.get("description"),
            "price": (row["price"] if row else None) or payload.get("price"),
            "category": (row["category"] if row else None) or payload.get("category"),
            "restaurant": (row["restaurant_name"] if row else None) or payload.get("restaurant_name"),
            "restaurant_id": (row["restaurant_id"] if row else None) or payload.get("restaurant_id"),
            "address": (row["address"] if row else None) or payload.get("address"),
            "city": (row["city"] if row else None) or payload.get("city"),
            "state": (row["state"] if row else None) or payload.get("state"),
            "latitude": (row["latitude"] if row else None) or payload.get("latitude"),
            "longitude": (row["longitude"] if row else None) or payload.get("longitude"),
            "cuisine": (row["cuisine"] if row else None) or payload.get("cuisine"),
            "rating": (row["rating"] if row else None) or payload.get("rating"),
            "review_count": (row["review_count"] if row else None) or payload.get("review_count"),
            "on_time_rate": (row["on_time_rate"] if row else None) or payload.get("on_time_rate"),
            "delivery_fee": (row["delivery_fee"] if row else None) or payload.get("delivery_fee"),
            "delivery_minimum": (row["delivery_minimum"] if row else None) or payload.get("delivery_minimum"),
            # Additional fields only in Qdrant payload
            "restaurant_type": payload.get("restaurant_type"),
            "restaurant_description": payload.get("restaurant_description"),
            "restaurant_history": payload.get("restaurant_history"),
            "contact_phone": payload.get("contact_phone"),
            "contact_website": payload.get("contact_website"),
            "rewards": payload.get("rewards"),
        }

        # Generate text blob for search context
        text_blob = payload.get("text")
        if not text_blob:
            name = metadata.get("name") or ""
            description = metadata.get("description") or ""
            text_blob = f"{name} {description}".strip()
        metadata["text"] = text_blob

        # Apply type conversions using helper functions
        metadata["latitude"] = _safe_float(metadata.get("latitude"))
        metadata["longitude"] = _safe_float(metadata.get("longitude"))
        metadata["price"] = _safe_float(metadata.get("price"))
        metadata["rating"] = _safe_float(metadata.get("rating"))
        metadata["review_count"] = _safe_int(metadata.get("review_count"))
        metadata["delivery_fee"] = _safe_float(metadata.get("delivery_fee"))
        metadata["delivery_minimum"] = _safe_float(metadata.get("delivery_minimum"))

        # Normalize cuisine to lowercase
        if metadata.get("cuisine"):
            metadata["cuisine"] = str(metadata["cuisine"]).lower()

        merged.append({
            "id": key,
            "score": float(point.score),
            "metadata": metadata,
        })

    return merged
