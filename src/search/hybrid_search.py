from config.settings import settings
import chromadb
import numpy as np
from whoosh.index import open_dir
from whoosh.qparser import QueryParser
from elasticsearch import Elasticsearch
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text: str) -> list:
    return model.encode([text])[0].tolist()

def filter_results(results: List[Dict], price_max: Optional[float] = None, dietary: Optional[str] = None, location: Optional[str] = None) -> List[Dict]:
    filtered = []
    for res in results:
        meta = res["metadata"]
        if price_max and meta.get("price", 0) > price_max:
            continue
        if dietary and dietary.lower() not in meta.get("text", "").lower():
            continue  # Simple check, can improve
        if location and location.lower() not in meta.get("address", "").lower():
            continue
        filtered.append(res)
    return filtered

def semantic_search(query: str, top_k: int = 10) -> List[Dict]:
    client = chromadb.PersistentClient(path=settings.chroma_path)
    collection = client.get_collection("menu_items")
    query_embedding = model.encode([query])[0].tolist()
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
    return [{"id": id, "score": 1 - score, "metadata": meta} for id, score, meta in zip(results["ids"][0], results["distances"][0], results["metadatas"][0])]

def keyword_search_whoosh(query: str, top_k: int = 10) -> List[Dict]:
    ix = open_dir(settings.whoosh_index_path)
    with ix.searcher() as searcher:
        qp = QueryParser("text", ix.schema)
        q = qp.parse(query)
        results = searcher.search(q, limit=top_k)
        return [{"id": hit["id"], "score": hit.score, "metadata": {"restaurant": hit["restaurant"], "price": hit["price"]}} for hit in results]

def keyword_search_es(query: str, top_k: int = 10) -> List[Dict]:
    try:
        es = Elasticsearch([{"host": settings.es_host, "port": settings.es_port, "scheme": settings.es_scheme}])
        body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["text", "restaurant"]
                }
            },
            "size": top_k
        }
        results = es.search(index="menu_items", body=body)
        return [{"id": hit["_id"], "score": hit["_score"], "metadata": hit["_source"]} for hit in results["hits"]["hits"]]
    except Exception:
        return []

def hybrid_search(query: str, top_k: int = 10, price_max: Optional[float] = None, dietary: Optional[str] = None, location: Optional[str] = None) -> List[Dict]:
    # Combine semantic and keyword results
    semantic = semantic_search(query, top_k * 2)  # Get more to filter
    keyword = keyword_search_whoosh(query, top_k * 2)
    # Combine
    combined = {}
    for res in semantic + keyword:
        id = res["id"]
        if id not in combined:
            combined[id] = {"id": id, "score": 0, "count": 0, "metadata": res["metadata"]}
        combined[id]["score"] += res["score"]
        combined[id]["count"] += 1
    # Average score
    for item in combined.values():
        item["score"] /= item["count"]
    # Sort by score
    sorted_results = sorted(combined.values(), key=lambda x: x["score"], reverse=True)
    # Apply filters
    filtered_results = filter_results(sorted_results, price_max, dietary, location)
    return filtered_results[:top_k]