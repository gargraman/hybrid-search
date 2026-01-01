# AI-Powered Hybrid Culinary Search Engine POC

A production-ready proof-of-concept for an AI-powered hybrid search engine that combines semantic vector search with traditional keyword search for restaurant menu discovery. Built with a multi-agent architecture using BeeAI framework, offering natural language query understanding and intelligent result ranking.

## Key Features

- **Hybrid Search with RRF Fusion**: Combines semantic (Qdrant vector search) + keyword (Whoosh BM25) using Reciprocal Rank Fusion algorithm (k=60)
- **Multi-Agent Orchestration** (BeeAI Framework v0.1.70):
  - **QueryParserAgent**: LLM-powered query parsing extracting keywords, price, dietary, and location filters
  - **SearchAgent**: Semantic search with LLM context from restaurant data
  - **QualityAgent**: LLM-based result validation for relevance and safety
  - **VerificationAgent**: Business rule compliance checking
  - **RankingAgent**: LLM-powered relevance scoring (0-10 scale)
  - **Orchestrator**: Coordinates the full 6-stage pipeline
- **Production-Grade Embeddings**: `sentence-transformers` with `all-MiniLM-L6-v2` model (384-dimensional vectors)
- **Scalable Database Architecture**: Qdrant for vector search + PostgreSQL for metadata with efficient join pattern
- **Location-Aware Search**: Filter by city/state in natural language queries
- **Comprehensive Monitoring**: Prometheus metrics, health/liveness/readiness endpoints, structured logging
- **Graceful Degradation**: Automatic fallback to basic hybrid search when LLM agents unavailable
- **RESTful API**: FastAPI with async endpoints, OpenAPI docs, CORS support
- **Kubernetes-Ready**: Liveness and readiness probes for container orchestration

## Prerequisites

- **Python 3.13+** (tested with 3.13)
- **Docker** and **Docker Compose** (for Qdrant and PostgreSQL)
- **LLM API Access**: DeepSeek API key (recommended) or OpenAI API key
- **8GB+ RAM** (for sentence-transformers model and databases)
- **2GB+ disk space** (for models, indexes, and data)

## Quick Start

```bash
# 1. Clone and install dependencies
git clone <repository-url>
cd hybrid-search
pip install -r requirements.txt

# 2. Start databases (Qdrant + PostgreSQL)
docker-compose up -d

# 3. Set environment variables
export DEEPSEEK_API_KEY="your-deepseek-api-key"
export POSTGRES_DSN="postgresql://user:password@localhost:5432/restaurantdb"
export QDRANT_HOST="localhost"
export QDRANT_PORT="6333"

# 4. Generate seed data (200 restaurants across 20 US cities)
python scripts/generate_seed_data.py

# 5. Ingest data to Qdrant + PostgreSQL (recommended)
python src/ingest_qdrant_postgres.py

# 6. (Optional) Ingest data to Whoosh for keyword search
python src/ingest.py

# 7. Start the API server
python src/main.py

# 8. Test the search endpoint
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "vegan tacos under 15", "top_k": 10}'
```

## Detailed Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Key dependencies installed:
- `fastapi` - REST API framework
- `qdrant-client>=1.7.0` - Vector database client
- `asyncpg` - PostgreSQL async driver
- `sentence-transformers==5.1.2` - Embedding generation
- `Whoosh==2.7.4` - Keyword search engine
- `beeai-framework==0.1.70` - Multi-agent orchestration
- `openai==2.8.1` - LLM client for DeepSeek/OpenAI
- `prometheus-client==0.21.1` - Metrics
- `loguru==0.7.2` - Structured logging

### 2. Configure Environment Variables

Create a `.env` file or export variables:

```bash
# LLM Configuration (at least one required for agent pipeline)
export DEEPSEEK_API_KEY="sk-..."           # Primary LLM (recommended)
export OPENAI_API_KEY="sk-..."             # Fallback LLM

# Database Configuration
export POSTGRES_DSN="postgresql://user:password@localhost:5432/restaurantdb"
export QDRANT_HOST="localhost"
export QDRANT_PORT="6333"
export QDRANT_API_KEY=""                   # Optional, leave empty for local

# Server Configuration (optional)
export HOST="0.0.0.0"
export PORT="8000"
export LOG_LEVEL="info"
export RELOAD="false"                      # Set to "true" for development
```

### 3. Start Databases with Docker Compose

If you have a `docker-compose.yml`:
```bash
docker-compose up -d
```

Or start manually:

**Qdrant:**
```bash
docker run -p 6333:6333 -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage:z \
  qdrant/qdrant
```

**PostgreSQL:**
```bash
docker run -p 5432:5432 \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=restaurantdb \
  -v $(pwd)/postgres_data:/var/lib/postgresql/data \
  postgres:15
```

### 4. Generate and Ingest Data

**Generate seed data** (200 restaurants with geo metadata):
```bash
python scripts/generate_seed_data.py
```
- Creates `input/seed/*.json` files
- Includes realistic restaurant data with menus, ratings, and locations
- 20 major US cities represented

**Ingest to Qdrant + PostgreSQL** (recommended):
```bash
python src/ingest_qdrant_postgres.py
```
- Creates PostgreSQL tables (`restaurants`, `menu_items`)
- Generates 384-dim embeddings using `all-MiniLM-L6-v2`
- Uploads vectors to Qdrant with rich payloads
- ~1-2 minutes for 200 restaurants

**Ingest to Whoosh** (optional, for keyword search):
```bash
python src/ingest.py
```
- Creates local Whoosh index at `./whoosh_index`
- Indexes all menu items with full metadata

### 5. Run the API Server

```bash
python src/main.py
```

Server starts on `http://localhost:8000` with:
- API endpoints at `/search`
- OpenAPI docs at `/docs`
- Health checks at `/health`, `/health/live`, `/health/ready`
- Prometheus metrics at `/metrics` and port `8001`

### 6. Verify Installation

**Check health:**
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "components": {
    "postgres": "healthy",
    "qdrant": "healthy"
  }
}
```

**Test search:**
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "vegan tacos under 15",
    "top_k": 5
  }'
```

**View API documentation:**
Open `http://localhost:8000/docs` in your browser

**Check Prometheus metrics:**
```bash
curl http://localhost:8001/metrics
curl http://localhost:8000/metrics
```

## API Endpoints

### POST /search
Search for menu items using natural language queries.

**Request Body:**
```json
{
  "query": "vegan tacos under 15",
  "top_k": 10
}
```

**Response:**
```json
[
  {
    "id": "TacoHaven_Appetizers_VeganTacos",
    "score": 0.89,
    "metadata": {
      "name": "Vegan Tacos",
      "description": "Plant-based tacos with avocado and salsa",
      "price": 12.99,
      "category": "Appetizers",
      "restaurant": "Taco Haven",
      "address": "123 Main St",
      "city": "San Francisco",
      "state": "CA",
      "cuisine": "mexican"
    },
    "relevance_score": 9.2
  }
]
```

**Supported Query Patterns:**
- Price filtering: "tacos under 15", "pizza less than 20"
- Dietary restrictions: "vegan pasta", "gluten-free dessert"
- Location: "pizza in San Francisco", "sushi in New York"
- Combined: "vegan tacos in SF under 15"

### GET /health
Comprehensive health check with component status.

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "postgres": "healthy",
    "qdrant": "healthy"
  }
}
```

### GET /health/live
Liveness probe for Kubernetes (checks if application is running).

### GET /health/ready
Readiness probe for Kubernetes (checks if application is ready to serve traffic).

### GET /metrics
Prometheus metrics endpoint.

**Metrics exposed:**
- `search_requests_total`: Total number of search requests
- `search_latency_seconds`: Histogram of search latency

### GET /docs
Interactive OpenAPI (Swagger) documentation.

## Architecture Overview

### Data Ingestion Pipeline

1. **Seed Data Generation** (`scripts/generate_seed_data.py`):
   - Generates 200 realistic restaurants using Faker library
   - Includes geo metadata (city, state, latitude, longitude) for 20 major US cities
   - Creates JSON files in `input/seed/` directory

2. **Vector + Metadata Ingestion** (`src/ingest_qdrant_postgres.py`):
   - Parses restaurant JSON files
   - Inserts restaurants into PostgreSQL `restaurants` table
   - Flattens menu items into PostgreSQL `menu_items` table with `external_id`
   - Generates 384-dim embeddings using `all-MiniLM-L6-v2` from text blob
   - Upserts vectors to Qdrant with rich payloads (all metadata)

3. **Keyword Index** (`src/ingest.py`, optional):
   - Creates Whoosh BM25 index with full metadata
   - Enables lexical search fallback

### Query Pipeline (Agent-Based)

1. **Request Handler** (`main.py:/search`):
   - Receives search request
   - Instantiates Orchestrator
   - Falls back to basic hybrid search if agents fail

2. **Query Parsing** (QueryParserAgent):
   - LLM extracts structured filters: keywords, price_max, dietary, location
   - Uses DeepSeek (primary) or OpenAI (fallback)
   - Temperature=0.1 for consistent parsing

3. **Semantic Search** (SearchAgent):
   - Loads LLM context from restaurant JSON files (max 20 files, 8000 chars)
   - Generates query embedding via `all-MiniLM-L6-v2`
   - Queries Qdrant vector database
   - Joins with PostgreSQL for full metadata
   - Applies filters: price, dietary, location

4. **Quality Validation** (QualityAgent):
   - LLM validates each result for relevance and safety
   - Binary yes/no filtering per result

5. **Business Rule Verification** (VerificationAgent):
   - LLM checks compliance with business rules
   - Binary yes/no verification per result

6. **Relevance Ranking** (RankingAgent):
   - LLM scores each result 0-10 for relevance to query
   - Sorts by relevance score descending
   - Returns final ranked results

### Hybrid Search (Fallback Mode)

When agents are unavailable, the system uses RRF-based hybrid search:

1. **Semantic Search**: Qdrant vector search → top_k*2 results
2. **Keyword Search**: Whoosh BM25 search → top_k*2 results
3. **RRF Fusion**: Merge using Reciprocal Rank Fusion (k=60)
4. **Filtering**: Apply price, dietary, location filters
5. **Return**: Top_k results with normalized scores

### Database Schema

**restaurants** table:
- `id`: Primary key (serial)
- `name`, `address`, `city`, `state`: Location fields
- `latitude`, `longitude`: Geographic coordinates
- `cuisine`, `rating`, `review_count`: Restaurant metadata
- `on_time_rate`, `delivery_fee`, `delivery_minimum`: Service metadata
- Unique index on `(name, address)`

**menu_items** table:
- `id`: Primary key (serial)
- `restaurant_id`: Foreign key to restaurants
- `external_id`: Unique identifier for Qdrant join (e.g., "RestaurantName_Category_ItemName")
- `category`, `name`, `description`, `price`: Menu item fields

**Qdrant collection** (`menu_items`):
- 384-dimensional vectors (cosine similarity)
- Payloads include all restaurant + menu item metadata
- External ID matches `menu_items.external_id`

## Technology Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.13 | Application runtime |
| API Framework | FastAPI | Latest | REST API, async endpoints |
| Vector Database | Qdrant | Latest | Semantic search, cosine similarity |
| Relational DB | PostgreSQL | 15+ | Metadata storage, relational queries |
| Async DB Driver | asyncpg | Latest | PostgreSQL connection pooling |
| Embeddings | sentence-transformers | 5.1.2 | `all-MiniLM-L6-v2` model |
| Keyword Search | Whoosh | 2.7.4 | BM25 lexical search |
| Multi-Agent Framework | BeeAI | 0.1.70 | Agent orchestration |
| LLM Client | openai | 2.8.1 | DeepSeek/OpenAI API |
| Metrics | prometheus-client | 0.21.1 | Monitoring, observability |
| Logging | loguru | 0.7.2 | Structured logging |
| Testing | pytest | 8.3.4 | Unit/integration tests (framework ready) |

## Development Workflow

### Running Tests

```bash
# Install test dependencies (already in requirements.txt)
pip install pytest pytest-asyncio pytest-cov pytest-mock pytest-timeout

# Run all tests (when implemented)
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_search.py -v
```

Note: Test directory exists but tests are not yet implemented.

### Local Development with Auto-Reload

```bash
export RELOAD="true"
python src/main.py
```

Or use uvicorn directly:
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Adding New Agents

1. Create agent class in `src/agents/` inheriting from `beeai_framework.Agent`
2. Implement required methods (typically async methods for processing)
3. Add agent to Orchestrator pipeline in `src/agents/orchestrator.py`
4. Update agent initialization with LLM client pattern
5. Add agent-specific instructions in agent constructor

Example agent template:
```python
from beeai_framework import Agent
from openai import OpenAI
from config.settings import settings

class MyAgent(Agent):
    def __init__(self):
        if settings.deepseek_api_key:
            self.client = OpenAI(api_key=settings.deepseek_api_key,
                                base_url=settings.deepseek_base_url)
            self.model = "deepseek-chat"
        elif settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key,
                                base_url=settings.openai_base_url)
            self.model = "gpt-3.5-turbo"
        else:
            raise ValueError("No API key set for LLM")
        super().__init__(instructions="Your agent instructions here")

    async def process(self, data):
        # Agent logic here
        pass
```

### Modifying Search Logic

- **Semantic search**: Edit `src/search/qdrant_postgres_search.py:search_menu_items()`
- **Keyword search**: Edit `src/search/hybrid_search.py:keyword_search_whoosh()`
- **RRF fusion**: Edit `src/search/hybrid_search.py:_merge_results()`
- **Filters**: Edit `src/search/hybrid_search.py:filter_results()`
- **RRF k parameter**: Modify `config/settings.py:rrf_k` (default: 60)

### Adding New Endpoints

1. Add endpoint function in `src/main.py`
2. Use FastAPI decorators (`@app.post`, `@app.get`, etc.)
3. Add Pydantic models for request/response validation
4. Include OpenAPI documentation in docstrings
5. Add metrics/logging as needed

## Troubleshooting

### LLM Agents Not Working

**Symptom:** API returns basic results without agent processing

**Solutions:**
1. Check API keys are set: `echo $DEEPSEEK_API_KEY`
2. Verify LLM API connectivity: Test API endpoint manually
3. Check logs for agent import errors: Look for "Orchestrator not available" message
4. System automatically falls back to basic hybrid search (this is expected behavior)

### Database Connection Errors

**PostgreSQL:**
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check connection string
echo $POSTGRES_DSN

# Test connection
psql $POSTGRES_DSN -c "SELECT 1"
```

**Qdrant:**
```bash
# Check if Qdrant is running
curl http://localhost:6333/collections

# Check health
curl http://localhost:6333/healthz
```

### Embedding Model Download Issues

**Symptom:** Slow first startup or SSL errors

**Solutions:**
1. Pre-download model: `python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"`
2. Set HuggingFace cache: `export TRANSFORMERS_CACHE=/path/to/cache`
3. Use offline mode if model is cached: `export TRANSFORMERS_OFFLINE=1`

### Search Returns No Results

**Checks:**
1. Verify data ingestion completed: Check PostgreSQL tables and Qdrant collection
2. Check Whoosh index exists: `ls -la whoosh_index/`
3. Verify embeddings are generated: Query Qdrant collection point count
4. Check filter logic: Overly restrictive filters may exclude all results
5. Review logs: `grep "Search" logs or check Loguru output`

### Performance Issues

**Optimization strategies:**
1. **Increase PostgreSQL connection pool**: Modify `main.py:lifespan` (current: 2-10)
2. **Reduce top_k**: Lower the number of results fetched from each search backend
3. **Disable agent pipeline**: Remove LLM API keys to use faster fallback search
4. **Tune RRF k parameter**: Adjust `settings.rrf_k` (lower = prioritize higher ranks)
5. **Add database indexes**: Create indexes on frequently queried PostgreSQL columns
6. **Cache embeddings**: Implement LRU cache for frequently searched queries

## Production Deployment

### Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 8001
CMD ["python", "src/main.py"]
```

Build and run:
```bash
docker build -t hybrid-search .
docker run -p 8000:8000 -p 8001:8001 \
  -e DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY \
  -e POSTGRES_DSN=$POSTGRES_DSN \
  -e QDRANT_HOST=$QDRANT_HOST \
  hybrid-search
```

### Kubernetes Deployment

Use provided health endpoints:
- Liveness probe: `/health/live`
- Readiness probe: `/health/ready`

Example deployment manifest:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hybrid-search
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: hybrid-search
        image: hybrid-search:latest
        ports:
        - containerPort: 8000
        - containerPort: 8001
        env:
        - name: DEEPSEEK_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-secrets
              key: deepseek-key
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Environment-Specific Configuration

**Development:**
- `RELOAD=true` for auto-reload
- `LOG_LEVEL=debug` for verbose logging
- Use local Docker databases

**Staging:**
- `RELOAD=false`
- `LOG_LEVEL=info`
- Use managed databases (RDS, Qdrant Cloud)
- Enable Prometheus scraping

**Production:**
- `LOG_LEVEL=warning`
- Connection pooling tuned for load
- Multiple replicas behind load balancer
- Monitoring and alerting configured
- Secrets managed via vault/secrets manager

## Project Structure

```
hybrid-search/
├── src/
│   ├── agents/              # Multi-agent system
│   │   ├── orchestrator.py  # Agent coordinator
│   │   ├── query_parser.py  # Query parsing agent
│   │   ├── search_agent.py  # Search agent
│   │   ├── ranking_agent.py # Ranking agent
│   │   ├── quality_agent.py # Quality validation agent
│   │   └── verification_agent.py # Verification agent
│   ├── db/                  # Database clients
│   │   ├── qdrant.py        # Qdrant client and operations
│   │   └── postgres.py      # PostgreSQL operations
│   ├── models/              # Data models
│   │   └── restaurant.py    # Pydantic models
│   ├── search/              # Search implementations
│   │   ├── hybrid_search.py # RRF hybrid search
│   │   └── qdrant_postgres_search.py # Semantic search
│   ├── utils/               # Utilities
│   │   └── chunking.py      # Text chunking
│   ├── ingest.py            # Whoosh ingestion
│   ├── ingest_qdrant_postgres.py # Vector ingestion
│   └── main.py              # FastAPI application
├── config/
│   ├── settings.py          # Environment configuration
│   └── db_config.py         # Database configuration
├── scripts/
│   └── generate_seed_data.py # Test data generation
├── input/
│   └── seed/                # Generated seed data
├── tests/                   # Test directory (empty)
├── docs/
│   └── geo_metadata.md      # Geo integration docs
├── requirements.txt         # Python dependencies
├── CLAUDE.md                # Claude Code guidance
└── README.md                # This file
```

## Contributing

This is a proof-of-concept project. Contributions welcome for:
- Implementing test suite (pytest framework ready)
- Adding new agents for specialized tasks
- Performance optimizations
- Additional search backends
- Enhanced monitoring and observability
- Documentation improvements

## License

See LICENSE file for details.

---

**For detailed implementation patterns and architecture decisions, see CLAUDE.md**