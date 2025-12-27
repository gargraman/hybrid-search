import asyncpg
from qdrant_client import QdrantClient

from config.db_config import QDRANT_HOST, QDRANT_PORT, QDRANT_API_KEY, POSTGRES_DSN

VECTOR_SIZE = 384
COLLECTION_NAME = "menu_items"

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, api_key=QDRANT_API_KEY)

async def search_menu_items(query_vector, top_k=10):
    # Qdrant vector search
    results = client.search(collection_name=COLLECTION_NAME, query_vector=query_vector, limit=top_k)
    external_ids = [str(point.id) for point in results]
    if not external_ids:
        return []

    conn = await asyncpg.connect(POSTGRES_DSN)
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
    await conn.close()

    rows_by_id = {row["external_id"]: row for row in rows}
    merged = []
    for point in results:
        key = str(point.id)
        row = rows_by_id.get(key)
        payload = point.payload or {}
        if not row and not payload:
            continue
        metadata = {
            "id": key,
            "name": payload.get("name") or (row["name"] if row else None),
            "description": payload.get("description") or (row["description"] if row else None),
            "price": payload.get("price") or (row["price"] if row else None),
            "category": payload.get("category") or (row["category"] if row else None),
            "restaurant": payload.get("restaurant_name") or (row["restaurant_name"] if row else None),
            "restaurant_id": payload.get("restaurant_id") or (row["restaurant_id"] if row else None),
            "address": payload.get("address") or (row["address"] if row else None),
            "city": payload.get("city") or (row["city"] if row else None),
            "state": payload.get("state") or (row["state"] if row else None),
            "latitude": payload.get("latitude") or (row["latitude"] if row else None),
            "longitude": payload.get("longitude") or (row["longitude"] if row else None),
            "cuisine": payload.get("cuisine") or (row["cuisine"] if row else None),
            "rating": payload.get("rating") or (row["rating"] if row else None),
            "review_count": payload.get("review_count") or (row["review_count"] if row else None),
            "on_time_rate": payload.get("on_time_rate") or (row["on_time_rate"] if row else None),
            "delivery_fee": payload.get("delivery_fee") or (row["delivery_fee"] if row else None),
            "delivery_minimum": payload.get("delivery_minimum") or (row["delivery_minimum"] if row else None),
            "restaurant_type": payload.get("restaurant_type"),
            "restaurant_description": payload.get("restaurant_description"),
            "restaurant_history": payload.get("restaurant_history"),
            "contact_phone": payload.get("contact_phone"),
            "contact_website": payload.get("contact_website"),
            "rewards": payload.get("rewards"),
        }
        text_blob = payload.get("text")
        if not text_blob:
            name = metadata.get("name") or ""
            description = metadata.get("description") or ""
            text_blob = f"{name} {description}".strip()
        metadata["text"] = text_blob
        if metadata.get("latitude") is not None:
            metadata["latitude"] = float(metadata["latitude"])
        if metadata.get("longitude") is not None:
            metadata["longitude"] = float(metadata["longitude"])
        if metadata.get("price") is not None:
            metadata["price"] = float(metadata["price"])
        if metadata.get("rating") is not None:
            metadata["rating"] = float(metadata["rating"])
        if metadata.get("review_count") is not None:
            metadata["review_count"] = int(metadata["review_count"])
        if metadata.get("delivery_fee") is not None:
            metadata["delivery_fee"] = float(metadata["delivery_fee"])
        if metadata.get("delivery_minimum") is not None:
            metadata["delivery_minimum"] = float(metadata["delivery_minimum"])
        if metadata.get("cuisine"):
            metadata["cuisine"] = str(metadata["cuisine"]).lower()
        merged.append(
            {
                "id": key,
                "score": float(point.score),
                "metadata": metadata,
            }
        )
    return merged
