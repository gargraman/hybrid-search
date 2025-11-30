from fastapi import FastAPI, Response
from pydantic import BaseModel
from typing import List
from prometheus_client import Counter, Histogram, start_http_server
from loguru import logger
import time

# Try to import orchestrator, but fall back to simple search if unavailable
try:
    from src.agents.orchestrator import Orchestrator
    USE_ORCHESTRATOR = True
    hybrid_search_func = None
except Exception as e:
    logger.warning(f"Orchestrator not available: {e}. Using simple hybrid search.")
    USE_ORCHESTRATOR = False
    from src.search.hybrid_search import hybrid_search as hybrid_search_func

app = FastAPI(title="AI-Powered Hybrid Culinary Search Engine")

# Metrics
SEARCH_REQUESTS = Counter('search_requests_total', 'Total search requests')
SEARCH_LATENCY = Histogram('search_latency_seconds', 'Search latency in seconds')

# Start Prometheus metrics server
start_http_server(8001)

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10

class SearchResult(BaseModel):
    id: str
    score: float
    metadata: dict
    relevance_score: float

@app.post("/search", response_model=List[SearchResult])
@SEARCH_LATENCY.time()
async def search(request: SearchRequest):
    SEARCH_REQUESTS.inc()
    start = time.time()
    try:
        if USE_ORCHESTRATOR:
            orchestrator = Orchestrator()
            results = await orchestrator.run_search(request.query, request.top_k)
            logger.info(f"Search query: {request.query}, top_k: {request.top_k}, results: {len(results)}")
            return results
        else:
            results = hybrid_search_func(request.query, request.top_k)
            logger.info(f"Search query (simple): {request.query}, top_k: {request.top_k}, results: {len(results)}")
            # Return dict compatible with SearchResult schema for proper serialization
            return [
                {
                    "id": r['id'],
                    "score": r['score'],
                    "metadata": r['metadata'],
                    "relevance_score": r['score'] * 10
                }
                for r in results
            ]
    except Exception as e:
        logger.error(f"Search error: {e}")
        # Fallback to simple search if orchestrator fails at runtime
        if hybrid_search_func is None:
            from src.search.hybrid_search import hybrid_search as fallback_search
        else:
            fallback_search = hybrid_search_func
        results = fallback_search(request.query, request.top_k)
        return [
            {
                "id": r['id'],
                "score": r['score'],
                "metadata": r['metadata'],
                "relevance_score": r['score'] * 10
            }
            for r in results
        ]
    finally:
        logger.info(f"Search latency: {time.time() - start:.3f}s")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    from prometheus_client import generate_latest
    return Response(generate_latest(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)