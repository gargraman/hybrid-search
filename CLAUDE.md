# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-Powered Hybrid Culinary Search Engine POC - A proof-of-concept implementation of an AI-powered hybrid search engine for restaurant menus using natural language queries.

## Development Commands

### Setup
```bash
pip install -r requirements.txt
```

### Data Ingestion
```bash
# ChromaDB + Whoosh (original)
python src/ingest.py

# Qdrant + PostgreSQL (alternative)
python src/ingest_qdrant_postgres.py
```

### Run API Server
```bash
python src/main.py
```

### Test Search
```bash
curl -X POST "http://localhost:8000/search" -H "Content-Type: application/json" -d '{"query": "vegan tacos under 15"}'
```

### Monitoring & Health Checks
```bash
# Health check
curl http://localhost:8000/health

# Prometheus metrics
curl http://localhost:8001/metrics
curl http://localhost:8000/metrics
```

## Architecture

### Multi-Agent System (BeeAI Framework)
- **Orchestrator** (`src/agents/orchestrator.py`): Coordinates the entire search workflow
- **QueryParserAgent** (`src/agents/query_parser.py`): Parses natural language queries into structured filters (keywords, price, dietary requirements, location)
- **SearchAgent** (`src/agents/search_agent.py`): Performs filtered hybrid search combining semantic and keyword retrieval
- **RankingAgent** (`src/agents/ranking_agent.py`): Applies LLM-based relevance scoring to results
- **QualityAgent** (`src/agents/quality_agent.py`): Validates and filters search results for relevance, completeness, and safety
- **VerificationAgent** (`src/agents/verification_agent.py`): Checks search results for factual accuracy and compliance with business rules

### Search Implementation
- **Hybrid Search** (`src/search/hybrid_search.py`): Combines semantic (ChromaDB) and keyword (Whoosh/Elasticsearch) search with filtering capabilities
- **Qdrant + PostgreSQL Search** (`src/search/qdrant_postgres_search.py`): Alternative search implementation using Qdrant for vectors and PostgreSQL for metadata
- **Semantic Search**: ChromaDB with deterministic hash-based embeddings (POC limitation) or Qdrant with proper embeddings
- **Keyword Search**: Whoosh (local) and Elasticsearch (optional) with graceful fallbacks

### Data Flow
1. JSON restaurant data ingestion → flattened menu items
2. Indexing in multiple backends (ChromaDB/Qdrant for vectors, Whoosh/PostgreSQL for keywords/metadata)
3. Query parsing with LLMs → structured filters
4. Hybrid search with filtering → combined results
5. Quality validation and verification checks → filtered results
6. LLM-based relevance ranking → final scored results

## Technology Stack

- **Python 3.13** with FastAPI for REST API
- **Vector Databases**: ChromaDB (original) / Qdrant (alternative) for vector search
- **Keyword/Metadata Stores**: Whoosh (local) / Elasticsearch (optional) / PostgreSQL (alternative)
- **Embeddings**: Deterministic hash-based (POC) or sentence-transformers (production-ready)
- **BeeAI Framework** for multi-agent architecture
- **LLMs**: DeepSeek (primary) / OpenAI (fallback) for query parsing and ranking
- **Monitoring**: Prometheus metrics, Loguru logging, health checks

## Configuration

Environment variables in `config/settings.py`:
- `DEEPSEEK_API_KEY`: DeepSeek API key for LLM operations
- `OPENAI_API_KEY`: OpenAI API key (fallback LLM)
- `ES_HOST`, `ES_PORT`, `ES_SCHEME`: Elasticsearch configuration (optional)

Database configuration in `config/db_config.py`:
- `QDRANT_HOST`, `QDRANT_PORT`, `QDRANT_API_KEY`: Qdrant vector database configuration
- `POSTGRES_DSN`: PostgreSQL database connection string

## Monitoring & Observability

- **Prometheus Metrics**: Search request counts and latency histograms exposed on port 8001
- **Structured Logging**: Loguru-based logging with search query details and performance metrics
- **Health Endpoint**: `/health` for service status monitoring
- **Graceful Fallback**: Automatic fallback to basic hybrid search when agents fail
- **Error Tracking**: Comprehensive error logging with request context

## Key Limitations & Production Notes

- **Embeddings**: Currently using deterministic hash-based embeddings due to SSL/network constraints. Modern sentence-transformers are now available in requirements.txt for production use
- **LLMs**: Requires API keys for DeepSeek or OpenAI to enable query parsing and ranking
- **SSL Issues**: Environment has SSL verification issues preventing model downloads
- **Database Options**: Two search architectures available - choose ChromaDB+Whoosh for simplicity or Qdrant+PostgreSQL for production scalability
- **No Test Suite**: Tests directory exists but is empty
- **Monitoring**: Basic Prometheus metrics implemented; consider adding agent-level metrics for production

## Project Structure

```
src/
├── agents/          # Multi-agent system components (orchestrator, query_parser, search_agent, ranking_agent, quality_agent, verification_agent)
├── models/          # Data models (restaurant.py)
├── search/          # Core search functionality (hybrid_search.py, qdrant_postgres_search.py)
├── db/              # Database integrations (qdrant.py, postgres.py)
├── ingest.py        # ChromaDB + Whoosh ingestion script
├── ingest_qdrant_postgres.py # Qdrant + PostgreSQL ingestion script
└── main.py          # FastAPI application entry point

config/
├── settings.py      # Environment configuration
└── db_config.py     # Database connection configuration

input/               # Sample data files
docs/                # Project documentation
```