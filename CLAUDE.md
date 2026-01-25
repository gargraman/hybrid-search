# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-Powered Hybrid Culinary Search Engine POC - A proof-of-concept implementation of an AI-powered hybrid search engine for restaurant menus using natural language queries.

## Development Commands

### Setup
```bash
# Install dependencies (Python 3.11 or 3.13 recommended)
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Database Setup (Docker)
```bash
# Start Qdrant and PostgreSQL
docker-compose up -d

# Check services are healthy
docker-compose ps
curl http://localhost:6333/health  # Qdrant
```

### Data Generation & Ingestion
```bash
# Generate seed data (500 restaurants with geo metadata - takes ~2 min)
python scripts/generate_seed_data.py

# Qdrant + PostgreSQL ingestion (recommended - creates 2129 menu items)
PYTHONPATH=/path/to/hybrid-search POSTGRES_DSN="postgresql://postgres:postgres@localhost:5432/restaurantdb" \
  python src/ingest_qdrant_postgres.py

# Whoosh ingestion (optional, for keyword search fallback)
python src/ingest.py
```

### Run API Server
```bash
# Without LLM API keys (uses fallback hybrid search)
PYTHONPATH=/path/to/hybrid-search python src/main.py

# With LLM API keys (enables full agent pipeline)
PYTHONPATH=/path/to/hybrid-search DEEPSEEK_API_KEY="sk-..." python src/main.py
```

### Test Search
```bash
# Basic search (works without API keys)
curl -X POST "http://localhost:8000/search" -H "Content-Type: application/json" -d '{"query": "pizza", "top_k": 5}'

# Location-aware search
curl -X POST "http://localhost:8000/search" -H "Content-Type: application/json" -d '{"query": "sushi in New York", "top_k": 5}'

# Complex query (works best with agent pipeline)
curl -X POST "http://localhost:8000/search" -H "Content-Type: application/json" -d '{"query": "vegan pasta under 15 dollars", "top_k": 5}'
```

### Monitoring & Health Checks
```bash
# Health check
curl http://localhost:8000/health

# Prometheus metrics
curl http://localhost:8001/metrics | grep search

# API documentation
open http://localhost:8000/docs

# Explore available data
python explore_data.py
```

### Testing
```bash
# View comprehensive testing guide
cat TESTING.md

# Test specific queries based on available data
curl -s -X POST "http://localhost:8000/search" -H "Content-Type: application/json" \
  -d '{"query": "chicken curry", "top_k": 3}' | python3 -m json.tool
```

## Architecture

### Multi-Agent System (Custom Implementation)

**IMPORTANT**: Agents are implemented as standalone Python classes (not inheriting from BeeAI's `BaseAgent`). The original BeeAI agent pattern was refactored because BeeAI framework doesn't export `Agent` or `LLM` classes - it only provides `BaseAgent` (abstract) and specialized agents like `ReActAgent`.

The agent pipeline executes in sequence:

1. **Orchestrator** (`src/agents/orchestrator.py`): Coordinates the entire search workflow
   - Instantiates all agents and manages the execution pipeline
   - Handles graceful fallback to basic hybrid search if agents fail
   - Does NOT inherit from BeeAI - pure Python coordinator

2. **QueryParserAgent** (`src/agents/query_parser.py`): Parses natural language queries into structured filters
   - Standalone class using OpenAI client directly (not BeeAI Agent)
   - Uses DeepSeek or OpenAI LLM to extract: keywords, price_max, dietary, location
   - Returns `ParsedQuery` with structured filters or falls back to raw query as keywords
   - Uses zero-shot JSON extraction with temperature=0.1 for consistency

3. **SearchAgent** (`src/agents/search_agent.py`): Performs filtered hybrid search
   - Standalone class (not BeeAI Agent)
   - Loads LLM context from JSON restaurant files (max 20 files, 8000 chars)
   - Delegates to `search_menu_items()` from `qdrant_postgres_search.py` for semantic search
   - Applies filters: price_max, dietary (text matching), location (address matching)
   - Returns list of `SearchResult` objects with id, score, metadata

4. **QualityAgent** (`src/agents/quality_agent.py`): Validates search results
   - Standalone class using OpenAI client directly (not BeeAI Agent)
   - LLM-based filtering for relevance, completeness, and safety
   - Binary yes/no filtering per result using LLM prompt
   - Only passes results deemed safe and relevant

5. **VerificationAgent** (`src/agents/verification_agent.py`): Business rule compliance
   - Standalone class using OpenAI client directly (not BeeAI Agent)
   - LLM-based verification for factual accuracy and business rules
   - Binary yes/no verification per result
   - Final quality gate before ranking

6. **RankingAgent** (`src/agents/ranking_agent.py`): LLM-based relevance scoring
   - Standalone class using OpenAI client directly (not BeeAI Agent)
   - Prompts LLM to score each result 0-10 for relevance to query
   - Falls back to `score * 10` if LLM response parsing fails
   - Sorts results by relevance_score in descending order
   - Returns `RankedResult` objects with relevance_score field

### Search Implementation

- **Hybrid Search** (`src/search/hybrid_search.py`): Combines semantic and keyword search with Reciprocal Rank Fusion (RRF)
  - `semantic_search()`: Qdrant vector search via `search_menu_items()` from qdrant_postgres_search.py
  - `keyword_search_whoosh()`: Whoosh full-text search across text, restaurant, cuisine, category fields
  - `_merge_results()`: RRF fusion using configurable k=60 parameter (`settings.rrf_k`)
  - `filter_results()`: Post-merge filtering for price_max, dietary, location
  - Handles async event loops gracefully for compatibility

- **Qdrant + PostgreSQL Search** (`src/search/qdrant_postgres_search.py`): Core semantic search implementation
  - `search_menu_items(query_vector, top_k)`: Vector search in Qdrant, metadata join from PostgreSQL
  - Returns enriched results with full restaurant and menu item metadata
  - Merges Qdrant payloads with PostgreSQL rows for complete data
  - Type conversions for latitude, longitude, price, rating, review_count

- **Embeddings** (`src/db/qdrant.py`): sentence-transformers implementation
  - Uses `all-MiniLM-L6-v2` model (384-dimensional vectors)
  - `get_embedding(text)`: Generates embeddings for query and ingestion
  - Shared model instance for efficiency

### Data Flow

**Ingestion Pipeline:**
1. Generate seed data: `scripts/generate_seed_data.py` creates 200 restaurants with geo metadata
2. Ingest to Whoosh: `src/ingest.py` creates lexical index with full metadata (optional)
3. Ingest to Qdrant+PostgreSQL: `src/ingest_qdrant_postgres.py` (recommended)
   - Parses JSON restaurant files
   - Inserts restaurants into PostgreSQL `restaurants` table with geo fields
   - Flattens menu items into PostgreSQL `menu_items` table with `external_id` for joins
   - Generates embeddings using `all-MiniLM-L6-v2` from text blob (restaurant + category + item + description)
   - Upserts vectors to Qdrant with rich payloads (all metadata fields)

**Query Pipeline:**
1. Query received by `/search` endpoint in `main.py`
2. Orchestrator instantiates all agents
3. QueryParserAgent extracts filters (keywords, price_max, dietary, location)
4. SearchAgent performs semantic search via Qdrant+PostgreSQL, applies filters
5. QualityAgent validates results for relevance and safety (LLM-based binary filter)
6. VerificationAgent checks business rule compliance (LLM-based binary filter)
7. RankingAgent scores results 0-10 for relevance, sorts by score
8. Final ranked results returned to client

**Fallback Behavior:**
- If Orchestrator fails to initialize or errors at runtime, falls back to `hybrid_search()` from `src/search/hybrid_search.py`
- Fallback performs RRF-merged semantic + keyword search without agent processing
- Ensures service availability even without LLM access

## Technology Stack

- **Python 3.11/3.13** with FastAPI for REST API
- **Vector Database**: Qdrant v1.16.2 for semantic search (cosine similarity on 384-dim vectors)
- **Metadata Store**: PostgreSQL 17 (asyncpg) for restaurant/menu metadata, geo data, relational queries
- **Keyword Search**: Whoosh 2.7.4 (local, always available) / Elasticsearch (deprecated)
- **Embeddings**: `sentence-transformers` 5.1.2 with `all-MiniLM-L6-v2` model (384 dimensions)
- **BeeAI Framework** (v0.1.70) - Available but NOT used for search agents (see Architecture section)
- **LLMs**: DeepSeek (primary, `deepseek-chat`) / OpenAI (fallback, `gpt-3.5-turbo`) via OpenAI client
- **Monitoring**: Prometheus metrics (port 8001 + /metrics endpoint), Loguru structured logging
- **Health Checks**: `/health`, `/health/live` (liveness), `/health/ready` (readiness) endpoints
- **Data Generation**: `scripts/generate_seed_data.py` with Faker for 500 restaurants across 20 US cities

## Configuration

Environment variables in `config/settings.py`:
- `DEEPSEEK_API_KEY`: DeepSeek API key for LLM operations (required for agent pipeline)
- `OPENAI_API_KEY`: OpenAI API key (fallback LLM if DeepSeek not available)
- `whoosh_index_path`: Whoosh index directory (default: `./whoosh_index`)
- `rrf_k`: RRF k parameter for hybrid search fusion (default: 60)

Database configuration in `config/db_config.py`:
- `QDRANT_HOST`: Qdrant host (default: `localhost`)
- `QDRANT_PORT`: Qdrant port (default: `6333`)
- `QDRANT_API_KEY`: Qdrant API key (optional)
- `POSTGRES_DSN`: PostgreSQL connection string (default: `postgresql://user:password@localhost:5432/restaurantdb`)

Server configuration (via environment in `main.py`):
- `HOST`: Server host (default: `0.0.0.0`)
- `PORT`: Server port (default: `8000`)
- `RELOAD`: Enable auto-reload for development (default: `false`)
- `LOG_LEVEL`: Logging level (default: `info`)

## Monitoring & Observability

- **Prometheus Metrics**:
  - `search_requests_total`: Counter for total search requests
  - `search_latency_seconds`: Histogram for search latency tracking
  - Exposed on dedicated port 8001 and `/metrics` endpoint on main port
  - Started via `prometheus_client.start_http_server(8001)` in lifespan startup

- **Structured Logging** (Loguru):
  - Search queries logged with query text, top_k, and result count
  - Search latency logged after each request
  - Health check failures logged with component details
  - Database connection lifecycle events logged

- **Health Endpoints**:
  - `/health`: Comprehensive health check (postgres + qdrant status, returns "healthy", "degraded", or component-level status)
  - `/health/live`: Liveness probe (returns 503 if shutting down, 200 otherwise)
  - `/health/ready`: Readiness probe (checks postgres + qdrant availability, returns 503 if not ready)

- **Graceful Shutdown**:
  - `shutdown_event` for coordinated shutdown signaling
  - Database connection pool closed gracefully
  - Qdrant client closed gracefully
  - 30-second graceful shutdown timeout configured in uvicorn

- **Graceful Fallback**:
  - Orchestrator failure at import → uses `hybrid_search()` function
  - Orchestrator runtime error → catches exception and falls back to `hybrid_search()`
  - LLM API unavailable → agents raise ValueError, triggering fallback
  - Service remains available even without LLM access

## Key Features & Production Notes

- **Geo Metadata Integration**: All restaurants include city, state, latitude, longitude for location-based filtering
- **Seed Data**: 500 restaurants across 15 cities (Charlotte: 34, Miami: 30, LA: 30, etc.) with 2,129 menu items
- **Embeddings**: Uses `sentence-transformers` with `all-MiniLM-L6-v2` model for production-ready semantic search
- **LLMs Optional**: Agent pipeline requires API keys, but system gracefully falls back to hybrid search without them
- **Database Stack**: Qdrant v1.16.2 + PostgreSQL 17 + Whoosh 2.7.4 for hybrid search (ChromaDB and Elasticsearch deprecated)
- **Location-aware Search**: Filter by city/state in natural language queries (e.g., "sushi in New York")
- **Reciprocal Rank Fusion (RRF)**: Merges semantic and keyword results using RRF algorithm with k=60
- **Agent-based Quality Gates**: LLM validation at QualityAgent and VerificationAgent stages when API keys available
- **Connection Pooling**: PostgreSQL connection pool (2-10 connections) for efficient async queries
- **Uvicorn Configuration**: Timeout settings (keep-alive: 65s, graceful shutdown: 30s), concurrency limits (1000)
- **No Test Suite**: Tests directory exists but is empty; pytest dependencies available in requirements.txt
- **Kubernetes-Ready**: Liveness and readiness probes available for k8s deployments
- **Docker-Managed Volumes**: Uses Docker named volumes (not bind mounts) to avoid permission issues
- **BeeAI Framework**: Installed but NOT used for search agents (see Architecture section for details)

## Project Structure

```
src/
├── agents/          # Multi-agent system (orchestrator, query_parser, search_agent, ranking_agent, quality_agent, verification_agent)
├── models/          # Data models (restaurant.py with geo fields)
├── search/          # Core search (hybrid_search.py with location filtering, qdrant_postgres_search.py)
├── db/              # Database integrations (qdrant.py, postgres.py with geo schema)
├── utils/           # Utilities (chunking.py)
├── ingest.py        # Whoosh ingestion script (lexical)
├── ingest_qdrant_postgres.py # Qdrant + PostgreSQL ingestion script
└── main.py          # FastAPI application entry point

config/
├── settings.py      # Environment configuration
└── db_config.py     # Database connection configuration

scripts/
└── generate_seed_data.py # Generates 200 test restaurants with geo metadata

input/
├── seed/            # Generated seed data (200 restaurants)
└── restaurant*.json # Sample input files

docs/
└── geo_metadata.md  # Geo metadata integration and geocoding strategy
```

## Important Implementation Details

### Geo Metadata Architecture
- All restaurants include `city`, `state`, `latitude`, `longitude` fields
- Seed data uses deterministic coordinates for 20 major US cities
- PostgreSQL schema includes geo columns with proper indexing
- Qdrant payloads include geo metadata for semantic search results
- Whoosh documents include city/state for keyword filtering
- Location filtering works across all search backends (see `src/search/hybrid_search.py:filter_results`)
- Ready for future geocoding integration without schema changes (see `docs/geo_metadata.md`)

### Database Schema
- **restaurants** table: Includes geo fields (city, state, latitude, longitude, cuisine) with unique index on (name, address)
- **menu_items** table: References restaurants with external_id for Qdrant join queries
- PostgreSQL joins enriched with Qdrant vector search results for complete metadata retrieval

### Hybrid Search Strategy (RRF-based Fusion)

1. **Semantic Search** (`semantic_search()` in `hybrid_search.py`):
   - Calls `search_menu_items()` from `qdrant_postgres_search.py`
   - Qdrant vector search with query embedding from `all-MiniLM-L6-v2`
   - PostgreSQL join to enrich results with full restaurant + menu item metadata
   - Returns normalized scores from Qdrant cosine similarity

2. **Keyword Search** (`keyword_search_whoosh()` in `hybrid_search.py`):
   - Whoosh multifield search across: text, restaurant, cuisine, category
   - Returns Whoosh BM25 scores
   - Includes all metadata fields in results (geo, price, rating, etc.)

3. **Reciprocal Rank Fusion** (`_merge_results()` in `hybrid_search.py`):
   - Assigns 1-based ranks to results from each search method
   - Computes RRF score: `sum(1 / (k + rank))` for each item across all methods it appears in
   - Uses `settings.rrf_k = 60` as fusion parameter
   - Merges metadata from both sources (lexical metadata overwrites semantic on conflict)
   - Sorts by RRF score descending

4. **Post-Merge Filtering** (`filter_results()` in `hybrid_search.py`):
   - `price_max`: Filters by `metadata['price'] <= price_max`
   - `dietary`: Case-insensitive substring match in description or text
   - `location`: Case-insensitive substring match in address, city, or state
   - Applied after RRF merge to ensure consistent filtering across both sources

5. **Agent Pipeline Integration**:
   - SearchAgent uses semantic search only (no RRF)
   - Applies filters inline after semantic search
   - Main.py fallback uses full RRF hybrid search when agents unavailable

## Important Implementation Patterns

### Agent Implementation Pattern (Post BeeAI Refactor)

**CRITICAL**: Agents are NOT using BeeAI's `Agent` base class. They are standalone Python classes using OpenAI client directly.

All agents (QueryParser, SearchAgent, Quality, Verification, Ranking) use this pattern:

```python
from openai import OpenAI
from config.settings import settings

class MyAgent:
    """Standalone agent (not inheriting from BeeAI)."""

    def __init__(self):
        """Initialize with direct OpenAI client."""
        if settings.deepseek_api_key:
            self.client = OpenAI(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url
            )
            self.model = "deepseek-chat"
        elif settings.openai_api_key:
            self.client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url
            )
            self.model = "gpt-3.5-turbo"
        else:
            raise ValueError("No API key set for LLM")

    async def process(self, data):
        # Use self.client directly for LLM calls
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1  # All agents use 0.1 for consistency
        )
```

**Why this pattern?**
- BeeAI framework only exports `BaseAgent` (abstract class requiring implementation)
- BeeAI's specialized agents (`ReActAgent`, etc.) are not suitable for this use case
- Direct OpenAI client provides full control and simplicity
- Graceful fallback handling when LLM API unavailable

### SearchAgent Context Loading
SearchAgent loads LLM context from restaurant JSON files on initialization:
- Loads max 20 files, max 8000 chars total
- Summarizes each restaurant (name, type, location, rating, menu highlights)
- Provides this as context in agent instructions
- Used for LLM grounding during search operations

### Async Event Loop Handling
`semantic_search()` handles async event loop edge cases:
- Detects if event loop is already running
- Creates new event loop if needed for sync callers
- Properly restores original event loop after completion
- Ensures compatibility with both sync and async contexts

### Qdrant-PostgreSQL Join Pattern
`search_menu_items()` implements efficient join pattern:
1. Qdrant vector search returns external_ids and scores
2. Single PostgreSQL query fetches all metadata using `ANY($1::text[])`
3. Results merged in-memory with Qdrant payload as fallback
4. Type conversions applied (float for numeric fields, int for counts)

### Graceful Degradation
Multiple layers of fallback ensure service availability:
1. Orchestrator import failure → use `hybrid_search()` function
2. Orchestrator runtime error → catch and fallback to `hybrid_search()`
3. LLM API unavailable → ValueError raised, triggers fallback
4. Database unavailable → health endpoints report degraded status, service continues if search doesn't require DB

### Database Lifecycle Management
`main.py` lifespan context manager handles:
- PostgreSQL connection pool creation (asyncpg.create_pool with 2-10 connections)
- Qdrant client initialization with timeout=30
- Health check validation during startup
- Graceful shutdown with connection pool closure
- Shutdown event signaling for in-flight requests