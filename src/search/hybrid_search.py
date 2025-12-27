import asyncio
from typing import Dict, List, Optional

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
    filtered: List[Dict] = []
    dietary_term = dietary.lower() if dietary else None
    location_term = location.lower() if location else None

    for res in results:
        meta = res["metadata"]
        price = float(meta.get("price", 0))
        if price_max is not None and price > price_max:
            continue
        description = (meta.get("description") or "").lower()
        text_blob = (meta.get("text") or "").lower()
        if dietary_term and dietary_term not in description and dietary_term not in text_blob:
            continue
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


def _normalize_scores(results: List[Dict]) -> List[Dict]:
    if not results:
        return []
    scores = [float(res.get("score", 0.0)) for res in results]
    max_score = max(scores)
    min_score = min(scores)
    if max_score == min_score:
        return [{**res, "normalized_score": 1.0} for res in results]
    normalized: List[Dict] = []
    for res, score in zip(results, scores):
        normalized_score = (score - min_score) / (max_score - min_score)
        normalized.append({**res, "normalized_score": normalized_score})
    return normalized


async def _semantic_search_async(query: str, top_k: int) -> List[Dict]:
    query_vector = get_embedding(query)
    results = await search_menu_items(query_vector, top_k)
    enriched: List[Dict] = []
    for item in results:
        metadata = item.get("metadata", {})
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


def semantic_search(query: str, top_k: int = 10) -> List[Dict]:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        new_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(new_loop)
            return new_loop.run_until_complete(_semantic_search_async(query, top_k))
        except Exception:
            return []
        finally:
            new_loop.close()
            asyncio.set_event_loop(loop)

    try:
        return asyncio.run(_semantic_search_async(query, top_k))
    except Exception:
        return []


def keyword_search_whoosh(query: str, top_k: int = 10) -> List[Dict]:
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
    semantic_norm = _normalize_scores(semantic)
    lexical_norm = _normalize_scores(lexical)

    combined: Dict[str, Dict] = {}

    for source, entries in (("semantic", semantic_norm), ("lexical", lexical_norm)):
        for entry in entries:
            entry_id = entry["id"]
            normalized_score = entry.get("normalized_score", 0.0)
            entry_metadata = entry.get("metadata", {}) or {}
            if entry_id not in combined:
                combined[entry_id] = {
                    "id": entry_id,
                    "metadata": {k: v for k, v in entry_metadata.items() if v is not None},
                    "scores": {},
                }
            combined_entry = combined[entry_id]
            if entry_metadata:
                cleaned_metadata = {k: v for k, v in entry_metadata.items() if v is not None}
                combined_entry["metadata"].update(cleaned_metadata)
            combined_entry["scores"][source] = normalized_score

    merged_results: List[Dict] = []
    for entry in combined.values():
        score_components = entry["scores"]
        averaged_score = sum(score_components.values()) / max(len(score_components), 1)
        merged_results.append({
            "id": entry["id"],
            "score": averaged_score,
            "metadata": entry["metadata"],
        })
    return sorted(merged_results, key=lambda item: item["score"], reverse=True)


def hybrid_search(
    query: str,
    top_k: int = 10,
    price_max: Optional[float] = None,
    dietary: Optional[str] = None,
    location: Optional[str] = None,
) -> List[Dict]:
    semantic_results = semantic_search(query, top_k * 2)
    lexical_results = keyword_search_whoosh(query, top_k * 2)
    merged = _merge_results(semantic_results, lexical_results)
    filtered = filter_results(merged, price_max=price_max, dietary=dietary, location=location)
    return filtered[:top_k]