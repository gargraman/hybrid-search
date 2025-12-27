from fastapi import FastAPI, Response
from pydantic import BaseModel
from typing import List
from contextlib import asynccontextmanager
from prometheus_client import Counter, Histogram, start_http_server
from loguru import logger
import time
import signal
import asyncio
import asyncpg
from qdrant_client import QdrantClient
from config.db_config import POSTGRES_DSN, QDRANT_HOST, QDRANT_PORT, QDRANT_API_KEY

# Try to import orchestrator, but fall back to simple search if unavailable
try:
    from src.agents.orchestrator import Orchestrator
    USE_ORCHESTRATOR = True
    hybrid_search_func = None
except Exception as e:
    logger.warning(f"Orchestrator not available: {e}. Using simple hybrid search.")
    USE_ORCHESTRATOR = False
    from src.search.hybrid_search import hybrid_search as hybrid_search_func

# Global shutdown event
shutdown_event = asyncio.Event()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle with graceful startup and shutdown.

    Startup:
    - Initialize database connection pool
    - Initialize Qdrant client
    - Start Prometheus metrics server

    Shutdown:
    - Close database connections gracefully
    - Close Qdrant client
    - Wait for in-flight requests to complete
    """
    # ========== STARTUP ==========
    logger.info("Starting AI-Powered Hybrid Culinary Search Engine...")

    # Initialize PostgreSQL connection pool
    try:
        logger.info(f"Connecting to PostgreSQL: {POSTGRES_DSN.split('@')[1] if '@' in POSTGRES_DSN else POSTGRES_DSN}")
        app.state.db_pool = await asyncpg.create_pool(
            POSTGRES_DSN,
            min_size=2,
            max_size=10,
            timeout=30,
            command_timeout=60
        )
        logger.info("PostgreSQL connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL connection pool: {e}")
        app.state.db_pool = None

    # Initialize Qdrant client
    try:
        logger.info(f"Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}")
        app.state.qdrant_client = QdrantClient(
            host=QDRANT_HOST,
            port=QDRANT_PORT,
            api_key=QDRANT_API_KEY,
            timeout=30
        )
        # Test connection
        collections = app.state.qdrant_client.get_collections()
        logger.info(f"Qdrant client initialized successfully. Collections: {len(collections.collections)}")
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant client: {e}")
        app.state.qdrant_client = None

    # Start Prometheus metrics server
    try:
        start_http_server(8001)
        logger.info("Prometheus metrics server started on port 8001")
    except Exception as e:
        logger.warning(f"Failed to start Prometheus metrics server: {e}")

    logger.info("Application startup complete. Ready to serve requests.")

    yield

    # ========== SHUTDOWN ==========
    logger.info("Initiating graceful shutdown...")
    shutdown_event.set()

    # Wait for in-flight requests to complete (max 30 seconds)
    logger.info("Waiting for in-flight requests to complete...")
    await asyncio.sleep(2)  # Give a brief moment for requests to finish

    # Close database connection pool
    if app.state.db_pool:
        try:
            logger.info("Closing PostgreSQL connection pool...")
            await app.state.db_pool.close()
            logger.info("PostgreSQL connection pool closed successfully")
        except Exception as e:
            logger.error(f"Error closing PostgreSQL connection pool: {e}")

    # Close Qdrant client
    if app.state.qdrant_client:
        try:
            logger.info("Closing Qdrant client...")
            app.state.qdrant_client.close()
            logger.info("Qdrant client closed successfully")
        except Exception as e:
            logger.error(f"Error closing Qdrant client: {e}")

    logger.info("Graceful shutdown complete. Goodbye!")

app = FastAPI(
    title="AI-Powered Hybrid Culinary Search Engine",
    lifespan=lifespan,
    version="1.0.0",
    description="Hybrid search engine combining semantic and keyword search for restaurant menus"
)

# Metrics
SEARCH_REQUESTS = Counter('search_requests_total', 'Total search requests')
SEARCH_LATENCY = Histogram('search_latency_seconds', 'Search latency in seconds')

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
async def health():
    """
    Comprehensive health check endpoint.
    Returns overall health status and component statuses.
    """
    health_status = {
        "status": "healthy",
        "components": {
            "postgres": "unknown",
            "qdrant": "unknown"
        }
    }

    # Check PostgreSQL
    if app.state.db_pool:
        try:
            async with app.state.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            health_status["components"]["postgres"] = "healthy"
        except Exception as e:
            logger.warning(f"PostgreSQL health check failed: {e}")
            health_status["components"]["postgres"] = "unhealthy"
            health_status["status"] = "degraded"
    else:
        health_status["components"]["postgres"] = "not_initialized"
        health_status["status"] = "degraded"

    # Check Qdrant
    if app.state.qdrant_client:
        try:
            app.state.qdrant_client.get_collections()
            health_status["components"]["qdrant"] = "healthy"
        except Exception as e:
            logger.warning(f"Qdrant health check failed: {e}")
            health_status["components"]["qdrant"] = "unhealthy"
            health_status["status"] = "degraded"
    else:
        health_status["components"]["qdrant"] = "not_initialized"
        health_status["status"] = "degraded"

    return health_status

@app.get("/health/live")
def liveness():
    """
    Liveness probe - checks if the application is running.
    Used by Kubernetes to determine if the pod should be restarted.
    """
    if shutdown_event.is_set():
        return Response(
            content='{"status": "shutting_down"}',
            status_code=503,
            media_type="application/json"
        )
    return {"status": "alive"}

@app.get("/health/ready")
async def readiness():
    """
    Readiness probe - checks if the application is ready to serve traffic.
    Used by Kubernetes to determine if the pod should receive traffic.
    """
    if shutdown_event.is_set():
        return Response(
            content='{"status": "shutting_down"}',
            status_code=503,
            media_type="application/json"
        )

    # Check critical dependencies
    postgres_ready = False
    qdrant_ready = False

    # Check PostgreSQL
    if app.state.db_pool:
        try:
            async with app.state.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            postgres_ready = True
        except Exception as e:
            logger.warning(f"PostgreSQL readiness check failed: {e}")

    # Check Qdrant
    if app.state.qdrant_client:
        try:
            app.state.qdrant_client.get_collections()
            qdrant_ready = True
        except Exception as e:
            logger.warning(f"Qdrant readiness check failed: {e}")

    if postgres_ready and qdrant_ready:
        return {
            "status": "ready",
            "postgres": "ready",
            "qdrant": "ready"
        }
    else:
        return Response(
            content=f'{{"status": "not_ready", "postgres": "{postgres_ready}", "qdrant": "{qdrant_ready}"}}',
            status_code=503,
            media_type="application/json"
        )

@app.get("/metrics")
def metrics():
    from prometheus_client import generate_latest
    return Response(generate_latest(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    import os

    # Configuration from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "info").lower()

    logger.info(f"Starting server on {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        timeout_keep_alive=65,  # Keep-alive timeout
        timeout_graceful_shutdown=30,  # Graceful shutdown timeout
        limit_concurrency=1000,  # Max concurrent connections
        limit_max_requests=10000,  # Restart worker after N requests (prevents memory leaks)
    )