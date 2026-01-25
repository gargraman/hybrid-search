from fastapi import FastAPI, Response, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from contextlib import asynccontextmanager
from prometheus_client import Counter, Histogram, start_http_server
from loguru import logger
from uuid import uuid4, UUID
import time
import signal
import asyncio
import asyncpg
from qdrant_client import QdrantClient
import urllib.parse
from config.db_config import POSTGRES_DSN, QDRANT_HOST, QDRANT_PORT, QDRANT_API_KEY

# Try to import orchestrator, but fall back to simple search if unavailable
try:
    from src.agents.orchestrator import Orchestrator
    USE_ORCHESTRATOR = True
    hybrid_search_func = None
except (ImportError, ModuleNotFoundError) as e:
    logger.warning(f"Orchestrator module not found: {e}. Using simple hybrid search.")
    USE_ORCHESTRATOR = False
    from src.search.hybrid_search import hybrid_search as hybrid_search_func
except (ValueError, RuntimeError) as e:
    logger.warning(f"Orchestrator initialization failed: {e}. Using simple hybrid search.")
    USE_ORCHESTRATOR = False
    from src.search.hybrid_search import hybrid_search as hybrid_search_func

# Try to import chat components
try:
    from src.agents.chat.chat_agent import ChatAgent
    from src.agents.chat.memory_manager import ChatSessionManager
    from src.models.conversation import (
        ChatRequest, ChatResponse, SessionCreateResponse,
        ConversationHistoryResponse, Message, MessageRole
    )
    from src.db.conversations import (
        create_tables as create_chat_tables,
        create_conversation,
        get_conversation_by_session,
        add_message as db_add_message,
        get_messages,
        delete_conversation
    )
    CHAT_AVAILABLE = True
except Exception as e:
    logger.warning(f"Chat components not available: {e}. Chat endpoints will be disabled.")
    CHAT_AVAILABLE = False
    # Define placeholder models to prevent FastAPI schema generation errors
    class ChatRequest(BaseModel):
        message: str = ""
        include_search_results: bool = False

    class ChatResponse(BaseModel):
        pass

    class SessionCreateResponse(BaseModel):
        pass

    class ConversationHistoryResponse(BaseModel):
        pass

    # Placeholder functions
    async def create_conversation(*args, **kwargs):
        raise HTTPException(status_code=503, detail="Chat feature not available")

    async def get_conversation_by_session(*args, **kwargs):
        raise HTTPException(status_code=503, detail="Chat feature not available")

    async def db_add_message(*args, **kwargs):
        raise HTTPException(status_code=503, detail="Chat feature not available")

    async def get_messages(*args, **kwargs):
        raise HTTPException(status_code=503, detail="Chat feature not available")

    async def delete_conversation(*args, **kwargs):
        raise HTTPException(status_code=503, detail="Chat feature not available")

    ChatAgent = None
    ChatSessionManager = None

# Global shutdown event
shutdown_event = asyncio.Event()


def mask_dsn(dsn: str) -> str:
    """
    Mask sensitive information in database DSN for logging.

    Args:
        dsn: Database connection string

    Returns:
        Masked DSN with credentials hidden
    """
    try:
        parsed = urllib.parse.urlparse(dsn)
        if parsed.password:
            masked = parsed._replace(
                netloc=f"{parsed.username}:***@{parsed.hostname}:{parsed.port}"
            )
            return masked.geturl()
        return dsn
    except Exception:
        return "***masked***"


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
        logger.info(f"Connecting to PostgreSQL: {mask_dsn(POSTGRES_DSN)}")
        app.state.db_pool = await asyncpg.create_pool(
            POSTGRES_DSN,
            min_size=2,
            max_size=10,
            timeout=30,
            command_timeout=60
        )
        logger.info("PostgreSQL connection pool initialized successfully")
    except (asyncpg.PostgresError, OSError) as e:
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

    # Initialize chat components
    if CHAT_AVAILABLE and app.state.db_pool:
        try:
            await create_chat_tables(app.state.db_pool)
            app.state.session_manager = ChatSessionManager(app.state.db_pool)
            logger.info("Chat components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize chat components: {e}")
            app.state.session_manager = None
    else:
        app.state.session_manager = None

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
CHAT_REQUESTS = Counter('chat_requests_total', 'Total chat requests')
CHAT_LATENCY = Histogram('chat_latency_seconds', 'Chat latency in seconds')

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Search query text")
    top_k: int = Field(default=10, ge=1, le=100, description="Maximum results to return")

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Strip whitespace from query."""
        return v.strip()


class SearchResult(BaseModel):
    id: str
    score: float
    metadata: dict
    relevance_score: float

@app.post("/search", response_model=List[SearchResult])
async def search(request: SearchRequest):
    """
    Search for menu items using hybrid search (semantic + keyword).

    Uses orchestrator with agent pipeline if available, otherwise falls back to simple hybrid search.
    """
    SEARCH_REQUESTS.inc()
    start = time.time()
    try:
        if USE_ORCHESTRATOR:
            # Pass pool and client to orchestrator
            orchestrator = Orchestrator(
                db_pool=app.state.db_pool,
                qdrant_client=app.state.qdrant_client
            )
            results = await orchestrator.run_search(request.query, request.top_k)
            logger.info(f"Search query: {request.query}, top_k: {request.top_k}, results: {len(results)}")
            return results
        else:
            # Pass pool and client to hybrid search function
            results = hybrid_search_func(
                request.query,
                request.top_k,
                qdrant_client=app.state.qdrant_client,
                db_pool=app.state.db_pool
            )
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
    except (ValueError, RuntimeError, Exception) as e:
        # Catch all exceptions including OpenAI errors and fallback to simple search
        logger.warning(f"Orchestrator search failed: {e}. Falling back to simple hybrid search.")
        # Fallback to simple search if orchestrator fails at runtime
        if hybrid_search_func is None:
            from src.search.hybrid_search import hybrid_search as fallback_search
        else:
            fallback_search = hybrid_search_func
        results = fallback_search(
            request.query,
            request.top_k,
            qdrant_client=app.state.qdrant_client,
            db_pool=app.state.db_pool
        )
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


# ==================== CHAT ENDPOINTS ====================

@app.post("/chat/sessions", response_model=SessionCreateResponse if CHAT_AVAILABLE else None)
async def create_chat_session():
    """
    Create a new chat session.

    Returns session_id and conversation_id for subsequent chat interactions.
    """
    if not CHAT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Chat feature not available")

    if not app.state.db_pool:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        session_id = str(uuid4())
        conversation = await create_conversation(app.state.db_pool, session_id)

        logger.info(f"Created chat session: {session_id}")

        return SessionCreateResponse(
            session_id=session_id,
            conversation_id=conversation.id,
            created_at=conversation.created_at
        )
    except Exception as e:
        logger.error(f"Failed to create chat session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/sessions/{session_id}/messages", response_model=ChatResponse if CHAT_AVAILABLE else None)
@CHAT_LATENCY.time()
async def send_chat_message(session_id: str, request: ChatRequest):
    """
    Send a message to an existing chat session.

    The chatbot will process the message, potentially perform searches,
    and return a conversational response.
    """
    if not CHAT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Chat feature not available")

    if not app.state.session_manager:
        raise HTTPException(status_code=503, detail="Chat session manager not available")

    CHAT_REQUESTS.inc()
    start = time.time()

    try:
        # Get or create conversation for session
        conversation = await get_conversation_by_session(app.state.db_pool, session_id)
        if not conversation:
            # Auto-create conversation for new session
            conversation = await create_conversation(app.state.db_pool, session_id)

        # Process message with ChatAgent
        agent = ChatAgent(app.state.session_manager, session_id)
        response_text, search_performed, search_results = await agent.process_message(
            request.message,
            conversation.id
        )

        # Create message object for response
        assistant_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=response_text,
            search_results=search_results
        )

        logger.info(
            f"Chat message processed: session={session_id}, "
            f"search_performed={search_performed}, "
            f"results_count={len(search_results) if search_results else 0}"
        )

        return ChatResponse(
            conversation_id=conversation.id,
            message=assistant_msg,
            search_performed=search_performed,
            search_results=search_results if request.include_search_results else None
        )

    except Exception as e:
        logger.error(f"Chat error for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        logger.info(f"Chat latency: {time.time() - start:.3f}s")


@app.get("/chat/sessions/{session_id}", response_model=ConversationHistoryResponse if CHAT_AVAILABLE else None)
async def get_chat_history(session_id: str):
    """
    Get conversation history for a chat session.
    """
    if not CHAT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Chat feature not available")

    if not app.state.db_pool:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        conversation = await get_conversation_by_session(app.state.db_pool, session_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Session not found")

        return ConversationHistoryResponse(
            conversation=conversation,
            message_count=len(conversation.messages)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/chat/sessions/{session_id}")
async def delete_chat_session(session_id: str):
    """
    Delete a chat session and all its messages.
    """
    if not CHAT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Chat feature not available")

    if not app.state.db_pool:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        conversation = await get_conversation_by_session(app.state.db_pool, session_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Session not found")

        deleted = await delete_conversation(app.state.db_pool, conversation.id)
        if deleted:
            # Clean up in-memory session
            if app.state.session_manager:
                await app.state.session_manager.cleanup_session(session_id)

            logger.info(f"Deleted chat session: {session_id}")
            return {"status": "deleted", "session_id": session_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete session")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete chat session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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