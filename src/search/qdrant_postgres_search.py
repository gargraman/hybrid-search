from qdrant_client import QdrantClient
from config.db_config import QDRANT_HOST, QDRANT_PORT, QDRANT_API_KEY, POSTGRES_DSN
import asyncpg

VECTOR_SIZE = 384
COLLECTION_NAME = "menu_items"

client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, api_key=QDRANT_API_KEY)

async def search_menu_items(query_vector, top_k=10):
    # Qdrant vector search
    results = client.search(collection_name=COLLECTION_NAME, query_vector=query_vector, limit=top_k)
    ids = [point.id for point in results]
    conn = await asyncpg.connect(POSTGRES_DSN)
    rows = await conn.fetch(
        'SELECT * FROM menu_items WHERE id = ANY($1::text[])', ids
    )
    await conn.close()
    merged = []
    for point in results:
        row = next((r for r in rows if str(r['id']) == str(point.id)), None)
        if row:
            merged.append({
                "id": point.id,
                "score": point.score,
                "metadata": dict(row)
            })
    return merged
