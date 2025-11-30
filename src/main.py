from fastapi import FastAPI
from pydantic import BaseModel
from src.agents.orchestrator import Orchestrator
from typing import List

app = FastAPI(title="AI-Powered Hybrid Culinary Search Engine")

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10

class SearchResult(BaseModel):
    id: str
    score: float
    metadata: dict
    relevance_score: float

@app.post("/search", response_model=List[SearchResult])
async def search(request: SearchRequest):
    try:
        orchestrator = Orchestrator()
        results = await orchestrator.run_search(request.query, request.top_k)
        return results
    except Exception as e:
        # Fallback to basic search
        from src.search.hybrid_search import hybrid_search
        results = hybrid_search(request.query, request.top_k)
        return [SearchResult(id=r['id'], score=r['score'], metadata=r['metadata'], relevance_score=r['score']*10) for r in results]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)