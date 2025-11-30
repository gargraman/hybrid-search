from qdrant_client import QdrantClient, models
from config.db_config import QDRANT_HOST, QDRANT_PORT, QDRANT_API_KEY

client = QdrantClient(
    host=QDRANT_HOST,
    port=QDRANT_PORT,
    api_key=QDRANT_API_KEY
)

def create_collection(collection_name: str, vector_size: int = 384):
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE)
    )

def upsert_vectors(collection_name: str, points: list):
    client.upsert(collection_name=collection_name, points=points)

def search_vectors(collection_name: str, query_vector: list, top_k: int = 10):
    return client.search(collection_name=collection_name, query_vector=query_vector, limit=top_k)
